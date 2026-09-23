"""Private self-service profiles and opaque managed-avatar URLs."""

from fastapi import APIRouter, HTTPException, Request
from pkdb.schemas.profiles import ProfileUpdate
from starlette.responses import FileResponse, Response

from pkdb_server.services.accounts import AccountThrottled
from pkdb_server.services.profiles import MAX_AVATAR_BYTES

router = APIRouter(prefix="/api/v1")


@router.get("/me")
def me(request: Request):
    return request.app.state.profiles.read(request.app.state.principal(request))


@router.patch("/me")
def update_me(data: ProfileUpdate, request: Request):
    return request.app.state.profiles.update(
        request.app.state.principal(request), data.model_dump(exclude_unset=True)
    )


@router.put("/me/avatar")
async def upload_avatar(request: Request):
    actor = request.app.state.principal(request)
    # Authenticate before accepting/decoding content, including revoked sessions.
    request.app.state.profiles.read(actor)
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_AVATAR_BYTES:
            raise HTTPException(413, "Avatar exceeds 5 MiB")
        content.extend(chunk)
    try:
        return request.app.state.profiles.set_avatar(actor, bytes(content))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except AccountThrottled as exc:
        raise HTTPException(
            429, "Too many avatar changes", headers={"Retry-After": "3600"}
        ) from exc


@router.delete("/me/avatar")
def remove_avatar(request: Request):
    try:
        return request.app.state.profiles.set_avatar(
            request.app.state.principal(request)
        )
    except AccountThrottled as exc:
        raise HTTPException(
            429, "Too many avatar changes", headers={"Retry-After": "3600"}
        ) from exc


@router.get("/avatars/default.svg")
def fallback_avatar():
    # Static icon: no account existence, names or contact hashes are disclosed.
    return Response(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<rect width="128" height="128" rx="64" fill="#e2e8f0"/>'
        '<circle cx="64" cy="46" r="24" fill="#64748b"/>'
        '<path d="M20 116a44 44 0 0 1 88 0" fill="#64748b"/></svg>',
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/avatars/{key}")
def avatar(key: str, request: Request):
    if len(key) != 32 or any(char not in "0123456789abcdef" for char in key):
        raise HTTPException(404, "Avatar not found")
    try:
        path = request.app.state.profiles.avatar(key)
    except LookupError as exc:
        raise HTTPException(404, "Avatar not found") from exc
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
    )
