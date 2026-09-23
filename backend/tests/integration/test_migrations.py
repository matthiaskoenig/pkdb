from pathlib import Path

from alembic.config import Config
from sqlalchemy import select

from alembic import command
from pkdb_server.db.models.users import User


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
    from pkdb_server.db.models.studies import Author, Reference

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


def test_password_auth_migration_preserves_profiles_and_revokes_old_sessions(
    session_factory,
):
    from sqlalchemy import inspect, text

    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    url = session_factory.kw["bind"].url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(config, "p775privacy01")
    with session_factory.begin() as session:
        identifier = session.scalar(
            text("""
            INSERT INTO users (username, role, active, password_hash, github, orcid,
                github_provenance, orcid_provenance)
            VALUES ('existing-login', 'user', true, 'preserved-hash', 'example-person',
                '0000-0002-1825-0097', 'authenticated', 'authenticated') RETURNING id
        """)
        )
        session.execute(
            text("""
            INSERT INTO browser_sessions (user_id, digest, last_seen_at, authenticated_at, expires_at, device)
            VALUES (:user_id, 'old-provider-session', now(), now(), now() + interval '7 days', 'Browser')
        """),
            {"user_id": identifier},
        )
        session.execute(
            text("""
            INSERT INTO external_identities (user_id, provider, issuer, subject, label)
            VALUES (:user_id, 'github', 'https://github.com', '12345', 'example-person')
        """),
            {"user_id": identifier},
        )
        session.execute(
            text("""
            INSERT INTO mfa_credentials (user_id, encrypted_secret, confirmed, last_step, recovery_digests)
            VALUES (:user_id, 'obsolete-secret', true, 0, '[]')
        """),
            {"user_id": identifier},
        )
    command.upgrade(config, "head")
    command.check(config)
    with session_factory() as session:
        user = session.get(User, identifier)
        assert user.password_hash == "preserved-hash" and user.active
        assert user.github == "example-person" and user.orcid == "0000-0002-1825-0097"
        assert user.github_provenance == user.orcid_provenance == "self_asserted"
        assert (
            session.scalar(text("SELECT revoked_at FROM browser_sessions")) is not None
        )
        tables = inspect(session.connection()).get_table_names()
        assert not {
            "external_identities",
            "oauth_transactions",
            "mfa_credentials",
        } & set(tables)
