"""Every test owns a database of an explicitly configured PostgreSQL test server.

Each pytest process, so each xdist worker, migrates one template database once.
Every test gets a copy of it (`CREATE DATABASE ... TEMPLATE`), which takes
milliseconds where the migrations take far longer, and which holds the rows that
the migrations insert, so a test sees a freshly migrated database. The tests of
the migrations migrate an empty database themselves (`fresh_session_factory`).
"""

import os
import re
import statistics
import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.subjects import Group
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyNode
from pkdb_server.db.session import make_session_factory

# A run drops the test databases that a killed run left after this many seconds.
STALE_SECONDS = 6 * 60 * 60
# The test property with the seconds that copying the template took for a test.
CLONE_PROPERTY = "database_clone_seconds"
# The copy times of this run, collected from the reports of every worker.
_clone_seconds: list[float] = []


class DatabaseServer:
    """Creates and drops the databases of the tests beside the configured one.

    Their names start with the name of the configured database and hold the
    time of their creation, `<database>_<unix time>_<12 hex digits>`, and
    `<database>_tpl_<unix time>_<12 hex digits>` for a template, so that test
    runs of several checkouts on one server never touch each other's databases.
    """

    def __init__(self, url: URL, prefix: str | None = None) -> None:
        if not url.database:
            raise ValueError("PKDB_TEST_DATABASE_URL names no database")
        self.url = url
        # a prefix of its own keeps the databases of a test of this class apart
        self.prefix = prefix or url.database
        # Every connection of this run names its run, so that another run sees it.
        self._owner = f"pkdbt:{self.prefix}:{uuid4().hex[:8]}"
        if len(self._owner.encode()) > 63:
            raise ValueError(f"{self._owner} is longer than an application name may be")
        self.admin = create_engine(
            url,
            isolation_level="AUTOCOMMIT",
            connect_args={"application_name": self._owner},
        )
        # kept open until close(), so that the run stays visible to other runs
        self._keepalive = self.admin.connect()
        self._ours = re.compile(
            rf"{re.escape(self.prefix)}_(?:tpl_)?(\d{{10}})_[0-9a-f]{{12}}"
        )

    def name(self, kind: str = "") -> str:
        """A new database name: `kind` is "" for a test database, "tpl_" for a template."""
        name = f"{self.prefix}_{kind}{int(time.time())}_{uuid4().hex[:12]}"
        if len(name.encode()) > 63:
            raise ValueError(f"{name} is longer than a PostgreSQL name may be")
        return name

    def create(self, template: str = "template0", name: str | None = None) -> URL:
        """Create the database `name`, by default a new name, as a copy of `template`."""
        name = name or self.name()
        with self.admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{template}"'))
            # the run that owns the database, for drop_stale
            connection.execute(
                text(f"COMMENT ON DATABASE \"{name}\" IS '{self._owner}'")
            )
        return self.url.set(database=name)

    def drop(self, name: str) -> None:
        """Drop the database `name` and the connections that a test left open."""
        with self.admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))

    def names(self) -> set[str]:
        """The names of all databases of the server."""
        with self.admin.connect() as connection:
            return set(connection.scalars(text("SELECT datname FROM pg_database")))

    def drop_stale(self, now: float | None = None) -> list[str]:
        """Drop the test databases older than STALE_SECONDS and return their names.

        A database whose creating run is still alive is never dropped, so a run that
        lasts longer than STALE_SECONDS keeps its databases. The run is alive while it
        keeps a connection named after it open, as DatabaseServer does until close().
        A database without a recorded run counts as left by a killed run.
        """
        now = time.time() if now is None else now
        with self.admin.connect() as connection:
            alive = set(
                connection.scalars(
                    text("SELECT DISTINCT application_name FROM pg_stat_activity")
                )
            )
            owners = dict(
                connection.execute(
                    text(
                        "SELECT datname, shobj_description(oid, 'pg_database') "
                        "FROM pg_database"
                    )
                ).all()
            )
        stale = sorted(
            name
            for name, owner in owners.items()
            if (match := self._ours.fullmatch(name))
            and now - int(match.group(1)) > STALE_SECONDS
            and (owner == self._owner or owner not in alive)
        )
        for name in stale:
            self.drop(name)
        return stale

    def close(self) -> None:
        self._keepalive.close()
        self.admin.dispose()


def migrate(url: URL) -> None:
    """Migrate the database of `url` to the head revision."""
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(config, "head")


@contextmanager
def owned_database(
    server: DatabaseServer, url: URL
) -> Generator[sessionmaker[Session]]:
    """A session factory of the database of `url`, which is dropped afterwards."""
    assert url.database
    try:
        factory = make_session_factory(url.render_as_string(hide_password=False))
        try:
            yield factory
        finally:
            factory.kw["bind"].dispose()
    finally:
        server.drop(url.database)


@pytest.fixture(scope="session")
def database_server() -> Iterator[DatabaseServer]:
    database_url = os.environ.get("PKDB_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "PKDB_TEST_DATABASE_URL must name an isolated PostgreSQL test database"
        )
    server = DatabaseServer(make_url(database_url))
    try:
        server.drop_stale()
        yield server
    finally:
        server.close()


@pytest.fixture(scope="session")
def template_database(database_server: DatabaseServer) -> Iterator[str]:
    """A database migrated to head once per pytest process, which every test copies.

    It refuses connections once migrated: a connection to it would make a copy fail.
    """
    name = database_server.name("tpl_")
    try:
        migrate(database_server.create(name=name))
        with database_server.admin.connect() as connection:
            connection.execute(
                text(f'ALTER DATABASE "{name}" WITH ALLOW_CONNECTIONS false')
            )
        yield name
    finally:
        database_server.drop(name)


@pytest.fixture
def session_factory(
    request: pytest.FixtureRequest,
    database_server: DatabaseServer,
    template_database: str,
) -> Iterator[sessionmaker[Session]]:
    """The session factory of a migrated database of this test alone."""
    start = time.perf_counter()
    url = database_server.create(template_database)
    request.node.user_properties.append((CLONE_PROPERTY, time.perf_counter() - start))
    with owned_database(database_server, url) as factory:
        yield factory


@pytest.fixture
def fresh_session_factory(
    database_server: DatabaseServer,
) -> Iterator[sessionmaker[Session]]:
    """The session factory of an empty database that is migrated for this test.

    For the tests of the migrations, which must not start from the template.
    """
    url = database_server.create()
    with owned_database(database_server, url) as factory:
        migrate(url)
        yield factory


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Collect the copy times; a parallel run gets the reports of every worker."""
    if report.when == "setup":
        _clone_seconds.extend(
            value
            for name, value in report.user_properties
            if name == CLONE_PROPERTY and isinstance(value, float)
        )


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Report how long the copies of the template took, the cost of a test database."""
    if _clone_seconds:
        count = len(_clone_seconds)
        terminalreporter.write_line(
            f"test databases: {count} {'copy' if count == 1 else 'copies'} of the template, "
            f"median {statistics.median(_clone_seconds) * 1000:.0f} ms, "
            f"max {max(_clone_seconds) * 1000:.0f} ms"
        )


@pytest.fixture
def db_session(session_factory):
    with session_factory.kw["bind"].connect() as connection:
        transaction = connection.begin()
        try:
            with Session(
                connection, join_transaction_mode="create_savepoint"
            ) as session:
                yield session
        finally:
            transaction.rollback()


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


@pytest.fixture
def ingestion_context(session_factory, tmp_path, vocabulary):
    import json

    from pkdb.schemas.security import Principal
    from pkdb_server.config import Settings
    from pkdb_server.db.bootstrap import bootstrap
    from pkdb_server.files.store import FileStore
    from pkdb_server.services.ingestion import IngestionService

    nodes = []
    for rule in vocabulary.measurements:
        nodes.append(
            dict(
                sid=rule.sid or rule.name,
                name=rule.name,
                kind="measurement",
                definition=rule.model_dump(mode="json", exclude={"sid", "name"}),
            )
        )
    for substance in vocabulary.substances:
        nodes.append(
            dict(
                sid=substance.sid,
                name=substance.name,
                kind="substance",
                definition=substance.model_dump(mode="json", exclude={"sid", "name"}),
            )
        )
    for field, kind in [
        ("tissues", "tissue"),
        ("methods", "method"),
        ("routes", "route"),
        ("forms", "form"),
        ("applications", "application"),
        ("calculation_types", "calculation_type"),
    ]:
        nodes.extend(
            dict(sid=name, name=name, kind=kind) for name in getattr(vocabulary, field)
        )
    (tmp_path / "users.json").write_text(
        json.dumps([dict(username="curator", role="curator")])
    )
    (tmp_path / "vocabulary.json").write_text(
        json.dumps(dict(version="test", nodes=nodes))
    )
    with session_factory.begin() as session:
        assert not bootstrap(tmp_path, session).errors
        user = session.scalar(select(User).where(User.username == "curator"))
        user.active = True
        principal = Principal(user_id=user.id, username=user.username, role=user.role)
    store = FileStore(tmp_path / "files", session_factory, 1024 * 1024)
    settings = Settings(
        database_url="postgresql+psycopg://unused", file_root=store.root
    )
    return IngestionService(session_factory, store, settings), principal


@pytest.fixture
def valid_bundle(valid_study):
    from pkdb.schemas.source import SourceBundle

    def scientific(record):
        result = record.model_dump(
            mode="json",
            exclude={
                "key",
                "statistics",
                "source",
                "origin",
                "calculated",
                "derived_from",
                "series_key",
                "time_not_reported",
                "time_unit_not_reported",
            },
            exclude_none=True,
        )
        result.update(record.statistics.model_dump(exclude_none=True))
        return result

    study = valid_study.metadata.model_dump(mode="json", exclude_none=True)
    study.update(sid=valid_study.sid, reference=valid_study.reference.sid)
    study["groupset"] = {
        "groups": [
            dict(
                name=g.name,
                count=g.count,
                characteristica=[scientific(c) for c in g.characteristica],
            )
            for g in valid_study.groups
        ]
    }
    study["interventionset"] = {
        "interventions": [scientific(i) for i in valid_study.interventions]
    }
    study["outputset"] = {"outputs": [scientific(m) for m in valid_study.measurements]}
    return SourceBundle(
        study=study,
        reference=valid_study.reference.model_dump(mode="json", exclude_none=True),
    )
