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
    assert len(list(scripts.walk_revisions())) == 2
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


def test_retirement_preserves_publication_files_and_attribution(
    ingestion_context, valid_bundle, session_factory
):
    import io

    from sqlalchemy import select

    from pkdb_server.db.models.files import StoredFile, StudyAttachment
    from pkdb_server.db.models.studies import Study, StudyGrant, StudyUser

    ingestion, principal = ingestion_context
    published = ingestion.replace(valid_bundle, principal)
    staged = ingestion.file_store.stage(
        principal, "figure.txt", io.BytesIO(b"preserved")
    )
    with session_factory.begin() as session:
        study = session.scalar(select(Study).where(Study.sid == published.sid))
        study_id = study.id
        session.add(
            StudyAttachment(study_id=study_id, file_id=staged.id, name="figure.txt")
        )
        session.add(
            StudyUser(study_id=study_id, user_id=principal.user_id, role="collaborator")
        )
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        session_factory.kw["bind"]
        .url.render_as_string(hide_password=False)
        .replace("%", "%%"),
    )
    command.downgrade(config, "p001initial")
    with session_factory.begin() as session:
        session.execute(
            text(
                "INSERT INTO study_grants (study_id, user_id, role) VALUES (:study, :user, 'collaborator')"
            ),
            {"study": study_id, "user": principal.user_id},
        )
        session.execute(
            text(
                "INSERT INTO reference_drafts (owner_id, sid, payload, expires_at) VALUES (:user, 'draft', '{}', now() + interval '1 day')"
            ),
            {"user": principal.user_id},
        )
        session.execute(
            text(
                "INSERT INTO study_drafts (id, owner_id, sid, payload, reference, sealed, expires_at) VALUES (:id, :user, 'draft', '{}', '{}', false, now() + interval '1 day')"
            ),
            {"user": principal.user_id, "id": staged.id},
        )
        session.execute(
            text("INSERT INTO legacy_file_handles (file_id) VALUES (:id)"),
            {"id": staged.id},
        )
    command.upgrade(config, "head")
    command.check(config)
    with session_factory() as session:
        assert session.get(Study, study_id).source_digest == published.digest
        assert session.get(StoredFile, staged.id) is not None
        assert (
            session.scalar(
                select(StudyAttachment.file_id).where(
                    StudyAttachment.study_id == study_id
                )
            )
            == staged.id
        )
        assert list(
            session.scalars(
                select(StudyGrant.role).where(StudyGrant.study_id == study_id)
            )
        ) == ["curator"]
        assert (
            "collaborator"
            in session.scalars(
                select(StudyUser.role).where(StudyUser.study_id == study_id)
            ).all()
        )
        assert not {"study_drafts", "reference_drafts", "legacy_file_handles"} & set(
            inspect(session.connection()).get_table_names()
        )
    with ingestion.file_store.open_authorized(principal, staged.id) as source:
        assert source.read() == b"preserved"
