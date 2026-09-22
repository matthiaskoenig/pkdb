"""FastAPI factory with explicit services and independent request sessions."""

import json
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from pkdb.api import (
    accounts,
    admin_roles,
    admin_users,
    exports,
    invitations,
    legacy_uploads,
    management,
    media,
    mfa,
    profiles,
    providers,
    reads,
    staging,
)
from pkdb.api.credentials import install_browser_security
from pkdb.api.errors import account_validation_error
from pkdb.api.limits import UploadLimits
from pkdb.api.quotas import RequestQuotas
from pkdb.config import Settings
from pkdb.db.read import publication_state, read_study
from pkdb.db.session import make_session_factory
from pkdb.files.store import FileStore, FileTooLarge
from pkdb.mcp.server import create_mcp
from pkdb.schemas.security import Principal
from pkdb.schemas.source import SourceBundle
from pkdb.schemas.validation import StudyValidationError, fail
from pkdb.services.accounts import AccountService
from pkdb.services.admin_users import AdminUserService
from pkdb.services.analysis import AnalysisService
from pkdb.services.authentication import AuthenticationFailed, authenticate_token
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import CredentialService, authenticate_session
from pkdb.services.drafts import DraftService
from pkdb.services.exports import ExportService
from pkdb.services.ingestion import IngestionService, PublicationConflict
from pkdb.services.invitations import InvitationService
from pkdb.services.mailer import SMTPMailer
from pkdb.services.mfa import MfaService
from pkdb.services.profiles import ProfileService
from pkdb.services.providers import ProviderService
from pkdb.services.queries import QueryService
from pkdb.services.quotas import QuotaService

log = logging.getLogger(__name__)
SCHEMA_REVISION = "p775privacy01"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    session_factory = make_session_factory(settings.database_url)
    file_store = FileStore(
        settings.file_root, session_factory, settings.upload_max_bytes
    )
    ingestion = IngestionService(session_factory, file_store, settings)

    queries = QueryService(session_factory)
    mcp = create_mcp(ingestion, queries, file_store, session_factory)
    mcp_app = mcp.http_app(path="/", json_response=True, stateless_http=False)

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with mcp_app.lifespan(app):
                yield
        finally:
            session_factory.kw["bind"].dispose()

    app = FastAPI(title="PK-DB", version="0.10.0", lifespan=lifespan)
    app.add_exception_handler(RequestValidationError, account_validation_error)
    app.state.accounts = AccountService(session_factory, SMTPMailer(settings))
    app.state.invitations = InvitationService(
        session_factory, app.state.accounts.mailer
    )
    app.include_router(invitations.router)
    app.state.credentials = CredentialService(session_factory, app.state.accounts)
    app.state.profiles = ProfileService(session_factory, settings.file_root)
    app.state.quotas = QuotaService(session_factory, settings)
    app.state.providers = ProviderService(
        session_factory,
        app.state.accounts,
        origin=settings.browser_origin,
        providers={
            name: {
                "client_id": getattr(settings, f"{name}_client_id"),
                "client_secret": getattr(
                    settings, f"{name}_client_secret"
                ).get_secret_value()
                if getattr(settings, f"{name}_client_secret")
                else "",
            }
            for name in ("github", "orcid")
        },
    )
    app.state.mfa = MfaService(
        session_factory,
        app.state.accounts,
        settings.mfa_encryption_key.get_secret_value()
        if settings.mfa_encryption_key
        else None,
    )
    install_browser_security(
        app, origin=settings.browser_origin, secure=settings.secure_cookies
    )
    app.include_router(profiles.router)
    app.include_router(mfa.router)
    app.include_router(management.router)
    app.include_router(management.account_router)
    app.include_router(providers.router)
    if settings.rate_limits_enabled:
        app.add_middleware(RequestQuotas)
    app.state.admin_users = AdminUserService(session_factory)
    app.state.file_store = file_store
    app.state.ingestion = ingestion
    app.state.queries = queries
    app.state.analysis = AnalysisService(session_factory)
    app.state.exports = ExportService(session_factory, queries, settings)
    app.state.drafts = DraftService(session_factory, ingestion)
    app.state.session_factory = session_factory
    app.add_middleware(
        UploadLimits,
        max_bytes=settings.upload_max_bytes,
        concurrency=settings.upload_concurrency,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        expose_headers=["Content-Disposition", "Retry-After"],
    )

    @app.exception_handler(StudyValidationError)
    async def validation_error(request, error):
        return JSONResponse(
            {**error.report.model_dump(mode="json"), "valid": False}, status_code=422
        )

    @app.exception_handler(AuthenticationFailed)
    async def authentication_error(request, error):
        return JSONResponse(
            {"detail": "Invalid or missing credentials"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationDenied)
    async def authorization_error(request, error):
        return JSONResponse({"detail": "Action not permitted"}, status_code=403)

    @app.exception_handler(PublicationConflict)
    async def conflict_error(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @app.exception_handler(FileTooLarge)
    async def size_error(request, error):
        return JSONResponse({"detail": str(error)}, status_code=413)

    @app.exception_handler(Exception)
    async def internal_error(request, error):
        request_id = uuid4().hex
        log.error("Request failed: %s (%s)", request_id, type(error).__name__)
        return JSONResponse(
            {"detail": "Internal server error", "request_id": request_id},
            status_code=500,
        )

    def principal(request: Request, required: bool = True) -> Principal:
        header = request.headers.get("Authorization", "")
        if not header:
            cookie = request.cookies.get(app.state.session_cookie_name)
            if cookie:
                with session_factory.begin() as session:
                    return authenticate_session(cookie, session)
            if not required:
                return Principal()
            raise AuthenticationFailed()
        scheme, _, raw = header.partition(" ")
        if scheme.lower() not in {"token", "bearer"} or not raw:
            raise AuthenticationFailed()
        if scheme.lower() == "token" and raw.startswith("pkdb_live_"):
            raise AuthenticationFailed()
        with session_factory.begin() as session:
            return authenticate_token(raw, session)

    def parse_json(value):
        if not isinstance(value, str):
            fail("invalid_json", "JSON form fields must contain text")

        def unique_pairs(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    fail("duplicate_json_key", f"Duplicate JSON key: {key}")
                result[key] = item
            return result

        def invalid_constant(value):
            fail("nonfinite_number", "JSON numbers must be finite")

        try:
            return json.loads(
                value, object_pairs_hook=unique_pairs, parse_constant=invalid_constant
            )
        except json.JSONDecodeError, RecursionError:
            fail("invalid_json", "Malformed JSON form field")

    async def upload(request: Request, sid: str | None = None):
        actor = await run_in_threadpool(principal, request)
        try:
            async with request.form(
                max_files=settings.upload_max_files,
                max_fields=2,
                max_part_size=settings.upload_max_bytes,
            ) as form:
                if (
                    len(form.getlist("study")) != 1
                    or len(form.getlist("reference")) != 1
                ):
                    fail(
                        "bundle_fields", "Exactly one study and reference are required"
                    )
                if set(form) - {"study", "reference", "files"}:
                    fail("bundle_fields", "Unknown multipart field")
                study = parse_json(form["study"])
                reference = parse_json(form["reference"])
                if not isinstance(study, dict) or not isinstance(reference, dict):
                    fail("invalid_json", "Study and reference must be JSON objects")
                if sid is not None and str(study.get("sid")) != sid:
                    fail("sid_mismatch", "Path SID must match study SID")
                with TemporaryDirectory(prefix="pkdb-upload-") as directory:
                    files = {}
                    for item in form.getlist("files"):
                        if not isinstance(item, UploadFile) or not item.filename:
                            fail("invalid_file", "Named file parts are required")
                        name = item.filename
                        if (
                            name in files
                            or name in {".", ".."}
                            or any(c in name for c in "/\\\0")
                        ):
                            fail(
                                "invalid_filename",
                                "Invalid or duplicate attachment filename",
                            )
                        path = Path(directory) / name
                        await run_in_threadpool(copy_upload, item.file, path)
                        files[name] = path
                    bundle = SourceBundle(study=study, reference=reference, files=files)
                    if sid is None:
                        prepared = await run_in_threadpool(
                            ingestion.validate, bundle, actor
                        )
                        return {
                            **prepared.report.model_dump(mode="json"),
                            "valid": True,
                        }
                    result = await run_in_threadpool(ingestion.replace, bundle, actor)
                    return JSONResponse(
                        result.model_dump(mode="json"),
                        status_code=201 if result.created else 200,
                    )
        except ValidationError, HTTPException:
            fail("invalid_bundle", "Malformed study bundle")

    def copy_upload(source, path):
        with path.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)

    @app.post("/api/v2/studies/validate")
    async def validate_upload(request: Request):
        return await upload(request)

    @app.put("/api/v2/studies/{sid}")
    async def replace_upload(sid: str, request: Request):
        return await upload(request, sid)

    @app.get("/api/v2/studies/{sid}")
    def get_study(sid: str, request: Request):
        actor = principal(request, required=False)
        try:
            return read_study(sid, actor, session_factory)
        except LookupError:
            raise HTTPException(404, "Study not found") from None

    @app.get("/api/v2/studies/{sid}/publication")
    def get_publication(sid: str, request: Request):
        actor = principal(request, required=False)
        try:
            return publication_state(sid, actor, session_factory)
        except LookupError:
            raise HTTPException(404, "Study not found") from None

    @app.get("/api/v1/swagger/", include_in_schema=False)
    def legacy_documentation():
        return RedirectResponse("/docs")

    @app.get("/health/live")
    def liveness():
        return {"status": "ok"}

    @app.get("/health/ready")
    def readiness():
        try:
            with session_factory() as session:
                version = session.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                if version != SCHEMA_REVISION:
                    raise RuntimeError("Schema mismatch")
            with TemporaryFile(dir=settings.file_root) as handle:
                handle.write(b"ready")
                handle.flush()
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ok"}

    from pkdb.api.compatibility import include_legacy_router

    app.state.principal = principal
    include_legacy_router(app, accounts.router)
    include_legacy_router(app, admin_users.router)
    include_legacy_router(app, admin_roles.router)
    app.include_router(media.router)
    include_legacy_router(app, reads.router)
    include_legacy_router(app, staging.router)
    include_legacy_router(app, exports.router)
    include_legacy_router(app, legacy_uploads.router)
    app.mount("/mcp", mcp_app)
    return app
