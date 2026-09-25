"""Transport-independent permissions against existing published ownership."""

from pkdb.schemas.security import Action, Principal, StudyAccess

# Public messages intentionally omit existing private-study metadata and identities.
PERMISSION_FEEDBACK = {
    "action_not_permitted": (
        "Action not permitted.",
        "Check your account permissions or contact an administrator.",
    ),
    "missing_scope": (
        "The API key does not allow this operation.",
        "For uploads, create a key with studies:write enabled (Allow study uploads and edits).",
    ),
    "upload_role_required": (
        "Your account role does not allow study uploads.",
        "Ask an administrator to enable curator or reviewer access for your account.",
    ),
    "study_write_forbidden": (
        "Your account does not have permission to upload this study.",
        "Ask an administrator to check your study assignments and write permissions. Uploading curator names does not grant access.",
    ),
    "licence_change_forbidden": (
        "The upload would change the study licence, which this credential cannot do.",
        "Preserve the existing licence or ask an administrator to change it through an authorized browser session. Administrator API keys cannot change licences.",
    ),
    "creator_change_forbidden": (
        "The upload would change the study creator, which this credential cannot do.",
        "Preserve the existing creator or ask an administrator to transfer ownership through an authorized browser session. Administrator API keys cannot transfer ownership.",
    ),
}


class AuthorizationDenied(PermissionError):
    """An internal explanation with a separate, allowlisted public error code."""

    def __init__(self, message: str, *, code: str = "action_not_permitted") -> None:
        super().__init__(message)
        self.code = code if code in PERMISSION_FEEDBACK else "action_not_permitted"

    def feedback(self) -> dict[str, str]:
        """Return safe, actionable fields for HTTP clients."""
        detail, suggestion = PERMISSION_FEEDBACK[self.code]
        return {"code": self.code, "detail": detail, "suggestion": suggestion}


def require_scope(principal: Principal, scope: str) -> None:
    if (
        principal.credential_kind in {"api_key", "legacy"}
        and scope not in principal.scopes
    ):
        raise AuthorizationDenied(
            "Credential scope is insufficient", code="missing_scope"
        )


def authorize_creation(principal: Principal) -> None:
    require_scope(principal, "studies:write")
    if principal.user_id is None or principal.role not in {
        "admin",
        "curator",
        "reviewer",
    }:
        raise AuthorizationDenied(
            "Study creation requires a curator or administrator",
            code="upload_role_required",
        )


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
        raise AuthorizationDenied(
            "Action is not permitted for this study",
            code="study_write_forbidden"
            if action == "write"
            else "action_not_permitted",
        )
