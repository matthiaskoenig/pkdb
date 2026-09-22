"""Explicit provisioning of the sole administrator, bound to an internal account ID."""

from sqlalchemy import select

from pkdb.db.models.security import SecurityConfiguration
from pkdb.db.models.users import EmailAddress, User
from pkdb.schemas.accounts import Registration
from pkdb.services.accounts import AccountService
from pkdb.services.authentication import password_hash


def create_admin(
    session_factory, username, email, password=None, *, adopt_user_id=None
):
    if username != "mkoenig":
        raise ValueError("Only mkoenig may be designated administrator")
    if adopt_user_id is None:
        if password is None:
            raise ValueError("A password is required for a new administrator")
        values = Registration(username=username, email=email, password=password)
        AccountService._password(values.password)
        encoded = password_hash.hash(values.password)
    else:
        if password is not None:
            raise ValueError(
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
            raise ValueError("Run security schema migrations first")
        user = session.scalar(
            select(User).where(User.username == username).with_for_update()
        )
        other_admin = session.scalar(
            select(User.id).where(
                User.role == "admin", User.id != (user.id if user else -1)
            )
        )
        if other_admin is not None:
            raise ValueError(
                "Review and demote conflicting legacy administrators before designation"
            )
        if configuration.designated_administrator_id is not None:
            if (
                user is None
                or configuration.designated_administrator_id != user.id
                or adopt_user_id != user.id
            ):
                raise ValueError(
                    "Administrator already designated; identity replacement is prohibited"
                )
        if adopt_user_id is not None:
            if (
                user is None
                or user.id != adopt_user_id
                or (user.email or "").casefold() != address
            ):
                raise ValueError(
                    "Adoption requires exact existing ID, username, and primary email"
                )
            if not user.active or user.suspended_at is not None:
                raise ValueError(
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
                raise ValueError(
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


def recover_admin_mfa(session_factory, username, user_id, *, confirm=False):
    """Offline operator recovery. Never replace the designated identity or password."""
    from datetime import UTC, datetime

    from sqlalchemy import update

    from pkdb.db.models.credentials import ApiKey, BrowserSession
    from pkdb.db.models.mfa import AuditEvent, MfaCredential
    from pkdb.db.models.users import Token

    if username != "mkoenig" or not confirm:
        raise ValueError("Recovery requires mkoenig and explicit confirmation")
    with session_factory.begin() as session:
        configuration = session.scalar(
            select(SecurityConfiguration)
            .where(SecurityConfiguration.id == 1)
            .with_for_update()
        )
        user = session.scalar(select(User).where(User.id == user_id).with_for_update())
        if (
            configuration is None
            or configuration.designated_administrator_id != user_id
            or user is None
            or user.username != username
            or user.role != "admin"
            or not user.active
            or user.suspended_at is not None
        ):
            raise ValueError(
                "Recovery requires the exact active designated administrator identity"
            )
        credential = session.get(MfaCredential, user_id)
        if credential is not None:
            session.delete(credential)
        now = datetime.now(UTC)
        for model in (Token, BrowserSession, ApiKey):
            session.execute(
                update(model)
                .where(model.user_id == user_id, model.revoked_at.is_(None))
                .values(revoked_at=now)
            )
        session.add(
            AuditEvent(
                actor_id=None,
                action="administrator.mfa_recovered_offline",
                target=f"user:{user_id}",
                details={"credentials_revoked": True},
            )
        )
        return {"ok": True, "user_id": user_id, "mfa_enrollment_required": True}
