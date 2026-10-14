"""Contract fixtures of the local curation API for the front-end tests; see curation_contract.py."""

import json
import os
import shutil
import threading
from pathlib import Path
from unittest.mock import Mock

import openpyxl
import pytest
from curation_contract import check_contract
from curation_http import authenticate, request

import pkdb.studyformat.review_edit as review_edit
from pkdb.cache import bundled_vocabulary
from pkdb.curation import launch, studies
from pkdb.curation.engine import CurationEngine
from pkdb.curation.server import create_server
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.load import load_study
from pkdb.studyformat.metadata import MetadataError
from pkdb.studyformat.sync import NEW_TABLE_KINDS, conflict_data, sync_study
from pkdb.studyformat.validation import validate_folder
from pkdb.studyformat.workbook.base import BASE_SHEET

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


def _validated(engine: CurationEngine, identity: str) -> dict:
    """The study page of `identity` after a validation job, run as the worker of pkdb curate does."""
    engine.enqueue([identity], "validate")
    job = engine.queue.pop(identity)
    engine.active = identity
    job["status"] = "running"
    try:
        engine.run_job(job)
    finally:
        engine.active = None
    return engine.study_detail(identity)


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is not in {path.name}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def test_tables_contract(workspace, engine_on):
    """The table files of Demo2020 and the conflicts of changed rows, a removed sheet and a removed raw sheet."""
    detail = engine_on(workspace).study_detail(DEMO)
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
        {
            "tables": detail["tables"],
            "table_kinds": detail["table_kinds"],
            "conflicts": conflicts,
        },
    )


def test_open_tables_contract(workspace, engine_on, monkeypatch):
    """Open tables at a cell of Demo2020: opened there, then named while the workbook is open."""
    engine = engine_on(workspace)
    monkeypatch.setattr(studies, "open_path", lambda path, **kwargs: None)
    place = {"action": "open", "file": "timecourses_Fig1.tsv", "cell": "O6"}
    opened = engine.tables_action(DEMO, place)
    (workspace / DEMO / ".~lock.Demo2020.xlsx#").write_text("curator", encoding="utf-8")
    already_open = engine.tables_action(DEMO, place)
    assert opened["opened"] and opened["notice"] is None
    assert already_open["notice"] == (
        "The workbook is already open. Go to sheet timecourses_Fig1, cell O6."
    )
    check_contract(
        "open-tables",
        {"request": place, "opened": opened, "already_open": already_open},
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


def test_limits_contract(workspace, engine_on, monkeypatch):
    """The study page of Demo2020 beyond each upload limit: the limit first, and no tables or sources."""
    engine = engine_on(workspace)
    details = []
    for limit, value in (("MAX_FILES", 2), ("MAX_ROWS", 3)):
        with monkeypatch.context() as patch:
            patch.setattr(studies, limit, value)
            detail = engine.study_detail(DEMO)
        details.append(
            {
                key: detail[key]
                for key in ("problems", "sources", "files", "tables", "targets")
            }
        )
    assert [detail["problems"][0]["code"] for detail in details] == [
        "file_limit",
        "row_limit",
    ]
    check_contract("limits", {"details": details})


def test_rows_contract(workspace, engine_on):
    """The study rows of the state after a validation of Demo2020: counts, no problem lists."""
    engine = engine_on(workspace)
    detail = _validated(engine, DEMO)
    rows = engine.snapshot()["studies"]
    demo = next(row for row in rows if row["id"] == DEMO)
    assert all("problems" not in row for row in rows)
    assert demo["counts"] == {"errors": 0, "warnings": 2}
    assert len(detail["problems"]) == 2
    # The id of a report is random.
    check_contract(
        "rows",
        [
            {**row, "report_id": "<report>" if row["report_id"] else None}
            for row in rows
        ],
    )


def test_problems_contract(workspace, engine_on):
    """The problems of Demo2020 after a validation, whose warnings review items can acknowledge,
    and after a sync stopped by a conflict in a workbook without its base sheet, whose warning
    they cannot."""
    engine = engine_on(workspace)
    validated = _validated(engine, DEMO)["problems"]
    folder = workspace / DEMO
    assert sync_study(folder, bundled_vocabulary()).ok
    workbook = openpyxl.load_workbook(folder / "Demo2020.xlsx")
    del workbook[BASE_SHEET]
    workbook["subjects"]["D2"] = 14
    workbook.save(folder / "Demo2020.xlsx")
    _replace(folder / "subjects.tsv", "Demo2020\tall\t\t12\t", "Demo2020\tall\t\t13\t")
    synced = _validated(engine, DEMO)["problems"]
    assert [(p["code"], p["acknowledgeable"]) for p in validated] == [
        ("unused_intervention", True),
        ("digitized_mismatch", True),
    ]
    assert [(p["code"], p["severity"], p["acknowledgeable"]) for p in synced] == [
        ("workbook_base_missing", "warning", False),
        ("sync_conflict", "error", False),
    ]
    check_contract("problems", {"validated": validated, "synced": synced})


def test_sources_contract(workspace, engine_on):
    """The sources of the study page of Demo2020 with the URLs of their images, which the
    navigator of the Data section shows, with the files that they lack, and its PDF, the paper."""
    # The version of the PDF follows its modification time, which the checkout sets.
    moment = 1_760_000_000_000_000_000
    os.utime(workspace / DEMO / "Demo2020.pdf", ns=(moment, moment))
    detail = engine_on(workspace).study_detail(DEMO)
    assert any(source["image_url"] for source in detail["sources"])
    assert [paper["file"] for paper in detail["papers"]] == ["Demo2020.pdf"]
    check_contract(
        "sources", {"sources": detail["sources"], "papers": detail["papers"]}
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
    # The project of Fig1 has linear axes.
    assert (view["log_x"], view["log_y"]) == (False, False)
    # Every row of Fig1 has a digitized error bar end of type sd, mirrored around its mean.
    for point in view["points"]:
        assert point["error_high"] - point["y"] == pytest.approx(
            point["y"] - point["error_low"]
        )
    mapped = [p for p in view["overlay"] if p["role"] == "mapped"]
    assert mapped and all(p["error_low_px"] and p["error_high_px"] for p in mapped)
    assert "error_bar" not in view["points"][0] and "error_px" not in mapped[0]
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
    engine = engine_on(workspace)
    # The warnings as the study page lists them after a validation.
    warnings = [
        problem
        for problem in _validated(engine, DEMO)["problems"]
        if problem["code"] == "unknown_dataset"
    ]
    assert all(problem["acknowledgeable"] for problem in warnings)
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
            "warnings": warnings,
            "payloads": payloads,
            "acknowledged": acknowledged,
            "refusals": refusals,
        },
    )


REQUEST_ID = "3f9c2a71"
FAILED_AT = "2026-10-12T14:03:11+02:00"
ACTIVITY_ID = "0" * 32


def test_errors_contract(workspace, engine_on, monkeypatch):
    """The error body of an Open tables whose open command fails, and its activity entry.

    The command is `false`, on every platform the same answer: a stand-in for Popen exits
    at once with the status of `false`, 1, and writes no stderr. The request id, the time
    and the ids are fixed.
    """
    engine = engine_on(workspace)
    monkeypatch.setenv("PKDB_OPEN_COMMAND", "false")
    monkeypatch.setattr(
        launch.subprocess, "Popen", Mock(return_value=Mock(wait=Mock(return_value=1)))
    )
    server = create_server(engine)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _, data = request(
            server,
            "POST",
            "/local/studies/tables",
            {"study": DEMO, "action": "open"},
            authenticate(server),
        )
        body = json.loads(data)
        entry = next(
            job
            for job in engine.study_detail(DEMO)["jobs"]
            if job["id"] == body["activity_id"]
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert status == 500
    body.update(request_id=REQUEST_ID, time=FAILED_AT, activity_id=ACTIVITY_ID)
    activity = {
        key: entry[key]
        for key in ("action", "status", "message", "automatic", "report_id")
    }
    activity.update(
        id=ACTIVITY_ID,
        created_at="2026-10-12T12:03:11.000000+00:00",
        error={**entry["error"], "request_id": REQUEST_ID, "time": FAILED_AT},
    )
    check_contract("errors", {"open_failed": body, "activity": activity})
