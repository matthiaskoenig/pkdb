"""The curation engine syncs and formats a format 2 study before it validates it."""

from contextlib import contextmanager

import openpyxl
import pytest

from pkdb.curation import engine as module
from pkdb.curation import jobs
from pkdb.curation import workspace as workspace_module
from pkdb.studyformat import pipeline as pipeline_module
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
    # The overview and the study page show the conflict as a problem.
    assert "sync_conflict" in {problem["code"] for problem in row(engine)["problems"]}
    assert row(engine)["counts"]["errors"] >= 1


def test_tables_that_cannot_be_synced_make_the_study_invalid(workspace, sf_vocabulary):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    table = folder / "timecourses_Fig1.tsv"
    header, *lines = table.read_text().splitlines()
    table.write_text(
        "\n".join([f"{header}\tcolour", *(f"{line}\tred" for line in lines)]) + "\n"
    )
    engine.scan()
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "failed", job["message"]
    current = row(engine)
    assert current["status"] == "invalid"
    assert current["counts"]["errors"] >= 1
    assert "unknown_column" in {problem["code"] for problem in current["problems"]}


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


def run_all(engine):
    jobs_run = []
    settle(engine)
    while engine.queue:
        jobs_run.append(run_next(engine))
        settle(engine)
    return jobs_run


@pytest.mark.parametrize(
    "moment", ["while formatting", "after the folder lock", "after the sync state"]
)
def test_a_save_during_the_job_is_never_absorbed(
    workspace, sf_vocabulary, monkeypatch, moment
):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    set_workbook_mean(folder, "timecourses_Fig1", 5)
    engine.scan()
    saved = []

    def save_again():
        if not saved:
            saved.append(moment)
            set_workbook_mean(folder, "timecourses_Fig1", 9)

    if moment == "while formatting":
        real_format = pipeline_module.format_folder

        def formatting(path, **kwargs):
            save_again()
            return real_format(path, **kwargs)

        monkeypatch.setattr(pipeline_module, "format_folder", formatting)
    elif moment == "after the folder lock":
        real_lock = jobs.folder_lock

        @contextmanager
        def lock(path):
            with real_lock(path):
                yield
            save_again()

        monkeypatch.setattr(jobs, "folder_lock", lock)
    else:
        real_describe = jobs.describe

        def describing(pipeline):
            save_again()
            return real_describe(pipeline)

        monkeypatch.setattr(jobs, "describe", describing)
    settle(engine)
    first = run_next(engine)
    assert saved
    # The job validated tables without the last save, so it must not count as current.
    assert first["status"] == "canceled", first["message"]
    assert engine.studies["caffeine/Example"]["_pending"] is True
    later = run_all(engine)
    assert [job["status"] for job in later] == ["succeeded"]
    assert "\t9\t" in (folder / "timecourses_Fig1.tsv").read_text().splitlines()[2]
    assert row(engine)["sync"]["status"] == "in_sync"


def test_closing_the_workbook_regenerates_it(workspace, sf_vocabulary):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    engine.scan()
    assert [job["status"] for job in run_all(engine)] == ["succeeded"]
    lock = folder / f".~lock.{folder.name}.xlsx#"
    lock.write_text("open")
    engine.scan()
    # Opening the workbook changes no source: no job.
    assert row(engine)["sync"]["status"] == "in_sync"
    settle(engine)
    assert not engine.queue
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    assert row(engine)["sync"]["status"] == "workbook_open"
    assert [job["status"] for job in run_all(engine)] == ["succeeded"]
    assert row(engine)["sync"]["status"] == "workbook_open"
    assert workbook_mean(folder, "timecourses_Fig1") == 2
    lock.unlink()
    engine.scan()
    assert row(engine)["sync"] == {"status": "changed", "changes": 0, "conflicts": 0}
    assert engine.studies["caffeine/Example"]["_pending"] is True
    settle(engine)
    assert [job["action"] for job in engine.queue.values()] == ["validate"]
    assert [job["status"] for job in run_all(engine)] == ["succeeded"]
    assert workbook_mean(folder, "timecourses_Fig1") == 6
    assert row(engine)["sync"]["status"] == "in_sync"


def test_a_closed_workbook_behind_the_tables_is_changed(workspace, sf_vocabulary):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    assert row(engine)["sync"] == {"status": "changed", "changes": 0, "conflicts": 0}


def test_a_workbook_closed_during_the_job_is_regenerated(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    # The tables are not formatted yet, so the job writes them and scans again.
    assert sync_study(folder, sf_vocabulary).ok
    lock = folder / f".~lock.{folder.name}.xlsx#"
    lock.write_text("open")
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    real_format = pipeline_module.format_folder

    def formatting(path, **kwargs):
        lock.unlink(missing_ok=True)
        return real_format(path, **kwargs)

    monkeypatch.setattr(pipeline_module, "format_folder", formatting)
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"
    assert engine.studies["caffeine/Example"]["_pending"] is True
    assert [job["status"] for job in run_all(engine)] == ["succeeded"]
    assert workbook_mean(folder, "timecourses_Fig1") == 6
    assert row(engine)["sync"]["status"] == "in_sync"


def test_a_failed_reference_lookup_still_syncs_the_workbook(workspace, sf_vocabulary):
    engine, folder = workspace
    assert sync_study(folder, sf_vocabulary).ok
    set_workbook_mean(folder, "timecourses_Fig1", 5)
    (folder / "reference.json").unlink()  # offline, nothing cached: the lookup fails
    engine.scan()
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "failed" and "reference.json" in job["message"]
    assert "\t5\t" in (folder / "timecourses_Fig1.tsv").read_text().splitlines()[2]
    assert row(engine)["sync"]["status"] == "in_sync"
    settle(engine)
    assert not engine.queue


def test_closing_the_workbook_keeps_a_queued_upload(workspace, sf_vocabulary):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    engine.scan()
    assert [job["status"] for job in run_all(engine)] == ["succeeded"]
    engine.offline = False
    engine.endpoint = "https://example.test"
    engine.api_key = "private-api-key"
    engine.account = "curator"
    engine.can_upload = True
    engine.set_mode(["caffeine/Example"], "upload")
    lock = folder / f".~lock.{folder.name}.xlsx#"
    lock.write_text("open")
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    settle(engine)
    [upload] = engine.queue.values()
    assert upload["action"] == "upload"
    lock.unlink()
    engine.scan()
    assert row(engine)["sync"]["status"] == "changed"
    settle(engine)
    # The queued upload syncs, and so regenerates, the closed workbook itself.
    assert list(engine.queue.values()) == [upload]
    assert upload["status"] == "queued"


def test_a_workbook_closed_while_the_job_validates_is_regenerated(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    lock = folder / f".~lock.{folder.name}.xlsx#"
    lock.write_text("open")
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    real_prepare = jobs.prepare

    def preparing(*args, **kwargs):
        # The watcher sees the workbook close while this job runs.
        lock.unlink()
        engine.scan()
        return real_prepare(*args, **kwargs)

    monkeypatch.setattr(jobs, "prepare", preparing)
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"
    assert engine.studies["caffeine/Example"]["_pending"] is True
    monkeypatch.setattr(jobs, "prepare", real_prepare)
    assert [job["action"] for job in run_all(engine)] == ["validate"]
    assert workbook_mean(folder, "timecourses_Fig1") == 6
    assert row(engine)["sync"]["status"] == "in_sync"


def test_a_workbook_closed_during_an_upload_keeps_the_upload_pending(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    engine.scan()
    assert [job["status"] for job in run_all(engine)] == ["succeeded"]
    engine.offline = False
    engine.endpoint = "https://example.test"
    engine.api_key = "private-api-key"
    engine.account = "curator"
    engine.can_upload = True
    engine.set_mode(["caffeine/Example"], "upload")
    monkeypatch.setattr(engine, "_vocabulary", lambda client, **kwargs: sf_vocabulary)
    lock = folder / f".~lock.{folder.name}.xlsx#"
    lock.write_text("open")
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    real_prepare = jobs.prepare

    def preparing(*args, **kwargs):
        # The watcher sees the workbook close, then the curator pauses before the transfer.
        lock.unlink()
        engine.scan()
        engine.paused = True
        return real_prepare(*args, **kwargs)

    monkeypatch.setattr(jobs, "prepare", preparing)
    settle(engine)
    job = run_next(engine)
    assert job["action"] == "upload" and job["status"] == "canceled"
    engine.paused = False
    settle(engine)
    # The edit is still uploaded; that job's sync regenerates the workbook.
    assert [queued["action"] for queued in engine.queue.values()] == ["upload"]


def test_a_workbook_that_cannot_be_replaced_is_not_requeued(
    workspace, sf_vocabulary, monkeypatch
):
    from pkdb.studyformat import sync

    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    real_atomic_bytes = sync.atomic_bytes

    def atomic_bytes(path, data):
        if path == workbook_path(folder):
            # Windows keeps an open workbook locked, without a lock file of ours.
            raise PermissionError(13, "Permission denied", str(path))
        return real_atomic_bytes(path, data)

    monkeypatch.setattr(sync, "atomic_bytes", atomic_bytes)
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    statuses = []
    for _ in range(5):
        settle(engine)
        if not engine.queue:
            break
        statuses.append(run_next(engine)["status"])
        engine.scan()
    assert statuses == ["succeeded"]
    assert row(engine)["sync"] == {
        "status": "workbook_open",
        "changes": 0,
        "conflicts": 0,
    }
    assert workbook_mean(folder, "timecourses_Fig1") == 2


def test_a_workbook_closed_during_a_failed_job_is_regenerated(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    lock = folder / f".~lock.{folder.name}.xlsx#"
    lock.write_text("open")
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    assert row(engine)["sync"]["status"] == "workbook_open"
    real_pipeline = jobs.sync_and_format

    def failing(path, vocabulary, **kwargs):
        lock.unlink()
        raise OSError("disk unavailable")

    monkeypatch.setattr(jobs, "sync_and_format", failing)
    settle(engine)
    assert run_next(engine)["status"] == "failed"
    assert engine.studies["caffeine/Example"]["_pending"] is True
    monkeypatch.setattr(jobs, "sync_and_format", real_pipeline)
    assert [job["action"] for job in run_all(engine)] == ["validate"]
    assert workbook_mean(folder, "timecourses_Fig1") == 6
    assert row(engine)["sync"]["status"] == "in_sync"


def test_workbooks_are_planned_by_the_jobs_not_by_the_initial_scan(
    tmp_path_factory, make_study, valid_files, sf_vocabulary, monkeypatch
):
    folder = make_study(valid_files)
    assert format_folder(folder).ok
    assert sync_study(folder, sf_vocabulary).ok
    plans = []
    real_check = workspace_module.workbook_check

    def check(path, vocabulary):
        plans.append(path)
        return real_check(path, vocabulary)

    monkeypatch.setattr(workspace_module, "workbook_check", check)
    engine = module.CurationEngine(
        folder.parent.parent,
        state_dir=tmp_path_factory.mktemp("state"),
        offline=True,
        start=False,
    )
    try:
        monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
        assert row(engine)["sync"]["status"] == "unknown"
        settle(engine)
        assert run_next(engine)["status"] == "succeeded"
        # The job knows the state of the workbook from its sync.
        assert row(engine)["sync"] == {
            "status": "in_sync",
            "changes": 0,
            "conflicts": 0,
        }
        assert plans == []
        set_workbook_mean(folder, "timecourses_Fig1", 5)
        engine.scan()
        assert row(engine)["sync"]["status"] == "changed" and len(plans) == 1
    finally:
        engine.close()


def test_the_rescan_of_a_job_plans_no_workbook_under_the_engine_lock(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    assert sync_study(folder, sf_vocabulary).ok
    set_mean(folder, "timecourses_Fig1.tsv", "6")  # the job writes the workbook
    engine.scan()
    held = []
    real_check = workspace_module.workbook_check

    def check(path, vocabulary):
        held.append(engine.lock._is_owned())
        return real_check(path, vocabulary)

    monkeypatch.setattr(workspace_module, "workbook_check", check)
    (folder / "timecourses_Fig1.tsv").write_text(
        (folder / "timecourses_Fig1.tsv").read_text() + "\n"
    )  # not canonical: the job formats it and scans again
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"
    assert held and not any(held)


def test_a_failing_workbook_plan_never_leaves_the_row_syncing(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    assert sync_study(folder, sf_vocabulary).ok

    def broken(path, vocabulary):
        raise RuntimeError("unexpected")

    def failing(path, vocabulary, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(workspace_module, "workbook_check", broken)
    set_mean(folder, "timecourses_Fig1.tsv", "6")
    engine.scan()
    assert row(engine)["sync"]["status"] == "unknown"
    monkeypatch.setattr(jobs, "sync_and_format", failing)
    settle(engine)
    assert run_next(engine)["status"] == "failed"
    assert row(engine)["sync"]["status"] == "unknown"


def test_a_symlink_in_the_study_waits_without_requeueing(workspace):
    engine, folder = workspace
    settle(engine)
    assert engine.queue
    # The symlink appears after the job was queued.
    (folder / "Example_Fig3.png").symlink_to(folder / "Example_Fig1.png")
    job = run_next(engine)
    assert job["status"] == "failed"
    waiting = engine.studies["caffeine/Example"]
    assert waiting["status"] == "waiting" and "Symlink" in waiting["message"]
    for _ in range(3):
        engine.scan()
        settle(engine)
        assert not engine.queue
    assert row(engine)["status"] == "waiting"
    (folder / "Example_Fig3.png").unlink()
    engine.scan()
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"
    assert "message" not in engine.studies["caffeine/Example"]
