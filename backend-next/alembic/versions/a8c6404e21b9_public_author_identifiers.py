"""Expose integer author identifiers while retaining reference order uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "a8c6404e21b9"
down_revision = "24471de5f5a4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "reference_authors",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
    )
    op.create_unique_constraint("uq_reference_authors_id", "reference_authors", ["id"])


def downgrade():
    op.drop_constraint("uq_reference_authors_id", "reference_authors", type_="unique")
    op.drop_column("reference_authors", "id")
