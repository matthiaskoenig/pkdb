from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from pkdb.api.credentials import set_cookie
from pkdb.services.accounts import AccountThrottled

router = APIRouter(prefix="/api/v1/auth/mfa")


class Code(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=6, max_length=100)


@router.post("/enroll")
def enroll(request: Request):
    try:
        return request.app.state.mfa.enroll(request.app.state.principal(request))
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


def complete(request, code, confirm):
    try:
        result, raw = request.app.state.mfa.verify(
            request.app.state.principal(request), code, confirm=confirm
        )
    except AccountThrottled as exc:
        raise HTTPException(
            429, "Too many MFA attempts", headers={"Retry-After": "600"}
        ) from exc
    except ValueError as exc:
        raise HTTPException(400, "Invalid MFA request") from exc
    response = JSONResponse(result)
    set_cookie(
        response, request, request.app.state.session_cookie_name, raw, max_age=7 * 86400
    )
    return response


@router.post("/confirm")
def confirm(data: Code, request: Request):
    return complete(request, data.code, True)


@router.post("/verify")
def verify(data: Code, request: Request):
    return complete(request, data.code, False)
