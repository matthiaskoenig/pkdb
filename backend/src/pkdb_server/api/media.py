"""Opaque file handles resolve through authorization, never through URL paths."""

import mimetypes
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from pkdb_server.api.streaming import ClosingStreamingResponse
from pkdb_server.db.models.files import StoredFile

router = APIRouter()


@router.get("/media/{attachment_id}/{filename}")
def download(attachment_id: UUID, filename: str, request: Request):
    principal = request.app.state.principal(request)
    store = request.app.state.file_store
    try:
        handle = store.open_authorized(principal, attachment_id)
    except FileNotFoundError:
        raise HTTPException(404, "Attachment not found") from None
    try:
        with request.app.state.session_factory() as session:
            file = session.scalar(
                select(StoredFile).where(StoredFile.id == attachment_id)
            )
            if file is None or file.original_name != filename:
                raise HTTPException(404, "Attachment not found")
            size = file.size
            name = file.original_name
    except BaseException:
        handle.close()
        raise

    def chunks():
        try:
            while chunk := handle.read(1024 * 1024):
                yield chunk
        finally:
            handle.close()

    return ClosingStreamingResponse(
        chunks(),
        close=handle.close,
        media_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
        headers={
            "Content-Length": str(size),
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(name, safe=""),
            "X-Content-Type-Options": "nosniff",
        },
    )
