"""Retain source image provenance for subjects and interventions."""

import sqlalchemy as sa

from alembic import op

revision = "276e94c58ad1"
down_revision = "b7cb74ce890d"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("groups", "individuals", "interventions"):
        op.add_column(table, sa.Column("image", sa.String(), nullable=True))


def downgrade():
    for table in ("interventions", "individuals", "groups"):
        op.drop_column(table, "image")
