"""The curation engine syncs and formats a format 2 study before it validates it."""

import openpyxl
import pytest

from pkdb.curation import engine as module
from pkdb.curation import jobs
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.sync import sync_study
from pkdb.studyformat.workbook.base import workbook_path


@pytest.fixture
def workspace(tmp_path_factory, make_study, valid_files, sf_vocabulary, monkeypatch):
    folder = make_study(valid_files)
    engine = module.CurationEngine(
        folder.parent.parent,
        state_dir=tmp_path_factory.mktemp("state"),
        offline=True,
        start=False,
    )
    # The bundled vocabulary lacks the substance of the test study.
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    yield engine, folder
    engine.close()


def run_next(engine):
    identifier = next(iter(engine.queue))
    job = engine.queue.pop(identifier)
    engine.active = identifier
    job["status"] = "running"
    try:
        engine.run_job(job)
    finally:
        engine.active = None
    return job


def settle(engine):
    for item in engine.studies.values():
        item["_changed_at"] -= 2
    engine.schedule_changes()


def row(engine):
    return engine.snapshot()["studies"][0]


def set_mean(folder, table, value):
    """Set the mean of the second data row of a table file."""
    path = folder / table
    lines = path.read_text().splitlines()
    header = lines[0].split("\t")
    cells = lines[2].split("\t")
    cells[header.index("mean")] = value
    lines[2] = "\t".join(cells)
    path.write_text("\n".join(lines) + "\n")


def set_workbook_mean(folder, sheet, value):
    """Set the mean of the second data row of a workbook sheet."""
    path = workbook_path(folder)
    book = openpyxl.load_workbook(path)
    rows = book[sheet]
    header = [cell.value for cell in rows[1]]
    rows.cell(3, header.index("mean") + 1).value = value
    book.save(path)


def workbook_mean(folder, sheet):
    rows = openpyxl.load_workbook(workbook_path(folder))[sheet]
    header = [cell.value for cell in rows[1]]
    return rows.cell(3, header.index("mean") + 1).value


def test_validation_formats_first(workspace):
    engine, folder = workspace
    table = folder / "timecourses_Fig1.tsv"
    table.write_text(table.read_text() + "\n\n")  # not canonical
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "succeeded", job["message"]
    assert not table.read_text().endswith("\n\n")
    assert row(engine)["counts"] == {"errors": 0, "warnings": 0}
    assert row(engine)["sync"]["status"] == "no_workbook"
    report = engine.report(job["report_id"])
    assert "timecourses_Fig1.tsv" in report["tables_updated"]


def test_conflict_stops_before_validation(workspace, sf_vocabulary, monkeypatch):
    engine, folder = workspace
    assert sync_study(folder, sf_vocabulary).ok
    set_workbook_mean(folder, "timecourses_Fig1", 5)
    set_mean(folder, "timecourses_Fig1.tsv", "7")
    engine.scan()
    assert row(engine)["sync"] == {"status": "conflict", "changes": 0, "conflicts": 1}
    settle(engine)
    called = []
    monkeypatch.setattr(jobs, "prepare", lambda *a, **k: called.append(1))
    job = run_next(engine)
    assert job["status"] == "conflict" and not called
    assert row(engine)["status"] == "conflict"
    assert row(engine)["sync"]["status"] == "conflict"
    report = engine.report(job["report_id"])
    assert (
        report["conflicts"] and report["conflicts"][0]["file"] == "timecourses_Fig1.tsv"
    )
    assert report["conflicts"][0]["workbook_rows"][0]["row"] == 3
    assert any(issue["code"] == "sync_conflict" for issue in report["pipeline_issues"])


def test_pipeline_runs_under_the_folder_lock(workspace, monkeypatch):
    engine, folder = workspace
    held = []

    class Lock:
        def __init__(self, path):
            held.append(("enter", path))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            held.append(("exit", None))

    real = jobs.sync_and_format

    def pipeline(path, vocabulary, **kwargs):
        assert held and held[-1][0] == "enter"
        assert row(engine)["sync"]["status"] == "syncing"
        return real(path, vocabulary, **kwargs)

    monkeypatch.setattr(jobs, "folder_lock", Lock)
    monkeypatch.setattr(jobs, "sync_and_format", pipeline)
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"
    assert held[0] == ("enter", folder)
    assert held[1] == ("exit", None)
    assert row(engine)["sync"]["status"] == "no_workbook"


def test_format_problems_fail_like_validation(workspace, monkeypatch):
    engine, folder = workspace
    table = folder / "timecourses_Fig1.tsv"
    table.write_text(table.read_text() + "<<<<<<< HEAD\n")
    settle(engine)
    called = []
    monkeypatch.setattr(jobs, "prepare", lambda *a, **k: called.append(1))
    job = run_next(engine)
    assert job["status"] == "failed" and not called
    assert row(engine)["status"] == "invalid"
    assert row(engine)["counts"]["errors"] >= 1
    report = engine.report(job["report_id"])
    assert any(
        issue["code"] == "merge_conflict" for issue in report["report"]["issues"]
    )


def test_sync_status_follows_the_workbook(workspace, sf_vocabulary):
    engine, folder = workspace
    assert sync_study(folder, sf_vocabulary).ok
    engine.scan()
    assert row(engine)["sync"] == {"status": "in_sync", "changes": 0, "conflicts": 0}
    set_workbook_mean(folder, "timecourses_Fig1", 5)
    engine.scan()
    assert row(engine)["sync"] == {"status": "changed", "changes": 1, "conflicts": 0}
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "succeeded", job["message"]
    assert "\t5\t" in (folder / "timecourses_Fig1.tsv").read_text().splitlines()[2]
    assert row(engine)["sync"]["status"] == "in_sync"
    (folder / f".~lock.{folder.name}.xlsx#").write_text("open")
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    assert row(engine)["sync"]["status"] == "workbook_open"


def test_regenerated_workbook_is_validated_by_the_same_job(workspace, sf_vocabulary):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    set_mean(folder, "timecourses_Fig1.tsv", "3")
    engine.scan()
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "succeeded", job["message"]
    assert workbook_mean(folder, "timecourses_Fig1") == 3
    settle(engine)
    assert not engine.queue
