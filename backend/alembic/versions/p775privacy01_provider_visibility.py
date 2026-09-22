"""Let users hide public provider references without disconnecting sign-in."""

import sqlalchemy as sa

from alembic import op

revision = "p775privacy01"
down_revision = "p775email01"
branch_labels = None
depends_on = None


def upgrade():
    for provider in ("github", "orcid"):
        op.add_column(
            "users",
            sa.Column(
                f"{provider}_visible",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade():
    for provider in ("orcid", "github"):
        op.drop_column("users", f"{provider}_visible")
