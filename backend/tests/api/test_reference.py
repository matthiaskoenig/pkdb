"""Default API surface and complete deployment reference contracts."""

import pytest
from fastapi.testclient import TestClient

from pkdb_server.app import create_app
from pkdb_server.config import Settings


@pytest.fixture
def current_client(ingestion_context, session_factory):
    ingestion, _ = ingestion_context
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion.file_store.root,
        rate_limits_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_researcher_and_complete_reference(current_client):
    primary = current_client.get("/openapi.json").json()
    full = current_client.get("/openapi/all.json").json()
    assert "/api/v2/query" in primary["paths"]
    assert "/api/v1/auth/login" in primary["paths"]
    assert "/api/v1/me/emails/" in primary["paths"]
    assert "/api/v1/studies/" not in primary["paths"]
    assert "/api/v1/studies/" in full["paths"]
    assert "/api/v1/admin/users" in full["paths"]
    assert "/api/v1/admin/users" not in primary["paths"]
    assert "/api/v2/files" not in full["paths"]
    for schema in (primary, full):
        for operations in schema["paths"].values():
            for operation in operations.values():
                assert len(operation["tags"]) == 1
    assert current_client.get("/docs/all").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/api-token-auth/",
        "/accounts/emails/",
        "/api/v1/_users/",
        "/api/v1/_studies/",
        "/api/v2/files",
    ],
)
def test_obsolete_routes_are_absent_by_default(current_client, path):
    assert current_client.post(path, json={}).status_code == 404


def test_current_email_route_requires_authentication(current_client, admin_headers):
    assert current_client.get("/api/v1/me/emails/").status_code == 401
    assert (
        current_client.get("/api/v1/me/emails/", headers=admin_headers).status_code
        == 200
    )


def test_legacy_reference_is_explicitly_deprecated(client):
    primary = client.get("/openapi.json").json()
    full = client.get("/openapi/all.json").json()
    assert "/accounts/emails/" not in primary["paths"]
    assert full["paths"]["/accounts/emails/"]["get"]["deprecated"] is True
