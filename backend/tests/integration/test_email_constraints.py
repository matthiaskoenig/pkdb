from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from pkdb_server.db.models.users import EmailAddress, User


def test_database_rejects_two_primary_email_addresses(session_factory):
    with session_factory.begin() as session:
        user = User(username="person")
        session.add(user)
        session.flush()
        user_id = user.id
        session.add(
            EmailAddress(
                user_id=user.id,
                email="first@example.org",
                is_primary=True,
                is_verified=True,
            )
        )
    with pytest.raises(IntegrityError):
        with session_factory.begin() as session:
            session.add(
                EmailAddress(
                    user_id=user_id,
                    email="second@example.org",
                    is_primary=True,
                    is_verified=True,
                )
            )
    with session_factory() as session:
        assert session.scalar(select(EmailAddress)).email == "first@example.org"


def test_database_rejects_case_insensitive_username_collision(session_factory):
    with session_factory.begin() as session:
        session.add(User(username="Curator"))
    with pytest.raises(IntegrityError):
        with session_factory.begin() as session:
            session.add(User(username="curator"))
    with session_factory() as session:
        assert list(session.scalars(select(User.username))) == ["Curator"]


@pytest.mark.parametrize("defect", ["username", "primary_email"])
def test_identity_migration_requires_operator_resolution_of_duplicates(
    session_factory, defect
):
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    url = session_factory.kw["bind"].url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(config, "p775limits01")
    # Exercise the historical schema independently of the current ORM model.
    with session_factory.begin() as session:
        user_id = session.scalar(
            text(
                "INSERT INTO users (username, active) VALUES ('Original', false) RETURNING id"
            )
        )
        if defect == "username":
            session.execute(
                text("INSERT INTO users (username, active) VALUES ('original', false)")
            )
        else:
            session.execute(
                text(
                    "INSERT INTO email_addresses (user_id, email, is_primary, is_verified) "
                    "VALUES (:user_id, :email, true, :verified)"
                ),
                [
                    {"user_id": user_id, "email": "one@example.org", "verified": True},
                    {"user_id": user_id, "email": "two@example.org", "verified": False},
                ],
            )
    with pytest.raises(RuntimeError, match="operator review"):
        command.upgrade(config, "head")
    with session_factory() as session:
        if defect == "username":
            assert set(session.scalars(text("SELECT username FROM users"))) == {
                "Original",
                "original",
            }
        else:
            assert (
                session.scalar(
                    text("SELECT count(*) FROM email_addresses WHERE is_primary")
                )
                == 2
            )
