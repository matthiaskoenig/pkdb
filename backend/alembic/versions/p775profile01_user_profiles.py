"""Minimal public profiles and managed avatar metadata."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "p775profile01"
down_revision = "p775grants01"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", "role", server_default="user")
    for name, length in [
        ("display_name", 200),
        ("affiliation", 250),
        ("title", 100),
        ("github", 39),
        ("orcid", 19),
        ("github_provenance", 16),
        ("orcid_provenance", 16),
        ("avatar_key", 32),
    ]:
        op.add_column("users", sa.Column(name, sa.String(length), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "profile_edited_fields",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "avatar_initialized",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        "UPDATE users SET display_name = NULLIF(TRIM(first_name || ' ' || last_name), '')"
    )
    op.create_table(
        "avatar_assets",
        sa.Column("key", sa.String(32), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_avatar_assets_user_id", "avatar_assets", ["user_id"])


def downgrade():
    op.drop_table("avatar_assets")
    for name in [
        "display_name",
        "affiliation",
        "title",
        "github",
        "orcid",
        "github_provenance",
        "orcid_provenance",
        "avatar_key",
        "avatar_initialized",
        "profile_edited_fields",
    ]:
        op.drop_column("users", name)
    op.alter_column("users", "role", server_default=None)
