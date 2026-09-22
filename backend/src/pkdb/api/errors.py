"""Translate legacy account input errors without echoing credentials or inputs."""

from fastapi.exception_handlers import request_validation_exception_handler
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from pkdb.api.accounts import require_account
from pkdb.api.admin_users import require_administrator
from pkdb.services.authentication import AuthenticationFailed
from pkdb.services.authorization import AuthorizationDenied


def field_message(error, field):
    kind = error["type"]
    if kind == "missing":
        return "This field is required."
    if error.get("input", object()) is None:
        return "This field may not be null."
    if kind == "string_type":
        return "Not a valid string."
    if kind == "string_too_short" and error.get("input") == "":
        return "This field may not be blank."
    if field == "email" and kind in {"string_pattern_mismatch", "string_too_short"}:
        return "Enter a valid email address."
    if kind == "string_too_long":
        return f"Ensure this field has no more than {error['ctx']['max_length']} characters."
    if kind == "string_too_short":
        return (
            f"Ensure this field has at least {error['ctx']['min_length']} characters."
        )
    return error["msg"]


async def account_validation_error(request, error):
    path = request.url.path
    if path.startswith(("/api/v1/auth/", "/api/v1/me")):
        return JSONResponse(
            {
                "detail": [
                    {
                        "loc": list(item["loc"]),
                        "type": item["type"],
                        "msg": "Invalid request field",
                    }
                    for item in error.errors()
                ]
            },
            status_code=422,
        )
    endpoint = request.scope.get("endpoint")
    module = getattr(endpoint, "__module__", "")
    if module == "pkdb.api.legacy_uploads" and any(
        item["type"] == "json_invalid" for item in error.errors()
    ):
        # FastAPI decodes model bodies before running router dependencies.
        try:
            await run_in_threadpool(request.app.state.principal, request)
        except (AuthenticationFailed, AuthorizationDenied) as denied:
            return await request.app.exception_handlers[type(denied)](request, denied)
    legacy = path == "/api-token-auth/" or path.startswith(
        ("/accounts/", "/api/v1/_users")
    )
    if not legacy:
        return await request_validation_exception_handler(request, error)
    # JSON decoding precedes FastAPI dependencies. Preserve the legacy permission
    # boundary even for malformed bodies, without blocking the event loop.
    if any(item["type"] == "json_invalid" for item in error.errors()):
        check = None
        if module == "pkdb.api.admin_users":
            check = require_administrator
        elif module == "pkdb.api.accounts" and path.startswith("/accounts/emails/"):
            check = require_account
        if check:
            try:
                await run_in_threadpool(check, request)
            except (AuthenticationFailed, AuthorizationDenied) as denied:
                return await request.app.exception_handlers[type(denied)](
                    request, denied
                )
        return JSONResponse({"non_field_errors": ["Invalid JSON."]}, status_code=400)
    fields = {}
    for item in error.errors():
        location = item["loc"]
        if location and location[0] == "path":
            return JSONResponse({"detail": "Not found."}, status_code=404)
        field = str(location[1]) if len(location) > 1 else "non_field_errors"
        fields.setdefault(field, []).append(field_message(item, field))
    return JSONResponse(fields, status_code=400)
