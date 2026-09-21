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
from pkdb_app.users.models import User

PUBLIC_ENDPOINTS = [
    "/api/v1/",
    "/api/v1/swagger.json",
    "/api/v1/statistics/",
    "/api/v1/studies/",
    "/api/v1/info_nodes/",
    "/api/v1/_studies/",
]

# the endpoints whose views use `rest_framework.permissions.IsAdminUser`
STAFF_ONLY_ENDPOINTS = [
    "/api/v1/_info_nodes/",
    "/api/v1/_users/",
    "/api/v1/_user_groups/",
]


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
@pytest.mark.parametrize("endpoint", ["/api/v1/_studies/", *STAFF_ONLY_ENDPOINTS])
def test_anonymous_write_rejected(endpoint: str) -> None:
    """An anonymous client cannot write."""
    response = APIClient().post(endpoint, data={}, format="json")
    assert response.status_code in {401, 403}


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", STAFF_ONLY_ENDPOINTS)
def test_non_staff_write_rejected(endpoint: str) -> None:
    """A user without staff rights cannot write on the endpoints reserved for staff."""
    client = APIClient()
    client.force_authenticate(
        user=User.objects.create_user(username="plain", password="plain-password")
    )
    response = client.post(endpoint, data={}, format="json")
    assert response.status_code in {401, 403}
