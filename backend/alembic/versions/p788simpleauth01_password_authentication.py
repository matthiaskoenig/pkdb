"""Remove external authentication and MFA while preserving profile references.

Existing provider-only accounts retain their identity and may set a password via
verified-email password reset. Downgrade restores empty authentication tables;
removed OAuth credentials and MFA secrets are intentionally not recoverable.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p788simpleauth01"
down_revision = "p775privacy01"
branch_labels = None
depends_on = None


def upgrade():
    # Old sessions may originate from a provider; require a fresh password login.
    op.execute(
        "UPDATE browser_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE revoked_at IS NULL"
    )
    # Retain every optional profile reference, but no longer claim authentication.
    op.execute(
        "UPDATE users SET github_provenance = 'self_asserted' "
        "WHERE github_provenance = 'authenticated'"
    )
    op.execute(
        "UPDATE users SET orcid_provenance = 'self_asserted' "
        "WHERE orcid_provenance = 'authenticated'"
    )
    op.drop_table("oauth_transactions")
    op.drop_table("external_identities")
    op.drop_table("mfa_credentials")
    op.drop_column("browser_sessions", "mfa_at")


def downgrade():
    op.add_column("browser_sessions", sa.Column("mfa_at", sa.DateTime(timezone=True)))
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
