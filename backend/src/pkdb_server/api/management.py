"""Explicit, session-only administrative operations."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, text

from pkdb_server.db.models.audit import AuditEvent
from pkdb_server.db.models.credentials import ApiKey
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import EmailAddress, Token, User
from pkdb_server.services.credentials import (
    require_admin_session,
    revoke_user_credentials,
)
from pkdb_server.services.ingestion import sid_lock
from pkdb_server.services.profiles import public_profile

router = APIRouter(prefix="/api/v1/admin")


class PatchUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "curator", "reviewer"] | None = None
    active: bool | None = None


class Access(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curator_ids: list[int] = Field(default_factory=list, max_length=1000)
    reader_ids: list[int] = Field(default_factory=list, max_length=1000)
    access: Literal["public", "private"]
    licence: Literal["open", "closed"]
    creator_id: int | None = None


def actor(request, session):
    return require_admin_session(request.app.state.principal(request), session)


@router.get("/users")
def users(
    request: Request,
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    with request.app.state.session_factory() as session:
        actor(request, session)
        rows = session.scalars(
            select(User)
            .where(User.username.icontains(q, autoescape=True))
            .order_by(User.username)
            .offset(offset)
            .limit(limit)
        ).all()
        ids = [row.id for row in rows]
        contacts = {
            email.user_id: email
            for email in session.scalars(
                select(EmailAddress).where(
                    EmailAddress.user_id.in_(ids), EmailAddress.is_primary.is_(True)
                )
            )
        }
        result = []
        for row in rows:
            email = contacts.get(row.id)
            contact_id = email.id if email and email.email == row.email else None
            has_credentials = bool(row.password_hash)
            can_invite = bool(
                not row.active
                and not has_credentials
                and row.role != "admin"
                and row.suspended_at is None
                and contact_id is not None
            )
            status = (
                "suspended"
                if row.suspended_at is not None
                else "active"
                if row.active
                else "pending"
                if row.pending_verification
                else "inactive"
                if has_credentials
                else "unclaimed"
            )
            result.append(
                {
                    **public_profile(row),
                    "id": row.id,
                    "role": row.role,
                    "active": row.active,
                    "email": row.email,
                    "status": status,
                    "invitation_email_id": contact_id,
                    "can_invite": can_invite,
                    "can_activate": bool(
                        not row.active
                        and row.role != "admin"
                        and not row.pending_verification
                        and has_credentials
                        and email is not None
                        and email.is_verified
                        and contact_id is not None
                    ),
                }
            )
        return result


@router.patch("/users/{user_id}")
def update_user(user_id: int, data: PatchUser, request: Request):
    with request.app.state.session_factory.begin() as session:
        administrator = actor(request, session)
        user = session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise HTTPException(404, "User not found")
        if user.role == "admin":
            raise HTTPException(403, "Cannot change the designated administrator")
        changes = data.model_dump(exclude_none=True)
        verified_contact = session.scalar(
            select(EmailAddress.id).where(
                EmailAddress.user_id == user.id,
                EmailAddress.email == user.email,
                EmailAddress.is_primary.is_(True),
                EmailAddress.is_verified.is_(True),
            )
        )
        if data.active is True and (
            user.pending_verification
            or not user.password_hash
            or verified_contact is None
        ):
            raise HTTPException(
                409, "Complete account invitation/verification before activation"
            )
        before = {key: getattr(user, key) for key in changes}
        for key, value in changes.items():
            setattr(user, key, value)
        if data.active is False:
            user.pending_verification = False
            now = datetime.now(UTC)
            user.suspended_at = now
            revoke_user_credentials(session, user.id, now)
            for token in session.scalars(
                select(Token).where(
                    Token.user_id == user.id, Token.revoked_at.is_(None)
                )
            ):
                token.revoked_at = now
        elif data.active is True:
            user.suspended_at = None
        session.add(
            AuditEvent(
                actor_id=administrator.id,
                action="user.update",
                target=str(user.id),
                details={"before": before, "after": changes},
            )
        )
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "active": user.active,
        }


@router.put("/studies/{sid}/access")
def study_access(sid: str, data: Access, request: Request):
    with request.app.state.session_factory.begin() as session:
        # Same ordering as ingestion publication: study advisory lock before account locks.
        session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": sid_lock(sid)}
        )
        administrator = actor(request, session)
        study = session.scalar(select(Study).where(Study.sid == sid).with_for_update())
        if study is None:
            raise HTTPException(404, "Study not found")
        ids = set(data.curator_ids) | set(data.reader_ids)
        if data.creator_id is not None:
            ids.add(data.creator_id)
        found = set(session.scalars(select(User.id).where(User.id.in_(ids))))
        if found != ids:
            raise HTTPException(422, "Unknown account in access grants")
        before = {
            "access": study.access,
            "licence": study.licence,
            "creator_id": study.creator_id,
        }
        study.access, study.licence = data.access, data.licence
        if data.creator_id is not None:
            study.creator_id = data.creator_id
        session.execute(delete(StudyGrant).where(StudyGrant.study_id == study.id))
        for role, ids in (
            ("curator", data.curator_ids),
            ("collaborator", data.reader_ids),
        ):
            session.add_all(
                StudyGrant(study_id=study.id, user_id=identifier, role=role)
                for identifier in sorted(set(ids))
            )
        session.add(
            AuditEvent(
                actor_id=administrator.id,
                action="study.access",
                target=sid,
                details={"before": before, "after": data.model_dump()},
            )
        )
        return data.model_dump()


@router.get("/studies/{sid}/access")
def read_access(sid: str, request: Request):
    with request.app.state.session_factory() as session:
        actor(request, session)
        study = session.scalar(select(Study).where(Study.sid == sid))
        if study is None:
            raise HTTPException(404, "Study not found")
        grants = list(
            session.scalars(select(StudyGrant).where(StudyGrant.study_id == study.id))
        )
        return {
            "access": study.access,
            "licence": study.licence,
            "creator_id": study.creator_id,
            "curator_ids": [g.user_id for g in grants if g.role == "curator"],
            "reader_ids": [g.user_id for g in grants if g.role == "collaborator"],
        }


@router.delete("/users/{user_id}/api-keys/{key_id}", status_code=204)
def revoke_key(user_id: int, key_id: int, request: Request):
    with request.app.state.session_factory.begin() as session:
        administrator = actor(request, session)
        session.scalar(select(User).where(User.id == user_id).with_for_update())
        key = session.scalar(
            select(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .with_for_update()
        )
        if key is None:
            raise HTTPException(404, "Key not found")
        key.revoked_at = key.revoked_at or datetime.now(UTC)
        session.add(
            AuditEvent(
                actor_id=administrator.id, action="key.revoke", target=str(key.id)
            )
        )


@router.get("/audit-events")
def audit_events(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    with request.app.state.session_factory() as session:
        actor(request, session)
        return [
            {
                "id": r.id,
                "actor_id": r.actor_id,
                "action": r.action,
                "target": r.target,
                "created_at": r.created_at,
                "details": r.details,
            }
            for r in session.scalars(
                select(AuditEvent)
                .order_by(AuditEvent.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ]


@router.get("/usage")
def usage(request: Request, user_id: int):
    with request.app.state.session_factory() as session:
        actor(request, session)
    return request.app.state.quotas.usage(user_id)


class RequestReason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=2000)


class RequestDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["approved", "rejected"]


account_router = APIRouter(prefix="/api/v1/me")


@account_router.post("/role-requests", status_code=201)
def request_role(data: RequestReason, request: Request):
    from pkdb_server.db.models.audit import RoleRequest
    from pkdb_server.services.credentials import require_session

    with request.app.state.session_factory.begin() as session:
        user, _ = require_session(
            request.app.state.principal(request), session, lock=True
        )
        if user.role != "user":
            raise HTTPException(409, "Account already has curation privileges")
        if session.scalar(
            select(RoleRequest.id).where(
                RoleRequest.user_id == user.id, RoleRequest.status == "pending"
            )
        ):
            raise HTTPException(409, "A request is already pending")
        row = RoleRequest(user_id=user.id, reason=data.reason.strip(), status="pending")
        if not row.reason:
            raise HTTPException(422, "Provide a reason")
        session.add(row)
        session.flush()
        return {"id": row.id, "status": row.status}


@router.get("/role-requests")
def requests(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    from pkdb_server.db.models.audit import RoleRequest

    with request.app.state.session_factory() as session:
        actor(request, session)
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "username": username,
                "reason": row.reason,
                "status": row.status,
            }
            for row, username in session.execute(
                select(RoleRequest, User.username)
                .join(User, User.id == RoleRequest.user_id)
                .order_by(RoleRequest.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ]


@router.patch("/role-requests/{identifier}")
def decide(identifier: int, data: RequestDecision, request: Request):
    from pkdb_server.db.models.audit import RoleRequest

    with request.app.state.session_factory.begin() as session:
        administrator = actor(request, session)
        row = session.scalar(
            select(RoleRequest).where(RoleRequest.id == identifier).with_for_update()
        )
        if row is None:
            raise HTTPException(404, "Request not found")
        if row.status != "pending":
            raise HTTPException(409, "Request already decided")
        user = session.scalar(
            select(User).where(User.id == row.user_id).with_for_update()
        )
        if data.status == "approved":
            if not user.active or user.suspended_at or user.role != "user":
                raise HTTPException(409, "Account is not eligible")
            user.role = "curator"
        row.status = data.status
        row.decided_by = administrator.id
        row.decided_at = datetime.now(UTC)
        session.add(
            AuditEvent(
                actor_id=administrator.id,
                action="role_request." + row.status,
                target=str(row.id),
            )
        )
        return {"id": row.id, "status": row.status}


@account_router.get("/studies")
def assigned_studies(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    from pkdb_server.services.credentials import require_session

    with request.app.state.session_factory() as session:
        user, _ = require_session(request.app.state.principal(request), session)
        return [
            {"sid": row.sid, "name": row.name}
            for row in session.scalars(
                select(Study)
                .join(StudyGrant)
                .where(StudyGrant.user_id == user.id, StudyGrant.role == "curator")
                .order_by(Study.sid)
                .offset(offset)
                .limit(limit)
            )
        ]


@account_router.get("/security-events")
def own_security_events(
    request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)
):
    from pkdb_server.services.credentials import require_session

    with request.app.state.session_factory() as session:
        user, _ = require_session(request.app.state.principal(request), session)
        return [
            {
                "id": row.id,
                "action": row.action,
                "created_at": row.created_at,
                "target": row.target,
            }
            for row in session.scalars(
                select(AuditEvent)
                .where(AuditEvent.actor_id == user.id)
                .order_by(AuditEvent.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ]
