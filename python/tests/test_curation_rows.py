import json
import os
import threading
import time

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
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
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
    (legacy / "study.json").write_text(json.dumps({"sid": "Legacy1990", "name": "L"}))
    engine.scan()
    engine.scan()
    assert decisions == ["Legacy1990"]
    assert engine.snapshot()["format1_folders"] == 1
    (legacy / "review.json").write_text(dump_json({"status": "draft"}))
    engine.scan()
    assert decisions == ["Legacy1990", "Legacy1990"]
    assert engine.snapshot()["format1_folders"] == 0


@pytest.mark.parametrize("replace", [False, True], ids=["in place", "replaced"])
def test_a_same_size_edit_with_a_preserved_mtime_reads_the_format_again(
    workspace, replace
):
    engine, folder, legacy = workspace
    path = legacy / "study.json"
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
    while path.stat().st_ctime_ns == before.st_ctime_ns:
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
