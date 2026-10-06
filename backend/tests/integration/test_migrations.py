from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from alembic import command
from pkdb_server.app import SCHEMA_REVISION
from pkdb_server.db.models import Base


def alembic_config(session_factory):
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        session_factory.kw["bind"]
        .url.render_as_string(hide_password=False)
        .replace("%", "%%"),
    )
    return config


def test_initial_schema_round_trip(session_factory):
    engine = session_factory.kw["bind"]
    config = alembic_config(session_factory)
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [SCHEMA_REVISION]
    assert len(list(scripts.walk_revisions())) == 6
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
    config = alembic_config(session_factory)
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


STUDY_FORMAT_COLUMNS = {
    "studies": {"pkdb_id", "release_date", "issue", "review_status", "review"},
    "interventions": {
        "gmean",
        "gsd",
        "gcv",
        "error_bar",
        "error_type",
        "interval",
        "doses",
        "time_list",
        "subject_id",
    },
    "observation_values": {"gmean", "gsd", "gcv", "error_bar", "error_type"},
}


def search_index(session_factory):
    """The definition of the study text search index, as the database reports it."""
    with session_factory() as session:
        return session.execute(
            text(
                "SELECT indexdef FROM pg_indexes WHERE schemaname = current_schema() "
                "AND indexname = 'ix_studies_search'"
            )
        ).scalar_one()


def test_study_format_revision_round_trip_keeps_published_studies(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb_server.db.read import read_study

    ingestion, principal = ingestion_context
    published = ingestion.replace(valid_bundle, principal)
    before = read_study(published.sid, principal, session_factory)
    config = alembic_config(session_factory)
    current = search_index(session_factory)
    assert "pkdb_id" in current
    command.downgrade(config, "p005vocabsearch")
    with session_factory() as session:
        inspector = inspect(session.connection())
        for table, columns in STUDY_FORMAT_COLUMNS.items():
            names = {column["name"] for column in inspector.get_columns(table)}
            assert not columns & names
    before_revision = search_index(session_factory)
    assert "pkdb_id" not in before_revision
    command.upgrade(config, "head")
    command.check(config)
    with session_factory() as session:
        inspector = inspect(session.connection())
        for table, columns in STUDY_FORMAT_COLUMNS.items():
            names = {column["name"] for column in inspector.get_columns(table)}
            assert columns <= names
    assert read_study(published.sid, principal, session_factory) == before
    # The study text search index is rebuilt as it was, and as it is now.
    assert search_index(session_factory) == current
    command.downgrade(config, "p005vocabsearch")
    assert search_index(session_factory) == before_revision
    command.upgrade(config, "head")
    command.check(config)


VALUES = """
SELECT s.kind, o.kind, v.representation, v.value, v.mean
FROM observation_values v
JOIN observations o ON o.id = v.observation_id
JOIN subjects s ON s.id = o.subject_id
WHERE o.kind = 'output'
ORDER BY s.kind, v.representation
"""
SCHEDULES = """
SELECT name, origin, time, time_text, value, mean
FROM interventions ORDER BY name, origin
"""


def test_study_format_moves_value_into_mean_and_structures_schedules(
    ingestion_context, valid_bundle, session_factory
):
    ingestion, principal = ingestion_context
    study = valid_bundle.study
    dose = study["interventionset"]["interventions"][0]
    study["interventionset"]["interventions"] = [
        {**dose, "name": "list", "time": "0|12|40"},
        {**dose, "name": "series", "time": "S0T24R7"},
        {**dose, "name": "single", "time": 2.5},
    ]
    output = study["outputset"]["outputs"][0]
    output["interventions"] = ["single"]
    individual = {key: value for key, value in output.items() if key != "group"}
    study["outputset"]["outputs"].append(
        {**individual, "individual": "person", "mean": 3.0}
    )
    study["individualset"] = {"individuals": [{"name": "person", "group": "all"}]}
    ingestion.replace(valid_bundle, principal)
    config = alembic_config(session_factory)
    with session_factory.begin() as session:
        session.execute(
            text(
                "INSERT INTO vocabulary_nodes (sid, name, kind, definition) "
                "VALUES ('unspecified-summary', 'unspecified summary', "
                "'calculation_type', '{}')"
            )
        )
        session.execute(
            text(
                "UPDATE observations o SET calculation_type = 'unspecified-summary' "
                "FROM subjects s WHERE s.id = o.subject_id AND s.kind = 'group' "
                "AND o.kind = 'output'"
            )
        )

    command.downgrade(config, "p005vocabsearch")
    with session_factory.begin() as session:
        # Individual and unspecified-summary values return to value.
        assert session.execute(text(VALUES)).all() == [
            ("group", "output", "normalized", 2.0, None),
            ("group", "output", "reported", 2.0, None),
            ("individual", "output", "normalized", 3.0, None),
            ("individual", "output", "reported", 3.0, None),
        ]
        assert session.execute(text(SCHEDULES)).all() == [
            ("list", "normalized", None, "0|12|40", 10.0, None),
            ("list", "reported", None, "0|12|40", 10.0, None),
            ("series", "normalized", None, "S0T24R7", 10.0, None),
            ("series", "reported", None, "S0T24R7", 10.0, None),
            ("single", "normalized", 2.5, None, 10.0, None),
            ("single", "reported", 2.5, None, 10.0, None),
        ]
        # Version 8 data: a group value, a value next to a mean and a mixed list.
        session.execute(
            text(
                "UPDATE observations SET calculation_type = NULL WHERE kind = 'output'"
            )
        )
        session.execute(
            text(
                "UPDATE interventions SET value = 11, mean = 12 "
                "WHERE name = 'series' AND origin = 'normalized'"
            )
        )
        session.execute(
            text(
                "UPDATE interventions SET time = NULL, time_text = ' S-6T0.5R2 | 24 ' "
                "WHERE name = 'single'"
            )
        )
        broken = session.scalar(
            text(
                "UPDATE interventions SET time_text = 'S0T24' "
                "WHERE name = 'list' AND origin = 'reported' RETURNING id"
            )
        )
    with pytest.raises(RuntimeError, match=rf"\b{broken}\b"):
        command.upgrade(config, "head")
    with session_factory.begin() as session:
        assert (
            session.scalar(text("SELECT version_num FROM alembic_version"))
            == "p005vocabsearch"
        )
        session.execute(
            text("UPDATE interventions SET time_text = '0|12|40' WHERE id = :id"),
            {"id": broken},
        )
    command.upgrade(config, "head")
    command.check(config)
    with session_factory() as session:
        columns = {
            table: {
                column["name"]
                for column in inspect(session.connection()).get_columns(table)
            }
            for table in ("observation_values", "interventions")
        }
        assert "value" not in columns["observation_values"]
        assert not {"value", "time_text"} & columns["interventions"]
        assert session.execute(
            text(VALUES.replace("v.value, v.mean", "v.mean"))
        ).all() == [
            ("group", "output", "normalized", 2.0),
            ("group", "output", "reported", 2.0),
            ("individual", "output", "normalized", 3.0),
            ("individual", "output", "reported", 3.0),
        ]
        assert session.execute(
            text(
                "SELECT name, origin, time, time_list, interval, doses, mean "
                "FROM interventions ORDER BY name, origin"
            )
        ).all() == [
            ("list", "normalized", None, [0.0, 12.0, 40.0], None, None, 10.0),
            ("list", "reported", None, [0.0, 12.0, 40.0], None, None, 10.0),
            ("series", "normalized", 0.0, None, 24.0, 7, 12.0),
            ("series", "reported", 0.0, None, 24.0, 7, 10.0),
            ("single", "normalized", None, [-6.0, -5.5, 24.0], None, None, 10.0),
            ("single", "reported", None, [-6.0, -5.5, 24.0], None, None, 10.0),
        ]


CORPUS_SCHEDULES = [
    "0|12|40",
    "-6 | -5 | -4 | -3 | -2 | -1 | 0",
    "0|1|2|2|4|5|6|7",
    "0|24|10",
    "S0T12R3",
    "S-14T0R14",
    "S56T0.25R224",
    "S0T6R1",
    "S0T6R3 | S24T6R3 | S48T6R3 | S72T6R3 | S96T6R3 | S120T6R3 | 144",
    "S-72T1R1 | S-71T1R23 | S-48T24R2",
    "1e-7|2.5E+3|.5|5.|+1|-0",
    " 12 ",
    "\tS0T1R2\n",
]
INVALID_SCHEDULES = [
    "",
    " ",
    "S0T12",
    "0|",
    "a|1",
    "S0T12R0",
    "S0T-12R3",
    "s0t12r3",
    "1e400|1",
    "S0T1R10001|1",
    "S0T1R99999999999",
    "0" + chr(0xA0) + "|1",
]


def test_schedule_migration_matches_the_format_1_importer(
    ingestion_context, valid_bundle, session_factory
):
    from pkdb.importers.folder import PLAIN_NUMBER, WHITESPACE, parse_schedule

    ingestion, principal = ingestion_context
    ingestion.replace(valid_bundle, principal)
    config = alembic_config(session_factory)
    command.downgrade(config, "p005vocabsearch")
    columns = (
        "study_id, source, measurement_type, substance, calculation_type, choice, "
        "unit, value, origin, calculated, time_unit, route, application, form"
    )
    with session_factory.begin() as session:
        for index, schedule in enumerate([*CORPUS_SCHEDULES, None]):
            session.execute(
                text(
                    f"INSERT INTO interventions (key, name, time_text, {columns}) "
                    f"SELECT :key, :key, :schedule, {columns} FROM interventions "
                    "WHERE name = 'dose' AND origin = 'reported'"
                ),
                {"key": f"schedule-{index}", "schedule": schedule},
            )
        probe = session.scalar(
            text("SELECT id FROM interventions WHERE time_text IS NULL AND key = :key"),
            {"key": f"schedule-{len(CORPUS_SCHEDULES)}"},
        )
    for schedule in INVALID_SCHEDULES:
        with session_factory.begin() as session:
            session.execute(
                text("UPDATE interventions SET time_text = :schedule WHERE id = :id"),
                {"schedule": schedule, "id": probe},
            )
        with pytest.raises(RuntimeError, match=rf"interventions {probe};"):
            command.upgrade(config, "head")
        with pytest.raises(ValueError):
            parse_schedule(schedule.strip(WHITESPACE))
    with session_factory.begin() as session:
        session.execute(
            text("UPDATE interventions SET time_text = NULL WHERE id = :id"),
            {"id": probe},
        )
        session.execute(
            text(
                f"INSERT INTO interventions (key, name, time_text, {columns}) "
                f"SELECT 'many-' || n, 'many-' || n, 'S0T24', {columns} "
                "FROM interventions, generate_series(1, 101) AS n "
                "WHERE name = 'dose' AND origin = 'reported'"
            )
        )
    with pytest.raises(RuntimeError, match=r", \d+ and 1 more; correct"):
        command.upgrade(config, "head")
    with session_factory.begin() as session:
        session.execute(text("DELETE FROM interventions WHERE key LIKE 'many-%'"))
    command.upgrade(config, "head")
    with session_factory() as session:
        converted = {
            key: (time, times, interval, doses)
            for key, time, times, interval, doses in session.execute(
                text(
                    "SELECT key, time, time_list, interval, doses FROM interventions "
                    "WHERE key LIKE 'schedule-%'"
                )
            )
        }
    for index, schedule in enumerate(CORPUS_SCHEDULES):
        stripped = schedule.strip(WHITESPACE)
        expected = (
            {"time": float(stripped)}
            if PLAIN_NUMBER.fullmatch(stripped)
            else parse_schedule(schedule)
        )
        time = expected.get("time")
        assert converted[f"schedule-{index}"] == (
            None if isinstance(time, list) else time,
            time if isinstance(time, list) else None,
            expected.get("interval"),
            expected.get("doses"),
        ), schedule
