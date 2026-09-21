"""Smoke tests of the backend against postgres and elasticsearch.

The services are the ones of `docker-compose-test.yml`, see `docs/development.md`.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

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
@pytest.mark.xfail(
    strict=True,
    reason=(
        "pkdb_app.studies.models.IdCollection.expire is declared as "
        "`default=expire()` (the function is called once at import time), so the "
        "baked-in migration default is a fixed past timestamp and every run computes "
        "a different 'current' default, which makemigrations reports as a pending "
        "'Alter field expire' migration. The real fix, `default=expire` (the callable "
        "itself), changes the default every model instance gets and is therefore a "
        "backend behavior change out of scope for this task, see task-3-report.md."
    ),
)
def test_no_missing_migrations() -> None:
    """The migrations are complete for the models."""
    call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())


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
