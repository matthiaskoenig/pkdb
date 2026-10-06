import json

import pytest

from pkdb.curation import engine as module
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


def test_old_state_with_mappings_loads(tmp_path, tmp_path_factory):
    state = tmp_path_factory.mktemp("state")
    (state / "state.json").write_text(json.dumps({"mappings": {"a#1": ["/x"]}}))
    engine = module.CurationEngine(tmp_path, state_dir=state, offline=True, start=False)
    try:
        assert not hasattr(engine, "mappings")
        engine.snapshot()
    finally:
        engine.close()
