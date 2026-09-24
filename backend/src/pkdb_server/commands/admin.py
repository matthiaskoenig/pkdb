"""Explicit provisioning of the sole administrator, bound to an internal account ID."""

import re

from pydantic import ValidationError
from sqlalchemy import select

from pkdb.schemas.accounts import Registration
from pkdb_server.db.models.security import SecurityConfiguration
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.accounts import AccountService
from pkdb_server.services.authentication import password_hash


class AdminProvisioningError(ValueError):
    """A fixed operator-facing provisioning error containing no secret input."""


def create_admin(
    session_factory, username, email, password=None, *, adopt_user_id=None
):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}", username):
        raise AdminProvisioningError("Invalid username")
    if adopt_user_id is None:
        if password is None:
            raise AdminProvisioningError(
                "A password is required for a new administrator"
            )
        try:
            values = Registration(username=username, email=email, password=password)
        except ValidationError as error:
            fields = {item["loc"][0] for item in error.errors(include_input=False)}
            if "email" in fields:
                raise AdminProvisioningError(
                    "Invalid administrator email address"
                ) from None
            raise AdminProvisioningError(
                "Password must contain between 8 and 1024 characters"
            ) from None
        try:
            AccountService._password(values.password)
        except ValueError:
            raise AdminProvisioningError(
                "Password must contain between 8 and 1024 characters"
            ) from None
        encoded = password_hash.hash(values.password)
    else:
        if password is not None:
            raise AdminProvisioningError(
                "Adoption preserves existing credentials; do not supply a password"
            )
        encoded = None
    address = email.strip().casefold()
    with session_factory.begin() as session:
        configuration = session.scalar(
            select(SecurityConfiguration)
            .where(SecurityConfiguration.id == 1)
            .with_for_update()
        )
        if configuration is None:
            raise AdminProvisioningError("Run security schema migrations first")
        user = session.scalar(
            select(User).where(User.username == username).with_for_update()
        )
        other_admin = session.scalar(
            select(User.id).where(
                User.role == "admin", User.id != (user.id if user else -1)
            )
        )
        if other_admin is not None:
            raise AdminProvisioningError(
                "Review and demote conflicting legacy administrators before designation"
            )
        if configuration.designated_administrator_id is not None:
            if (
                user is None
                or configuration.designated_administrator_id != user.id
                or adopt_user_id != user.id
            ):
                raise AdminProvisioningError(
                    "Administrator already designated; identity replacement is prohibited"
                )
        if adopt_user_id is not None:
            if (
                user is None
                or user.id != adopt_user_id
                or (user.email or "").casefold() != address
            ):
                raise AdminProvisioningError(
                    "Adoption requires exact existing ID, username, and primary email"
                )
            if not user.active or user.suspended_at is not None:
                raise AdminProvisioningError(
                    "Administrator adoption must not reactivate a disabled account"
                )
            user.role = "admin"
        else:
            if (
                user is not None
                or session.scalar(select(User.id).where(User.email == address))
                is not None
                or session.scalar(
                    select(EmailAddress.id).where(EmailAddress.email == address)
                )
                is not None
            ):
                raise AdminProvisioningError(
                    "Identity exists; use explicit adoption with its internal user ID"
                )
            user = User(
                username=username,
                email=address,
                role="admin",
                active=True,
                password_hash=encoded,
            )
            session.add(user)
            session.flush()
            session.add(
                EmailAddress(
                    user_id=user.id, email=address, is_primary=True, is_verified=True
                )
            )
        configuration.designated_administrator_id = user.id
        return user.id
