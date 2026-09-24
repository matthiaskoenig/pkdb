from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from alembic import command
from pkdb_server.app import SCHEMA_REVISION
from pkdb_server.db.models import Base


def test_initial_schema_round_trip(session_factory):
    engine = session_factory.kw["bind"]
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        engine.url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [SCHEMA_REVISION]
    assert len(list(scripts.walk_revisions())) == 1
    command.check(config)
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == SCHEMA_REVISION
        )
        assert connection.scalar(text("SELECT id FROM security_configuration")) == 1
        assert (
            connection.scalar(
                text(
                    "SELECT legacy_token_cutoff > CURRENT_TIMESTAMP FROM security_configuration"
                )
            )
            is True
        )
        assert set(inspect(connection).get_table_names()) == set(
            Base.metadata.tables
        ) | {"alembic_version"}
    command.downgrade(config, "base")
    with engine.connect() as connection:
        assert inspect(connection).get_table_names() == ["alembic_version"]
        assert inspect(connection).get_sequence_names() == []
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_proc WHERE pronamespace = current_schema()::regnamespace"
                )
            )
            == 0
        )
    command.upgrade(config, "head")
    command.check(config)


def test_reference_authors_have_public_identifiers(session_factory):
    from pkdb_server.db.models.studies import Author, Reference

    with session_factory.begin() as session:
        reference = Reference(sid="r", name="reference")
        session.add(reference)
        session.flush()
        author = Author(
            reference_id=reference.id, position=0, first_name="First", last_name="Last"
        )
        session.add(author)
        session.flush()
        assert author.id > 0
