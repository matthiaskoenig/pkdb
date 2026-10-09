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
        "pkdb.issues_cli.github_client",
        lambda repository, token, **options: github.client(**options),
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
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "caffeine/B: adopted #2, renamed",
        "#1 caffeine/A: title, labels +caffeine +curate, assignees ana-gh",
        "#2 caffeine/B: labels +caffeine +curate, assignees ana-gh",
    ]
    assert captured.out == "Changed 2 issues.\n"


def test_json_output_has_no_progress(setup, capsys):
    assert main(["issues", "sync", "--format", "json"]) == 0
    assert capsys.readouterr().err == ""


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
    assert capsys.readouterr().err == (
        "Stopped: GitHub answered 401 for GET /repos/owner/data/issues: refused\n"
    )


def test_a_stopped_run_reports_what_was_done(setup, tmp_path, capsys):
    study(tmp_path, "caffeine/B", issue=2)
    setup.issues[2] = {**setup.issues[1], "number": 2}
    setup.fail[("PATCH", 2)] = 403
    assert main(["issues", "sync", "--format", "human"]) == 1
    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "#1 caffeine/A: title, labels +caffeine +curate, assignees ana-gh",
        "Stopped: GitHub answered 403 for PATCH /repos/owner/data/issues/2: refused",
    ]
    assert captured.out == "Changed 1 issues.\n"
    assert main(["issues", "sync", "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["stopped"].startswith("GitHub answered 403") and data["applied"] == 0


def test_waits_for_github_are_announced(setup, capsys):
    setup.fail[("PATCH", 1)] = 429
    assert main(["issues", "sync", "--format", "human"]) == 1
    err = capsys.readouterr().err.splitlines()
    assert err == [
        *["Waiting 60 seconds: GitHub limits the requests."] * 5,
        "Stopped: GitHub limits the requests; try again in 60 seconds",
    ]


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


@pytest.mark.parametrize("output", ["human", "json"])
def test_ctrl_c_during_the_sync_reports_what_was_done(
    setup, tmp_path, monkeypatch, capsys, output
):
    study(tmp_path, "caffeine/B", issue=2)
    setup.issues[2] = {**setup.issues[1], "number": 2}
    answer = setup.handler

    def handler(request):
        if request.url.path.endswith("/issues/2"):
            raise KeyboardInterrupt
        return answer(request)

    monkeypatch.setattr(setup, "handler", handler)
    assert main(["issues", "sync", "--format", output]) == 130
    captured = capsys.readouterr()
    if output == "json":
        data = json.loads(captured.out)
        assert data["stopped"] == "Interrupted." and data["applied"] == 1
    else:
        assert captured.err.splitlines()[-1] == "Interrupted."
        assert captured.out == "Changed 1 issues.\n"


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


def test_a_file_error_exits_1_after_naming_what_was_done(
    setup, tmp_path, monkeypatch, capsys
):
    from pkdb.issues import sync as sync_module

    study(tmp_path, "caffeine/B")
    study(tmp_path, "caffeine/C")
    write = sync_module.patch_metadata
    calls = []

    def write_once(*args, **kwargs):
        calls.append(args)
        if len(calls) > 1:
            raise OSError("No space left on device")
        return write(*args, **kwargs)

    monkeypatch.setattr("pkdb.issues.sync.patch_metadata", write_once)
    assert (
        main(["issues", "sync", "--adopt", "--user", "ana", "--format", "human"]) == 1
    )
    assert capsys.readouterr().err.splitlines() == [
        "caffeine/B: created #2",
        "Cannot sync the issues: No space left on device",
    ]
