"""The study pages of the website (#963): JSON documents by audience and the files of curators."""

import gzip
import hashlib
import json

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import FileResponse, Response

router = APIRouter(prefix="/api/v2")

HEADERS = {"Cache-Control": "private, no-cache", "Vary": "Cookie, Authorization"}
# The JSON answers may be compressed; the files are not.
JSON_HEADERS = {**HEADERS, "Vary": "Cookie, Authorization, Accept-Encoding"}
#: The size from which a JSON answer is compressed for a client that accepts gzip.
COMPRESS_FROM = 1024


def matches(header: str | None, etag: str) -> bool:
    """RFC 9110 weak comparison of an `If-None-Match` list with the ETag."""
    if not header:
        return False
    etag = etag.removeprefix("W/")
    for entry in header.split(","):
        entry = entry.strip().removeprefix("W/")
        if entry == "*" or entry == etag:
            return True
    return False


def answer(request: Request, body: dict) -> Response:
    """The JSON body with a weak ETag of its content, gzip-compressed for clients that
    accept it; 304 when the client has it.

    The keys keep their order, which the app shows. The ETag is weak because the compressed
    and the plain answer share it.
    """
    data = json.dumps(body, separators=(",", ":")).encode()
    etag = 'W/"' + hashlib.sha256(data).hexdigest()[:32] + '"'
    headers = {**JSON_HEADERS, "ETag": etag}
    if matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    accepted = request.headers.get("accept-encoding", "").lower()
    if len(data) > COMPRESS_FROM and "gzip" in accepted:
        data = gzip.compress(data)
        headers["Content-Encoding"] = "gzip"
    return Response(data, media_type="application/json", headers=headers)


def _read(request: Request, read, *args):
    principal = request.app.state.principal(request, required=False)
    try:
        return read(*args, principal)
    except LookupError:
        raise HTTPException(404, "Not found") from None


@router.get("/study-rows")
def study_rows(request: Request):
    principal = request.app.state.principal(request, required=False)
    return answer(request, request.app.state.study_views.rows(principal))


@router.get("/studies/{substance}/{name}/view")
def study_view(substance: str, name: str, request: Request):
    views = request.app.state.study_views
    return answer(request, _read(request, views.study, f"{substance}/{name}"))


@router.get("/studies/{substance}/{name}/view/tables/{file}")
def study_view_table(substance: str, name: str, file: str, request: Request):
    views = request.app.state.study_views
    return answer(request, _read(request, views.table, f"{substance}/{name}", file))


@router.get("/studies/{substance}/{name}/view/sources/{source}")
def study_view_source(substance: str, name: str, source: str, request: Request):
    views = request.app.state.study_views
    return answer(request, _read(request, views.source, f"{substance}/{name}", source))


@router.get("/studies/{substance}/{name}/view/files/{file}")
def study_view_file(substance: str, name: str, file: str, request: Request):
    views = request.app.state.study_views
    path, media_type = _read(request, views.file, f"{substance}/{name}", file)
    return FileResponse(
        path,
        media_type=media_type,
        filename=file,
        content_disposition_type="inline",
        headers={**HEADERS, "X-Content-Type-Options": "nosniff"},
    )
