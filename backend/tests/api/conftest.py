import pytest
from fastapi.testclient import TestClient

from pkdb.app import create_app
from pkdb.config import Settings
from pkdb.db.models.users import User
from pkdb.services.authentication import issue_token


@pytest.fixture
def client(ingestion_context, session_factory):
    ingestion, principal = ingestion_context
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion.file_store.root,
        rate_limits_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def creator_headers(ingestion_context, session_factory):
    _, principal = ingestion_context
    with session_factory.begin() as session:
        token = issue_token(session.get(User, principal.user_id), session)
    return {"Authorization": f"Token {token}"}


@pytest.fixture
def admin_headers(session_factory):
    import secrets
    from datetime import UTC, datetime, timedelta

    from pkdb.db.models.credentials import BrowserSession
    from pkdb.db.models.security import SecurityConfiguration
    from pkdb.services.credentials import digest

    with session_factory.begin() as session:
        user = User(username="mkoenig", role="admin", active=True)
        session.add(user)
        session.flush()
        config = session.get(SecurityConfiguration, 1)
        if config is None:
            config = SecurityConfiguration(id=1)
            session.add(config)
        config.designated_administrator_id = user.id
        raw = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
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
    return {
        "Cookie": f"pkdb_dev_session={raw}; pkdb_dev_csrf=test-csrf",
        "X-CSRF-Token": "test-csrf",
        "Origin": "http://localhost:8080",
    }
