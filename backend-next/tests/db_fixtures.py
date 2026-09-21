"""Every test run owns a random schema in an explicitly configured test database."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from pkdb.db.models.studies import Study
from pkdb.db.models.subjects import Group
from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import VocabularyNode
from pkdb.db.session import make_session_factory


@pytest.fixture
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
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
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

    from pkdb.config import Settings
    from pkdb.db.bootstrap import bootstrap
    from pkdb.files.store import FileStore
    from pkdb.schemas.security import Principal
    from pkdb.services.ingestion import IngestionService

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
