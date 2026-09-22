"""Typed analysis point identities and expiring saved query criteria."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "594a61dbe9c3"
down_revision = "8f512a96d470"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subset_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "study_id",
            sa.Integer(),
            sa.ForeignKey("studies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(512), nullable=False),
        sa.Column("source", postgresql.JSONB()),
        sa.Column("subset_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("study_id", "id"),
        sa.UniqueConstraint("study_id", "key"),
        sa.UniqueConstraint("study_id", "subset_id", "id"),
        sa.UniqueConstraint("subset_id", "position"),
        sa.ForeignKeyConstraint(
            ["study_id", "subset_id"],
            ["subsets.study_id", "subsets.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_subset_points_study_id", "subset_points", ["study_id"])
    op.add_column("subset_dimensions", sa.Column("point_id", sa.Integer()))
    op.execute("""INSERT INTO subset_points(study_id, subset_id, position, key)
        SELECT DISTINCT d.study_id, d.subset_id,
            d.position / greatest(jsonb_array_length(s.dimension_labels), 1),
            'subset:' || d.subset_id || ':point:' || (d.position / greatest(jsonb_array_length(s.dimension_labels), 1))
        FROM subset_dimensions d JOIN subsets s ON s.id = d.subset_id""")
    op.execute("""UPDATE subset_dimensions d SET point_id = p.id
        FROM subset_points p, subsets s WHERE s.id = d.subset_id AND p.subset_id = d.subset_id
        AND p.position = d.position / greatest(jsonb_array_length(s.dimension_labels), 1)""")
    op.alter_column("subset_dimensions", "point_id", nullable=False)
    op.create_foreign_key(
        "fk_subset_dimensions_study_id_subset_id_point_id_subset_points",
        "subset_dimensions",
        "subset_points",
        ["study_id", "subset_id", "point_id"],
        ["study_id", "subset_id", "id"],
        ondelete="CASCADE",
    )
    op.create_table(
        "saved_queries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")
        ),
        sa.Column("criteria", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_saved_queries_owner_id", "saved_queries", ["owner_id"])
    op.create_index("ix_saved_queries_expires_at", "saved_queries", ["expires_at"])


def downgrade():
    op.drop_table("saved_queries")
    op.drop_constraint(
        "fk_subset_dimensions_study_id_subset_id_point_id_subset_points",
        "subset_dimensions",
        type_="foreignkey",
    )
    op.drop_column("subset_dimensions", "point_id")
    op.drop_table("subset_points")
