"""Transport-independent permissions against existing published ownership."""

from pkdb.schemas.security import Action, Principal, StudyAccess


class AuthorizationDenied(PermissionError):
    pass


def require_scope(principal: Principal, scope: str) -> None:
    if (
        principal.credential_kind in {"api_key", "legacy"}
        and scope not in principal.scopes
    ):
        raise AuthorizationDenied("Credential scope is insufficient")


def authorize_creation(principal: Principal) -> None:
    require_scope(principal, "studies:write")
    if principal.user_id is None or principal.role not in {
        "admin",
        "curator",
        "reviewer",
    }:
        raise AuthorizationDenied("Study creation requires a curator or administrator")


def authorize(principal: Principal, action: Action, study: StudyAccess) -> None:
    if principal.role not in {"admin", "curator", "reviewer", "user", "anonymous"}:
        raise AuthorizationDenied("Unknown role")
    if action not in {"read", "write", "delete", "read_file", "administer"}:
        raise AuthorizationDenied("Unknown action")
    require_scope(principal, "studies:write" if action == "write" else "read")
    if action in {"delete", "administer"} and principal.credential_kind in {
        "api_key",
        "legacy",
    }:
        raise AuthorizationDenied("Browser session required")
    authenticated = principal.user_id is not None and principal.role != "anonymous"
    if authenticated and principal.role == "admin":
        return
    assigned_curator = authenticated and principal.user_id in study.curator_ids
    allowed = False
    if action == "read":
        allowed = study.access == "public" or assigned_curator
    elif action == "read_file":
        allowed = (
            assigned_curator or study.access == "public" and study.licence == "open"
        )
    elif action == "write":
        allowed = authenticated and (
            principal.role in {"curator", "reviewer"}
            and (
                assigned_curator
                or principal.role == "reviewer"
                and study.access == "public"
            )
        )
    if not allowed:
        raise AuthorizationDenied("Action is not permitted for this study")
