"""Separate effective permissions from scientific contributor attribution."""

import sqlalchemy as sa

from alembic import op

revision = "p775grants01"
down_revision = "276e94c58ad1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_grants",
        sa.Column(
            "study_id",
            sa.Integer(),
            sa.ForeignKey("studies.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(16), primary_key=True),
        sa.CheckConstraint(
            "role IN ('curator', 'collaborator')", name="ck_study_grants_role"
        ),
    )
    op.execute(
        "INSERT INTO study_grants (study_id, user_id, role) SELECT study_id, user_id, role FROM study_users"
    )
    # Preserve prior creator access explicitly; role checks still gate writes.
    op.execute(
        "INSERT INTO study_grants (study_id, user_id, role) SELECT id, creator_id, 'curator' FROM studies WHERE creator_id IS NOT NULL ON CONFLICT DO NOTHING"
    )


def downgrade():
    op.drop_table("study_grants")
