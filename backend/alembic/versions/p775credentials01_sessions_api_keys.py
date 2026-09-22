"""Separate browser sessions and scoped API keys.

Revision ID: p775credentials01
Revises: p775profile01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p775credentials01"
down_revision = "p775profile01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("digest", sa.String(64), unique=True, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("authenticated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mfa_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("device", sa.String(200), nullable=False),
    )
    op.create_index("ix_browser_sessions_user_id", "browser_sessions", ["user_id"])
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("prefix", sa.String(24), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "rotated_from_id",
            sa.Integer(),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
        ),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])


def downgrade():
    op.drop_table("api_keys")
    op.drop_table("browser_sessions")
