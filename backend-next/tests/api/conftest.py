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
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def creator_headers(ingestion_context, session_factory):
    _, principal = ingestion_context
    with session_factory.begin() as session:
        token = issue_token(session.get(User, principal.user_id), session)
    return {"Authorization": f"Token {token}"}
