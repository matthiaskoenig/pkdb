"""The fixture workspace of the curation app end-to-end tests stays as its specs expect it.

The Playwright specs in frontend/tests/curation-e2e and the documentation screenshots rely on
exactly these deliberate problems, so a change of the library that moves them fails here first.
"""

import importlib.util
import json
from pathlib import Path

from pkdb.cache import bundled_vocabulary
from pkdb.studyformat.digitize import png_size
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.sync import sync_study
from pkdb.studyformat.validation import is_v2_folder, validate_folder

TESTING = Path(__file__).resolve().parents[2] / "tools/curation_testing"
FIXTURE = TESTING / "fixture/caffeine"

spec = importlib.util.spec_from_file_location(
    "curation_workspace", TESTING / "workspace.py"
)
assert spec is not None and spec.loader is not None
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)

large_spec = importlib.util.spec_from_file_location(
    "curation_large_workspace", TESTING / "large_workspace.py"
)
assert large_spec is not None and large_spec.loader is not None
large_workspace = importlib.util.module_from_spec(large_spec)
large_spec.loader.exec_module(large_workspace)


def problems(folder: Path) -> list[tuple]:
    report = validate_folder(folder, bundled_vocabulary())
    return [
        (
            issue.severity,
            issue.code,
            issue.source.file if issue.source else None,
            issue.source.row if issue.source else None,
            issue.source.header if issue.source else None,
        )
        for issue in report.issues
    ]


def test_demo_study_has_only_its_two_deliberate_warnings():
    assert sorted(problems(FIXTURE / "Demo2020")) == [
        ("warning", "digitized_mismatch", "timecourses_Fig1.tsv", 6, "mean"),
        ("warning", "unused_intervention", "interventions.tsv", 4, "name"),
    ]


def test_draft_study_has_one_deliberate_error():
    assert problems(FIXTURE / "Draft2021") == [
        ("error", "unknown_substance", "outputs_Tab1.tsv", 3, "substance"),
    ]


def test_fixture_studies_are_canonical_and_the_legacy_folder_is_format_1():
    for name in ("Demo2020", "Draft2021"):
        result = format_folder(FIXTURE / name, check=True)
        assert result.ok and not result.changes, name
    assert not is_v2_folder(FIXTURE / "Legacy1990")
    figure = (FIXTURE / "Demo2020/Demo2020_Fig1.png").read_bytes()
    assert png_size(figure) == (900, 600)


def test_workspace_copies_the_fixture_with_a_workbook_in_sync(tmp_path):
    target = workspace.create(tmp_path / "workspace")
    demo = target / "caffeine/Demo2020"
    assert (demo / "Demo2020.xlsx").is_file()
    assert not (target / "caffeine/Draft2021/Draft2021.xlsx").exists()
    result = sync_study(demo, bundled_vocabulary(), check=True)
    assert result.ok and result.workbook_action == "unchanged" and not result.changes


def test_large_workspace_generates_distinct_studies_that_validate_like_the_draft(
    tmp_path,
):
    target = large_workspace.create(tmp_path / "large", 50)
    folders = sorted(path.parent for path in target.glob("*/*/study.json"))
    assert len(folders) == 50
    assert len({folder.name for folder in folders}) == 50
    assert {folder.parent.name for folder in folders} == set(large_workspace.SUBSTANCES)
    assert all(is_v2_folder(folder) for folder in folders)
    statuses = {
        json.loads((folder / "review.json").read_text(encoding="utf-8"))["status"]
        for folder in folders
    }
    assert statuses == {"draft", "in_review", "approved"}
    # Study 1 has neither an issue nor a release: it validates exactly like the draft.
    second = target / large_workspace.SUBSTANCES[1] / large_workspace.study_name(1)
    assert sorted(path.name for path in second.iterdir()) == sorted(
        path.name.replace("Draft2021", second.name)
        for path in (FIXTURE / "Draft2021").iterdir()
    )
    result = format_folder(second, check=True)
    assert result.ok and not result.changes
    assert problems(second) == problems(FIXTURE / "Draft2021")


def test_large_workspace_names_one_surname_in_25_of_1000_studies(tmp_path):
    names = [large_workspace.study_name(index) for index in range(1000)]
    assert len(set(names)) == 1000
    assert sum("dahlqvist" in name.lower() for name in names) == 25
    target = large_workspace.create(tmp_path / "titles", 40)
    titles = [
        json.loads(path.read_text(encoding="utf-8"))["title"].lower()
        for path in target.glob("*/*/reference.json")
    ]
    assert len(titles) == 40 and not any("dahlqvist" in title for title in titles)


def test_large_workspace_writes_a_valid_review_for_each_status(tmp_path):
    target = large_workspace.create(tmp_path / "reviews", 12)
    seen: dict[str, Path] = {}
    for folder in sorted(path.parent for path in target.glob("*/*/study.json")):
        status = json.loads((folder / "review.json").read_text(encoding="utf-8"))[
            "status"
        ]
        seen.setdefault(status, folder)
    assert set(seen) == {"draft", "in_review", "approved"}
    for status, folder in seen.items():
        codes = {code for _, code, *_ in problems(folder)}
        assert not codes & {"invalid_review_json", "review_json_invalid"}, status
        review = json.loads((folder / "review.json").read_text(encoding="utf-8"))
        assert ("approved_by" in review) == (status == "approved")
    fixed = target / large_workspace.SUBSTANCES[2] / large_workspace.study_name(2)
    assert ("error", "unknown_substance", "outputs_Tab1.tsv", 3, "substance") not in (
        problems(fixed)
    )
