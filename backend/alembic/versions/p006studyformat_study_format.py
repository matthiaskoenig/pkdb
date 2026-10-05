"""Study format 2: geometric and error-bar statistics, schedules, release and review."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p006studyformat"
down_revision = "p005vocabsearch"
branch_labels = None
depends_on = None

STATISTICS = ("gmean", "gsd", "gcv", "error_bar")
SCIENTIFIC_TABLES = ("observation_values", "interventions")


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
    for table in reversed(SCIENTIFIC_TABLES):
        op.drop_constraint(op.f(f"ck_{table}_error_type"), table, type_="check")
        for name in ("error_type", *reversed(STATISTICS)):
            op.drop_column(table, name)
