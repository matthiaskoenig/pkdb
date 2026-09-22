"""Legacy account route names with shared transactional account services."""

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse, Response

from pkdb.schemas.accounts import (
    EmailCreate,
    EmailRequest,
    EmailUpdate,
    Login,
    PasswordReset,
    Registration,
    Verification,
)
from pkdb.services.accounts import AccountThrottled, MailDeliveryFailed
from pkdb.services.authentication import AuthenticationFailed

router = APIRouter()


def require_account(request: Request):
    from pkdb.api.credentials import actor

    request.state.account_actor = actor(
        request, recent=request.method not in {"GET", "HEAD", "OPTIONS"}
    )


email_router = APIRouter(dependencies=[Depends(require_account)])


def perform(request, operation, data, result=None):
    service = request.app.state.accounts
    try:
        value = getattr(service, operation)(**data)
        return result(value) if result else {}
    except AccountThrottled:
        return JSONResponse(
            {"detail": "Too many attempts"},
            status_code=429,
            headers={"Retry-After": "600"},
        )
    except MailDeliveryFailed:
        return JSONResponse(
            {"detail": "Email delivery unavailable; retry"},
            status_code=503,
            headers={"Retry-After": "60"},
        )
    except LookupError:
        return JSONResponse({"detail": "Not found"}, status_code=404)
    except AuthenticationFailed, ValueError:
        return JSONResponse(
            {"non_field_errors": ["Invalid account request or credentials."]},
            status_code=400,
        )


@router.post("/api-token-auth/")
def login(data: Login, request: Request):
    return JSONResponse(
        {
            "detail": "Use /api/v1/auth/login for browser sessions or create a personal API key in account settings.",
            "code": "legacy_login_retired",
        },
        status_code=410,
    )


@router.post("/accounts/register/", status_code=201)
def register(data: Registration, request: Request):
    return perform(
        request,
        "register",
        data.model_dump(),
        lambda _: {"username": data.username, "email": data.email},
    )


@router.post("/accounts/request-password-reset/")
def request_reset(data: EmailRequest, request: Request):
    return perform(
        request, "request_reset", data.model_dump(), lambda _: {"email": data.email}
    )


@router.post("/accounts/reset-password/")
def complete_reset(data: PasswordReset, request: Request):
    return perform(
        request, "complete_reset", {"token": data.key, "new_password": data.password}
    )


@router.post("/accounts/verify-email/")
def verify_email(data: Verification, request: Request):
    return perform(
        request, "verify_email", {"token": data.key}, lambda email: {"email": email}
    )


@router.post("/accounts/resend-verification/")
def resend_verification(data: EmailRequest, request: Request):
    return perform(
        request,
        "resend_verification",
        data.model_dump(),
        lambda _: {"email": data.email},
    )


@email_router.get("/accounts/emails/")
def emails(request: Request):
    actor = request.state.account_actor
    return perform(request, "emails", {"principal": actor}, lambda rows: rows)


@email_router.post("/accounts/emails/", status_code=201)
def add_email(data: EmailCreate, request: Request):
    actor = request.state.account_actor
    return perform(
        request, "add_email", {"principal": actor, **data.model_dump()}, lambda row: row
    )


@email_router.get("/accounts/emails/{email_id}/")
def email_detail(email_id: int, request: Request):
    actor = request.state.account_actor
    return perform(
        request, "emails", {"principal": actor, "email_id": email_id}, lambda row: row
    )


@email_router.put("/accounts/emails/{email_id}/")
@email_router.patch("/accounts/emails/{email_id}/")
def change_email(email_id: int, data: EmailUpdate, request: Request):
    actor = request.state.account_actor
    return perform(
        request,
        "change_email",
        {
            "principal": actor,
            "email_id": email_id,
            "values": data.model_dump(exclude_unset=True, exclude_none=True),
        },
        lambda row: row,
    )


@email_router.delete("/accounts/emails/{email_id}/", status_code=204)
def delete_email(email_id: int, request: Request):
    actor = request.state.account_actor
    return perform(
        request,
        "change_email",
        {"principal": actor, "email_id": email_id, "values": {}, "remove": True},
        lambda _: Response(status_code=204),
    )


router.include_router(email_router)
