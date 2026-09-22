"""Invitation issuance is explicit; accepting claims the already reviewed identity."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from pkdb.api.admin_users import require_administrator
from pkdb.services.accounts import AccountThrottled, MailDeliveryFailed
from pkdb.services.authentication import AuthenticationFailed

router = APIRouter()


class InvitationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_id: int = Field(gt=0)


class InvitationAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=1024)
    password: str = Field(min_length=8, max_length=1024)


@router.post(
    "/api/v1/admin/users/{user_id}/invitations",
    dependencies=[Depends(require_administrator)],
)
def issue(user_id: int, data: InvitationIssue, request: Request):
    try:
        return request.app.state.invitations.issue(
            request.state.admin_actor, user_id, data.email_id
        )
    except LookupError:
        raise HTTPException(404, "User not found") from None
    except ValueError:
        raise HTTPException(
            400, "Account cannot be invited with this contact"
        ) from None
    except MailDeliveryFailed:
        raise HTTPException(
            503, "Invitation delivery unavailable; retry", headers={"Retry-After": "60"}
        ) from None


@router.post("/api/v1/auth/invitations/accept")
def accept(data: InvitationAccept, request: Request):
    try:
        request.app.state.accounts._throttle(
            "invite_accept",
            request.client.host if request.client else "unknown",
            10,
            timedelta(minutes=10),
        )
        return request.app.state.invitations.accept(data.token, data.password)
    except AccountThrottled:
        raise HTTPException(
            429, "Too many attempts", headers={"Retry-After": "600"}
        ) from None
    except AuthenticationFailed, ValueError:
        raise HTTPException(400, "Invalid or expired invitation") from None
