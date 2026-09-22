"""Read-only legacy catalogue of the four application roles."""

from fastapi import APIRouter, Depends, HTTPException, Request

from pkdb.api.admin_users import require_administrator

# Fresh-database identifiers; historical Django group PKs are not preserved.
ROLES = ("basic", "admin", "reviewer", "curator")
router = APIRouter(
    prefix="/api/v1/_user_groups", dependencies=[Depends(require_administrator)]
)


def role_response(name):
    # Authorization is application policy, not Django content-type permissions.
    return {"name": name, "permissions": []}


@router.get("/")
def role_catalogue(request: Request):
    if request.query_params.get("format", "json") != "json":
        raise HTTPException(404, "Unsupported response format")
    try:
        size = int(request.query_params.get("page_size", "20"))
        if size <= 0:
            size = 20
    except ValueError:
        size = 20
    last = (len(ROLES) + size - 1) // size
    raw = request.query_params.get("page", "1")
    try:
        page = last if raw == "last" else int(raw)
    except ValueError:
        raise HTTPException(404, "Invalid page") from None
    if not 1 <= page <= last:
        raise HTTPException(404, "Invalid page")
    return {
        "current_page": page,
        "last_page": last,
        "next_page_url": str(request.url.include_query_params(page=page + 1))
        if page < last
        else None,
        "prev_page_url": str(request.url.include_query_params(page=page - 1))
        if page > 1
        else None,
        "data": {
            "count": len(ROLES),
            "data": [
                role_response(name) for name in ROLES[(page - 1) * size : page * size]
            ],
        },
    }


@router.get("/{identifier}/")
def role_detail(identifier: str):
    if identifier not in {str(i) for i in range(1, len(ROLES) + 1)}:
        raise HTTPException(404, "Role not found")
    return role_response(ROLES[int(identifier) - 1])
