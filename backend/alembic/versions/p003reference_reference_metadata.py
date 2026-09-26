"""Preserve publication date precision, corporate authors, and metadata provenance."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p003reference"
down_revision = "p002retirelegacy"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "references", sa.Column("publication_date", sa.String(10), nullable=True)
    )
    op.add_column(
        "references",
        sa.Column(
            "provenance", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
    )
    op.add_column(
        "reference_authors", sa.Column("organization", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("reference_authors", "organization")
    op.drop_column("references", "provenance")
    op.drop_column("references", "publication_date")
