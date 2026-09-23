"""Opaque credentials; only digests are persisted and no secrets are logged."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pkdb.schemas.security import Principal
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from pkdb_server.db.models.credentials import ApiKey
from pkdb_server.db.models.security import SecurityConfiguration
from pkdb_server.db.models.users import Token, User

password_hash = PasswordHash.recommended()


class AuthenticationFailed(ValueError):
    pass


def issue_token(
    user: User,
    session: Session,
    *,
    lifetime: timedelta = timedelta(days=30),
    purpose: str = "api",
) -> str:
    if not user.active or lifetime <= timedelta(0):
        raise AuthenticationFailed("Active user and positive token lifetime required")
    raw = secrets.token_urlsafe(32)
    session.add(
        Token(
            user_id=user.id,
            digest=hashlib.sha256(raw.encode()).hexdigest(),
            purpose=purpose,
            expires_at=datetime.now(UTC) + lifetime,
        )
    )
    session.flush()
    return raw


def authenticate_token(raw_token: str, session: Session) -> Principal:
    if not raw_token or len(raw_token) > 1024:
        raise AuthenticationFailed("Invalid credentials")
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    if raw_token.startswith("pkdb_live_"):
        result = session.execute(
            select(User, ApiKey)
            .join(ApiKey)
            .where(
                ApiKey.digest == digest,
                ApiKey.revoked_at.is_(None),
                ApiKey.expires_at > datetime.now(UTC),
                User.active.is_(True),
            )
            .execution_options(populate_existing=True)
        ).one_or_none()
        if result is None:
            raise AuthenticationFailed("Invalid credentials")
        user, key = result
        now = datetime.now(UTC)
        if key.last_used_at is None or key.last_used_at < now - timedelta(minutes=5):
            key.last_used_at = now
        return Principal(
            user_id=user.id,
            username=user.username,
            role=user.role,
            credential_kind="api_key",
            credential_id=key.id,
            scopes=frozenset(key.scopes),
        )
    require_legacy_window(session)
    row = session.execute(
        select(User, Token)
        .join(Token)
        .where(
            Token.digest == digest,
            Token.purpose == "api",
            Token.revoked_at.is_(None),
            Token.expires_at > datetime.now(UTC),
            User.active.is_(True),
        )
        .execution_options(populate_existing=True)
    ).one_or_none()
    if row is None:
        raise AuthenticationFailed("Invalid credentials")
    user, token = row
    return Principal(
        user_id=user.id,
        username=user.username,
        role=user.role,
        credential_kind="legacy",
        credential_id=token.id,
        scopes=frozenset({"read", "studies:write"}),
    )


def authenticate_password(username: str, password: str, session: Session) -> User:
    user = session.scalar(select(User).where(User.username == username))
    if user is None or not user.active or not user.password_hash:
        raise AuthenticationFailed("Invalid credentials")
    try:
        valid = password_hash.verify(password, user.password_hash)
    except ValueError, TypeError:
        valid = False
    if not valid:
        raise AuthenticationFailed("Invalid credentials")
    return user


def revalidate_principal(
    principal: Principal, session: Session, *, lock=False
) -> Principal:
    """Refresh identity and original credential inside the operation transaction.

    Locks always acquire the user before its credential. Internal principals are
    reserved for trusted services and tests, never constructed by HTTP/MCP input.
    """
    from pkdb_server.db.models.credentials import BrowserSession

    now = datetime.now(UTC)
    statement = select(User).where(User.id == principal.user_id, User.active.is_(True))
    if lock:
        statement = statement.with_for_update()
    user = session.scalar(statement.execution_options(populate_existing=True))
    if user is None:
        raise AuthenticationFailed("Inactive or missing account")
    if principal.credential_kind == "internal":
        return principal.model_copy(
            update={"username": user.username, "role": user.role}
        )
    models = {"api_key": ApiKey, "session": BrowserSession, "legacy": Token}
    model = models.get(principal.credential_kind)
    if model is None:
        raise AuthenticationFailed("Invalid credential kind")
    statement = select(model).where(
        model.id == principal.credential_id,
        model.user_id == user.id,
        model.revoked_at.is_(None),
        model.expires_at > now,
    )
    if lock:
        statement = statement.with_for_update()
    row = session.scalar(statement.execution_options(populate_existing=True))
    if row is None:
        raise AuthenticationFailed("Invalid credentials")
    if isinstance(row, BrowserSession):
        if row.last_seen_at <= now - timedelta(hours=24):
            raise AuthenticationFailed("Expired session")
        return principal.model_copy(
            update={
                "username": user.username,
                "role": user.role,
                "scopes": frozenset(),
                "authenticated_at": row.authenticated_at,
            }
        )
    if isinstance(row, Token):
        require_legacy_window(session)
    if isinstance(row, Token) and row.purpose != "api":
        raise AuthenticationFailed("Invalid credential purpose")
    scopes = (
        frozenset(row.scopes)
        if isinstance(row, ApiKey)
        else frozenset({"read", "studies:write"})
    )
    return principal.model_copy(
        update={
            "username": user.username,
            "role": user.role,
            "scopes": scopes,
            "authenticated_at": None,
        }
    )


def require_legacy_window(session):
    config = session.get(SecurityConfiguration, 1, populate_existing=True)
    if (
        config is None
        or config.legacy_token_cutoff is None
        or config.legacy_token_cutoff <= datetime.now(UTC)
    ):
        raise AuthenticationFailed("Legacy credential support has ended")
