"""Contract fixtures of the local curation API for the front-end tests; see curation_contract.py."""

import json
import shutil
from pathlib import Path

import openpyxl
import pytest
from curation_contract import check_contract

from pkdb.cache import bundled_vocabulary
from pkdb.curation.engine import CurationEngine
from pkdb.studyformat.sync import conflict_data, sync_study
from pkdb.studyformat.tables import TABLES

FIXTURE = Path(__file__).resolve().parents[2] / "tools" / "curation_testing" / "fixture"
DEMO = "caffeine/Demo2020"


@pytest.fixture
def workspace(tmp_path):
    """A copy of the fixture workspace of the end-to-end tests."""
    root = tmp_path / "workspace"
    shutil.copytree(FIXTURE, root)
    return root


@pytest.fixture
def engine_on(tmp_path):
    """Start engines of pkdb curate offline and without threads, writing as curator."""
    started = []

    def start(workspace: Path, saved: dict | None = None) -> CurationEngine:
        state = tmp_path / f"state{len(started)}"
        state.mkdir()
        if saved is not None:
            (state / "state.json").write_text(json.dumps(saved), encoding="utf-8")
        engine = CurationEngine(workspace, state_dir=state, offline=True, start=False)
        engine.user = "curator"
        started.append(engine)
        return engine

    yield start
    for engine in started:
        engine.close()


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is not in {path.name}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def test_tables_contract(workspace, engine_on):
    """The table files of Demo2020 and the conflicts of changed rows, a removed sheet and a removed raw sheet."""
    tables = engine_on(workspace).study_detail(DEMO)["tables"]
    folder = workspace / DEMO
    vocabulary = bundled_vocabulary()
    assert sync_study(folder, vocabulary).ok
    workbook = openpyxl.load_workbook(folder / "Demo2020.xlsx")
    del workbook["outputs_Tab2"]
    del workbook["Demo2020_Tab2"]
    workbook["subjects"]["D2"] = 14
    workbook.save(folder / "Demo2020.xlsx")
    _replace(folder / "subjects.tsv", "Demo2020\tall\t\t12\t", "Demo2020\tall\t\t13\t")
    _replace(folder / "outputs_Tab2.tsv", "\t17.6\t", "\t17.8\t")
    _replace(folder / "Demo2020_Tab2.tsv", "17.6 ± 4.2", "17.8 ± 4.2")
    conflicts = [
        conflict_data(conflict)
        for conflict in sync_study(folder, vocabulary, check=True).conflicts
    ]
    assert [(c["file"], c["kind"], c["removed"]) for c in conflicts] == [
        ("subjects.tsv", "subjects", None),
        ("outputs_Tab2.tsv", "outputs", "workbook"),
        ("Demo2020_Tab2.tsv", "raw", "workbook"),
    ]
    check_contract(
        "tables",
        {"tables": tables, "table_kinds": list(TABLES), "conflicts": conflicts},
    )
