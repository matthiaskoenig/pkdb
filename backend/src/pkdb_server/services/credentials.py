"""Transactional sessions and least-privilege personal API keys."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pkdb.schemas.security import Principal
from sqlalchemy import select, update

from pkdb_server.db.models.audit import AuditEvent
from pkdb_server.db.models.credentials import ApiKey, BrowserSession
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.authentication import AuthenticationFailed, password_hash
from pkdb_server.services.authorization import AuthorizationDenied


def digest(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def session_principal(user, credential):
    return Principal(
        user_id=user.id,
        username=user.username,
        role=user.role,
        credential_kind="session",
        credential_id=credential.id,
        authenticated_at=credential.authenticated_at,
    )


def require_session(principal, session, *, recent=False, now=None, lock=False):
    now = now or datetime.now(UTC)
    if principal.credential_kind != "session":
        raise AuthorizationDenied("Browser session required")
    user_query = select(User).where(User.id == principal.user_id, User.active.is_(True))
    credential_query = select(BrowserSession).where(
        BrowserSession.id == principal.credential_id,
        BrowserSession.user_id == principal.user_id,
        BrowserSession.revoked_at.is_(None),
        BrowserSession.expires_at > now,
        BrowserSession.last_seen_at > now - timedelta(hours=24),
    )
    if lock:
        user_query = user_query.with_for_update()
        credential_query = credential_query.with_for_update()
    user = session.scalar(user_query.execution_options(populate_existing=True))
    credential = session.scalar(
        credential_query.execution_options(populate_existing=True)
    )
    if credential is None or user is None:
        raise AuthenticationFailed("Invalid session")
    if recent and credential.authenticated_at <= now - timedelta(minutes=10):
        raise AuthorizationDenied("Recent authentication required")
    return user, credential


def require_admin_session(principal, session):
    """Require the designated administrator's valid browser session."""
    from pkdb_server.db.models.security import SecurityConfiguration

    user, _ = require_session(principal, session, lock=True)
    config = session.get(SecurityConfiguration, 1)
    if (
        user.role != "admin"
        or config is None
        or config.designated_administrator_id != user.id
    ):
        raise AuthorizationDenied("Designated administrator session required")
    return user


def authenticate_session(raw, session):
    if not raw or len(raw) > 1024:
        raise AuthenticationFailed("Invalid session")
    row = session.scalar(
        select(BrowserSession).where(BrowserSession.digest == digest(raw))
    )
    if row is None:
        raise AuthenticationFailed("Invalid session")
    user, row = require_session(
        Principal(user_id=row.user_id, credential_kind="session", credential_id=row.id),
        session,
    )
    now = datetime.now(UTC)
    if row.last_seen_at < now - timedelta(minutes=5):
        row.last_seen_at = now
    return session_principal(user, row)


def revoke_user_credentials(session, user_id, now):
    for model in (BrowserSession, ApiKey):
        session.execute(
            update(model)
            .where(model.user_id == user_id, model.revoked_at.is_(None))
            .values(revoked_at=now)
        )


class CredentialService:
    def __init__(self, session_factory, accounts):
        self.session_factory = session_factory
        self.accounts = accounts

    def login(self, username, password, device=""):
        self.accounts._throttle("login", username, 10, timedelta(minutes=10))
        with self.session_factory.begin() as session:
            user = session.scalar(
                select(User).where(User.username == username).with_for_update()
            )
            encoded = (
                user.password_hash
                if user and user.password_hash
                else self.accounts._dummy_hash
            )
            try:
                valid = password_hash.verify(password, encoded)
            except ValueError, TypeError:
                valid = False
            if not valid or user is None or not user.active:
                raise AuthenticationFailed("Invalid credentials")
            now = datetime.now(UTC)
            raw = secrets.token_urlsafe(32)
            row = BrowserSession(
                user_id=user.id,
                digest=digest(raw),
                last_seen_at=now,
                authenticated_at=now,
                expires_at=now + timedelta(days=7),
                device=device[:200],
            )
            session.add(row)
            session.flush()
            return raw, session_principal(user, row)

    def reauthenticate(self, principal, password):
        self.accounts._throttle(
            "reauthenticate", str(principal.user_id), 10, timedelta(minutes=10)
        )
        with self.session_factory.begin() as session:
            user, credential = require_session(principal, session, lock=True)
            try:
                valid = password_hash.verify(
                    password, user.password_hash or self.accounts._dummy_hash
                )
            except ValueError, TypeError:
                valid = False
            if not valid or not user.password_hash:
                raise AuthenticationFailed("Invalid credentials")
            credential.authenticated_at = datetime.now(UTC)
            raw = secrets.token_urlsafe(32)
            credential.digest = digest(raw)
            session.add(
                AuditEvent(
                    actor_id=user.id,
                    action="session.reauthenticate",
                    target=str(credential.id),
                    details={},
                )
            )
            return raw

    def sessions(self, principal):
        with self.session_factory.begin() as session:
            require_session(principal, session)
            rows = session.scalars(
                select(BrowserSession)
                .where(BrowserSession.user_id == principal.user_id)
                .order_by(BrowserSession.id.desc())
                .limit(100)
            )
            return [
                dict(
                    id=r.id,
                    created_at=r.created_at,
                    last_seen_at=r.last_seen_at,
                    expires_at=r.expires_at,
                    revoked_at=r.revoked_at,
                    device=r.device,
                    current=r.id == principal.credential_id,
                )
                for r in rows
            ]

    def revoke_session(self, principal, identifier):
        with self.session_factory.begin() as session:
            require_session(principal, session, lock=True)
            row = session.scalar(
                select(BrowserSession)
                .where(
                    BrowserSession.id == identifier,
                    BrowserSession.user_id == principal.user_id,
                )
                .with_for_update()
            )
            if row is None:
                raise LookupError("Session not found")
            row.revoked_at = row.revoked_at or datetime.now(UTC)
            session.add(
                AuditEvent(
                    actor_id=principal.user_id,
                    action="session.revoke",
                    target=str(row.id),
                    details={},
                )
            )

    @staticmethod
    def key_data(row):
        return {
            field: getattr(row, field)
            for field in (
                "id",
                "name",
                "prefix",
                "scopes",
                "created_at",
                "expires_at",
                "last_used_at",
                "revoked_at",
                "rotated_from_id",
            )
        }

    def keys(self, principal):
        with self.session_factory.begin() as session:
            require_session(principal, session)
            return [
                self.key_data(row)
                for row in session.scalars(
                    select(ApiKey)
                    .where(ApiKey.user_id == principal.user_id)
                    .order_by(ApiKey.id.desc())
                    .limit(100)
                )
            ]

    def create_key(
        self,
        principal,
        name,
        scopes=("read",),
        lifetime_days=90,
        *,
        rotate_id=None,
        overlap_hours=24,
    ):
        name = name.strip()
        scopes = set(scopes)
        if not name or len(name) > 100 or not 1 <= lifetime_days <= 365:
            raise ValueError("Invalid key name or expiry")
        if (
            scopes not in ({"read"}, {"read", "studies:write"})
            or not 0 <= overlap_hours <= 24
        ):
            raise ValueError("Invalid key scopes or overlap")
        now = datetime.now(UTC)
        with self.session_factory.begin() as session:
            user, _ = require_session(principal, session, recent=True, lock=True)
            if user.role == "admin":
                require_admin_session(principal, session)
            session.execute(select(User.id).where(User.id == user.id).with_for_update())
            session.refresh(user)
            if not user.active:
                raise AuthenticationFailed("Inactive account")
            if "studies:write" in scopes and user.role not in {
                "curator",
                "reviewer",
                "admin",
            }:
                raise AuthorizationDenied("Write scope requires curator privileges")
            if (
                session.scalar(
                    select(EmailAddress.id).where(
                        EmailAddress.user_id == user.id,
                        EmailAddress.is_primary.is_(True),
                        EmailAddress.is_verified.is_(True),
                    )
                )
                is None
            ):
                raise AuthorizationDenied("Verified primary email required")
            active = list(
                session.scalars(
                    select(ApiKey).where(
                        ApiKey.user_id == user.id,
                        ApiKey.revoked_at.is_(None),
                        ApiKey.expires_at > now,
                    )
                )
            )
            old = None
            if rotate_id is not None:
                old = next((r for r in active if r.id == rotate_id), None)
                if old is None:
                    raise LookupError("Active key not found")
                if set(old.scopes) != scopes:
                    raise ValueError("Rotation must preserve scopes")
                if session.scalar(
                    select(ApiKey.id).where(ApiKey.rotated_from_id == old.id)
                ):
                    raise ValueError("Key already rotated")
            if len(active) >= 10:
                raise ValueError("Revoke a key before creating another")
            raw = "pkdb_live_" + secrets.token_urlsafe(32)
            row = ApiKey(
                user_id=user.id,
                name=name,
                prefix=raw[:17],
                digest=digest(raw),
                scopes=sorted(scopes),
                expires_at=now + timedelta(days=lifetime_days),
                rotated_from_id=old.id if old else None,
            )
            session.add(row)
            if old:
                old.expires_at = min(
                    old.expires_at, now + timedelta(hours=overlap_hours)
                )
            session.flush()
            session.add(
                AuditEvent(
                    actor_id=user.id,
                    action="key.rotate" if old else "key.create",
                    target=str(row.id),
                    details={"scopes": sorted(scopes)},
                )
            )
            result = self.key_data(row)
            result["secret"] = raw
            if old:
                result["overlap_expires_at"] = old.expires_at
            return result

    def rotate_key(self, principal, identifier, overlap_hours=24):
        with self.session_factory.begin() as session:
            require_session(principal, session, recent=True)
            row = session.scalar(
                select(ApiKey).where(
                    ApiKey.id == identifier, ApiKey.user_id == principal.user_id
                )
            )
            if row is None:
                raise LookupError("Key not found")
            name, scopes = row.name, row.scopes
        return self.create_key(
            principal, name, scopes, rotate_id=identifier, overlap_hours=overlap_hours
        )

    def revoke_key(self, principal, identifier):
        with self.session_factory.begin() as session:
            require_session(principal, session, lock=True)
            row = session.scalar(
                select(ApiKey)
                .where(ApiKey.id == identifier, ApiKey.user_id == principal.user_id)
                .with_for_update()
            )
            if row is None:
                raise LookupError("Key not found")
            row.revoked_at = row.revoked_at or datetime.now(UTC)
            session.add(
                AuditEvent(
                    actor_id=principal.user_id,
                    action="key.revoke",
                    target=str(row.id),
                    details={},
                )
            )
