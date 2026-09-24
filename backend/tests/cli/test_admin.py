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


def test_admin_cli_explains_existing_administrator_without_changing_accounts(
    session_factory, tmp_path, monkeypatch, capsys
):
    import io
    import json

    from pkdb_server.cli import main

    create_admin(session_factory, "tester", "tester@example.org", "Password12345!")
    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO("Private-password-42!\n"))
    assert (
        main(
            [
                "create-admin",
                "mkoenit",
                "--email",
                "operator@example.org",
                "--password-stdin",
            ]
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "Private-password-42!" not in output
    result = json.loads(output)
    assert result["ok"] is False
    assert "conflicting legacy administrators" in result["error"]
    with session_factory() as session:
        assert session.scalar(select(User).where(User.username == "mkoenit")) is None
        assert (
            session.scalar(select(User).where(User.username == "tester")).role
            == "admin"
        )


@pytest.mark.parametrize(
    ("username", "email", "password", "expected"),
    [
        (
            "mkoenit",
            "operator@example.org",
            "short",
            "Password must contain between 8 and 1024 characters",
        ),
        (
            "mkoenit",
            "not-an-email",
            "Secret-password-42!",
            "Invalid administrator email address",
        ),
        (
            "invalid name",
            "operator@example.org",
            "Secret-password-42!",
            "Invalid username",
        ),
    ],
)
def test_admin_cli_reports_safe_input_errors(
    tmp_path, monkeypatch, capsys, username, email, password, expected
):
    import io
    import json

    from pkdb_server.cli import main

    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        "postgresql+psycopg://unused:database-secret@localhost/unused",
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(password + "\n"))
    assert main(["create-admin", username, "--email", email, "--password-stdin"]) == 1
    output = capsys.readouterr().out
    assert password not in output
    assert "database-secret" not in output
    assert json.loads(output) == {"ok": False, "error": expected}


def test_admin_cli_keeps_unexpected_configuration_errors_private(monkeypatch, capsys):
    import json

    from pkdb_server.cli import main

    def broken_factory(*args, **kwargs):
        raise ValueError("postgresql://operator:database-secret@localhost/pkdb")

    monkeypatch.setattr("pkdb_server.db.session.make_session_factory", broken_factory)
    assert main(["create-admin", "mkoenit", "--email", "operator@example.org"]) == 1
    output = capsys.readouterr().out
    assert "database-secret" not in output
    assert json.loads(output)["error"].startswith("Local administration failed")
