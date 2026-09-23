"""Local study bootstrap preserves attribution without enabling accounts."""

import json
from copy import deepcopy

from sqlalchemy import select

from pkdb_server.cli import main
from pkdb_server.db.models.users import User


def test_bootstrap_study_creates_disabled_identities_and_preserves_accounts(
    session_factory, valid_bundle, tmp_path, monkeypatch, capsys
):
    study = deepcopy(valid_bundle.study)
    study["comments"] = [["comment-author", "Study comment"]]
    source = tmp_path / "Example"
    source.mkdir()
    (source / "study.json").write_text(json.dumps(study))
    (source / "reference.json").write_text(json.dumps(valid_bundle.reference))
    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(tmp_path / "files"))
    with session_factory.begin() as session:
        session.add(
            User(
                username="curator", role="admin", active=True, password_hash="existing"
            )
        )
    assert main(["bootstrap-study", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["inserted"] == 1
    with session_factory() as session:
        users = {user.username: user for user in session.scalars(select(User))}
        assert users["curator"].role == "admin" and users["curator"].active
        assert users["curator"].password_hash == "existing"
        assert users["comment-author"].role == "user"
        assert not users["comment-author"].active
        assert users["comment-author"].password_hash is None
    assert main(["bootstrap-study", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["inserted"] == 0


def test_bootstrap_study_validates_all_folders_before_creating_accounts(
    session_factory, valid_bundle, tmp_path, monkeypatch, capsys
):
    for name in ("first", "second"):
        source = tmp_path / name
        source.mkdir()
        study = deepcopy(valid_bundle.study)
        study["creator"] = name
        study["name"] = name
        (source / "study.json").write_text(json.dumps(study))
        if name == "first":
            (source / "reference.json").write_text(json.dumps(valid_bundle.reference))
    monkeypatch.setenv(
        "PKDB_DATABASE_URL",
        session_factory.kw["bind"].url.render_as_string(hide_password=False),
    )
    monkeypatch.setenv("PKDB_FILE_ROOT", str(tmp_path / "files"))
    assert main(["bootstrap-study", str(tmp_path)]) == 1
    assert not json.loads(capsys.readouterr().out)["ok"]
    with session_factory() as session:
        assert list(session.scalars(select(User))) == []
