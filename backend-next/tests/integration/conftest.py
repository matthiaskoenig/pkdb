"""Every test run owns a random schema in an explicitly configured test database."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from alembic import command
from pkdb.db.models.studies import Study
from pkdb.db.models.subjects import Group
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyNode
from pkdb.db.session import make_session_factory


@pytest.fixture(scope="session")
def session_factory():
    database_url = os.environ.get("PKDB_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "PKDB_TEST_DATABASE_URL must name an isolated PostgreSQL test database"
        )
    schema = f"test_{uuid4().hex}"
    admin = create_engine(database_url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(database_url).update_query_dict(
        {"options": f"-csearch_path={schema}"}
    )
    factory = make_session_factory(url.render_as_string(hide_password=False))
    try:
        config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
        config.set_main_option(
            "sqlalchemy.url",
            url.render_as_string(hide_password=False).replace("%", "%%"),
        )
        command.upgrade(config, "head")
        yield factory
    finally:
        factory.kw["bind"].dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def db_session(session_factory):
    with session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def schema_seed(db_session):
    user = User(username="curator", role="curator")
    db_session.add_all(
        [
            user,
            VocabularyNode(
                sid="concentration", name="concentration", kind="measurement"
            ),
        ]
    )
    db_session.flush()
    first = Study(
        sid="S1", name="one", access="public", licence="open", creator_id=user.id
    )
    second = Study(
        sid="S2", name="two", access="private", licence="closed", creator_id=user.id
    )
    db_session.add_all([first, second])
    db_session.flush()
    group = Group(study_id=first.id, key="g1", name="all", count=2)
    db_session.add_all(
        [group, Group(study_id=second.id, key="g1", name="all", count=3)]
    )
    db_session.flush()
    return first.id, second.id, group.id
