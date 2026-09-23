"""Authenticated immutable attachment handles for complete-bundle clients."""

from fastapi import APIRouter, Request
from pkdb.schemas.validation import fail
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

router = APIRouter()


@router.post("/api/v2/files", status_code=201)
async def stage_file(request: Request):
    actor = await run_in_threadpool(request.app.state.principal, request)
    try:
        async with request.form(max_files=1, max_fields=0) as form:
            if set(form) != {"file"} or len(form.getlist("file")) != 1:
                fail("invalid_file", "Exactly one file is required")
            upload = form["file"]
            if not isinstance(upload, UploadFile) or not upload.filename:
                fail("invalid_file", "A named attachment is required")
            try:
                row = await run_in_threadpool(
                    request.app.state.file_store.stage,
                    actor,
                    upload.filename,
                    upload.file,
                )
            except ValueError:
                fail("invalid_file", "Invalid attachment")
            return {
                "id": str(row.id),
                "name": row.original_name,
                "size": row.size,
                "sha256": row.digest,
                "expires_at": row.expires_at.isoformat(),
            }
    except HTTPException:
        fail("invalid_file", "Malformed attachment upload")
