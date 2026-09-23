import pytest

from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.authentication import password_hash


@pytest.fixture
def browser(client, session_factory):
    with session_factory.begin() as session:
        user = User(
            username="browser-user",
            role="curator",
            active=True,
            password_hash=password_hash.hash("Browser-password-42"),
        )
        session.add(user)
        session.flush()
        session.add(
            EmailAddress(
                user_id=user.id,
                email="browser@example.org",
                is_primary=True,
                is_verified=True,
            )
        )
    challenge = client.get("/api/v1/auth/csrf")
    headers = {
        "Origin": client.app.state.browser_origin,
        "X-CSRF-Token": challenge.json()["csrf_token"],
    }
    return client, headers


def login(client, headers):
    return client.post(
        "/api/v1/auth/login",
        json={"username": "browser-user", "password": "Browser-password-42"},
        headers=headers,
    )


def test_login_requires_origin_and_csrf_and_uses_httponly_cookie(browser):
    client, headers = browser
    assert login(client, {}).status_code == 403
    assert (
        login(client, {**headers, "Origin": "https://untrusted.example"}).status_code
        == 403
    )
    result = login(client, headers)
    assert result.status_code == 200
    assert "token" not in result.json()
    assert "HttpOnly" in result.headers["set-cookie"]
    assert "SameSite=lax" in result.headers["set-cookie"]
    assert result.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/me/sessions").status_code == 200


def test_key_secret_shown_once_and_invalid_header_never_falls_back(browser):
    client, headers = browser
    assert login(client, headers).status_code == 200
    assert client.post("/api/v1/me/api-keys", json={"name": "test"}).status_code == 403
    result = client.post("/api/v1/me/api-keys", json={"name": "test"}, headers=headers)
    assert result.status_code == 201
    key = result.json()
    assert "secret" not in client.get("/api/v1/me/api-keys").json()[0]
    assert (
        client.get(
            "/api/v1/me/api-keys", headers={"Authorization": "Bearer invalid"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/me/api-keys", headers={"Authorization": f"Bearer {key['secret']}"}
        ).status_code
        == 403
    )
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/me/sessions").status_code == 401


@pytest.mark.parametrize(
    "field,value", [("access", "public"), ("licence", "closed"), ("creator", "mkoenig")]
)
def test_administrator_api_key_cannot_change_study_access_control(
    client, admin_headers, valid_bundle, session_factory, field, value
):
    import json
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from pkdb_server.db.models.credentials import ApiKey
    from pkdb_server.services.credentials import digest

    valid_bundle.study["licence"] = "open"
    endpoint = f"/api/v2/studies/{valid_bundle.study['sid']}"
    body = {
        "study": json.dumps(valid_bundle.study),
        "reference": json.dumps(valid_bundle.reference),
    }
    assert client.put(endpoint, headers=admin_headers, data=body).status_code == 201
    secret = "pkdb_live_test_administrator_key"
    with session_factory.begin() as session:
        user = session.scalar(select(User).where(User.username == "mkoenig"))
        session.add(
            ApiKey(
                user_id=user.id,
                name="admin uploader",
                prefix=secret[:17],
                digest=digest(secret),
                scopes=["read", "studies:write"],
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
    headers = {"Authorization": f"Bearer {secret}"}
    assert client.put(endpoint, headers=headers, data=body).status_code == 200
    valid_bundle.study[field] = value
    body["study"] = json.dumps(valid_bundle.study)
    assert client.put(endpoint, headers=headers, data=body).status_code == 403
