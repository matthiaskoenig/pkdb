"""FastAPI factory with explicit services and independent request sessions."""

import json
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from uuid import uuid4

from fastapi import FastAPI, Request
from pydantic import ValidationError
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from pkdb.api.limits import UploadLimits
from pkdb.config import Settings
from pkdb.db.read import read_study
from pkdb.db.session import make_session_factory
from pkdb.files.store import FileStore, FileTooLarge
from pkdb.schemas.security import Principal
from pkdb.schemas.source import SourceBundle
from pkdb.schemas.validation import StudyValidationError, fail
from pkdb.services.authentication import AuthenticationFailed, authenticate_token
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.ingestion import IngestionService, PublicationConflict

log = logging.getLogger(__name__)
SCHEMA_REVISION = "7dd23f32b5f9"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    session_factory = make_session_factory(settings.database_url)
    file_store = FileStore(
        settings.file_root, session_factory, settings.upload_max_bytes
    )
    ingestion = IngestionService(session_factory, file_store, settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        session_factory.kw["bind"].dispose()

    app = FastAPI(title="PK-DB", version="0.10.0", lifespan=lifespan)
    app.state.ingestion = ingestion
    app.state.session_factory = session_factory
    app.add_middleware(
        UploadLimits,
        max_bytes=settings.upload_max_bytes,
        concurrency=settings.upload_concurrency,
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
            if not required:
                return Principal()
            raise AuthenticationFailed()
        scheme, _, raw = header.partition(" ")
        if scheme.lower() not in {"token", "bearer"} or not raw:
            raise AuthenticationFailed()
        with session_factory() as session:
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
        except json.JSONDecodeError:
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
        except (ValidationError, HTTPException):
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

    return app
