import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from pkdb_server.commands.admin import create_admin
from pkdb_server.commands.user_import import import_roster
from pkdb_server.db.models.security import SecurityConfiguration, UserImportRun
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.user_import import load_roster


def write_roster(tmp_path, users):
    path = tmp_path / "users.json"
    path.write_text(json.dumps(users))
    return path


def test_dry_run_then_apply_and_replay_preserve_later_demotion(
    session_factory, tmp_path
):
    path = write_roster(
        tmp_path,
        [
            {
                "username": "MariiaMysh",
                "role": "reviewer",
                "email": "reviewer@example.org",
            }
        ],
    )
    report = import_roster(path, session_factory)
    assert report["ok"] and not report["applied"]
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0
        assert session.scalar(select(func.count()).select_from(UserImportRun)) == 0
    assert import_roster(path, session_factory, apply=True)["applied"]
    with session_factory.begin() as session:
        user = session.scalar(select(User))
        assert (
            user.role == "reviewer" and not user.active and user.password_hash is None
        )
        assert not session.scalar(select(EmailAddress)).is_verified
        user.role = "user"
    report = import_roster(path, session_factory, apply=True, update_existing=True)
    assert report["already_applied"] and not report["applied"]
    with session_factory() as session:
        assert session.scalar(select(User)).role == "user"
        assert session.scalar(select(func.count()).select_from(UserImportRun)) == 1


def test_conflicts_roll_back_entire_batch_and_update_preserves_credentials(
    session_factory, tmp_path
):
    with session_factory.begin() as session:
        user = User(
            username="existing",
            role="user",
            active=False,
            password_hash="preserve-me",
            suspended_at=datetime.now(UTC),
            email="existing@example.org",
        )
        session.add(user)
        session.flush()
        existing_id = user.id
        session.add(
            EmailAddress(
                user_id=user.id, email=user.email, is_primary=True, is_verified=True
            )
        )
    path = write_roster(
        tmp_path,
        [
            {"username": "new", "role": "curator"},
            {
                "username": "existing",
                "role": "reviewer",
                "email": "existing@example.org",
                "user_id": existing_id,
            },
        ],
    )
    report = import_roster(path, session_factory, apply=True)
    assert not report["ok"]
    assert report["conflicts"][0]["reason"] == "role_change_requires_update_existing"
    with session_factory() as session:
        assert session.scalar(select(User.id).where(User.username == "new")) is None
    assert import_roster(path, session_factory, apply=True, update_existing=True)["ok"]
    with session_factory() as session:
        user = session.get(User, existing_id)
        assert user.role == "reviewer" and not user.active
        assert user.password_hash == "preserve-me"
        assert user.suspended_at is not None
        assert session.scalar(select(EmailAddress)).is_verified


def test_explicit_study_grants_and_missing_study_conflict(session_factory, tmp_path):
    with session_factory.begin() as session:
        user = User(username="curator", role="curator", active=True)
        study = Study(sid="S1", name="Study", access="public", licence="open")
        session.add_all([user, study])
        session.flush()
        user_id, study_id = user.id, study.id
    path = write_roster(
        tmp_path,
        [{"username": "curator", "role": "curator", "assigned_study_ids": [study_id]}],
    )
    assert not import_roster(path, session_factory, apply=True)["ok"]
    assert import_roster(path, session_factory, apply=True, update_existing=True)["ok"]
    with session_factory() as session:
        assert session.get(StudyGrant, (study_id, user_id, "curator"))
    path = write_roster(
        tmp_path,
        [{"username": "new", "role": "curator", "assigned_study_ids": [99999]}],
    )
    report = import_roster(path, session_factory, apply=True)
    assert report["conflicts"][0]["reason"] == "missing_study:99999"
    with session_factory() as session:
        assert session.scalar(select(User.id).where(User.username == "new")) is None


def test_private_contact_overlay_never_enters_report_or_ledger(
    session_factory, tmp_path
):
    path = write_roster(tmp_path, [{"username": "curator", "role": "curator"}])
    contacts = tmp_path / "contacts.csv"
    contacts.write_text("username,email\ncurator,private@example.org\n")
    report = import_roster(path, session_factory, contacts=contacts, apply=True)
    assert report["ok"]
    assert "private@example.org" not in json.dumps(report)
    with session_factory() as session:
        assert session.scalar(select(User)).email == "private@example.org"
        ledger = session.scalar(select(UserImportRun))
        assert "private@example.org" not in json.dumps(ledger.report)


def test_duplicate_contacts_and_identity_mismatch_block_import(
    session_factory, tmp_path
):
    path = write_roster(
        tmp_path,
        [
            {"username": "one", "email": "same@example.org"},
            {"username": "two", "email": "SAME@example.org", "user_id": 9999},
        ],
    )
    report = import_roster(path, session_factory, apply=True)
    assert {item["reason"] for item in report["conflicts"]} == {
        "duplicate_contact_in_roster",
        "explicit_user_id_mismatch",
    }
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 0


def test_public_roster_imports_named_reviewers_and_skips_admin_and_test(
    session_factory, tmp_path
):
    root = Path(__file__).resolve().parents[3]
    report = import_roster(
        root / "backend/bootstrap/curator-roster.json",
        session_factory,
        apply=True,
        file_root=tmp_path / "files",
        avatar_root=root / "frontend/public",
    )
    assert report["ok"], report["conflicts"]
    with session_factory() as session:
        assert set(
            session.scalars(select(User.username).where(User.role == "reviewer"))
        ) == {"MariiaMysh", "mii-halina", "shubhankarpalwankar"}
        assert (
            session.scalar(
                select(User.id).where(User.username.in_(["mkoenig", "reviewer"]))
            )
            is None
        )
        assert session.scalar(select(func.count()).select_from(User)) == 67
        assert session.scalar(
            select(User).where(User.username == "MariiaMysh")
        ).avatar_initialized
        assert not session.scalar(
            select(User).where(User.username == "MariiaMysh")
        ).active


def test_administrator_can_be_explicitly_adopted(session_factory):
    with session_factory.begin() as session:
        user = User(
            username="USERNAME",
            role="curator",
            email="admin@example.org",
            active=True,
            password_hash="preserve",
        )
        session.add(user)
        session.flush()
        user_id = user.id
    with pytest.raises(ValueError, match="Identity exists"):
        create_admin(session_factory, "USERNAME", "admin@example.org", "Password12345!")
    assert (
        create_admin(
            session_factory, "USERNAME", "admin@example.org", adopt_user_id=user_id
        )
        == user_id
    )
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user.role == "admin" and user.password_hash == "preserve"
        assert (
            session.get(SecurityConfiguration, 1).designated_administrator_id == user_id
        )


def test_admin_adoption_does_not_reactivate_disabled_account(session_factory):
    with session_factory.begin() as session:
        user = User(
            username="mkoenig", role="curator", email="admin@example.org", active=False
        )
        session.add(user)
        session.flush()
        user_id = user.id
    with pytest.raises(ValueError, match="must not reactivate"):
        create_admin(
            session_factory, "mkoenig", "admin@example.org", adopt_user_id=user_id
        )
    with session_factory() as session:
        assert not session.get(User, user_id).active
        assert session.get(User, user_id).role == "curator"


def test_import_input_rejects_privilege_bypass_and_unknown_contacts(tmp_path):
    for row in (
        {"username": "other", "role": "admin"},
        {"username": "mkoenig"},
        {"username": "reviewer"},
    ):
        with pytest.raises(ValueError):
            load_roster(write_roster(tmp_path, [row]))
    path = write_roster(tmp_path, [{"username": "one"}])
    contacts = tmp_path / "contacts.json"
    contacts.write_text(json.dumps([{"username": "unknown", "email": "x@example.org"}]))
    with pytest.raises(ValueError, match="unknown usernames"):
        load_roster(path, contacts)


def test_designated_administrator_profile_import_never_changes_identity_or_credentials(
    session_factory, tmp_path
):
    root = Path(__file__).resolve().parents[3]
    user_id = create_admin(
        session_factory, "mkoenig", "admin@example.org", "Long-strong-password!"
    )
    manifest = json.loads((root / "backend/bootstrap/curator-roster.json").read_text())
    admin_row = next(row for row in manifest["users"] if row["username"] == "mkoenig")
    path = write_roster(tmp_path, [admin_row])
    with session_factory() as session:
        original_password = session.get(User, user_id).password_hash
    report = import_roster(
        path,
        session_factory,
        apply=True,
        file_root=tmp_path / "files",
        avatar_root=root / "frontend/public",
    )
    assert report["ok"]
    assert report["operations"][0]["action"] == "administrator_profile_only"
    with session_factory() as session:
        user = session.get(User, user_id)
        assert user.avatar_initialized and user.display_name == "Matthias König"
        assert (
            user.role == "admin"
            and user.active
            and user.password_hash == original_password
        )
        assert (
            session.get(SecurityConfiguration, 1).designated_administrator_id == user_id
        )


def test_import_reports_case_collision_without_guessing_identity(
    session_factory, tmp_path
):
    with session_factory.begin() as session:
        session.add(User(username="Existing", role="user", active=False))
    path = write_roster(tmp_path, [{"username": "existing", "role": "curator"}])
    report = import_roster(path, session_factory)
    assert report["conflicts"] == [
        {"username": "existing", "reason": "case_insensitive_username_collision"}
    ]
    assert not import_roster(path, session_factory, apply=True, update_existing=True)[
        "applied"
    ]
    with session_factory() as session:
        assert list(session.scalars(select(User.username))) == ["Existing"]
