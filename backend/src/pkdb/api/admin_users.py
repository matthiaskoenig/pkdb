"""Legacy user administration routes; account secrets appear only at creation."""

from fastapi import APIRouter, Depends, HTTPException, Request

from pkdb.schemas.admin_users import AdminUserCreate, AdminUserPatch, AdminUserPut
from pkdb.services.authorization import AuthorizationDenied


def require_administrator(request: Request):
    actor = request.app.state.principal(request)
    if actor.role != "admin":
        raise AuthorizationDenied("Administrator required")
    from pkdb.services.credentials import require_admin_session

    with request.app.state.session_factory() as session:
        require_admin_session(actor, session)
    request.state.admin_actor = actor


router = APIRouter(
    prefix="/api/v1/_users", dependencies=[Depends(require_administrator)]
)


@router.post("/", status_code=201)
def create_user(data: AdminUserCreate, request: Request):
    return request.app.state.admin_users.create(request.state.admin_actor, data)


@router.get("/{user_id}/")
def retrieve_user(user_id: int, request: Request):
    try:
        return request.app.state.admin_users.retrieve(
            request.state.admin_actor, user_id
        )
    except LookupError:
        raise HTTPException(404, "User not found") from None


def update_user(user_id, data, request):
    try:
        return request.app.state.admin_users.update(
            request.state.admin_actor,
            user_id,
            data.model_dump(exclude_unset=True),
        )
    except LookupError:
        raise HTTPException(404, "User not found") from None


@router.patch("/{user_id}/")
def patch_user(user_id: int, data: AdminUserPatch, request: Request):
    return update_user(user_id, data, request)


@router.put("/{user_id}/")
def put_user(user_id: int, data: AdminUserPut, request: Request):
    return update_user(user_id, data, request)
