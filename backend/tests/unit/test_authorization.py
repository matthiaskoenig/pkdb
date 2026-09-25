import pytest

from pkdb.schemas.security import Principal, StudyAccess
from pkdb_server.services.authorization import AuthorizationDenied, authorize


@pytest.fixture
def private_study():
    return StudyAccess(
        sid="S1",
        access="private",
        licence="closed",
        creator_id=1,
        curator_ids=frozenset({2}),
    )


@pytest.mark.parametrize(
    "role,user_id,can_read,can_write",
    [
        ("anonymous", None, False, False),
        ("user", 9, False, False),
        ("curator", 1, False, False),
        ("curator", 2, True, True),
        ("user", 3, False, False),
        ("reviewer", 4, False, False),
        ("user", 2, True, False),
        ("reviewer", 2, True, True),
        ("admin", 5, True, True),
        ("unexpected", 1, False, False),
    ],
)
@pytest.mark.parametrize(
    "action", ["read", "write", "delete", "read_file", "administer"]
)
def test_private_authorization_matrix(
    private_study, role, user_id, can_read, can_write, action
):
    principal = Principal(
        user_id=user_id, username="test" if user_id else None, role=role
    )
    allowed = (
        role == "admin"
        if action in {"administer", "delete"}
        else can_write
        if action == "write"
        else can_read
    )
    if allowed:
        authorize(principal, action, private_study)
    else:
        with pytest.raises(AuthorizationDenied):
            authorize(principal, action, private_study)


def test_public_access_does_not_grant_write_or_closed_files(private_study):
    principal = Principal(role="anonymous")
    study = private_study.model_copy(update={"access": "public"})
    authorize(principal, "read", study)
    for action in ("write", "delete", "read_file", "administer"):
        with pytest.raises(AuthorizationDenied):
            authorize(principal, action, study)
    authorize(principal, "read_file", study.model_copy(update={"licence": "open"}))


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("anonymous", False),
        ("user", False),
        ("reviewer", True),
        ("curator", True),
        ("admin", True),
    ],
)
def test_creation_requires_permitted_role(role, allowed):
    from pkdb_server.services.authorization import authorize_creation

    principal = Principal(user_id=None if role == "anonymous" else 1, role=role)
    if allowed:
        authorize_creation(principal)
    else:
        with pytest.raises(AuthorizationDenied):
            authorize_creation(principal)
