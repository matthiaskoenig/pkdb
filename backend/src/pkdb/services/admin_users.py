"""Small transactional administrative adapter over the fixed application roles."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pkdb.db.models.users import EmailAddress, User
from pkdb.schemas.security import Principal
from pkdb.services.authorization import AuthorizationDenied
from pkdb.services.credentials import require_admin_session
from pkdb.services.ingestion import PublicationConflict

LEGACY_ROLES = {
    "user": "basic",
    "curator": "curator",
    "reviewer": "reviewer",
    "admin": "admin",
}


def require_admin(principal, session, *, target_id=None):
    require_admin_session(principal, session)
    # Lock in a consistent order even when administrators edit each other.
    ids = {principal.user_id, target_id} - {None}
    users = session.scalars(
        select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update()
    ).all()
    actor = next((user for user in users if user.id == principal.user_id), None)
    if actor is None or not actor.active or actor.role != "admin":
        raise AuthorizationDenied("Administrator required")
    return next((user for user in users if user.id == target_id), None)


def user_response(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "groups": [LEGACY_ROLES[user.role]],
    }


class AdminUserService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create(self, principal: Principal, values):
        try:
            with self.session_factory.begin() as session:
                require_admin(principal, session)
                role = values.groups[0]
                user = User(
                    username=values.username,
                    email=values.email.strip().casefold(),
                    password_hash=None,
                    first_name=values.first_name,
                    last_name=values.last_name,
                    role="user" if role == "basic" else role,
                    active=False,
                )
                session.add(user)
                session.flush()
                session.add(
                    EmailAddress(
                        user_id=user.id,
                        email=user.email,
                        is_primary=True,
                        is_verified=False,
                    )
                )
                result = {
                    **user_response(user),
                    "email": user.email,
                }
            return result
        except IntegrityError:
            raise PublicationConflict("Username or email already exists") from None

    def retrieve(self, principal: Principal, identifier: int):
        with self.session_factory.begin() as session:
            user = require_admin(principal, session, target_id=identifier)
            if user is None:
                raise LookupError("User not found")
            return user_response(user)

    def update(self, principal: Principal, identifier: int, values):
        with self.session_factory.begin() as session:
            user = require_admin(principal, session, target_id=identifier)
            if user is None:
                raise LookupError("User not found")
            for name in ("first_name", "last_name"):
                if name in values:
                    setattr(user, name, values[name])
            if "groups" in values:
                if user.role == "admin":
                    raise AuthorizationDenied(
                        "Cannot change the designated administrator role"
                    )
                role = values["groups"][0]
                user.role = "user" if role == "basic" else role
            session.flush()
            return user_response(user)
