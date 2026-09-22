"""Legacy user administration routes; account secrets appear only at creation."""

from fastapi import APIRouter, HTTPException, Request

from pkdb.schemas.admin_users import AdminUserCreate, AdminUserPatch, AdminUserPut

router = APIRouter(prefix="/api/v1/_users")


@router.post("/", status_code=201)
def create_user(data: AdminUserCreate, request: Request):
    return request.app.state.admin_users.create(
        request.app.state.principal(request), data
    )


@router.get("/{user_id}/")
def retrieve_user(user_id: int, request: Request):
    try:
        return request.app.state.admin_users.retrieve(
            request.app.state.principal(request), user_id
        )
    except LookupError:
        raise HTTPException(404, "User not found") from None


def update_user(user_id, data, request):
    try:
        return request.app.state.admin_users.update(
            request.app.state.principal(request),
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
