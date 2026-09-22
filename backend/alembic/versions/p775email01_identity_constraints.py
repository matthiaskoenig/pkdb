"""Enforce one primary contact and case-insensitive username uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "p775email01"
down_revision = "p775limits01"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if (
        connection.execute(
            sa.text(
                "SELECT 1 FROM users GROUP BY lower(username) HAVING count(*) > 1 LIMIT 1"
            )
        ).scalar()
        is not None
    ):
        raise RuntimeError(
            "Case-insensitive duplicate usernames require operator review before migration; "
            "no accounts have been merged or renamed."
        )
    if (
        connection.execute(
            sa.text(
                "SELECT 1 FROM email_addresses WHERE is_primary GROUP BY user_id HAVING count(*) > 1 LIMIT 1"
            )
        ).scalar()
        is not None
    ):
        raise RuntimeError(
            "Accounts with multiple primary email addresses require operator review before migration; "
            "no contact addresses have been changed."
        )
    op.create_index(
        "uq_users_username_lower", "users", [sa.text("lower(username)")], unique=True
    )
    op.create_index(
        "uq_email_addresses_primary_user",
        "email_addresses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade():
    op.drop_index("uq_email_addresses_primary_user", table_name="email_addresses")
    op.drop_index("uq_users_username_lower", table_name="users")
