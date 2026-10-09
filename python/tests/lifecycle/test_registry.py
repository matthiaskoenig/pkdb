import json
from datetime import date

from lifecycle_fixtures import released_study

from pkdb.cli import main
from pkdb.lifecycle.registry import duplicates, identifier, next_identifier, scan


def test_scan_lists_released_studies_and_issues(tmp_path):
    released_study(tmp_path, "caffeine/B", pkdb_id="PKDB00002", issue=7)
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001", issue=8)
    released_study(tmp_path, "codeine/C", issue=9)
    result = scan(tmp_path)
    assert [(r.pkdb_id, r.location, r.date) for r in result.released] == [
        ("PKDB00001", "caffeine/A", date(2026, 9, 28)),
        ("PKDB00002", "caffeine/B", date(2026, 9, 28)),
    ]
    assert result.issues == {7: ["caffeine/B"], 8: ["caffeine/A"], 9: ["codeine/C"]}
    assert duplicates(result) == [] and next_identifier(result, tmp_path) == 3
    assert identifier(3) == "PKDB00003"


def test_duplicates_are_named(tmp_path):
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001", issue=7)
    released_study(tmp_path, "caffeine/B", pkdb_id="PKDB00001", issue=7)
    assert duplicates(scan(tmp_path)) == [
        "Issue #7 is named by several studies: caffeine/A, caffeine/B",
        "PKDB00001 is the identifier of several studies: caffeine/A, caffeine/B",
    ]


def test_the_next_identifier_counts_the_registry_file(tmp_path):
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00004")
    (tmp_path / "studies" / "study_identifiers.json").write_text(
        json.dumps({"PKDB01237": ["albuterol/Guo2016", "2026-09-28"]}), encoding="utf-8"
    )
    assert next_identifier(scan(tmp_path), tmp_path) == 1238


def test_an_unreadable_study_is_an_error(tmp_path):
    folder = released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001")
    (folder / "study.json").write_text(
        '{"format": 2, "reference": 5}', encoding="utf-8"
    )
    result = scan(tmp_path)
    assert result.released == [] and result.errors[0].startswith("caffeine/A: ")


def test_registry_command_checks_duplicates(tmp_path, monkeypatch, capsys):
    released_study(tmp_path, "caffeine/A", pkdb_id="PKDB00001", issue=7)
    monkeypatch.chdir(tmp_path / "studies")
    assert main(["registry", "--format", "json"]) == 0
    assert (
        json.loads(capsys.readouterr().out)["released"][0]["location"] == "caffeine/A"
    )
    released_study(tmp_path, "caffeine/B", issue=7)
    assert main(["registry", "--check", "--format", "human"]) == 1
    assert "Issue #7" in capsys.readouterr().out


def test_registry_command_without_a_checkout_is_a_usage_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    assert main(["registry"]) == 2
    assert "studies folder" in capsys.readouterr().err
