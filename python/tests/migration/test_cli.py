import json
import os

import pytest
from migration_fixtures import v1_full_example

from pkdb.cli import main


def test_migrate_dry_run_prints_counts_and_exits_zero(
    tmp_path, monkeypatch, capsys, sf_vocabulary
):
    v1_full_example(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pkdb.migration_cli.bundled_vocabulary", lambda: sf_vocabulary)
    code = main(["migrate", "studies", "--dry-run", "--jobs", "1", "--format", "human"])
    out = capsys.readouterr().out
    assert code == 0
    assert "identical: 1" in out
    assert "Report: " in out and (tmp_path / "migration.md").exists()


def test_json_output_is_the_report(tmp_path, monkeypatch, capsys, sf_vocabulary):
    v1_full_example(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pkdb.migration_cli.bundled_vocabulary", lambda: sf_vocabulary)
    code = main(["migrate", "studies", "--dry-run", "--jobs", "1", "--format", "json"])
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["dry_run"] is True and len(report["studies"]) == 1


def test_a_registry_needs_an_approver(tmp_path, monkeypatch, capsys):
    v1_full_example(tmp_path)
    (tmp_path / "studies" / "study_identifiers.json").write_text(json.dumps({}))
    monkeypatch.chdir(tmp_path)
    code = main(["migrate", "studies", "--dry-run"])
    assert code == 2
    assert "--approver is required with a registry" in capsys.readouterr().err


def test_a_path_outside_a_checkout_is_an_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["migrate", "nowhere"])
    assert code == 2
    assert capsys.readouterr().err


def test_an_interrupted_run_exits_130(tmp_path, monkeypatch, capsys, sf_vocabulary):
    v1_full_example(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("pkdb.migration_cli.bundled_vocabulary", lambda: sf_vocabulary)

    def interrupted(*args, **options):
        raise KeyboardInterrupt

    monkeypatch.setattr("pkdb.migration.run.migrate", interrupted)
    assert main(["migrate", "studies", "--jobs", "1"]) == 130
    assert capsys.readouterr().err == (
        "Interrupted. migration.md lists the studies written so far. "
        "Run pkdb migrate again to finish or undo the interrupted swaps.\n"
    )


@pytest.mark.parametrize(
    ("report", "message"),
    [
        (
            "migration.md",
            "The report migration.md cannot end in .md, because the Markdown "
            "report is written next to it; name a .json file.\n",
        ),
        (
            "missing/migration.json",
            "The folder missing of the report does not exist.\n",
        ),
    ],
)
def test_a_report_path_that_cannot_be_written_is_refused_first(
    tmp_path, monkeypatch, capsys, report, message
):
    v1_full_example(tmp_path)
    monkeypatch.chdir(tmp_path)
    before = sorted(path.name for path in tmp_path.iterdir())
    assert main(["migrate", "studies", "--dry-run", "--report", report]) == 2
    assert capsys.readouterr().err == message
    assert sorted(path.name for path in tmp_path.iterdir()) == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into any folder")
def test_a_report_folder_that_is_not_writable_is_refused(tmp_path, monkeypatch, capsys):
    v1_full_example(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "locked").mkdir(mode=0o555)
    code = main(["migrate", "studies", "--dry-run", "--report", "locked/r.json"])
    assert code == 2
    assert (
        capsys.readouterr().err == "The folder locked of the report is not writable.\n"
    )
