"""Study format 2: geometric and error-bar statistics, schedules, release and review.

The `value` statistic moves into `mean` and schedule strings (`time_text`) become
`time`, `time_list`, `interval` and `doses`. Interventions gain the observation
context of outputs and characteristics: tissue, method and not-reported times. Every study is re-uploaded with
processing version 9 afterwards, so the downgrade restores the version 8 columns
only as far as they are derivable.
"""

import logging

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p006studyformat"
down_revision = "p005vocabsearch"
branch_labels = None
depends_on = None

STATISTICS = ("gmean", "gsd", "gcv", "error_bar")
SCIENTIFIC_TABLES = ("observation_values", "interventions")
# Observation context that interventions share with outputs and characteristics.
CONTEXT_FLAGS = ("time_not_reported", "time_unit_not_reported")
CONTEXT_TERMS = ("tissue", "method")
# Row triggers on observation_values, disabled around the statistics UPDATE. This is
# required: the two deferred constraint triggers would queue one event per updated
# row, and PostgreSQL refuses the following DROP COLUMN while trigger events are
# pending in the transaction. It is also safe and keeps large tables fast: the
# identity check compares observation_id and the deferred checks return early for
# unchanged ids or rows without a course, so a statistics-only UPDATE cannot
# violate them.
OBSERVATION_TRIGGERS = (
    "observation_context_immutable",
    "observation_course_kind_valid",
    "dataset_member_delete_valid",
)
MAX_SCHEDULE_TIMES = 10_000
UNSIGNED = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
# The format 1 schedule grammar of pkdb.importers.folder.parse_schedule in SQL:
# a|b|c, S<start>T<interval>R<doses> and |-lists mixing both (expanded). A lone
# number is a single time. Invalid input returns no time and no time list.
SCHEDULE_FUNCTION = rf"""
CREATE FUNCTION p006_schedule(
    schedule text,
    OUT out_time double precision,
    OUT out_time_list double precision[],
    OUT out_interval double precision,
    OUT out_doses integer
) LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    parts text[] := string_to_array(schedule, '|');
    part text;
    series text[];
    start double precision;
    step double precision;
    repeat numeric;
    times double precision[] := '{{}}';
BEGIN
    IF cardinality(parts) = 0 THEN
        RETURN;
    END IF;
    FOREACH part IN ARRAY parts LOOP
        part := btrim(part, E' \t\n\r\f\v');
        series := regexp_match(part, '^S([-+]?{UNSIGNED})T({UNSIGNED})R([0-9]+)$');
        IF series IS NULL THEN
            IF part !~ '^[-+]?{UNSIGNED}$' THEN
                RETURN;
            END IF;
            IF cardinality(parts) = 1 THEN
                out_time := part::double precision;
                RETURN;
            END IF;
            times := times || part::double precision;
            CONTINUE;
        END IF;
        start := series[1]::double precision;
        step := series[2]::double precision;
        repeat := series[3]::numeric;
        IF repeat < 1 OR repeat > 2147483647 THEN
            RETURN;
        END IF;
        IF cardinality(parts) = 1 THEN
            out_time := start;
            out_interval := step;
            out_doses := repeat::integer;
            RETURN;
        END IF;
        IF cardinality(times) + repeat > {MAX_SCHEDULE_TIMES} THEN
            RETURN;
        END IF;
        times := times || ARRAY(
            SELECT start + step * k FROM generate_series(0, repeat::integer - 1) AS k
            ORDER BY k
        );
    END LOOP;
    IF cardinality(times) < 2 OR cardinality(times) > {MAX_SCHEDULE_TIMES} THEN
        RETURN;
    END IF;
    out_time_list := times;
EXCEPTION
    WHEN numeric_value_out_of_range OR invalid_text_representation THEN
        out_time := NULL;
        out_time_list := NULL;
        out_interval := NULL;
        out_doses := NULL;
END $$;
"""
SCHEDULES = """
FROM interventions AS source
CROSS JOIN LATERAL p006_schedule(source.time_text) AS parsed
WHERE source.time_text IS NOT NULL
"""
LISTED_IDS = 100
log = logging.getLogger("alembic.runtime.migration")


def listed(ids, total):
    """At most LISTED_IDS ids, then how many more there are."""
    text = ", ".join(map(str, ids[:LISTED_IDS]))
    return f"{text} and {total - LISTED_IDS} more" if total > LISTED_IDS else text


def set_observation_triggers(state):
    for trigger in OBSERVATION_TRIGGERS:
        op.execute(f"ALTER TABLE observation_values {state} TRIGGER {trigger}")


def move_values_into_mean():
    """Format 1 value (one subject or an unspecified summary) is now mean."""
    bind = op.get_bind()
    for table in SCIENTIFIC_TABLES:
        conflicts = bind.execute(
            sa.text(
                "SELECT id, count(*) OVER () FROM "
                + table
                + " WHERE value IS NOT NULL AND mean IS NOT NULL AND value <> mean"
                f" ORDER BY id LIMIT {LISTED_IDS}"
            )
        ).all()
        if conflicts:
            log.warning(
                "Keeping mean and discarding a different value in %s rows %s",
                table,
                listed([row[0] for row in conflicts], conflicts[0][1]),
            )
    set_observation_triggers("DISABLE")
    for table in SCIENTIFIC_TABLES:
        op.execute(
            f"UPDATE {table} SET mean = value WHERE mean IS NULL AND value IS NOT NULL"
        )
    set_observation_triggers("ENABLE")
    for table in SCIENTIFIC_TABLES:
        op.drop_column(table, "value")


def structure_schedules():
    """Convert schedule strings, refusing to drop any that cannot be converted."""
    bind = op.get_bind()
    op.execute(SCHEDULE_FUNCTION)
    invalid = bind.execute(
        sa.text(
            "SELECT source.id, count(*) OVER ()"
            + SCHEDULES
            + "AND parsed.out_time IS NULL AND parsed.out_time_list IS NULL "
            f"ORDER BY source.id LIMIT {LISTED_IDS}"
        )
    ).all()
    if invalid:
        raise RuntimeError(
            "Cannot convert the schedule (time_text) of interventions "
            f"{listed([row[0] for row in invalid], invalid[0][1])}; correct them "
            "to a|b|c or S<start>T<interval>R<doses> and upgrade again"
        )
    op.execute(
        """
        UPDATE interventions AS target
        SET "time" = parsed.out_time,
            time_list = parsed.out_time_list,
            "interval" = parsed.out_interval,
            doses = parsed.out_doses
        """
        + SCHEDULES
        + "AND target.id = source.id"
    )
    op.execute("DROP FUNCTION p006_schedule(text)")
    op.drop_column("interventions", "time_text")


def restore_values_and_schedule_text():
    """Version 8 kept one subject, unspecified summaries and doses in value."""
    op.add_column("observation_values", sa.Column("value", sa.Float(), nullable=True))
    op.add_column("interventions", sa.Column("value", sa.Float(), nullable=True))
    op.add_column("interventions", sa.Column("time_text", sa.String(), nullable=True))
    set_observation_triggers("DISABLE")
    op.execute(
        """
        UPDATE observation_values AS v
        SET value = v.mean, mean = NULL
        FROM observations AS o
        JOIN subjects AS s ON s.id = o.subject_id
        LEFT JOIN vocabulary_nodes AS c
            ON c.sid = o.calculation_type AND c.kind = 'calculation_type'
        WHERE o.id = v.observation_id
          AND v.mean IS NOT NULL
          AND (s.kind = 'individual' OR c.name = 'unspecified summary')
        """
    )
    set_observation_triggers("ENABLE")
    op.execute(
        "UPDATE interventions SET value = mean, mean = NULL WHERE mean IS NOT NULL"
    )
    # Shortest exact float text, so that the upgrade reads the same numbers back.
    op.execute("SET LOCAL extra_float_digits = 1")
    op.execute(
        "UPDATE interventions SET time_text = array_to_string(time_list, '|') "
        "WHERE time_list IS NOT NULL"
    )
    op.execute(
        """
        UPDATE interventions
        SET time_text = 'S' || "time" || 'T' || "interval" || 'R' || doses,
            "time" = NULL
        WHERE "time" IS NOT NULL AND "interval" IS NOT NULL AND doses IS NOT NULL
        """
    )


def upgrade():
    for table in SCIENTIFIC_TABLES:
        for name in STATISTICS:
            op.add_column(table, sa.Column(name, sa.Float(), nullable=True))
        op.add_column(table, sa.Column("error_type", sa.String(16), nullable=True))
        op.create_check_constraint(
            op.f(f"ck_{table}_error_type"),
            table,
            "error_type IN ('sd', 'se', 'gsd')",
        )
    op.add_column("interventions", sa.Column("interval", sa.Float(), nullable=True))
    op.add_column("interventions", sa.Column("doses", sa.Integer(), nullable=True))
    op.add_column(
        "interventions",
        sa.Column("time_list", postgresql.ARRAY(sa.Float()), nullable=True),
    )
    for name in CONTEXT_FLAGS:
        op.add_column(
            "interventions",
            sa.Column(name, sa.Boolean(), server_default="false", nullable=False),
        )
    for name in CONTEXT_TERMS:
        op.add_column("interventions", sa.Column(name, sa.String(255), nullable=True))
        op.create_foreign_key(
            op.f(f"fk_interventions_{name}_vocabulary_nodes"),
            "interventions",
            "vocabulary_nodes",
            [name],
            ["sid"],
        )
    op.add_column("interventions", sa.Column("subject_id", sa.Integer(), nullable=True))
    op.create_index("ix_interventions_subject_id", "interventions", ["subject_id"])
    op.create_foreign_key(
        op.f("fk_interventions_study_id_subject_id_subjects"),
        "interventions",
        "subjects",
        ["study_id", "subject_id"],
        ["study_id", "id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        op.f("ck_interventions_doses"), "interventions", "doses IS NULL OR doses >= 1"
    )
    op.create_check_constraint(
        op.f("ck_interventions_time_list"),
        "interventions",
        "time_list IS NULL OR (time IS NULL AND cardinality(time_list) >= 2)",
    )
    move_values_into_mean()
    structure_schedules()
    op.add_column("studies", sa.Column("pkdb_id", sa.String(16), nullable=True))
    op.add_column("studies", sa.Column("release_date", sa.Date(), nullable=True))
    op.add_column("studies", sa.Column("issue", sa.Integer(), nullable=True))
    op.add_column("studies", sa.Column("review_status", sa.String(16), nullable=True))
    op.add_column("studies", sa.Column("review", postgresql.JSONB(), nullable=True))
    op.create_unique_constraint(op.f("uq_studies_pkdb_id"), "studies", ["pkdb_id"])
    for name, condition in (
        ("pkdb_id", "pkdb_id ~ '^PKDB[0-9]{5}$'"),
        ("release", "(pkdb_id IS NULL) = (release_date IS NULL)"),
        ("issue", "issue IS NULL OR issue > 0"),
        ("review_status", "review_status IN ('draft', 'in_review', 'approved')"),
        ("review", "(review_status IS NULL) = (review IS NULL)"),
    ):
        op.create_check_constraint(op.f(f"ck_studies_{name}"), "studies", condition)


def downgrade():
    restore_values_and_schedule_text()
    for name in ("review", "review_status", "issue", "release", "pkdb_id"):
        op.drop_constraint(op.f(f"ck_studies_{name}"), "studies", type_="check")
    op.drop_constraint(op.f("uq_studies_pkdb_id"), "studies", type_="unique")
    for name in ("review", "review_status", "issue", "release_date", "pkdb_id"):
        op.drop_column("studies", name)
    for name in ("time_list", "doses"):
        op.drop_constraint(
            op.f(f"ck_interventions_{name}"), "interventions", type_="check"
        )
    op.drop_constraint(
        op.f("fk_interventions_study_id_subject_id_subjects"),
        "interventions",
        type_="foreignkey",
    )
    op.drop_index("ix_interventions_subject_id", table_name="interventions")
    for name in ("subject_id", "time_list", "doses", "interval"):
        op.drop_column("interventions", name)
    for name in reversed(CONTEXT_TERMS):
        op.drop_constraint(
            op.f(f"fk_interventions_{name}_vocabulary_nodes"),
            "interventions",
            type_="foreignkey",
        )
        op.drop_column("interventions", name)
    for name in reversed(CONTEXT_FLAGS):
        op.drop_column("interventions", name)
    for table in reversed(SCIENTIFIC_TABLES):
        op.drop_constraint(op.f(f"ck_{table}_error_type"), table, type_="check")
        for name in ("error_type", *reversed(STATISTICS)):
            op.drop_column(table, name)
