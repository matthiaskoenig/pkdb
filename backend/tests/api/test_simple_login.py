"""Password-only local accounts work through the public browser API."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from pkdb.commands.admin import create_admin
from pkdb.commands.users import create_user
from pkdb.db.models.credentials import BrowserSession
from pkdb.db.models.users import User


def sign_in(client, username, password="Local-password-42!"):
    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    headers = {"Origin": client.app.state.browser_origin, "X-CSRF-Token": csrf}
    response = client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"username": username, "password": password},
    )
    return response, headers


def test_local_account_needs_only_username_and_password(client, session_factory):
    identifier = create_user(session_factory, "local-user", "Local-password-42!")
    response, headers = sign_in(client, "local-user")
    assert response.status_code == 200
    assert response.json() == {"username": "local-user", "role": "user"}
    profile = client.get("/api/v1/me").json()
    assert not any(key.startswith("mfa") for key in profile)
    assert profile["github"] is None and profile["orcid"] is None
    assert (
        client.patch(
            "/api/v1/me",
            headers=headers,
            json={"github": "local-user", "orcid": "0000-0002-1825-0097"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert sign_in(client, "local-user", "wrong-password")[0].status_code == 401
    with session_factory.begin() as session:
        user = session.get(User, identifier)
        assert user.email is None
        user.active = False
    assert sign_in(client, "local-user")[0].status_code == 401


def test_administrator_password_login_grants_access_without_mfa(
    client, session_factory
):
    create_admin(session_factory, "USERNAME", "admin@example.org", "Local-password-42!")
    response, headers = sign_in(client, "USERNAME")
    assert response.status_code == 200
    assert client.get("/api/v1/admin/users").status_code == 200
    assert client.get("/api/v1/studies/").status_code == 200
    with session_factory.begin() as session:
        row = session.scalar(select(BrowserSession))
        row.authenticated_at = datetime.now(UTC) - timedelta(minutes=11)
    assert client.get("/api/v1/admin/users").status_code == 200
    assert (
        client.post(
            "/api/v1/auth/reauthenticate",
            headers=headers,
            json={"password": "Local-password-42!"},
        ).status_code
        == 204
    )
    assert client.get("/api/v1/admin/users").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/providers",
        "/api/v1/auth/github/callback",
        "/api/v1/auth/orcid/callback",
        "/api/v1/me/identities",
    ],
)
def test_provider_routes_are_removed(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/api/v1/auth/mfa/enroll", "/api/v1/auth/mfa/verify"])
def test_mfa_routes_are_removed(client, session_factory, path):
    create_user(session_factory, "local-user", "Local-password-42!")
    _, headers = sign_in(client, "local-user")
    assert client.post(path, headers=headers, json={}).status_code == 404


def test_local_provisioning_preserves_existing_identity(session_factory):
    identifier = create_user(session_factory, "local-user", "Local-password-42!")
    with pytest.raises(ValueError):
        create_user(session_factory, "LOCAL-USER", "Replacement-password-42!")
    with pytest.raises(ValueError):
        create_user(session_factory, "another", "Local-password-42!", role="admin")
    with pytest.raises(ValueError):
        create_user(session_factory, "another", "short")
    with pytest.raises(ValueError, match="create-admin"):
        create_user(session_factory, "MKoenig", "Local-password-42!")
    with session_factory() as session:
        assert session.get(User, identifier).role == "user"


def test_create_user_cli_provisions_login_without_mail(
    client, session_factory, monkeypatch, capsys
):
    import io

    from pkdb.cli import main

    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(client.app.state.file_store.root))
    monkeypatch.setattr("sys.stdin", io.StringIO("Local-password-42!\n"))
    assert main(["create-user", "cli-user", "--password-stdin"]) == 0
    assert "Local-password-42!" not in capsys.readouterr().out
    assert sign_in(client, "cli-user")[0].status_code == 200
