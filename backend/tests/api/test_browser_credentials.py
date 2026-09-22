import pytest

from pkdb.db.models.users import EmailAddress, User
from pkdb.services.authentication import password_hash


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


def test_provider_link_callback_cleans_url_and_exposes_only_verified_identity(
    browser, monkeypatch
):
    from urllib.parse import parse_qs, urlsplit

    client, headers = browser
    assert login(client, headers).status_code == 200
    service = client.app.state.providers
    service.providers["github"] = {"client_id": "test", "client_secret": "test"}
    monkeypatch.setattr(
        service,
        "_exchange",
        lambda *args: {"subject": "12345", "label": "example-person"},
    )
    result = client.post("/api/v1/me/identities/github/link", headers=headers)
    assert result.status_code == 200
    state = parse_qs(urlsplit(result.json()["authorization_url"]).query)["state"][0]
    callback = f"/api/v1/auth/github/callback?state={state}&code=one-use-code"
    response = client.get(callback, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/account?oauth=linked"
    assert response.headers["cache-control"] == "no-store"
    profile = client.get("/api/v1/me").json()
    assert profile["github"] == "example-person"
    assert profile["github_provenance"] == "authenticated"
    assert (
        client.get(callback, follow_redirects=False).headers["location"]
        == "/account?oauth=error"
    )


@pytest.mark.parametrize(
    "field,value", [("access", "public"), ("licence", "closed"), ("creator", "mkoenig")]
)
def test_administrator_api_key_cannot_change_study_access_control(
    client, admin_headers, valid_bundle, session_factory, field, value
):
    import json
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from pkdb.db.models.credentials import ApiKey
    from pkdb.services.credentials import digest

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
