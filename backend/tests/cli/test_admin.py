"""The first administrator is provisioned locally with hashed credentials."""

import pytest
from sqlalchemy import select

from pkdb_server.commands.admin import create_admin
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.authentication import authenticate_password


def test_local_admin_creation_hashes_password_and_verifies_email(session_factory):
    create_admin(
        session_factory, "USERNAME", "operator@example.test", "Initial-password-42!"
    )
    with session_factory() as session:
        user = authenticate_password("USERNAME", "Initial-password-42!", session)
        assert user.role == "admin" and user.active
        assert user.password_hash != "Initial-password-42!"
        email = session.scalar(
            select(EmailAddress).where(EmailAddress.user_id == user.id)
        )
        assert email is not None and email.is_primary and email.is_verified


def test_existing_identity_is_not_silently_elevated_or_rekeyed(session_factory):
    with session_factory.begin() as session:
        session.add(User(username="existing", role="user", active=False))
    with pytest.raises(ValueError):
        create_admin(
            session_factory, "existing", "operator@example.test", "Initial-password-42!"
        )
    with session_factory() as session:
        user = session.scalar(select(User).where(User.username == "existing"))
        assert user.role == "user" and not user.active and user.password_hash is None


def test_short_admin_password_leaves_no_account(session_factory):
    with pytest.raises(ValueError):
        create_admin(session_factory, "USERNAME", "operator@example.test", "short")
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "USERNAME")) is None


def test_admin_cli_accepts_protected_stdin_and_never_prints_password(
    session_factory, tmp_path, monkeypatch, capsys
):
    import io
    import json

    from pkdb_server.cli import main

    password = "Private-administrator-password-42!"
    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(password + "\n"))
    assert (
        main(
            [
                "create-admin",
                "USERNAME",
                "--email",
                "operator@example.test",
                "--password-stdin",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert password not in output
    assert json.loads(output) == {"ok": True, "username": "USERNAME"}
    with session_factory() as session:
        assert authenticate_password("USERNAME", password, session).role == "admin"


def test_second_administrator_is_rejected(session_factory):
    create_admin(session_factory, "USERNAME", "first@example.org", "Password12345!")
    with pytest.raises(ValueError, match="conflicting legacy administrators"):
        create_admin(session_factory, "another", "second@example.org", "Password12345!")
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "another")) is None
