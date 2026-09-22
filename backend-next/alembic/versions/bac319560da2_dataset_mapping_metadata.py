"""Retain source dimension labels and shared-field definitions for datasets."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "bac319560da2"
down_revision = "a8c6404e21b9"
branch_labels = None
depends_on = None


def upgrade():
    for name in ("shared_fields", "dimension_labels"):
        op.add_column(
            "subsets",
            sa.Column(name, postgresql.JSONB(), nullable=False, server_default="[]"),
        )


def downgrade():
    op.drop_column("subsets", "dimension_labels")
    op.drop_column("subsets", "shared_fields")
