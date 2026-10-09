"""The curator roster with GitHub logins, for the GitHub issue sync of study folders."""

from fastapi import APIRouter, Request
from sqlalchemy import select

from pkdb.schemas.curators import Curator, CuratorList
from pkdb_server.db.models.users import User
from pkdb_server.services.authorization import require_scope

router = APIRouter(prefix="/api/v2")
ROLES = ("admin", "curator", "reviewer")


def _name(user: User) -> str:
    full = " ".join(part for part in (user.first_name, user.last_name) if part)
    return user.display_name or full or user.username


@router.get("/curators", response_model=CuratorList)
def curators(request: Request) -> CuratorList:
    """Every administrator, curator and reviewer with name and GitHub login.

    Logins are listed also when a user hides them on the profile, because assigning
    the user to a GitHub issue shows the login there anyway.
    """
    actor = request.app.state.principal(request, required=True)
    require_scope(actor, "read")
    with request.app.state.session_factory() as session:
        users = session.scalars(
            select(User).where(User.role.in_(ROLES)).order_by(User.username)
        ).all()
        return CuratorList(
            curators=[
                Curator(
                    username=user.username, name=_name(user), github=user.github or None
                )
                for user in users
            ]
        )
