"""Explicit offline provisioning of an active password account."""

import re

from sqlalchemy import func, select

from pkdb.db.models.users import EmailAddress, User
from pkdb.schemas.accounts import EmailRequest
from pkdb.services.accounts import AccountService
from pkdb.services.authentication import password_hash


def create_user(session_factory, username, password, *, email=None, role="user"):
    """Create a new identity without SMTP; never replace an existing account."""
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{1,150}", username):
        raise ValueError("Invalid username")
    if username.casefold() == "mkoenig":
        raise ValueError("Use create-admin for the reserved administrator username")
    if role not in {"user", "curator", "reviewer"}:
        raise ValueError("Use create-admin to provision an administrator")
    AccountService._password(password)
    address = EmailRequest(email=email.strip().casefold()).email if email else None
    encoded = password_hash.hash(password)
    with session_factory.begin() as session:
        if (
            session.scalar(
                select(User.id).where(func.lower(User.username) == username.lower())
            )
            is not None
        ):
            raise ValueError("Username already exists; existing accounts are preserved")
        if address and (
            session.scalar(select(User.id).where(func.lower(User.email) == address))
            is not None
            or session.scalar(
                select(EmailAddress.id).where(func.lower(EmailAddress.email) == address)
            )
            is not None
        ):
            raise ValueError("Email already belongs to an account")
        user = User(
            username=username,
            email=address,
            role=role,
            active=True,
            password_hash=encoded,
        )
        session.add(user)
        session.flush()
        if address:
            session.add(
                EmailAddress(
                    user_id=user.id, email=address, is_primary=True, is_verified=True
                )
            )
        return user.id
