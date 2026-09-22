"""Translate legacy account input errors without echoing credentials or inputs."""

from fastapi.exception_handlers import request_validation_exception_handler
from starlette.responses import JSONResponse


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
    legacy = path == "/api-token-auth/" or path.startswith(
        ("/accounts/", "/api/v1/_users")
    )
    if not legacy:
        return await request_validation_exception_handler(request, error)
    fields = {}
    for item in error.errors():
        location = item["loc"]
        if location and location[0] == "path":
            return JSONResponse({"detail": "Not found."}, status_code=404)
        field = str(location[1]) if len(location) > 1 else "non_field_errors"
        fields.setdefault(field, []).append(field_message(item, field))
    return JSONResponse(fields, status_code=400)
