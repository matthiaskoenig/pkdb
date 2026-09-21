"""Smoke tests of the backend against postgres and elasticsearch.

The services are the ones of `docker-compose-test.yml`, see `docs/development.md`.
"""

import datetime
from io import StringIO
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from pkdb_app.studies.models import IdCollection

PUBLIC_ENDPOINTS = [
    "/api/v1/",
    "/api/v1/swagger.json",
    "/api/v1/statistics/",
    "/api/v1/studies/",
    "/api/v1/info_nodes/",
    "/api/v1/_studies/",
]


@pytest.fixture
def search_index(db: None) -> None:
    """Create the elasticsearch indices for the empty test database."""
    call_command("search_index", "--rebuild", "-f", stdout=StringIO())


def test_check() -> None:
    """The Django system check reports no issue."""
    call_command("check", "--fail-level", "WARNING", stdout=StringIO())


@pytest.mark.django_db
def test_id_collection_expires_a_day_after_its_creation() -> None:
    """Every `IdCollection` row gets its own expiry, a day after it was created."""
    one_day = datetime.timedelta(days=1)
    before = timezone.now()
    first = IdCollection.objects.create(
        resource=IdCollection.Recourses.Studies, uuid=uuid4(), ids=[1]
    )
    second = IdCollection.objects.create(
        resource=IdCollection.Recourses.Groups, uuid=uuid4(), ids=[2]
    )
    after = timezone.now()

    assert first.expire < second.expire
    assert before + one_day <= first.expire <= after + one_day
    assert before + one_day <= second.expire <= after + one_day


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", PUBLIC_ENDPOINTS)
def test_public_endpoint(endpoint: str, search_index: None) -> None:
    """The public endpoints answer for an empty database."""
    response = APIClient().get(endpoint)
    assert response.status_code == 200, response.content[:500]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param(
            "/api/v1/_studies/",
            marks=pytest.mark.xfail(
                strict=True,
                reason="pinned until the permission classes are revised",
            ),
        ),
        "/api/v1/_info_nodes/",
    ],
)
def test_anonymous_write_rejected(endpoint: str) -> None:
    """An anonymous client cannot write."""
    response = APIClient().post(endpoint, data={}, format="json")
    assert response.status_code in {401, 403}
