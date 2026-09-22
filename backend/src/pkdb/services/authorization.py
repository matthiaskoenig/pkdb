"""Transport-independent permissions against existing published ownership."""

from pkdb.schemas.security import Action, Principal, StudyAccess


class AuthorizationDenied(PermissionError):
    pass


def require_scope(principal: Principal, scope: str) -> None:
    if (
        principal.role == "admin"
        and principal.credential_kind == "session"
        and principal.mfa_at is None
    ):
        raise AuthorizationDenied("Administrator MFA required")
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
    if action in {"delete", "administer"} and principal.credential_kind == "session":
        from datetime import UTC, datetime, timedelta

        if principal.mfa_at is None or principal.mfa_at <= datetime.now(
            UTC
        ) - timedelta(minutes=10):
            raise AuthorizationDenied("Recent administrator MFA required")
    authenticated = principal.user_id is not None and principal.role != "anonymous"
    if authenticated and principal.role == "admin":
        return
    member = authenticated and (
        principal.user_id == study.creator_id or principal.user_id in study.curator_ids
    )
    privileged_reader = (
        member
        or authenticated
        and (
            principal.user_id in study.collaborator_ids or principal.role == "reviewer"
        )
    )
    allowed = False
    if action == "read":
        allowed = study.access == "public" or privileged_reader
    elif action == "read_file":
        allowed = (
            privileged_reader or study.access == "public" and study.licence == "open"
        )
    elif action == "write":
        allowed = authenticated and (
            principal.role == "reviewer"
            or principal.role == "curator"
            and principal.user_id in study.curator_ids
        )
    if not allowed:
        raise AuthorizationDenied("Action is not permitted for this study")
