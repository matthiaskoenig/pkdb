"""Provider redirects never expose tokens or retain callback parameters."""

from datetime import timedelta

from authlib.common.errors import AuthlibBaseError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from requests import RequestException
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse, RedirectResponse, Response

from pkdb.api.credentials import actor, set_cookie
from pkdb.schemas.accounts import EmailRequest
from pkdb.services.accounts import AccountThrottled, MailDeliveryFailed
from pkdb.services.authentication import AuthenticationFailed
from pkdb.services.authorization import AuthorizationDenied

router = APIRouter(prefix="/api/v1")


class OnboardingInput(EmailRequest):
    username: str = Field(min_length=1, max_length=150)


def browser_cookie(request):
    return "__Host-pkdb_oauth" if request.app.state.secure_cookies else "pkdb_dev_oauth"


def onboarding_cookie(request):
    return (
        "__Host-pkdb_onboarding"
        if request.app.state.secure_cookies
        else "pkdb_dev_onboarding"
    )


def perform(request, operation, *args, **kwargs):
    try:
        return getattr(request.app.state.providers, operation)(*args, **kwargs)
    except AccountThrottled as error:
        raise HTTPException(
            429, "Too many attempts", headers={"Retry-After": "600"}
        ) from error
    except MailDeliveryFailed as error:
        raise HTTPException(503, "Email delivery unavailable") from error
    except LookupError as error:
        raise HTTPException(404, "Provider or identity unavailable") from error
    except IntegrityError as error:
        raise HTTPException(409, "Account or identity already exists") from error
    except ValueError as error:
        if isinstance(error, AuthenticationFailed):
            raise
        raise HTTPException(409, str(error)) from error


@router.get("/auth/providers")
def providers(request: Request):
    return {"providers": request.app.state.providers.enabled()}


@router.get("/auth/onboarding")
def onboarding(request: Request):
    return perform(
        request,
        "onboarding",
        request.cookies.get(onboarding_cookie(request)),
        request.cookies.get(browser_cookie(request)),
    )


@router.post("/auth/onboarding", status_code=202)
def complete_onboarding(data: OnboardingInput, request: Request):
    return perform(
        request,
        "onboarding",
        request.cookies.get(onboarding_cookie(request)),
        request.cookies.get(browser_cookie(request)),
        **data.model_dump(),
    )


class InvitationOnboardingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=1024)


@router.post("/auth/onboarding/invitation")
def accept_invitation(data: InvitationOnboardingInput, request: Request):
    try:
        request.app.state.accounts._throttle(
            "invite_accept",
            request.client.host if request.client else "unknown",
            10,
            timedelta(minutes=10),
        )
    except AccountThrottled:
        raise HTTPException(
            429, "Too many attempts", headers={"Retry-After": "600"}
        ) from None
    result = perform(
        request,
        "accept_invitation",
        request.cookies.get(onboarding_cookie(request)),
        request.cookies.get(browser_cookie(request)),
        data.token,
    )
    credential = result.pop("session")
    response = JSONResponse(result)
    set_cookie(
        response,
        request,
        request.app.state.session_cookie_name,
        credential,
        max_age=7 * 86400,
    )
    response.delete_cookie(onboarding_cookie(request), path="/")
    response.delete_cookie(browser_cookie(request), path="/")
    return response


@router.get("/auth/{provider}/start")
def start(provider: str, request: Request):
    url, browser = perform(request, "start", provider)
    response = RedirectResponse(url, status_code=303)
    set_cookie(response, request, browser_cookie(request), browser, max_age=600)
    return response


@router.get("/auth/{provider}/callback")
def callback(provider: str, request: Request):
    principal = None
    if request.cookies.get(request.app.state.session_cookie_name):
        try:
            principal = request.app.state.principal(request)
        except AuthenticationFailed, AuthorizationDenied:
            pass
    try:
        result = request.app.state.providers.callback(
            provider,
            request.query_params.get("state", ""),
            request.cookies.get(browser_cookie(request), ""),
            request.query_params.get("code", ""),
            principal=principal,
        )
    except (
        AuthenticationFailed,
        AuthorizationDenied,
        ValueError,
        LookupError,
        IntegrityError,
        AuthlibBaseError,
        RequestException,
    ):
        return RedirectResponse("/account?oauth=error", status_code=303)
    response = RedirectResponse(f"/account?oauth={result['status']}", status_code=303)
    if "session" in result:
        set_cookie(
            response,
            request,
            request.app.state.session_cookie_name,
            result["session"],
            max_age=7 * 86400,
        )
    if "onboarding" in result:
        set_cookie(
            response,
            request,
            onboarding_cookie(request),
            result["onboarding"],
            max_age=600,
        )
    return response


@router.get("/me/identities")
def identities(request: Request):
    return perform(request, "identities", actor(request))


def start_bound(provider, request, intent):
    url, browser = perform(
        request,
        "start",
        provider,
        principal=actor(request, recent=intent == "link"),
        intent=intent,
    )
    from starlette.responses import JSONResponse

    response = JSONResponse({"authorization_url": url})
    set_cookie(response, request, browser_cookie(request), browser, max_age=600)
    return response


@router.post("/me/identities/{provider}/link")
def link(provider: str, request: Request):
    return start_bound(provider, request, "link")


@router.post("/me/identities/{provider}/reauthenticate")
def reauthenticate(provider: str, request: Request):
    return start_bound(provider, request, "reauthenticate")


@router.delete("/me/identities/{identifier}", status_code=204)
def unlink(identifier: int, request: Request):
    perform(request, "unlink", actor(request, recent=True), identifier)
    return Response(status_code=204)
