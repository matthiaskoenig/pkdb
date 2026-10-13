"""Every test gets a copy of a migrated template database of its own."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import OperationalError

from pkdb_server.app import SCHEMA_REVISION
from pkdb_server.db.models.users import User
from tests.db_fixtures import CLONE_PROPERTY, STALE_SECONDS, owned_database


def test_a_test_database_is_a_migrated_copy_of_the_template(
    session_factory, template_database
):
    engine = session_factory.kw["bind"]
    assert engine.url.database != template_database
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT current_schema()")) == "public"
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == SCHEMA_REVISION
        )
        # a row that a migration inserts
        assert connection.scalar(text("SELECT id FROM security_configuration")) == 1


@pytest.mark.parametrize("attempt", [1, 2])
def test_no_test_sees_the_rows_of_another(session_factory, attempt):
    with session_factory.begin() as session:
        probe = select(func.count()).where(User.username == "isolation-probe")
        assert session.scalar(probe) == 0
        session.add(User(username="isolation-probe", role="curator"))


def test_the_template_refuses_connections(database_server, template_database):
    engine = create_engine(database_server.url.set(database=template_database))
    try:
        with pytest.raises(OperationalError, match="not currently accepting"):
            engine.connect()
    finally:
        engine.dispose()


def test_a_test_records_how_long_copying_its_database_took(request, session_factory):
    seconds = [
        value for name, value in request.node.user_properties if name == CLONE_PROPERTY
    ]
    assert len(seconds) == 1
    assert 0 <= seconds[0] < 60


def test_a_run_drops_the_databases_that_a_killed_run_left(database_server):
    stale = f"{database_server.prefix}_1000000000_{uuid4().hex[:12]}"
    recent = database_server.name()
    for name in (stale, recent):
        database_server.create(name=name)
    try:
        database_server.drop_stale(now=1000000000 + STALE_SECONDS + 1)
        names = database_server.names()
        assert stale not in names
        assert recent in names
    finally:
        for name in (stale, recent):
            database_server.drop(name)


def test_a_connection_left_open_does_not_keep_the_database(
    database_server, template_database
):
    url = database_server.create(template_database)
    # an engine that a test never disposed, as the pool of an app in a TestClient
    forgotten = create_engine(url)
    try:
        with owned_database(database_server, url) as factory:
            factory.kw["bind"].connect()
            forgotten.connect()
        assert url.database not in database_server.names()
    finally:
        forgotten.dispose()
