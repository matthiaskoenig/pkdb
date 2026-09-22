"""Administrator MFA and auditable security operations."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p775mfa01"
down_revision = "p775import01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mfa_credentials",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("encrypted_secret", sa.String(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("last_step", sa.Integer(), nullable=False),
        sa.Column("recovery_digests", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
    )

    op.create_table(
        "role_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_role_requests_user_id", "role_requests", ["user_id"])
    op.create_index(
        "uq_role_requests_pending",
        "role_requests",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade():
    op.drop_table("role_requests")
    op.drop_table("audit_events")
    op.drop_table("mfa_credentials")
