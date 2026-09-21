"""Tests of the permission layer of the endpoints which accept writes.

The services are the ones of `docker-compose-test.yml`, see `docs/development.md`.

Covered are the views which use one of the permission classes of
`pkdb_app.users.permissions`: `StudyViewSet` (`/_studies/`), `ReferencesViewSet`
(`/_references/`) and `DataFileViewSet` (`/_datafiles/`), and `update_index_study`
(`/update_index/`), which applies `study_permissions()` itself. The elastic views
`ElasticStudyViewSet`, `StudyAnalysisViewSet` and `ElasticReferenceViewSet` use
the same classes but are read only and therefore route no unsafe method.
"""

import datetime
from pathlib import Path
from typing import Optional

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from pytest_django.fixtures import SettingsWrapper
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from pkdb_app.studies.models import CLOSED, OPEN, Reference, Study
from pkdb_app.subjects.models import DataFile
from pkdb_app.users.models import PRIVATE, PUBLIC, User

STUDY_SID = "TESTSTUDY"
REFERENCE_SID = "TESTREFERENCE"

STUDY_DETAIL = "/api/v1/_studies/{study_sid}/"
REFERENCE_DETAIL = "/api/v1/_references/{reference_sid}/"
DATA_FILE_DETAIL = "/api/v1/_datafiles/{data_file_pk}/"
UPDATE_INDEX = "/api/v1/update_index/"

# every unsafe method routed by one of the three view sets, as `(path, method)`.
# The path is a template filled from the `write_targets` fixture.
UNSAFE_REQUESTS = [
    ("/api/v1/_studies/", "post"),
    (STUDY_DETAIL, "put"),
    (STUDY_DETAIL, "patch"),
    (STUDY_DETAIL, "delete"),
    ("/api/v1/_references/", "post"),
    (REFERENCE_DETAIL, "put"),
    (REFERENCE_DETAIL, "patch"),
    (REFERENCE_DETAIL, "delete"),
    ("/api/v1/_datafiles/", "post"),
    (DATA_FILE_DETAIL, "put"),
    (DATA_FILE_DETAIL, "patch"),
    (DATA_FILE_DETAIL, "delete"),
]

# the detail route of `/_datafiles/` never reaches the view, see
# `test_data_file_detail_raises`
UNSAFE_REQUESTS_REACHING_THE_VIEW = [
    (path, method) for path, method in UNSAFE_REQUESTS if path != DATA_FILE_DETAIL
]

SAFE_REQUESTS = [
    (path, method)
    for path in [
        "/api/v1/_studies/",
        STUDY_DETAIL,
        "/api/v1/_references/",
        REFERENCE_DETAIL,
        "/api/v1/_datafiles/",
    ]
    for method in ["get", "head", "options"]
]


def _user_of_group(username: str, group: Optional[str]) -> User:
    """Create a user, in one of the groups `user_group()` knows or in none."""
    user = User.objects.create_user(username=username, password=f"{username}-password")
    if group is not None:
        user.groups.add(Group.objects.get_or_create(name=group)[0])
    return user


@pytest.fixture
def owner(db: None) -> User:
    """The `basic` user who created the objects under test."""
    return _user_of_group("owner", "basic")


@pytest.fixture
def private_study(db: None) -> Study:
    """A study of another user with `access=private`."""
    return Study.objects.create(
        sid="PRIVATESTUDY",
        name="private study",
        access=PRIVATE,
        licence=CLOSED,
        creator=_user_of_group("private-owner", "basic"),
    )


@pytest.fixture
def write_targets(
    owner: User, tmp_path: Path, settings: SettingsWrapper
) -> dict[str, str]:
    """One public object per endpoint which routes unsafe methods.

    Uploads are redirected to a temporary directory, the configured `MEDIA_ROOT`
    is the media volume of the deployment.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    reference = Reference.objects.create(
        sid=REFERENCE_SID,
        name="test reference",
        title="A reference used by the permission tests",
        date=datetime.date(2020, 1, 1),
    )
    study = Study.objects.create(
        sid=STUDY_SID,
        name="test study",
        access=PUBLIC,
        licence=OPEN,
        creator=owner,
        reference=reference,
    )
    data_file = DataFile.objects.create(filetype="csv")
    return {
        "study_sid": study.sid,
        "reference_sid": reference.sid,
        "data_file_pk": str(data_file.pk),
    }


def _request(client: APIClient, path: str, method: str) -> HttpResponse:
    """Send `method` to `path` with the smallest payload the view accepts."""
    if path.startswith("/api/v1/_datafiles/"):
        # DataFileViewSet.create() reads `request.data["file"]` before validation
        return getattr(client, method)(
            path,
            data={"file": SimpleUploadedFile("test.csv", b"a,b\n1,2\n")},
            format="multipart",
        )
    return getattr(client, method)(path, data={}, format="json")


def _authenticated_client(user: User) -> APIClient:
    """A client which sends its requests as `user`."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize(("path", "method"), UNSAFE_REQUESTS)
def test_anonymous_unsafe_request_is_rejected(
    path: str, method: str, write_targets: dict[str, str]
) -> None:
    response = _request(APIClient(), path.format(**write_targets), method)
    assert response.status_code in {401, 403}, response.status_code


@pytest.mark.django_db
@pytest.mark.parametrize(("path", "method"), UNSAFE_REQUESTS_REACHING_THE_VIEW)
def test_owner_unsafe_request_is_not_rejected(
    path: str, method: str, owner: User, write_targets: dict[str, str]
) -> None:
    response = _request(
        _authenticated_client(owner), path.format(**write_targets), method
    )
    assert response.status_code not in {401, 403}, response.status_code


@pytest.mark.django_db
@pytest.mark.parametrize(("path", "method"), SAFE_REQUESTS)
def test_anonymous_safe_request_is_allowed(
    path: str, method: str, write_targets: dict[str, str]
) -> None:
    response = getattr(APIClient(), method)(path.format(**write_targets))
    assert response.status_code == 200, response.status_code


@pytest.mark.django_db
@pytest.mark.parametrize("path", [STUDY_DETAIL, REFERENCE_DETAIL])
@pytest.mark.parametrize("group", ["basic", "reviewer", None])
def test_put_is_not_narrowed_by_the_object_check(
    path: str, group: Optional[str], write_targets: dict[str, str]
) -> None:
    """Pin the current contract of `is_allowed_method()` for `PUT`."""
    client = _authenticated_client(_user_of_group("bystander", group))
    response = _request(client, path.format(**write_targets), "put")
    assert response.status_code == 400, response.status_code


@pytest.mark.django_db
@pytest.mark.parametrize(("group", "status_code"), [("basic", 404), ("reviewer", 400)])
def test_put_is_narrowed_by_the_queryset_of_the_view(
    group: str, status_code: int, private_study: Study
) -> None:
    """Pin the current contract of `StudyViewSet.get_queryset()` for `PUT`."""
    client = _authenticated_client(_user_of_group("reader", group))
    response = _request(client, f"/api/v1/_studies/{private_study.sid}/", "put")
    assert response.status_code == status_code, response.status_code


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "head", "options", "put", "patch", "delete"])
def test_data_file_detail_raises(
    method: str, owner: User, write_targets: dict[str, str]
) -> None:
    """Pin the current contract of `StudyPermission` for an object without a creator."""
    client = _authenticated_client(owner)
    with pytest.raises(
        AttributeError, match="'DataFile' object has no attribute 'creator'"
    ):
        _request(client, DATA_FILE_DETAIL.format(**write_targets), method)


# ---------------------------------------------------------------------------
# update_index_study, which applies `study_permissions()` itself
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_anonymous_index_update_is_rejected(
    write_targets: dict[str, str], search_index: None
) -> None:
    response = APIClient().post(UPDATE_INDEX, data={"sid": STUDY_SID}, format="json")
    assert response.status_code in {401, 403}, response.status_code


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["basic", "reviewer", None])
def test_index_update_without_the_study_permission_is_rejected(
    group: Optional[str], write_targets: dict[str, str], search_index: None
) -> None:
    client = _authenticated_client(_user_of_group("bystander", group))
    response = client.post(UPDATE_INDEX, data={"sid": STUDY_SID}, format="json")
    assert response.status_code == 403, response.status_code


@pytest.mark.django_db
def test_index_update_by_the_creator(
    owner: User, write_targets: dict[str, str], search_index: None
) -> None:
    client = _authenticated_client(owner)
    response = client.post(UPDATE_INDEX, data={"sid": STUDY_SID}, format="json")
    assert response.status_code == 200, response.status_code
    assert response.json() == {"success": "True"}


@pytest.mark.django_db
def test_index_update_by_an_admin(
    write_targets: dict[str, str], search_index: None
) -> None:
    client = _authenticated_client(_user_of_group("indexer", "admin"))
    response = client.post(UPDATE_INDEX, data={"sid": STUDY_SID}, format="json")
    assert response.status_code == 200, response.status_code
    assert response.json() == {"success": "True"}


@pytest.mark.django_db
def test_index_update_with_a_token_header(
    owner: User, write_targets: dict[str, str], search_index: None
) -> None:
    """The request `pkdb_data` sends: a token header and the sid as JSON."""
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(
        UPDATE_INDEX,
        data={"sid": STUDY_SID},
        format="json",
        HTTP_AUTHORIZATION=f"token {Token.objects.get(user=owner).key}",
    )
    assert response.status_code == 200, response.status_code
    assert response.json() == {"success": "True"}


@pytest.mark.django_db
def test_index_update_with_a_session_is_csrf_checked(
    owner: User, write_targets: dict[str, str], search_index: None
) -> None:
    """`SessionAuthentication` still enforces the CSRF check on this view."""
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(owner)
    response = client.post(UPDATE_INDEX, data={"sid": STUDY_SID}, format="json")
    assert response.status_code == 403, response.status_code


@pytest.mark.django_db
def test_index_update_of_an_unknown_study(owner: User, search_index: None) -> None:
    """An unknown sid is answered with a JSON body, not with an error status."""
    client = _authenticated_client(owner)
    response = client.post(UPDATE_INDEX, data={"sid": "NOSUCHSTUDY"}, format="json")
    assert response.status_code == 200, response.status_code
    assert response.json() == {"success": "False", "reason": "Instance not in database"}


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_index_update_rejects_other_methods(
    method: str, owner: User, write_targets: dict[str, str], search_index: None
) -> None:
    client = _authenticated_client(owner)
    response = getattr(client, method)(
        UPDATE_INDEX, data={"sid": STUDY_SID}, format="json"
    )
    assert response.status_code == 405, response.status_code
