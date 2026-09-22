"""Persist sole administrator designation and idempotent roster import history."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p775import01"
down_revision = "p775credentials01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("suspended_at", sa.DateTime(timezone=True)))
    # Multiple legacy administrators must be reviewed before applying this migration.
    op.create_index(
        "uq_users_sole_admin",
        "users",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'admin'"),
    )
    op.create_table(
        "security_configuration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "designated_administrator_id", sa.Integer(), sa.ForeignKey("users.id")
        ),
        sa.Column("legacy_token_cutoff", sa.DateTime(timezone=True)),
        sa.CheckConstraint("id = 1", name="ck_security_configuration_singleton"),
    )
    op.execute(
        "INSERT INTO security_configuration (id, legacy_token_cutoff) VALUES (1, CURRENT_TIMESTAMP + INTERVAL '30 days')"
    )
    op.create_table(
        "user_import_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("digest", sa.String(64), nullable=False, unique=True),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
    )


def downgrade():
    op.drop_table("user_import_runs")
    op.drop_table("security_configuration")
    op.drop_index("uq_users_sole_admin", table_name="users")
    op.drop_column("users", "suspended_at")
