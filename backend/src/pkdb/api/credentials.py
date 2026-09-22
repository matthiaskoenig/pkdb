"""Canonical browser credentials API and same-origin CSRF protection."""

import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from pkdb.schemas.accounts import (
    EmailRequest,
    PasswordReset,
    Registration,
    Verification,
)
from pkdb.services.accounts import AccountThrottled, MailDeliveryFailed
from pkdb.services.authentication import AuthenticationFailed
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import require_session

router = APIRouter(prefix="/api/v1")


class CredentialInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(CredentialInput):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=1024)


class PasswordInput(CredentialInput):
    password: str = Field(min_length=1, max_length=1024)


class KeyInput(CredentialInput):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=lambda: ["read"], max_length=2)
    lifetime_days: int = Field(default=90, ge=1, le=365)


class RotateInput(CredentialInput):
    overlap_hours: int = Field(default=24, ge=0, le=24)


class BrowserSecurity(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        state = request.app.state
        canonical = request.url.path.startswith(
            "/api/v1/auth/"
        ) or request.url.path.startswith("/api/v1/me")
        cookie_auth = bool(request.cookies.get(state.session_cookie_name))
        mutation = request.method not in {"GET", "HEAD", "OPTIONS"}
        # Explicit credentials are resolved by the shared principal validator.
        # Canonical login/reauthentication always require CSRF, even with a header.
        credential_action = request.url.path in {
            "/api/v1/auth/login",
            "/api/v1/auth/reauthenticate",
            "/api/v1/auth/logout",
        }
        if (
            mutation
            and (canonical or cookie_auth)
            and (credential_action or not request.headers.get("authorization"))
        ):
            origin = request.headers.get("origin")
            expected = state.browser_origin
            csrf_cookie = request.cookies.get(state.csrf_cookie_name, "")
            csrf_header = request.headers.get("x-csrf-token", "")
            if (
                origin != expected
                or not csrf_cookie
                or not secrets.compare_digest(csrf_cookie, csrf_header)
            ):
                return JSONResponse(
                    {"detail": "CSRF validation failed", "code": "csrf_failed"},
                    status_code=403,
                )
        response = await call_next(request)
        if (
            canonical
            or cookie_auth
            or request.headers.get("authorization")
            or request.url.path.startswith("/api/v1/admin")
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response


def install_browser_security(app, *, origin, secure=True):
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
    ):
        raise ValueError("An explicit browser origin is required")
    if secure and parsed.scheme != "https":
        raise ValueError("Secure cookies require an HTTPS browser origin")
    if not secure and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "testserver",
    }:
        raise ValueError(
            "Insecure browser sessions are restricted to local development"
        )
    app.state.browser_origin = origin.rstrip("/")
    app.state.secure_cookies = secure
    app.state.session_cookie_name = (
        "__Host-pkdb_session" if secure else "pkdb_dev_session"
    )
    app.state.csrf_cookie_name = "__Host-pkdb_csrf" if secure else "pkdb_dev_csrf"
    app.add_middleware(BrowserSecurity)
    app.include_router(router)


def set_cookie(response, request, name, value, *, max_age):
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        secure=request.app.state.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/",
    )


def actor(request, *, recent=False):
    principal = request.app.state.principal(request)
    with request.app.state.session_factory.begin() as session:
        require_session(principal, session, recent=recent)
    return principal


def perform(request, operation, *args, **kwargs):
    try:
        return getattr(request.app.state.credentials, operation)(*args, **kwargs)
    except AccountThrottled as error:
        raise HTTPException(
            429, "Too many attempts", headers={"Retry-After": "600"}
        ) from error
    except LookupError as error:
        raise HTTPException(404, "Resource not found") from error
    except ValueError as error:
        if isinstance(error, AuthenticationFailed):
            raise
        raise HTTPException(422, str(error)) from error


@router.get("/auth/csrf")
def csrf(request: Request):
    token = secrets.token_urlsafe(32)
    response = JSONResponse({"csrf_token": token})
    set_cookie(
        response, request, request.app.state.csrf_cookie_name, token, max_age=86400
    )
    return response


@router.post("/auth/login")
def login(data: LoginInput, request: Request):
    raw, principal = perform(
        request,
        "login",
        data.username,
        data.password,
        request.headers.get("user-agent", ""),
    )
    # Replace an existing cookie session instead of accumulating credentials.
    if request.cookies.get(request.app.state.session_cookie_name):
        try:
            previous = request.app.state.principal(request)
            if previous.credential_kind == "session":
                perform(request, "revoke_session", previous, previous.credential_id)
        except AuthenticationFailed, AuthorizationDenied:
            pass
    response = JSONResponse({"username": principal.username, "role": principal.role})
    set_cookie(
        response, request, request.app.state.session_cookie_name, raw, max_age=7 * 86400
    )
    return response


@router.post("/auth/logout", status_code=204)
def logout(request: Request):
    principal = actor(request)
    perform(request, "revoke_session", principal, principal.credential_id)
    response = Response(status_code=204)
    response.delete_cookie(
        request.app.state.session_cookie_name,
        path="/",
        secure=request.app.state.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/auth/reauthenticate", status_code=204)
def reauthenticate(data: PasswordInput, request: Request):
    raw = perform(request, "reauthenticate", actor(request), data.password)
    response = Response(status_code=204)
    set_cookie(
        response, request, request.app.state.session_cookie_name, raw, max_age=7 * 86400
    )
    return response


@router.get("/me/sessions")
def sessions(request: Request):
    return perform(request, "sessions", actor(request))


@router.delete("/me/sessions/{identifier}", status_code=204)
def revoke_session(identifier: int, request: Request):
    perform(request, "revoke_session", actor(request), identifier)
    return Response(status_code=204)


@router.get("/me/api-keys")
def keys(request: Request):
    return perform(request, "keys", actor(request))


@router.post("/me/api-keys", status_code=201)
def create_key(data: KeyInput, request: Request):
    return perform(
        request, "create_key", actor(request, recent=True), **data.model_dump()
    )


@router.delete("/me/api-keys/{identifier}", status_code=204)
def revoke_key(identifier: int, request: Request):
    perform(request, "revoke_key", actor(request), identifier)
    return Response(status_code=204)


@router.post("/me/api-keys/{identifier}/rotate", status_code=201)
def rotate_key(identifier: int, data: RotateInput, request: Request):
    return perform(
        request,
        "rotate_key",
        actor(request, recent=True),
        identifier,
        **data.model_dump(),
    )


def account_action(request, operation, **values):
    try:
        return getattr(request.app.state.accounts, operation)(**values)
    except AccountThrottled as error:
        raise HTTPException(
            429, "Too many attempts", headers={"Retry-After": "600"}
        ) from error
    except MailDeliveryFailed as error:
        raise HTTPException(
            503, "Email delivery unavailable", headers={"Retry-After": "60"}
        ) from error
    except (ValueError, AuthenticationFailed) as error:
        raise HTTPException(400, "Invalid account request") from error


@router.post("/auth/register", status_code=202)
def register(data: Registration, request: Request):
    # Reserved and existing usernames receive the same acceptance response.
    if data.username.strip().casefold() != "mkoenig":
        account_action(request, "register", **data.model_dump())
    return {
        "detail": "If registration can be completed, verification instructions will be sent."
    }


@router.post("/auth/request-password-reset", status_code=202)
def request_reset(data: EmailRequest, request: Request):
    account_action(request, "request_reset", email=data.email)
    return {"detail": "If eligible, recovery instructions will be sent."}


@router.post("/auth/resend-verification", status_code=202)
def resend_verification(data: EmailRequest, request: Request):
    account_action(request, "resend_verification", email=data.email)
    return {"detail": "If eligible, verification instructions will be sent."}


@router.post("/auth/verify-email", status_code=204)
def verify_email(data: Verification, request: Request):
    account_action(request, "verify_email", token=data.key)
    return Response(status_code=204)


@router.post("/auth/reset-password", status_code=204)
def reset_password(data: PasswordReset, request: Request):
    account_action(
        request, "complete_reset", token=data.key, new_password=data.password
    )
    return Response(status_code=204)
