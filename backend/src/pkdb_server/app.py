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

from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.schemas.security import Principal
from pkdb.schemas.source import SourceBundle
from pkdb.schemas.validation import StudyValidationError, fail
from pkdb_server import __version__
from pkdb_server.api import (
    accounts,
    admin_roles,
    admin_users,
    curation,
    data,
    exports,
    invitations,
    management,
    media,
    profiles,
    reads,
)
from pkdb_server.api.credentials import install_browser_security
from pkdb_server.api.errors import account_validation_error
from pkdb_server.api.limits import UploadLimits
from pkdb_server.api.quotas import RequestQuotas
from pkdb_server.api.upload_reports import UploadReports
from pkdb_server.config import Settings
from pkdb_server.db.bootstrap import load_vocabulary
from pkdb_server.db.read import publication_state, read_study
from pkdb_server.db.session import make_session_factory
from pkdb_server.files.store import FileStore, FileTooLarge
from pkdb_server.mcp.server import create_mcp
from pkdb_server.services.accounts import AccountService
from pkdb_server.services.admin_users import AdminUserService
from pkdb_server.services.analysis import AnalysisService
from pkdb_server.services.authentication import AuthenticationFailed, authenticate_token
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.credentials import CredentialService, authenticate_session
from pkdb_server.services.exports import ExportService
from pkdb_server.services.ingestion import IngestionService, PublicationConflict
from pkdb_server.services.invitations import InvitationService
from pkdb_server.services.mailer import SMTPMailer
from pkdb_server.services.profiles import ProfileService
from pkdb_server.services.queries import QueryService
from pkdb_server.services.quotas import QuotaService

log = logging.getLogger(__name__)
SCHEMA_REVISION = "p002retirelegacy"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    session_factory = make_session_factory(settings.database_url)
    file_store = FileStore(
        settings.file_root, session_factory, settings.upload_max_bytes
    )
    ingestion = IngestionService(session_factory, file_store, settings)

    queries = QueryService(session_factory)
    mcp = create_mcp(queries, session_factory)
    mcp_app = mcp.http_app(path="/", json_response=True, stateless_http=False)

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with mcp_app.lifespan(app):
                yield
        finally:
            session_factory.kw["bind"].dispose()

    app = FastAPI(title="PK-DB", version=__version__, lifespan=lifespan)
    app.add_exception_handler(RequestValidationError, account_validation_error)
    app.state.accounts = AccountService(session_factory, SMTPMailer(settings))
    app.state.invitations = InvitationService(
        session_factory, app.state.accounts.mailer
    )
    app.include_router(invitations.router)
    app.state.credentials = CredentialService(session_factory, app.state.accounts)
    app.state.profiles = ProfileService(session_factory, settings.file_root)
    app.state.quotas = QuotaService(session_factory, settings)
    install_browser_security(
        app, origin=settings.browser_origin, secure=settings.secure_cookies
    )
    app.include_router(profiles.router)
    app.include_router(management.router)
    app.include_router(management.account_router)
    app.state.admin_users = AdminUserService(session_factory)
    app.state.file_store = file_store
    app.state.ingestion = ingestion
    app.state.queries = queries
    app.state.analysis = AnalysisService(session_factory)
    app.state.exports = ExportService(session_factory, settings)
    app.state.session_factory = session_factory
    app.add_middleware(
        UploadLimits,
        max_bytes=settings.upload_max_bytes,
        concurrency=settings.upload_concurrency,
        admission_enabled=settings.rate_limits_enabled,
    )
    if settings.rate_limits_enabled:
        app.add_middleware(RequestQuotas)
    app.add_middleware(UploadReports)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-CSRF-Token",
            "X-PKDB-Vocabulary-Hash",
            "X-PKDB-Processing-Version",
            "X-PKDB-Report-Version",
        ],
        expose_headers=["Content-Disposition", "Retry-After", "X-Request-ID"],
    )

    @app.exception_handler(StudyValidationError)
    async def validation_error(request, error):
        return JSONResponse(
            {
                **(
                    error.report.model_dump(mode="json")
                    if request.headers.get("X-PKDB-Report-Version") == "2"
                    else error.report.legacy_dict()
                ),
                "valid": False,
            },
            status_code=422,
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
        return JSONResponse(error.feedback(), status_code=403)

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
        request.state.upload_stage = "compatibility"
        actor = await run_in_threadpool(principal, request)
        expected_hash = request.headers.get("X-PKDB-Vocabulary-Hash")
        expected_processing = request.headers.get("X-PKDB-Processing-Version")
        request.state.upload_versions.update(
            {
                "client_processing_version": expected_processing,
                "client_vocabulary_hash": expected_hash,
            }
        )
        if request.headers.get("X-PKDB-Report-Version") == "2":

            def current_hash():
                with session_factory() as session:
                    return vocabulary_hash(load_vocabulary(session))

            request.state.upload_versions[
                "server_vocabulary_hash"
            ] = await run_in_threadpool(current_hash)
        await run_in_threadpool(
            ingestion.check_compatibility, expected_hash, expected_processing
        )
        request.state.upload_stage = "parse"
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
                request.state.upload_study = {
                    key: study[key]
                    for key in ("sid", "name")
                    if isinstance(study.get(key), str)
                }
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
                    request.state.upload_stage = "server_validation"
                    if sid is None:
                        prepared = await run_in_threadpool(
                            ingestion.validate, bundle, actor
                        )
                        return {
                            **(
                                prepared.report.model_dump(mode="json")
                                if request.headers.get("X-PKDB-Report-Version") == "2"
                                else prepared.report.legacy_dict()
                            ),
                            "valid": True,
                        }
                    request.state.upload_save_started = True
                    result = await run_in_threadpool(
                        ingestion.replace,
                        bundle,
                        actor,
                        expected_vocabulary_hash=expected_hash,
                        expected_processing_version=expected_processing,
                    )
                    request.state.upload_stage = "save"
                    request.state.upload_persistence = (
                        "created" if result.created else "replaced"
                    )
                    payload = result.model_dump(mode="json", exclude_unset=False)
                    if request.headers.get("X-PKDB-Report-Version") != "2":
                        payload["warnings"] = [
                            issue.legacy_dict() for issue in result.warnings
                        ]
                    return JSONResponse(
                        payload,
                        status_code=201 if result.created else 200,
                    )
        except ValidationError as error:
            if request.headers.get("X-PKDB-Report-Version") == "2":
                return JSONResponse(
                    {
                        "detail": error.errors(
                            include_input=False,
                            include_context=False,
                            include_url=False,
                        )
                    },
                    status_code=422,
                )
            fail("invalid_bundle", "Malformed study bundle")
        except HTTPException:
            if request.headers.get("X-PKDB-Report-Version") == "2":
                raise
            fail("invalid_bundle", "Malformed study bundle")

    def copy_upload(source, path):
        with path.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)

    @app.get("/api/v2/vocabulary")
    def validation_vocabulary():
        with session_factory() as session:
            vocabulary = load_vocabulary(session)
        digest = vocabulary_hash(vocabulary)
        return JSONResponse(
            {
                "schema_version": 1,
                "vocabulary": vocabulary.model_dump(mode="json"),
                "vocabulary_hash": digest,
            },
            headers={"ETag": f'"{digest}"'},
        )

    @app.get("/api/v2/capabilities")
    def capabilities():
        with session_factory() as session:
            vocabulary = load_vocabulary(session)
        return {
            "schema_version": 1,
            "upload_report_versions": [1, 2],
            "server_version": __version__,
            "processing_version": PROCESSING_VERSION,
            "vocabulary_version": vocabulary.version,
            "vocabulary_hash": vocabulary_hash(vocabulary),
            "upload_limits": {
                "max_upload_bytes": settings.upload_max_bytes,
                "max_attachment_bytes": settings.upload_max_bytes,
                "max_files": settings.upload_max_files,
                "max_rows": settings.upload_max_rows,
            },
        }

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

    from pkdb_server.api.compatibility import include_legacy_router

    app.state.principal = principal
    app.include_router(data.router)
    app.include_router(curation.router)
    app.include_router(accounts.email_router, prefix="/api/v1/me")
    app.include_router(media.router)
    if settings.legacy_api_enabled:
        for router in (
            accounts.router,
            admin_users.router,
            admin_roles.router,
            reads.router,
            exports.router,
        ):
            include_legacy_router(app, router)
    else:
        app.include_router(reads.router)
        app.include_router(exports.router)
    app.mount("/mcp", mcp_app)
    from pkdb_server.api.reference import install_reference

    install_reference(app)
    return app
