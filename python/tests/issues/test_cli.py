import json

import pytest
from fake_github import FakeGitHub
from issue_fixtures import study

from pkdb.cli import main
from pkdb.schemas.curators import Curator


@pytest.fixture
def setup(tmp_path, monkeypatch):
    study(tmp_path, "caffeine/A", issue=1)
    github = FakeGitHub(issues=[{"number": 1, "title": "x"}], assignable=["ana-gh"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PKDB_ENDPOINT", "https://example.test")
    monkeypatch.setenv("PKDB_API_KEY", "pkdb_live_x")
    monkeypatch.setenv("GH_TOKEN", "token")
    monkeypatch.setattr(
        "pkdb.issues_cli.github_client", lambda repository, token: github.client()
    )
    monkeypatch.setattr(
        "pkdb.issues_cli.roster",
        lambda endpoint, api_key: [
            Curator(username="ana", name="Ana", github="ana-gh")
        ],
    )
    return github


def test_sync_changes_issues_and_reports_json(setup, capsys):
    assert main(["issues", "sync", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["applied"] == 1 and setup.issues[1]["title"] == "caffeine/A"


def test_a_dry_run_without_token_writes_nothing(setup, monkeypatch, capsys):
    monkeypatch.delenv("GH_TOKEN")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert main(["issues", "sync", "--dry-run", "--format", "human"]) == 0
    assert setup.writes == [] and "Dry run: 1 changes." in capsys.readouterr().out


def test_changes_need_a_token(setup, monkeypatch, capsys):
    monkeypatch.delenv("GH_TOKEN")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert main(["issues", "sync", "--format", "human"]) == 2
    assert "GH_TOKEN" in capsys.readouterr().err


def test_the_roster_needs_the_server(setup, monkeypatch, capsys):
    monkeypatch.delenv("PKDB_API_KEY")
    assert main(["issues", "sync", "--format", "human"]) == 2
    assert "PKDB_API_KEY" in capsys.readouterr().err


def test_adoption_needs_a_user_of_the_roster(setup, monkeypatch, capsys):
    monkeypatch.delenv("PKDB_USER", raising=False)
    assert main(["issues", "sync", "--adopt", "--format", "human"]) == 2
    assert (
        main(["issues", "sync", "--adopt", "--user", "zed", "--format", "human"]) == 2
    )
    assert "not in the PK-DB roster" in capsys.readouterr().err
    assert setup.writes == []


def test_adoption_writes_the_issue_number(setup, tmp_path, capsys):
    folder = study(tmp_path, "caffeine/B")
    setup.issues[2] = {
        "number": 2,
        "title": "Curate caffeine/B",
        "state": "open",
        "state_reason": None,
        "labels": [],
        "assignees": [],
    }
    assert (
        main(["issues", "sync", "--adopt", "--user", "ana", "--format", "human"]) == 0
    )
    assert '"issue": 2' in (folder / "study.json").read_text(encoding="utf-8")
    out = capsys.readouterr().out
    assert "caffeine/B: adopt #2, rename" in out
    assert "#1 caffeine/A: title, labels" in out
    assert "Changed 2 issues." in out
