"""Contract fixtures of the local curation API for the front-end tests; see curation_contract.py."""

import json
import shutil
from pathlib import Path

import openpyxl
import pytest
from curation_contract import check_contract

import pkdb.studyformat.review_edit as review_edit
from pkdb.cache import bundled_vocabulary
from pkdb.curation.engine import CurationEngine
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.load import load_study
from pkdb.studyformat.metadata import MetadataError
from pkdb.studyformat.sync import NEW_TABLE_KINDS, conflict_data, sync_study
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.validation import validate_folder

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


TABLE_PREVIEWS = [
    {"kind": "outputs", "source": "Tab3"},
    {"kind": "timecourses", "source": "Text"},
    {"kind": "raw", "source": "Tab2"},
    {"kind": "raw", "source": "Fig2"},
    {"kind": "outputs", "source": "Tab 3"},
    {"kind": "outputs", "source": "Tab2"},
]


def test_table_preview_contract(workspace, engine_on):
    """The kinds of a new table, and previews of Demo2020 that can be added or are refused."""
    engine = engine_on(workspace)
    previews = [
        {"request": request, "response": engine.table_preview(DEMO, request)}
        for request in TABLE_PREVIEWS
    ]
    refused = [len(entry["response"]["issues"]) for entry in previews]
    assert refused == [0, 0, 1, 1, 1, 1]
    check_contract(
        "table-preview", {"kinds": list(NEW_TABLE_KINDS), "previews": previews}
    )


TARGET_DRAFTS = [
    {
        "file": "timecourses_Fig1.tsv",
        "rows": {"label": "caf_plasma_100mg", "time": "4"},
    },
    {"file": "timecourses_Fig1.tsv", "rows": {"label": "caf_plasma_200mg"}},
    {"file": "outputs_Tab2.tsv", "rows": {"measurement": "auc_inf", "comment": ""}},
    {"file": "outputs_Tab2.tsv", "rows": {"measurement": "AUC"}},
    {"file": "Demo2020_Tab2.tsv"},
]


def test_targets_contract(workspace, engine_on):
    """The rows and the digitized series of the review targets of Demo2020, and of draft targets."""
    engine = engine_on(workspace)
    detail = engine.study_detail(DEMO)
    previews = [
        {"request": draft, "response": engine.target_preview(DEMO, {"target": draft})}
        for draft in TARGET_DRAFTS
    ]
    check_contract(
        "targets",
        {
            "items": [
                {"id": item["id"], "state": item["state"], "target": item.get("target")}
                for item in detail["review"]["value"]["items"]
            ],
            "targets": detail["targets"],
            "previews": previews,
        },
    )


def test_source_contract(workspace, engine_on):
    """The source view of Fig1 of Demo2020, whose project digitizes the error bar ends of both series."""
    view = engine_on(workspace).study_source(DEMO, "Fig1")
    assert {
        (p["series"], p["error_bar_end"]) for p in view["overlay"] if p["role"] == "raw"
    } == {
        ("caf_plasma_100mg", False),
        ("caf_plasma_100mg", True),
        ("caf_plasma_200mg", False),
        ("caf_plasma_200mg", True),
    }
    check_contract("source-fig1", view)


ITEM = "01M3A00000000000000000000Z"
QUESTION = "Is the 4 h point read from the figure?"
# A write job and a canceled job of Demo2020 as part C saved them in state.json.
PART_C_JOBS = [
    {
        "id": "legacy-write",
        "study_id": DEMO,
        "study_name": "Demo2020",
        "action": "write",
        "status": "succeeded",
        "created_at": "2026-10-01T10:00:00+00:00",
        "message": "Added review item 01M2FC4AG038NKRKAYDXR834N3",
        "automatic": False,
        "report_id": None,
    },
    {
        "id": "legacy-canceled",
        "study_id": DEMO,
        "study_name": "Demo2020",
        "action": "validate",
        "status": "canceled",
        "created_at": "2026-10-01T09:00:00+00:00",
        "message": "Queued",
        "automatic": True,
        "report_id": None,
    },
]


def test_messages_contract(workspace, engine_on, monkeypatch):
    """The suggestion of each kind, the jobs of writes with their review item, also as part C
    saved them, and the issues of a refused study.json."""
    folder = workspace / DEMO
    vocabulary = bundled_vocabulary()
    _replace(
        folder / "timecourses_Fig1.tsv",
        "\tFig1\tcaf_plasma_100mg\tall\t",
        "\tFig1\tcaf_plasma_100mg\tal\t",
    )
    term = next(
        issue
        for issue in validate_folder(
            workspace / "caffeine/Draft2021", vocabulary
        ).issues
        if issue.code == "unknown_substance"
    )
    name = next(
        issue
        for issue in validate_folder(folder, vocabulary).issues
        if issue.code == "unknown_reference"
    )
    hint = make_issue(
        "unit_dimension",
        "mg cannot be converted to a unit of concentration",
        file="outputs_Tab2.tsv",
        line=2,
        header="unit",
        hint="Units of concentration; amounts of a substance convert with its molar mass.",
        candidates=["mg/l", "g/l"],
    )
    engine = engine_on(workspace, {"jobs": PART_C_JOBS})
    monkeypatch.setattr(review_edit, "new_ulid", lambda: ITEM)
    detail = engine.study_detail(DEMO)
    engine.review_action(
        DEMO,
        {
            "action": "add",
            "revision": detail["review"]["revision"],
            "kind": "question",
            "text": QUESTION,
        },
    )
    metadata = {
        **detail["metadata"]["value"],
        "creator": "demo curator",
        "reference": {},
    }
    with pytest.raises(MetadataError) as refused:
        engine.write_metadata(DEMO, detail["metadata"]["revision"], metadata)
    detail = engine.study_detail(DEMO)
    check_contract(
        "messages",
        {
            "suggestions": [
                issue.suggestions[0].model_dump(mode="json")
                for issue in (term, name, hint)
            ],
            "items": [
                {"id": item["id"], "kind": item["kind"], "text": item["text"]}
                for item in detail["review"]["value"]["items"]
            ],
            "jobs": [
                {
                    key: job[key]
                    for key in ("action", "status", "message", "item", "parts")
                    if key in job
                }
                for job in detail["jobs"]
            ],
            "metadata_issues": [
                issue.model_dump(mode="json") for issue in refused.value.issues
            ],
        },
    )


ACKNOWLEDGED = "01M3B00000000000000000000Z"
LEGACY = "01M2S000000000000000000000"


def test_acknowledgements_contract(workspace, engine_on, monkeypatch):
    """Two datasets of a WebPlotDigitizer project without mapped rows, one acknowledged by its
    key, and a file-wide acknowledgement as review.json files written before keys hold it."""
    folder = workspace / DEMO
    path = folder / "Demo2020_Fig1.wpd.json"
    wpd = json.loads(path.read_text(encoding="utf-8"))
    axes = wpd["datasetColl"][0]["axesName"]
    wpd["datasetColl"] += [
        {"name": name, "axesName": axes, "data": []}
        for name in ("legend", "axis_labels")
    ]
    path.write_text(json.dumps(wpd), encoding="utf-8")
    review = json.loads((folder / "review.json").read_text(encoding="utf-8"))
    created = "2026-09-18T09:00:00+02:00"
    review["items"].append(
        {
            "id": LEGACY,
            "kind": "issue",
            "state": "resolved",
            "target": {"file": "timecourses_Fig1.tsv"},
            "acknowledges": "digitized_mismatch",
            "text": "Written before acknowledgements were exact.",
            "author": "curator",
            "created": created,
            "resolved_by": "curator",
            "resolved": created,
        }
    )
    (folder / "review.json").write_text(json.dumps(review), encoding="utf-8")
    assert format_folder(folder).ok
    vocabulary = bundled_vocabulary()
    warnings = [
        issue
        for issue in validate_folder(folder, vocabulary).issues
        if issue.code == "unknown_dataset"
    ]
    payloads = [
        {
            "code": "unknown_dataset",
            "file": "Demo2020_Fig1.wpd.json",
            "line": None,
            "column": None,
            "key": key,
        }
        for key in ("legend", "axis_labels")
    ]
    engine = engine_on(workspace)
    monkeypatch.setattr(review_edit, "new_ulid", lambda: ACKNOWLEDGED)
    revision = engine.study_detail(DEMO)["review"]["revision"]
    # How the local server refuses an acknowledgement that matches no warning or several, and
    # how the library refuses a warning without a row and a key; the server sends error and code.
    refusals = {}
    for name, payload in (
        (
            "ambiguous",
            {key: value for key, value in payloads[0].items() if key != "key"},
        ),
        ("missing", {**payloads[0], "key": "grid"}),
    ):
        with pytest.raises(review_edit.ReviewError) as refused:
            engine.review_action(
                DEMO,
                {"action": "acknowledge", "revision": revision, "text": "x", **payload},
            )
        refusals[name] = {"error": str(refused.value), "code": refused.value.code}
    unkeyed = make_issue("unknown_dataset", "Old.", file="Demo2020_Fig1.wpd.json")
    with pytest.raises(review_edit.NoExactTarget) as refused:
        review_edit.target_for_issue(load_study(folder), unkeyed)
    refusals["inexact"] = {"error": str(refused.value), "code": refused.value.code}
    engine.review_action(
        DEMO,
        {
            "action": "acknowledge",
            "revision": revision,
            "text": "The legend is no series.",
            **payloads[0],
        },
    )
    remaining = [
        issue.source.key
        for issue in validate_folder(folder, vocabulary).issues
        if issue.code == "unknown_dataset" and issue.source
    ]
    assert remaining == ["axis_labels"]
    # The legacy acknowledgement keeps hiding every digitized_mismatch of its file.
    assert not any(
        issue.code == "digitized_mismatch"
        and issue.source
        and issue.source.file == "timecourses_Fig1.tsv"
        for issue in validate_folder(folder, vocabulary).issues
    )
    acknowledged = [
        {key: value for key, value in entry.items() if key != "resolved"}
        for entry in engine.study_detail(DEMO)["acknowledged"]
    ]
    check_contract(
        "acknowledgements",
        {
            "warnings": [issue.model_dump(mode="json") for issue in warnings],
            "payloads": payloads,
            "acknowledged": acknowledged,
            "refusals": refusals,
        },
    )
