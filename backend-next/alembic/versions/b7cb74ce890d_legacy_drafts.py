"""Owned legacy draft generations and integer attachment aliases."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b7cb74ce890d"
down_revision = "594a61dbe9c3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "study_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sid", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("reference", postgresql.JSONB(), nullable=False),
        sa.Column("sealed", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("owner_id", "sid"),
    )
    op.create_index("ix_study_drafts_expires_at", "study_drafts", ["expires_at"])
    op.create_table(
        "reference_drafts",
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sid", sa.String(255), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_reference_drafts_expires_at", "reference_drafts", ["expires_at"]
    )
    op.create_table(
        "legacy_file_handles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "file_id",
            sa.Uuid(),
            sa.ForeignKey("files.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
    )


def downgrade():
    op.drop_table("legacy_file_handles")
    op.drop_table("reference_drafts")
    op.drop_table("study_drafts")
