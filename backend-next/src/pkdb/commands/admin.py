"""Explicit local administrator provisioning; never alter an existing identity."""

from sqlalchemy import or_, select

from pkdb.db.models.users import EmailAddress, User
from pkdb.schemas.accounts import Registration
from pkdb.services.accounts import AccountService
from pkdb.services.authentication import password_hash


def create_admin(session_factory, username, email, password):
    values = Registration(username=username, email=email, password=password)
    AccountService._password(values.password)
    address = values.email.strip().casefold()
    encoded = password_hash.hash(values.password)
    with session_factory.begin() as session:
        if (
            session.scalar(
                select(User.id).where(
                    or_(User.username == username, User.email == address)
                )
            )
            is not None
            or session.scalar(
                select(EmailAddress.id).where(EmailAddress.email == address)
            )
            is not None
        ):
            raise ValueError("Identity already exists")
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
