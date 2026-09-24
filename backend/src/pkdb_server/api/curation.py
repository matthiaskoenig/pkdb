"""Read-only identity and assignment context for the local curation client."""

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.services.authorization import (
    AuthorizationDenied,
    authorize_creation,
    require_scope,
)

router = APIRouter(prefix="/api/v2")


@router.get("/curation-context")
def curation_context(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
):
    actor = request.app.state.principal(request, required=True)
    require_scope(actor, "read")
    try:
        authorize_creation(actor)
        can_upload = True
    except AuthorizationDenied:
        can_upload = False
    with request.app.state.session_factory() as session:
        rows = session.scalars(
            select(Study)
            .join(StudyGrant)
            .where(
                StudyGrant.user_id == actor.user_id,
                StudyGrant.role == "curator",
            )
            .order_by(Study.sid)
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        ).all()
    return {
        "username": actor.username,
        "role": actor.role,
        "scopes": sorted(actor.scopes),
        "can_upload": can_upload,
        "studies": [{"sid": r.sid, "name": r.name} for r in rows[:page_size]],
        "page": page,
        "next": page + 1 if len(rows) > page_size else None,
    }
