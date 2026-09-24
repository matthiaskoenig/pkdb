import secrets
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from pkdb_server.app import create_app
from pkdb_server.config import Settings
from pkdb_server.db.models.credentials import BrowserSession
from pkdb_server.db.models.limits import WorkLease
from pkdb_server.db.models.users import User
from pkdb_server.services.credentials import digest


def test_curator_request_requires_session_and_explicit_admin_decision(
    client, admin_headers, creator_headers, session_factory
):
    assert (
        client.post(
            "/api/v1/me/role-requests",
            headers=creator_headers,
            json={"reason": "Curate studies"},
        ).status_code
        == 403
    )
    raw = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        user = User(username="reader", role="user", active=True)
        session.add(user)
        session.flush()
        user_id = user.id
        session.add(
            BrowserSession(
                user_id=user.id,
                digest=digest(raw),
                last_seen_at=now,
                authenticated_at=now,
                expires_at=now + timedelta(days=7),
                device="test",
            )
        )
    headers = {
        "Cookie": f"pkdb_dev_session={raw}; pkdb_dev_csrf=csrf",
        "X-CSRF-Token": "csrf",
        "Origin": "http://localhost:8080",
    }
    response = client.post(
        "/api/v1/me/role-requests", headers=headers, json={"reason": "Curate studies"}
    )
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    assert (
        client.post(
            "/api/v1/me/role-requests", headers=headers, json={"reason": "Again"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/admin/role-requests/{identifier}",
            headers=headers,
            json={"status": "approved"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/admin/role-requests/{identifier}",
            headers=admin_headers,
            json={"status": "approved"},
        ).status_code
        == 200
    )
    with session_factory() as session:
        assert session.get(User, user_id).role == "curator"


def test_http_quota_releases_stream_lease_and_returns_retry_after(
    ingestion_context, session_factory
):
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion_context[0].file_store.root,
        quota_anonymous_per_minute=1,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/studies/").status_code == 200
        response = client.get("/api/v1/studies/")
        assert response.status_code == 429, response.text
        assert int(response.headers["retry-after"]) > 0
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(WorkLease)) == 0


def test_canonical_validation_does_not_echo_password(client):
    token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    secret = "do-not-echo-" * 200
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": token},
        json={"username": "missing", "password": secret},
    )
    assert response.status_code == 422
    assert "do-not-echo" not in response.text


def test_authenticated_http_bypasses_exhausted_limits(
    ingestion_context, session_factory, admin_headers, creator_headers
):
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion_context[0].file_store.root,
        quota_anonymous_per_minute=1,
        quota_ip_per_minute=1,
    )
    app = create_app(settings)
    with TestClient(app) as browser:
        assert browser.get("/api/v1/studies/").status_code == 200
        assert browser.get("/api/v1/studies/").status_code == 429
        for headers in (admin_headers, creator_headers):
            for _ in range(5):
                assert (
                    browser.get("/api/v1/studies/", headers=headers).status_code == 200
                )
        from pkdb_server.api.limits import UploadLimits

        middleware = app.middleware_stack
        while not isinstance(middleware, UploadLimits):
            middleware = getattr(middleware, "app")
        for _ in range(settings.upload_concurrency):
            assert middleware.slots.acquire(blocking=False)
        # Even a fully occupied anonymous upload gate cannot throttle a session.
        response = browser.post("/api/v2/studies/validate", headers=admin_headers)
        assert response.status_code == 422, response.text
        for _ in range(settings.upload_concurrency):
            middleware.slots.release()
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(WorkLease)) == 0
