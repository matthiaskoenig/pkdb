"""The study pages of the website (#963): JSON documents by audience and the files of curators."""

import hashlib
import json

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import FileResponse, JSONResponse, Response

router = APIRouter(prefix="/api/v2")

HEADERS = {"Cache-Control": "private, no-cache", "Vary": "Cookie, Authorization"}


def answer(request: Request, body: dict) -> Response:
    """The JSON body with an ETag of its content; 304 when the client has it."""
    data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    etag = '"' + hashlib.sha256(data).hexdigest()[:32] + '"'
    headers = {**HEADERS, "ETag": etag}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(body, headers=headers)


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
