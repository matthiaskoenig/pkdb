import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
