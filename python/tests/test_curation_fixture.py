"""The fixture workspace of the curation app end-to-end tests stays as its specs expect it.

The Playwright specs in frontend/tests/curation-e2e and the documentation screenshots rely on
exactly these deliberate problems, so a change of the library that moves them fails here first.
"""

import importlib.util
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
