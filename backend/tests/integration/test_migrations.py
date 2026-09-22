from pathlib import Path

from alembic.config import Config
from sqlalchemy import select

from alembic import command
from pkdb.db.models.users import User


def test_forward_migrations_preserve_existing_users(session_factory):
    with session_factory.begin() as session:
        session.add(User(username="existing", role="user", active=False))
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    url = session_factory.kw["bind"].url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(config, "4fc4c2157761")
    command.upgrade(config, "head")
    command.check(config)
    with session_factory() as session:
        user = session.scalar(select(User).where(User.username == "existing"))
        assert user.first_name == ""
        assert not user.pending_verification


def test_reference_authors_have_public_identifiers(session_factory):
    from pkdb.db.models.studies import Author, Reference

    with session_factory.begin() as session:
        reference = Reference(sid="r", name="reference")
        session.add(reference)
        session.flush()
        author = Author(
            reference_id=reference.id, position=0, first_name="First", last_name="Last"
        )
        session.add(author)
        session.flush()
        assert author.id > 0
