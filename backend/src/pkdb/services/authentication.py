"""Opaque credentials; only digests are persisted and no secrets are logged."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from pkdb.db.models.users import Token, User
from pkdb.schemas.security import Principal

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
    row = session.execute(
        select(User)
        .join(Token)
        .where(
            Token.digest == digest,
            Token.purpose == "api",
            Token.revoked_at.is_(None),
            Token.expires_at > datetime.now(UTC),
            User.active.is_(True),
        )
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if row is None:
        raise AuthenticationFailed("Invalid credentials")
    return Principal(user_id=row.id, username=row.username, role=row.role)


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
