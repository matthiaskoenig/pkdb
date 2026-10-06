"""Study identity in URLs: two-segment sids and redirects from PKDB identifiers.

A study format 2 study has the sid `<substance>/<name>` and is addressed by two
path segments. Single-segment routes serve study format 1 sids and redirect
the PKDB identifier of a released study stored under another sid (its former
study format 1 sid) permanently to the same route for that sid.
"""

from typing import Any
from urllib.parse import quote

from fastapi import Request
from starlette.responses import JSONResponse

from pkdb.schemas.security import Principal
from pkdb.studyformat.validation import study_path
from pkdb_server.db.read import moved_study

# OpenAPI documentation of the redirect for single-segment routes.
MOVED: dict[int | str, dict[str, Any]] = {
    308: {
        "description": "The PKDB identifier of a study stored as "
        "`<substance>/<name>`; `Location` is the same route for that sid"
    }
}


def study_redirect(
    request: Request,
    identifier: str,
    principal: Principal | None = None,
    *,
    parameter: str = "sid",
) -> JSONResponse | None:
    """A permanent redirect to the study released as `identifier`, if any.

    The location is the matched route with its path parameter `parameter`
    replaced by the sid of the study, so suffixes and query strings are kept.
    None when there is no such study or the principal may not read it.
    """
    if principal is None:
        principal = request.app.state.principal(request, required=False)
    sid = moved_study(identifier, principal, request.app.state.session_factory)
    if sid is None:
        return None
    values = {
        name: quote(str(value), safe="") for name, value in request.path_params.items()
    }
    values[parameter] = study_path(sid)
    route = request.scope["route"]
    location = request.scope.get("root_path", "") + route.path_format.format(**values)
    if request.url.query:
        location += "?" + request.url.query
    return JSONResponse(
        {"detail": f"{identifier} identifies the study {sid}", "sid": sid},
        status_code=308,
        # The study may move to another folder later; clients revalidate.
        headers={"Location": location, "Cache-Control": "no-cache"},
    )
