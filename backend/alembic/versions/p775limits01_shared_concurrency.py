"""Shared expiring work leases for cross-worker concurrency."""

import sqlalchemy as sa

from alembic import op

revision = "p775limits01"
down_revision = "p775providers01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_leases",
        sa.Column("request_id", sa.String(32), primary_key=True),
        sa.Column("bucket", sa.String(100), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_work_leases_expires_at", "work_leases", ["expires_at"])


def downgrade():
    op.drop_table("work_leases")
