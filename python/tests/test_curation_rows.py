import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from pkdb.curation import engine as module
from pkdb.curation import workspace as workspace_module
from pkdb.studyformat.jsonio import dump_json


@pytest.fixture
def workspace(tmp_path, tmp_path_factory, make_study, valid_files):
    folder = make_study(valid_files)  # tmp_path/caffeine/Example
    legacy = tmp_path / "caffeine" / "Legacy1990"
    legacy.mkdir()
    (legacy / "study.json").write_text(
        json.dumps({"sid": "Legacy1990", "name": "Legacy1990"})
    )
    (legacy / "Legacy1990.xlsx").write_bytes(b"not a workbook")
    engine = module.CurationEngine(
        tmp_path,
        state_dir=tmp_path_factory.mktemp("state"),
        offline=True,
        start=False,
    )
    yield engine, folder, legacy
    engine.close()


def test_rows_are_format_2_studies_by_identity(workspace):
    engine, folder, legacy = workspace
    snapshot = engine.snapshot()
    assert [row["id"] for row in snapshot["studies"]] == ["caffeine/Example"]
    assert snapshot["format1_folders"] == 1
    row = snapshot["studies"][0]
    assert row["path"] == "caffeine/Example" and row["duplicate"] is False
    assert row["summary"]["review_status"] == "draft"
    assert row["summary"]["curators"] == ["curator"]
    assert row["summary"]["title"] == "Example study"
    assert "sid" not in row and "metadata" not in row


def test_rows_skip_folders_below_hidden_folders(workspace, valid_files):
    import shutil

    engine, folder, legacy = workspace
    # The leftovers of an interrupted pkdb new, of format 2 and format 1.
    shutil.copytree(folder, folder.parent / ".Example.new" / "Example")
    shutil.copytree(legacy, folder.parent / ".Legacy1990.new" / "Legacy1990")
    engine.scan()
    snapshot = engine.snapshot()
    assert [row["id"] for row in snapshot["studies"]] == ["caffeine/Example"]
    assert snapshot["format1_folders"] == 1


def run_queue(engine):
    while engine.queue:
        identifier = next(iter(engine.queue))
        job = engine.queue.pop(identifier)
        engine.active = identifier
        job["status"] = "running"
        try:
            engine.run_job(job)
        finally:
            engine.active = None


def listing(folder):
    return {
        str(path.relative_to(folder)): path.read_bytes()
        for path in folder.rglob("*")
        if path.is_file()
    }


def test_format_1_folders_are_never_touched(workspace, sf_vocabulary, monkeypatch):
    engine, folder, legacy = workspace
    monkeypatch.setattr(engine, "_local_vocabulary", lambda folder=None: sf_vocabulary)
    before = listing(legacy)
    engine.scan()
    for item in engine.studies.values():
        item["_changed_at"] -= 2
    engine.schedule_changes()
    assert set(engine.queue) == {"caffeine/Example"}
    run_queue(engine)
    assert [job["study_id"] for job in engine.jobs] == ["caffeine/Example"]
    assert listing(legacy) == before


def test_job_for_a_folder_that_became_format_1_is_canceled(workspace):
    engine, folder, legacy = workspace
    engine.enqueue(["caffeine/Example"], "validate")
    for path in folder.iterdir():
        path.unlink()
    (folder / "study.json").write_text(json.dumps({"sid": "Example", "name": "x"}))
    (folder / "Example.xlsx").write_bytes(b"not a workbook")
    before = listing(folder)
    run_queue(engine)
    assert engine.jobs[-1]["status"] == "canceled"
    assert "no longer" in engine.jobs[-1]["message"]
    assert listing(folder) == before
    with pytest.raises(ValueError, match="no longer"):
        engine.resolve_file("caffeine/Example")


def test_duplicate_identity_is_marked_and_refused(workspace, tmp_path, valid_files):
    engine, folder, legacy = workspace
    copy = tmp_path / "copies" / "caffeine" / "Example"
    copy.mkdir(parents=True)
    for file, content in valid_files.items():
        (copy / file).write_bytes(
            content if isinstance(content, bytes) else content.encode()
        )
    engine.scan()
    rows = [
        row for row in engine.snapshot()["studies"] if row["id"] == "caffeine/Example"
    ]
    assert len(rows) == 2 and all(row["duplicate"] for row in rows)
    with pytest.raises(ValueError, match="identity of two folders"):
        engine.enqueue(["caffeine/Example"], "validate")


def test_duplicates_are_never_scheduled(workspace, tmp_path, valid_files):
    engine, folder, legacy = workspace
    copy = tmp_path / "copies" / "caffeine" / "Example"
    copy.mkdir(parents=True)
    for file, content in valid_files.items():
        (copy / file).write_bytes(
            content if isinstance(content, bytes) else content.encode()
        )
    engine.scan()
    assert all(row["duplicate"] and row["_pending"] for row in engine.studies.values())
    for row in engine.studies.values():
        row["_changed_at"] -= 2
    engine.schedule_changes()
    assert not engine.queue


@pytest.fixture
def substance(tmp_path, tmp_path_factory, make_study, valid_files):
    """An engine whose workspace is the substance folder of two studies."""
    folders = [make_study(valid_files, name=name) for name in ("Example", "Other")]
    engine = module.CurationEngine(
        folders[0].parent,
        state_dir=tmp_path_factory.mktemp("state"),
        offline=True,
        start=False,
    )
    assert sorted(engine.studies) == ["Example", "Other"]
    for row in engine.studies.values():
        row["_signature"] = None  # the next scan reads both studies again
    yield engine, folders
    engine.close()


def test_a_workspace_switch_waits_for_the_running_scan(
    substance, tmp_path, monkeypatch
):
    engine, folders = substance
    real_summary = workspace_module.study_summary
    switches = []

    def summary(folder):
        if not switches:
            # The curator opens the repository root while the watcher scans.
            switches.append(
                threading.Thread(target=engine.select_workspace, args=(tmp_path,))
            )
            switches[0].start()
            switches[0].join(timeout=0.5)
        return real_summary(folder)

    monkeypatch.setattr(workspace_module, "study_summary", summary)
    engine.scan()
    switches[0].join(timeout=10)
    assert not switches[0].is_alive()
    assert engine.root == tmp_path
    rows = engine.snapshot()["studies"]
    assert sorted(row["path"] for row in rows) == ["caffeine/Example", "caffeine/Other"]
    assert not any(row["duplicate"] for row in rows)
    assert engine.study_folder("caffeine/Other") == folders[1]


def test_a_scan_of_a_replaced_workspace_stops(substance, tmp_path, monkeypatch):
    engine, folders = substance
    real_summary = workspace_module.study_summary
    switched = []

    def summary(folder):
        if not switched:
            # A new workspace without rows, as if the switch had not waited for this scan.
            switched.append(folder)
            engine.root, engine.studies = tmp_path, {}
        return real_summary(folder)

    monkeypatch.setattr(workspace_module, "study_summary", summary)
    engine.format1_folders = 7
    engine.scan()
    assert engine.studies == {}
    assert engine.format1_folders == 7


def test_summary_of_unreadable_files(workspace):
    engine, folder, legacy = workspace
    (folder / "review.json").write_text("{broken")
    (folder / "study.json").write_text(dump_json({"format": 2}))
    engine.scan()
    summary = engine.snapshot()["studies"][0]["summary"]
    assert summary["review_status"] is None and summary["curators"] == []


def test_issue_comes_from_the_number_in_study_json(workspace):
    engine, folder, legacy = workspace
    metadata = json.loads((folder / "study.json").read_text())
    (folder / "study.json").write_text(dump_json({**metadata, "issue": 2158}))
    engine.github.data = {
        **engine.github.data,
        "issues": [
            {
                "number": 2158,
                "title": "Curate caffeine/Example",
                "html_url": "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
                "state": "open",
                "assignees": ["mkoenig"],
                "labels": ["caffeine", "check"],
            }
        ],
    }
    engine.scan()
    assert engine.snapshot()["studies"][0]["issue"] == {
        "number": 2158,
        "state": "open",
        "labels": ["caffeine", "check"],
        "assignees": ["mkoenig"],
        "url": "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
    }
    engine.github.data = {**engine.github.data, "issues": []}
    assert engine.snapshot()["studies"][0]["issue"]["state"] is None


class _CreationTime:
    """A status as Windows reports it: st_ctime_ns is the creation time, which stays."""

    def __init__(self, status, ctime_ns):
        self._status, self.st_ctime_ns = status, ctime_ns

    def __getattr__(self, name):
        return getattr(self._status, name)


def _as_on_windows(monkeypatch, path):
    """Let the curation app see `path` as on Windows: a status change time that stays."""
    ctime_ns = path.stat().st_ctime_ns
    real = Path.stat

    def stat(self, *, follow_symlinks=True):
        status = real(self, follow_symlinks=follow_symlinks)
        return _CreationTime(status, ctime_ns) if self == path else status

    monkeypatch.setattr(workspace_module, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(Path, "stat", stat)


def test_the_format_is_read_again_only_after_study_json_changes(workspace, monkeypatch):
    engine, folder, legacy = workspace
    decisions = []
    real = workspace_module.is_v2_folder

    def is_v2(path):
        decisions.append(path.name)
        return real(path)

    monkeypatch.setattr(workspace_module, "is_v2_folder", is_v2)
    engine.scan()
    engine.scan()
    assert decisions == []
    (legacy / "study.json").write_text(
        json.dumps({"sid": "Legacy1990", "name": "L"}), encoding="utf-8", newline=""
    )
    engine.scan()
    engine.scan()
    assert decisions == ["Legacy1990"]
    assert engine.snapshot()["format1_folders"] == 1
    # A format 2 file decides without study.json.
    (legacy / "review.json").write_text(
        dump_json({"status": "draft"}), encoding="utf-8", newline=""
    )
    engine.scan()
    assert decisions == ["Legacy1990"]
    assert engine.snapshot()["format1_folders"] == 0


@pytest.mark.parametrize(
    ("windows", "reads"), [(False, []), (True, ["Legacy1990"])], ids=["posix", "win32"]
)
def test_a_scan_without_changes_reads_study_json_only_on_windows(
    workspace, monkeypatch, windows, reads
):
    engine, folder, legacy = workspace
    if windows:
        _as_on_windows(monkeypatch, legacy / "study.json")
    elif sys.platform == "win32":
        pytest.skip("os.stat on Windows has no status change time")
    engine.scan()
    read = []
    real = Path.read_bytes

    def read_bytes(self):
        if self.name == "study.json":
            read.append(self.parent.name)
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    engine.scan()
    # The format 2 study has format 2 files; only the format 1 folder has study.json read.
    assert read == reads


@pytest.mark.parametrize("windows", [False, True], ids=["posix", "win32"])
@pytest.mark.parametrize("replace", [False, True], ids=["in place", "replaced"])
def test_a_same_size_edit_with_a_preserved_mtime_reads_the_format_again(
    workspace, monkeypatch, replace, windows
):
    engine, folder, legacy = workspace
    path = legacy / "study.json"
    if windows:
        _as_on_windows(monkeypatch, path)
    elif sys.platform == "win32":
        pytest.skip("os.stat on Windows has no status change time")
    before = path.stat()
    old = path.read_bytes()
    new = b'{"format": 2}'.ljust(len(old))
    assert len(new) == len(old)
    if replace:
        # As rsync -t and tar x write a file: a new inode.
        (legacy / "study.json.tmp").write_bytes(new)
        os.replace(legacy / "study.json.tmp", path)
    else:
        # As cp -p writes a file: the same inode, a new status change time.
        path.write_bytes(new)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    if not windows:
        # The status change time changes within its resolution, a clock tick at most.
        deadline = time.monotonic() + 5
        while path.stat().st_ctime_ns == before.st_ctime_ns:
            assert time.monotonic() < deadline, "The status change time stayed"
            time.sleep(0.001)
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = path.stat()
    assert (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns)
    assert (after.st_ino != before.st_ino) is replace
    engine.scan()
    assert engine.snapshot()["format1_folders"] == 0
    assert "caffeine/Legacy1990" in engine.studies


def test_state_of_other_app_versions_is_kept(tmp_path, tmp_path_factory):
    state = tmp_path_factory.mktemp("state")
    (state / "state.json").write_text(
        json.dumps({"mappings": {"a#1": ["/x"]}, "future": {"key": 1}, "user": "old"})
    )
    engine = module.CurationEngine(tmp_path, state_dir=state, offline=True, start=False)
    try:
        engine.user = "curator"
        engine._save()
        saved = json.loads((state / "state.json").read_text())
        assert saved["mappings"] == {"a#1": ["/x"]}
        assert saved["future"] == {"key": 1}
        assert saved["user"] == "curator"
        # A key written meanwhile by the other version survives the next save, too.
        (state / "state.json").write_text(json.dumps({**saved, "mappings": {}}))
        engine._save()
        assert json.loads((state / "state.json").read_text())["mappings"] == {}
    finally:
        engine.close()
    assert json.loads((state / "state.json").read_text())["future"] == {"key": 1}


def test_old_state_with_mappings_loads(tmp_path, tmp_path_factory):
    state = tmp_path_factory.mktemp("state")
    (state / "state.json").write_text(json.dumps({"mappings": {"a#1": ["/x"]}}))
    engine = module.CurationEngine(tmp_path, state_dir=state, offline=True, start=False)
    try:
        assert not hasattr(engine, "mappings")
        engine.snapshot()
    finally:
        engine.close()


def start_engine(path, state_dir):
    return module.CurationEngine(path, state_dir=state_dir, offline=True, start=False)


@pytest.fixture
def two_substances(tmp_path, tmp_path_factory, make_study, valid_files):
    """An engine on caffeine/Example, whose tables name drug, and on drug/Other.

    The watcher read their tables, as it does before its first wait.
    """
    folder = make_study(valid_files)
    make_study(valid_files, name="Other", substance="drug")
    engine = start_engine(tmp_path, tmp_path_factory.mktemp("state"))
    engine._read_substances()
    yield engine, folder
    engine.close()


def substances(engine):
    return {row["id"]: row["substances"] for row in engine.snapshot()["studies"]}


def saved_substances(engine):
    return engine.state_dir / "substances.json"


def name_in_interventions(folder, old, new):
    """Let the interventions of a study name `new` where they named `old`."""
    interventions = folder / "interventions.tsv"
    text = interventions.read_text(encoding="utf-8")
    assert f"\t{old}\t" in text
    interventions.write_text(
        text.replace(f"\t{old}\t", f"\t{new}\t"), encoding="utf-8", newline=""
    )


def counted_reads(monkeypatch):
    """The study folders whose tables `study_substances` reads from now on."""
    read = []
    real = workspace_module.study_substances

    def counted(folder, **options):
        read.append(folder.name)
        return real(folder, **options)

    monkeypatch.setattr(workspace_module, "study_substances", counted)
    return read


def no_reads(monkeypatch):
    def refused(folder, **options):
        raise AssertionError(f"read the tables of {folder}")

    monkeypatch.setattr(workspace_module, "study_substances", refused)


class Waits(threading.Event):
    """A stop event whose waits return at once; the wait after `ticks` ticks stops."""

    def __init__(self, ticks):
        super().__init__()
        self.ticks = ticks

    def wait(self, timeout=None):
        if self.ticks == 0:
            return True
        self.ticks -= 1
        return False


def test_the_start_reads_no_table_and_serves_the_substances_read_before(
    tmp_path, tmp_path_factory, make_study, valid_files, monkeypatch
):
    make_study(valid_files)
    make_study(valid_files, name="Other", substance="drug")
    state = tmp_path_factory.mktemp("state")
    read = counted_reads(monkeypatch)
    first = start_engine(tmp_path, state)
    try:
        # Until the watcher reads the tables, a study has the substance of its folder.
        assert read == []
        assert substances(first) == {
            "caffeine/Example": ["caffeine"],
            "drug/Other": ["drug"],
        }
        first._read_substances()
        assert sorted(read) == ["Example", "Other"]
    finally:
        first.close()
    again = start_engine(tmp_path, state)
    try:
        # No validation ran: the substances are those that the first engine read.
        assert not again.jobs
        assert substances(again) == {
            "caffeine/Example": ["caffeine", "drug"],
            "drug/Other": ["drug"],
        }
        again._read_substances()
        assert sorted(read) == ["Example", "Other"]
    finally:
        again.close()


def test_a_workspace_switch_keeps_the_saved_substances_of_the_old_workspace(
    two_substances, tmp_path, tmp_path_factory, make_study, valid_files, monkeypatch
):
    engine, folder = two_substances
    other = tmp_path_factory.mktemp("other")
    study = other / "codeine" / "Third"
    shutil.copytree(folder, study)
    name_in_interventions(study, "drug", "midazolam")
    engine.select_workspace(str(other))
    engine._read_substances()
    saved = json.loads(saved_substances(engine).read_text(encoding="utf-8"))
    assert str(folder) in saved["studies"]
    assert str(study) in saved["studies"]
    engine.close()
    no_reads(monkeypatch)
    again = start_engine(tmp_path, engine.state_dir)
    try:
        assert substances(again)["caffeine/Example"] == ["caffeine", "drug"]
        again.stop.set()
        again._read_substances()
        assert substances(again)["caffeine/Example"] == ["caffeine", "drug"]
    finally:
        again.close()


def test_tables_that_changed_while_stopped_are_read_again(
    two_substances, tmp_path, make_study, valid_files, monkeypatch
):
    engine, folder = two_substances
    engine.close()
    name_in_interventions(folder, "drug", "codeine")
    make_study(valid_files, name="Third", substance="codeine")
    read = counted_reads(monkeypatch)
    again = start_engine(tmp_path, engine.state_dir)
    try:
        # What was read before, until the watcher reads the changed tables.
        assert substances(again)["caffeine/Example"] == ["caffeine", "drug"]
        again._read_substances()
        assert sorted(read) == ["Example", "Third"]
        assert substances(again)["caffeine/Example"] == ["caffeine", "codeine", "drug"]
    finally:
        again.close()


@pytest.mark.parametrize(
    "damage",
    [
        lambda saved: b"{not json",
        lambda saved: b"\xff\xfe",
        lambda saved: json.dumps(list(saved)).encode(),
        lambda saved: json.dumps({**saved, "studies": []}).encode(),
        # Another version may count the substances of a table otherwise.
        lambda saved: json.dumps({**saved, "version": "0.0.1"}).encode(),
    ],
    ids=["not json", "not utf-8", "no object", "no studies", "another version"],
)
def test_saved_substances_that_cannot_be_used_are_read_again(
    two_substances, tmp_path, monkeypatch, damage
):
    engine, folder = two_substances
    engine.close()
    saved = json.loads(saved_substances(engine).read_text(encoding="utf-8"))
    saved_substances(engine).write_bytes(damage(saved))
    read = counted_reads(monkeypatch)
    again = start_engine(tmp_path, engine.state_dir)
    try:
        assert substances(again)["caffeine/Example"] == ["caffeine"]
        again._read_substances()
        assert sorted(read) == ["Example", "Other"]
        assert substances(again)["caffeine/Example"] == ["caffeine", "drug"]
        assert json.loads(saved_substances(again).read_text(encoding="utf-8")) == saved
    finally:
        again.close()


def test_damaged_saved_entries_and_studies_that_are_gone_are_dropped(
    two_substances, tmp_path, monkeypatch
):
    engine, folder = two_substances
    engine.close()
    saved = json.loads(saved_substances(engine).read_text(encoding="utf-8"))
    studies = saved["studies"]
    other = str(tmp_path / "drug" / "Other")
    gone = str(tmp_path / "caffeine" / "Gone")
    damaged = {
        other: {"tables": [["interventions.tsv", "1", 2]], "substances": ["drug"]},
        gone: studies[str(folder)],
    }
    saved_substances(engine).write_text(
        json.dumps({**saved, "studies": {**studies, **damaged}}), encoding="utf-8"
    )
    read = counted_reads(monkeypatch)
    again = start_engine(tmp_path, engine.state_dir)
    try:
        again._read_substances()
        assert read == ["Other"]
        assert json.loads(saved_substances(again).read_text(encoding="utf-8")) == saved
        assert sorted(saved["studies"]) == sorted([str(folder), other])
    finally:
        again.close()


def test_requests_and_the_state_read_no_table(two_substances, monkeypatch, tmp_path):
    engine, folder = two_substances
    no_reads(monkeypatch)
    name_in_interventions(folder, "drug", "codeine")
    # The scan of an app write and a workspace switch, and the state, read no table:
    # they serve what was read before until the watcher reads the changed tables.
    engine.scan()
    engine.select_workspace(str(tmp_path))
    assert substances(engine) == {
        "caffeine/Example": ["caffeine", "drug"],
        "drug/Other": ["drug"],
    }


def test_selecting_the_workspace_again_reads_only_the_tables_that_changed(
    two_substances, make_study, valid_files, monkeypatch, tmp_path
):
    engine, folder = two_substances
    make_study(valid_files, name="Third", substance="codeine")
    read = counted_reads(monkeypatch)
    engine.select_workspace(str(tmp_path))
    engine._read_substances()
    assert read == ["Third"]
    assert substances(engine) == {
        "caffeine/Example": ["caffeine", "drug"],
        "codeine/Third": ["codeine", "drug"],
        "drug/Other": ["drug"],
    }


def test_the_watcher_reads_only_the_tables_that_changed(
    two_substances, make_study, valid_files, monkeypatch
):
    engine, folder = two_substances
    read = counted_reads(monkeypatch)
    # A save of the metadata changes study.json alone and reads no table.
    metadata = json.loads((folder / "study.json").read_text(encoding="utf-8"))
    (folder / "study.json").write_text(
        dump_json({**metadata, "issue": 7}), encoding="utf-8"
    )
    engine.scan()
    engine._read_substances()
    assert read == []
    # The interventions name codeine now, the folder of a new study.
    name_in_interventions(folder, "drug", "codeine")
    make_study(valid_files, name="Third", substance="codeine")
    engine.scan()
    engine._read_substances()
    assert sorted(read) == ["Example", "Third"]
    # The data still name drug.
    assert substances(engine)["caffeine/Example"] == ["caffeine", "codeine", "drug"]
    engine.scan()
    engine._read_substances()
    assert sorted(read) == ["Example", "Third"]


def test_a_substance_folder_added_later_counts_without_reading_the_tables_again(
    tmp_path, tmp_path_factory, make_study, valid_files, monkeypatch
):
    make_study(valid_files)
    engine = start_engine(tmp_path, tmp_path_factory.mktemp("state"))
    try:
        engine._read_substances()
        # drug has no folder yet, like a metabolite.
        assert substances(engine) == {"caffeine/Example": ["caffeine"]}
        no_reads(monkeypatch)
        make_study(valid_files, name="Other", substance="drug")
        engine.scan()
        assert substances(engine)["caffeine/Example"] == ["caffeine", "drug"]
    finally:
        engine.close()


def test_the_first_watcher_tick_reads_every_table_after_scheduling(
    tmp_path, tmp_path_factory, make_study, valid_files, monkeypatch
):
    make_study(valid_files)
    make_study(valid_files, name="Other", substance="drug")
    engine = start_engine(tmp_path, tmp_path_factory.mktemp("state"))
    try:
        events = counted_reads(monkeypatch)
        schedule_changes = engine.schedule_changes

        def scheduled():
            events.append("scheduled")
            schedule_changes()

        monkeypatch.setattr(engine, "schedule_changes", scheduled)
        # Nothing happens before the first wait, so a start without saved substances
        # schedules the validation of the studies before it reads their tables.
        engine.stop = Waits(0)
        engine._watch()
        assert events == []
        engine.stop = Waits(1)
        engine._watch()
        assert events[0] == "scheduled"
        assert sorted(events[1:]) == ["Example", "Other"]
        assert substances(engine) == {
            "caffeine/Example": ["caffeine", "drug"],
            "drug/Other": ["drug"],
        }
    finally:
        engine.close()


def test_a_watcher_tick_reads_a_changed_study_after_scheduling(
    two_substances, make_study, valid_files, monkeypatch
):
    engine, folder = two_substances
    events = counted_reads(monkeypatch)
    schedule_changes = engine.schedule_changes

    def scheduled():
        events.append("scheduled")
        schedule_changes()

    monkeypatch.setattr(engine, "schedule_changes", scheduled)
    name_in_interventions(folder, "drug", "codeine")
    make_study(valid_files, name="Third", substance="codeine")
    engine.stop = Waits(1)
    engine._watch()
    # The read before the first wait finds no change, as no scan saw it yet.
    assert events[0] == "scheduled"
    assert sorted(events[1:]) == ["Example", "Third"]
    assert substances(engine)["caffeine/Example"] == ["caffeine", "codeine", "drug"]


def test_a_read_during_a_workspace_switch_stores_nothing(
    two_substances, tmp_path, monkeypatch
):
    engine, folder = two_substances
    saved = saved_substances(engine).read_bytes()
    name_in_interventions(folder, "drug", "codeine")
    engine.scan()
    old = engine.studies["caffeine/Example"]
    real = workspace_module.study_substances

    def switching(study, **options):
        engine.select_workspace(str(tmp_path))
        return real(study, **options)

    monkeypatch.setattr(workspace_module, "study_substances", switching)
    engine._read_substances()
    assert old["_named_substances"] == ("drug",)
    assert old["_tables"] != old["_table_signature"]
    # The rows of the switch have what was saved, not what the read found.
    new = engine.studies["caffeine/Example"]
    assert new is not old
    assert new["_named_substances"] == ("drug",)
    assert new["_tables"] != new["_table_signature"]
    assert saved_substances(engine).read_bytes() == saved


def test_a_read_of_tables_that_change_meanwhile_stores_nothing_and_reads_them_again(
    two_substances, make_study, valid_files, monkeypatch
):
    engine, folder = two_substances
    make_study(valid_files, name="Fourth", substance="midazolam")
    name_in_interventions(folder, "drug", "codeine")
    engine.scan()
    real = workspace_module.study_substances
    read = []

    def changing(study, **options):
        named = real(study, **options)
        read.append(study.name)
        if read == ["Example"]:
            # The curator saves the study again while its tables are read.
            name_in_interventions(folder, "codeine", "midazolam")
            engine.scan()
        return named

    monkeypatch.setattr(workspace_module, "study_substances", changing)
    engine._read_substances()
    row = engine.studies["caffeine/Example"]
    assert "Example" in read
    assert row["_named_substances"] == ("drug",)
    assert row["_tables"] != row["_table_signature"]
    engine._read_substances()
    assert substances(engine)["caffeine/Example"] == ["caffeine", "drug", "midazolam"]


def tracebacks(engine):
    path = engine.log.path
    return path.read_text(encoding="utf-8").count("Traceback") if path.exists() else 0


@pytest.mark.parametrize(
    ("error", "logged"),
    [(RuntimeError("unexpected"), 1), (PermissionError("in use"), 0)],
)
def test_a_study_whose_tables_fail_to_read_keeps_its_substances_and_is_read_again(
    two_substances, make_study, valid_files, monkeypatch, capsys, error, logged
):
    engine, folder = two_substances
    make_study(valid_files, name="Fourth", substance="midazolam")
    name_in_interventions(folder, "drug", "midazolam")
    engine.scan()
    real = workspace_module.study_substances

    def failing(study, **options):
        if study.name == "Example":
            raise error
        return real(study, **options)

    monkeypatch.setattr(workspace_module, "study_substances", failing)
    engine._read_substances()
    engine._read_substances()
    # The other studies are read; the study that failed keeps what was read before.
    assert substances(engine)["midazolam/Fourth"] == ["midazolam", "drug"]
    assert substances(engine)["caffeine/Example"] == ["caffeine", "drug"]
    # An unexpected error is logged with its traceback once a minute, as the watcher
    # logs its failures; a file that cannot be read now is read on the next call.
    assert tracebacks(engine) == logged
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == logged
    if logged:
        assert re.fullmatch(
            r"Error [0-9a-f]{8} in File watching: RuntimeError \(see .*curation\.log\)",
            lines[0],
        )
    monkeypatch.setattr(workspace_module, "study_substances", real)
    engine._read_substances()
    assert substances(engine)["caffeine/Example"] == [
        "caffeine",
        "drug",
        "midazolam",
    ]


def test_substances_that_cannot_be_saved_are_saved_on_the_next_read(
    two_substances, make_study, valid_files, monkeypatch, capsys
):
    engine, folder = two_substances
    make_study(valid_files, name="Third", substance="codeine")
    engine.scan()
    real = workspace_module.atomic_text

    def full(path, text):
        raise OSError("disk full")

    monkeypatch.setattr(workspace_module, "atomic_text", full)
    engine._read_substances()
    assert substances(engine)["codeine/Third"] == ["codeine", "drug"]
    assert tracebacks(engine) == 1
    assert len(capsys.readouterr().err.splitlines()) == 1
    monkeypatch.setattr(workspace_module, "atomic_text", real)
    engine._read_substances()
    saved = json.loads(saved_substances(engine).read_text(encoding="utf-8"))
    assert str(folder.parent.parent / "codeine" / "Third") in saved["studies"]


def test_a_read_stops_when_the_engine_stops(two_substances, monkeypatch):
    engine, folder = two_substances
    name_in_interventions(folder, "drug", "codeine")
    engine.scan()
    read = counted_reads(monkeypatch)
    engine.stop.set()
    engine._read_substances()
    assert read == []


def test_saved_substances_keep_folder_names_that_are_no_text(tmp_path):
    # A path on Linux with a byte that is no UTF-8, as Python decodes it.
    folder = "/data/studies/caf\udce9/Example"
    read = {folder: ((("interventions.tsv", 1, 2),), ("caffeine", "drug"))}
    path = tmp_path / "substances.json"
    workspace_module.save_substances(path, read)
    assert workspace_module.load_substances(path) == read


def test_the_table_signature_has_the_tables_whose_substances_count():
    files = [
        ("interventions.tsv", 1, 10),
        ("outputs_Tab1.tsv", 2, 20),
        ("timecourses_Fig2A.tsv", 3, 30),
        ("scatters_Fig3.tsv", 4, 40),
        # Tables whose substances do not count, and no tables.
        ("subjects.tsv", 5, 50),
        ("characteristica.tsv", 6, 60),
        ("outputs.tsv", 7, 70),
        ("outputs_Notes.tsv", 8, 80),
        ("Example_Tab1.tsv", 9, 90),
        ("interventions.xlsx", 10, 100),
        ("archive/interventions.tsv", 11, 110),
        ("old/outputs_Tab1.tsv", 12, 120),
    ]
    assert workspace_module.table_signature(files) == (
        ("interventions.tsv", 1, 10),
        ("outputs_Tab1.tsv", 2, 20),
        ("timecourses_Fig2A.tsv", 3, 30),
        ("scatters_Fig3.tsv", 4, 40),
    )
