"""External identities and one-use OAuth transactions.

Revision ID: p775providers01
Revises: p775mfa01
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p775providers01"
down_revision = "p775mfa01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "external_identities",
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
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("issuer", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.UniqueConstraint("provider", "issuer", "subject"),
        sa.UniqueConstraint("user_id", "provider"),
    )
    op.create_index(
        "ix_external_identities_user_id", "external_identities", ["user_id"]
    )
    op.create_table(
        "oauth_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("digest", sa.String(64), unique=True, nullable=False),
        sa.Column("browser_digest", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("intent", sa.String(16), nullable=False),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("browser_sessions.id", ondelete="CASCADE"),
        ),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("identity", postgresql.JSONB()),
        sa.Column("onboarding_digest", sa.String(64), unique=True),
    )

    op.create_index(
        "ix_oauth_transactions_expires_at", "oauth_transactions", ["expires_at"]
    )


def downgrade():
    op.drop_table("oauth_transactions")
    op.drop_table("external_identities")
