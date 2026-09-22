"""Retain shared source identities for public subset provenance."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "d37e5b126084"
down_revision = "bac319560da2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "measurement_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "study_id",
            sa.Integer(),
            sa.ForeignKey("studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(512), nullable=False),
        sa.Column("source", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("study_id", "id"),
        sa.UniqueConstraint("study_id", "key"),
    )
    op.create_index(
        "ix_measurement_sources_study_id", "measurement_sources", ["study_id"]
    )
    op.add_column("measurements", sa.Column("source_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_measurements_study_id_source_id_measurement_sources",
        "measurements",
        "measurement_sources",
        ["study_id", "source_id"],
        ["study_id", "id"],
    )


def downgrade():
    op.drop_constraint(
        "fk_measurements_study_id_source_id_measurement_sources",
        "measurements",
        type_="foreignkey",
    )
    op.drop_column("measurements", "source_id")
    op.drop_table("measurement_sources")
