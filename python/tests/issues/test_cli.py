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


def test_a_run_from_a_subfolder_finds_the_checkout(setup, tmp_path, monkeypatch):
    sub = tmp_path / "studies" / "caffeine"
    monkeypatch.chdir(sub)
    assert main(["issues", "sync", "--format", "json"]) == 0
    assert setup.issues[1]["title"] == "caffeine/A"


def test_a_run_outside_a_checkout_is_a_usage_error(
    setup, tmp_path_factory, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path_factory.mktemp("empty"))
    assert main(["issues", "sync", "--format", "human"]) == 2
    assert "studies folder" in capsys.readouterr().err


def test_a_github_error_exits_1(setup, capsys):
    setup.fail[("GET", None)] = 401
    assert main(["issues", "sync", "--format", "human"]) == 1
    assert capsys.readouterr().err


def test_a_roster_error_exits_1(setup, monkeypatch, capsys):
    from pkdb.errors import ClientError

    def broken(endpoint, api_key):
        raise ClientError("Roster unavailable")

    monkeypatch.setattr("pkdb.issues_cli.roster", broken)
    assert main(["issues", "sync", "--format", "human"]) == 1
    assert "Roster unavailable" in capsys.readouterr().err


def test_errors_of_the_result_exit_1(setup, monkeypatch, capsys):
    setup.fail[("PATCH", 1)] = 500
    assert main(["issues", "sync", "--format", "human"]) == 1
    assert "Error:" in capsys.readouterr().err


def test_ctrl_c_exits_130(setup, monkeypatch):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("pkdb.issues.sync.sync", interrupt)
    assert main(["issues", "sync"]) == 130


@pytest.mark.parametrize("mode", ["success", "github", "roster"])
@pytest.mark.parametrize("output", ["human", "json"])
def test_secrets_never_appear_in_output(setup, monkeypatch, capsys, mode, output):
    from pkdb.errors import ClientError

    monkeypatch.setenv("GH_TOKEN", "ghp_SECRET_canary")
    monkeypatch.setenv("PKDB_API_KEY", "pkdb_live_SECRET_canary")
    if mode == "github":
        setup.fail[("GET", None)] = 401
    if mode == "roster":

        def broken(endpoint, api_key):
            raise ClientError("Roster unavailable")

        monkeypatch.setattr("pkdb.issues_cli.roster", broken)
    main(["issues", "sync", "--format", output])
    captured = capsys.readouterr()
    assert "SECRET_canary" not in captured.out + captured.err
