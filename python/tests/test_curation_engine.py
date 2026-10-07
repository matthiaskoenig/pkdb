"""Save generations, immutable inputs, and recovery in the local workspace."""

import json
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pkdb.curation import connection, jobs
from pkdb.curation import engine as module
from pkdb.curation import workspace as workspace_module
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.errors import ClientError, CompatibilityError
from pkdb.identity import UserMismatch
from pkdb.preparation import source_hashes
from pkdb.progress import ProgressEvent
from pkdb.schemas.validation import ValidationIssue, ValidationReport
from pkdb.studyformat import format_folder


@pytest.fixture
def workspace(tmp_path, tmp_path_factory, make_study, valid_files):
    folder = make_study(valid_files)
    engine = module.CurationEngine(
        tmp_path, state_dir=tmp_path_factory.mktemp("state"), offline=True, start=False
    )
    yield engine, folder
    engine.close()


def row(engine):
    return next(iter(engine.studies.values()))


def settle(engine):
    for item in engine.studies.values():
        item["_changed_at"] -= 2
    engine.schedule_changes()


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


def prepare_mock(monkeypatch, *, after=None):
    def prepare(folder, **kwargs):
        prepared = SimpleNamespace(
            file_hashes=source_hashes(folder),
            vocabulary_hash="rules",
            report=SimpleNamespace(
                model_dump=lambda **_: {"issues": [], "complete": True}
            ),
            study=SimpleNamespace(source_digest="snapshot", sid="Example2020"),
        )
        if after:
            after()
        return prepared

    monkeypatch.setattr(jobs, "prepare", prepare)


def enable_upload(engine, monkeypatch, upload):
    engine.offline = False
    engine.endpoint = "https://example.test"
    engine.api_key = "private-api-key"
    engine.account = "curator"
    engine.can_upload = True
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.upload.side_effect = upload
    factory = Mock(return_value=client)
    monkeypatch.setattr(jobs, "Client", factory)
    monkeypatch.setattr(connection, "Client", factory)
    monkeypatch.setattr(
        engine, "_vocabulary", Mock(return_value=jobs.bundled_vocabulary())
    )
    return client, factory


def test_duplicate_events_and_editor_locks_do_not_queue_twice(workspace, monkeypatch):
    engine, folder = workspace
    prepare_mock(monkeypatch)
    settle(engine)
    assert len(engine.queue) == 1
    engine.scan()
    settle(engine)
    assert len(engine.jobs) == 1
    assert run_next(engine)["status"] == "succeeded"
    (folder / "~$outputs.xlsx").write_text("editor lock")
    engine.scan()
    settle(engine)
    assert not engine.queue
    assert row(engine)["stale"] is False


def test_manual_validation_consumes_pending_generation(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    engine.enqueue([row(engine)["id"]], "validate")
    run_next(engine)
    settle(engine)
    assert not engine.queue
    assert len(engine.jobs) == 1


def test_save_during_validation_supersedes_result(workspace, monkeypatch):
    engine, folder = workspace
    prepare_mock(monkeypatch, after=lambda: (folder / "new.txt").write_text("new save"))
    engine.enqueue([row(engine)["id"]], "validate")
    assert run_next(engine)["status"] == "canceled"
    assert row(engine)["stale"] is True
    assert row(engine)["_pending"] is True
    engine.scan()
    prepare_mock(monkeypatch)
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"


def test_offline_validation_never_requests_http(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    request = Mock(side_effect=AssertionError("Offline network request"))
    monkeypatch.setattr(jobs.Client, "_request", request)
    engine.connect()
    engine.refresh_assignments()
    engine.enqueue([row(engine)["id"]], "validate")
    assert run_next(engine)["status"] == "succeeded"
    request.assert_not_called()
    with pytest.raises(ValueError):
        engine.enqueue([row(engine)["id"]], "upload")


def test_unknown_upload_blocks_new_jobs_and_redacts_key(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    client, _ = enable_upload(
        engine,
        monkeypatch,
        ClientError("failed private-api-key", persistence="unknown"),
    )
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    assert job["status"] == "unknown"
    assert row(engine)["_blocked"] is True
    with pytest.raises(ValueError):
        engine.enqueue([row(engine)["id"]], "upload")
    settle(engine)
    assert not engine.queue
    assert "private-api-key" not in json.dumps(engine.snapshot())
    assert "private-api-key" not in json.dumps(engine.report(job["report_id"]))
    assert "private-api-key" not in (engine.state_dir / "state.json").read_text()
    client.upload.assert_called_once()


def test_resume_says_why_an_unknown_upload_cannot_be_reconciled(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    client, _ = enable_upload(
        engine, monkeypatch, ClientError("lost", persistence="unknown")
    )
    identifier = row(engine)["id"]
    engine.enqueue([identifier], "upload")
    run_next(engine)
    engine.endpoint = "https://other.test"
    with pytest.raises(
        jobs.ResumeRefused, match="went to https://example.test. Connect to that"
    ):
        engine.resume()
    engine.endpoint = "https://example.test"
    client.publication.return_value.model_dump.return_value = {"digest": "other"}
    with pytest.raises(jobs.ResumeRefused, match="another version of caffeine/"):
        engine.resume()
    assert row(engine)["_blocked"] is True
    client.publication.return_value.model_dump.return_value = {"digest": "snapshot"}
    engine.resume()
    assert row(engine)["_blocked"] is False
    assert engine.paused is False
    assert identifier.startswith("caffeine/")


def test_restart_marks_transferring_job_unknown(workspace):
    engine, folder = workspace
    engine.offline = False
    engine.endpoint = "https://example.test"
    engine.api_key = "secret"
    job = engine.enqueue([row(engine)["id"]], "upload")[0]
    engine.queue.clear()
    job.update(
        status="running", stage="transfer", source_digest="snapshot", sid="Example2020"
    )
    engine._save()
    replacement = module.CurationEngine(
        folder.parent.parent, state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        assert replacement.jobs[-1]["status"] == "unknown"
        assert row(replacement)["_blocked"] is True
        settle(replacement)
        assert not replacement.queue
        with pytest.raises(jobs.ResumeRefused, match="Turn off offline mode"):
            replacement.resume()
    finally:
        replacement.close()


def test_resolve_file_rechecks_symlink_and_rejects_traversal(workspace, tmp_path):
    engine, folder = workspace
    identifier = row(engine)["id"]
    assert engine.resolve_file(identifier, "study.json") == folder / "study.json"
    with pytest.raises(ValueError):
        engine.resolve_file(identifier, "../../secret")
    outside = tmp_path / "secret.json"
    outside.write_text("private")
    (folder / "study.json").unlink()
    (folder / "study.json").symlink_to(outside)
    with pytest.raises(ValueError):
        engine.resolve_file(identifier, "study.json")


@pytest.mark.parametrize("stage", ["transfer", "response", "commit"])
def test_unexpected_failure_after_write_stays_unknown(workspace, monkeypatch, stage):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    _, factory = enable_upload(engine, monkeypatch, None)

    def upload(_):
        factory.call_args.kwargs["progress"](ProgressEvent(stage))
        raise RuntimeError("interrupted")

    factory.return_value.upload.side_effect = upload
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    assert job["status"] == "unknown"
    assert job["persistence"] == "unknown"
    assert row(engine)["_blocked"] is True


def test_reports_redact_server_echoed_credentials(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    result = SimpleNamespace(
        created=True, url=None, model_dump=lambda **_: {"created": True}
    )
    client, _ = enable_upload(engine, monkeypatch, lambda _: result)
    client.last_upload_report = {"message": "echoed private-api-key"}
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    assert job["status"] == "succeeded"
    report = engine.report(job["report_id"])
    assert report["server_report"]["message"] == "echoed [redacted]"


def test_the_last_upload_survives_many_app_writes_and_a_restart(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    url = "https://pk-db.example/data/Example2020"
    result = SimpleNamespace(
        created=True, url=url, model_dump=lambda **_: {"created": True}
    )
    client, _ = enable_upload(engine, monkeypatch, lambda _: result)
    client.last_upload_report = None
    identity = row(engine)["id"]
    engine.enqueue([identity], "upload")
    job = run_next(engine)
    assert job["status"] == "succeeded", job["message"]
    for index in range(150):
        engine._record_write(identity, f"Saved study.json {index}")
    writes = [entry for entry in engine.jobs if entry["action"] == "write"]
    assert len(writes) == 100
    assert job in engine.jobs
    engine.close()
    restarted = module.CurationEngine(
        engine.root, state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        assert row(restarted)["last_upload"] == job["upload"]
        assert restarted.snapshot()["studies"][0]["last_upload"]["url"] == url
    finally:
        restarted.close()


def job_entry(identifier, status="succeeded", **changes):
    """A finished job of caffeine/Example as an earlier version of the engine saved it."""
    return {
        "id": identifier,
        "study_id": "caffeine/Example",
        "study_name": "Example",
        "action": "validate",
        "status": status,
        "created_at": jobs.now(),
        "message": "Validation passed",
        "automatic": False,
        "endpoint": "",
        "persistence": "not_attempted",
        "report_id": None,
        **changes,
    }


def reports_of(engine):
    return {path.stem for path in (engine.state_dir / "reports").glob("*.json")}


def test_clearing_the_history_keeps_active_jobs_uploads_and_current_reports(
    workspace, monkeypatch
):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    url = "https://pk-db.example/data/Example2020"
    result = SimpleNamespace(
        created=True, url=url, model_dump=lambda **_: {"created": True}
    )
    client, _ = enable_upload(engine, monkeypatch, lambda _: result)
    client.last_upload_report = None
    identity = row(engine)["id"]
    engine.enqueue([identity], "upload")
    earlier = run_next(engine)
    engine.enqueue([identity], "upload")
    upload = run_next(engine)
    engine.enqueue([identity], "validate")
    validation = run_next(engine)
    engine._record_write(identity, "Saved study.json")
    # A running validation and the one queued behind it.
    engine.enqueue([identity], "validate")
    running = engine.queue.pop(identity)
    running["status"] = "running"
    engine.enqueue([identity], "validate")
    queued = engine.queue[identity]
    unknown = job_entry(
        "unknown", "unknown", action="upload", workspace=str(engine.root)
    )
    engine.jobs.append(unknown)
    assert row(engine)["report_id"] == validation["id"]
    assert engine.snapshot()["clearable_jobs"] == 2

    engine.clear_history()

    # The earlier upload and the write go; the report of the study stays downloadable.
    assert [job["id"] for job in engine.jobs] == [
        job["id"] for job in [upload, validation, running, queued, unknown]
    ]
    assert reports_of(engine) == {upload["id"], validation["id"]}
    assert row(engine)["report_id"] == validation["id"]
    assert engine.report(validation["id"])["job"]["id"] == validation["id"]
    assert engine.snapshot()["clearable_jobs"] == 0
    assert earlier["id"] not in reports_of(engine)
    engine.close()
    restarted = module.CurationEngine(
        engine.root, state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        assert row(restarted)["last_upload"]["url"] == url
    finally:
        restarted.close()


def test_clearing_the_history_removes_the_finished_jobs_of_this_workspace_only(
    workspace, tmp_path_factory, monkeypatch
):
    engine, folder = workspace
    prepare_mock(monkeypatch)
    identity = row(engine)["id"]
    first = engine.root
    engine.enqueue([identity], "validate")
    first_old = run_next(engine)
    engine.enqueue([identity], "validate")
    first_current = run_next(engine)
    engine._record_write(identity, "Saved study.json")
    first_write = engine.jobs[-1]
    # Saved by an earlier version without its workspace: it cannot be placed and stays.
    legacy = job_entry("legacy", action="write", message="Saved study.json")
    engine.jobs.insert(0, legacy)
    # A second workspace with a study of the same identity.
    second = tmp_path_factory.mktemp("second")
    shutil.copytree(folder, second / "caffeine" / "Example")
    engine.select_workspace(second)
    engine.enqueue([identity], "validate")
    second_old = run_next(engine)
    engine.enqueue([identity], "validate")
    second_current = run_next(engine)
    engine._record_write(identity, "Saved study.json")
    second_write = engine.jobs[-1]
    detail = engine.study_detail(identity)
    assert [job["id"] for job in detail["jobs"]] == [
        second_write["id"],
        second_current["id"],
        second_old["id"],
        "legacy",
    ]
    assert engine.snapshot()["clearable_jobs"] == 2

    engine.clear_history()

    remaining = [job["id"] for job in engine.jobs]
    assert second_old["id"] not in remaining and second_write["id"] not in remaining
    assert {first_old["id"], first_current["id"], first_write["id"], "legacy"} <= set(
        remaining
    )
    assert second_current["id"] in remaining
    assert first_old["id"] in reports_of(engine)
    assert second_old["id"] not in reports_of(engine)

    # The rows of a workspace that opens again have no report yet, so its last one goes too.
    engine.select_workspace(first)
    assert engine.snapshot()["clearable_jobs"] == 3
    engine.clear_history()
    remaining = [job["id"] for job in engine.jobs]
    assert not {first_old["id"], first_current["id"], first_write["id"]} & set(
        remaining
    )
    assert {"legacy", second_current["id"]} <= set(remaining)


def test_canceled_jobs_say_why(workspace, tmp_path_factory):
    engine, _ = workspace
    identity = row(engine)["id"]
    engine.enqueue([identity], "validate")
    replaced = engine.queue[identity]
    engine.enqueue([identity], "validate")
    assert replaced["status"] == "canceled"
    assert replaced["message"] == "Replaced by a newer validation"
    paused = engine.queue[identity]
    engine.set_paused(True)
    assert paused["status"] == "canceled"
    assert paused["message"] == "Canceled when automatic actions were paused"
    engine.set_paused(False)
    engine.enqueue([identity], "validate")
    switched = engine.queue[identity]
    first = engine.root
    engine.select_workspace(tmp_path_factory.mktemp("other"))
    assert switched["status"] == "canceled"
    assert switched["message"] == "Canceled when the workspace changed"
    # A job still queued when pkdb curate ended without closing the engine.
    engine.select_workspace(first)
    engine.enqueue([identity], "validate")
    stopped = engine.queue[identity]["id"]
    engine._save()
    restarted = module.CurationEngine(
        engine.root, state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        job = next(job for job in restarted.jobs if job["id"] == stopped)
        assert (job["status"], job["message"]) == (
            "canceled",
            "Canceled when pkdb curate stopped",
        )
    finally:
        restarted.close()


def test_problems_found_are_no_failure_of_the_job(workspace, monkeypatch):
    engine, folder = workspace
    identity = row(engine)["id"]
    path = folder / "interventions.tsv"
    path.write_text(path.read_text().replace("oral", "rectal"))
    engine.scan()
    engine.enqueue([identity], "validate")
    job = run_next(engine)
    assert (job["status"], job["message"]) == ("invalid", "Validation found problems")
    assert row(engine)["status"] == "invalid"


def test_a_refusal_of_the_server_validation_with_a_report_is_problems_found(
    workspace, monkeypatch
):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    enable_upload(engine, monkeypatch, lambda _: upload_result())
    identity = row(engine)["id"]
    report = ValidationReport(
        issues=[ValidationIssue(code="unknown_unit", message="Unknown unit")]
    )
    refusals = [
        ClientError(
            "The server found problems",
            status_code=422,
            report=report,
            persistence="not_saved",
        ),
        ClientError("The server failed", status_code=500, persistence="unknown"),
    ]

    def refuse(client, prepared):
        raise refusals.pop(0)

    monkeypatch.setattr(engine, "_server_validate", refuse)
    engine.enqueue([identity], "validate_remote")
    job = run_next(engine)
    assert job["status"] == "invalid"
    assert row(engine)["status"] == "invalid"
    assert engine.paused is False
    # Without a report the job failed, and the engine pauses as before.
    engine.enqueue([identity], "validate_remote")
    job = run_next(engine)
    assert job["status"] == "failed"
    assert engine.paused is True


def test_saved_problems_found_load_with_their_own_status(workspace):
    engine, _ = workspace
    engine.jobs.extend(
        [
            job_entry("problems", "failed", message="Validation found problems"),
            job_entry("broken", "failed", message="Could not read the source files"),
        ]
    )
    engine.close()
    restarted = module.CurationEngine(
        engine.root, state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        statuses = {job["id"]: job["status"] for job in restarted.jobs}
        assert statuses == {"problems": "invalid", "broken": "failed"}
    finally:
        restarted.close()


def upload_result():
    return SimpleNamespace(
        created=True,
        url="https://pk-db.example/data/Example2020",
        model_dump=lambda **_: {"created": True},
    )


def pause_and_resume(engine):
    engine.set_paused(True)
    assert not engine.queue
    engine.set_paused(False)
    settle(engine)
    return [job["action"] for job in engine.queue.values()]


def test_a_paused_initial_validation_resumes_as_a_validation(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    client, _ = enable_upload(engine, monkeypatch, lambda _: upload_result())
    client.last_upload_report = None
    identity = row(engine)["id"]
    settle(engine)
    assert [job["action"] for job in engine.queue.values()] == ["validate"]
    engine.set_mode([identity], "upload")
    assert pause_and_resume(engine) == ["validate"]
    assert run_next(engine)["status"] == "succeeded"
    client.upload.assert_not_called()
    settle(engine)
    assert not engine.queue


def test_a_paused_manual_validation_resumes_as_a_validation(workspace, monkeypatch):
    engine, _ = workspace
    enable_upload(engine, monkeypatch, lambda _: upload_result())
    identity = row(engine)["id"]
    engine.set_mode([identity], "upload")
    engine.enqueue([identity], "validate")
    assert pause_and_resume(engine) == ["validate"]


def test_a_paused_upload_resumes_as_an_upload(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    client, _ = enable_upload(engine, monkeypatch, lambda _: upload_result())
    client.last_upload_report = None
    engine.enqueue([row(engine)["id"]], "upload")
    assert pause_and_resume(engine) == ["upload"]
    job = run_next(engine)
    assert job["status"] == "succeeded" and job["upload"]
    client.upload.assert_called_once()


def test_a_paused_job_of_a_study_with_save_action_off_resumes(workspace, monkeypatch):
    engine, _ = workspace
    identity = row(engine)["id"]
    engine.set_mode([identity], "off")
    engine.enqueue([identity], "validate")
    assert pause_and_resume(engine) == ["validate"]


def test_a_save_after_pausing_follows_the_save_action(workspace, monkeypatch):
    engine, folder = workspace
    enable_upload(engine, monkeypatch, lambda _: upload_result())
    engine.enqueue([row(engine)["id"]], "upload")
    engine.set_paused(True)
    (folder / "notes.txt").write_text("a new save")
    engine.scan()
    engine.set_paused(False)
    settle(engine)
    assert [job["action"] for job in engine.queue.values()] == ["validate"]


def test_a_used_resume_action_is_not_used_again(workspace, monkeypatch):
    engine, folder = workspace
    prepare_mock(monkeypatch)
    client, _ = enable_upload(engine, monkeypatch, lambda _: upload_result())
    client.last_upload_report = None
    engine.enqueue([row(engine)["id"]], "upload")
    assert pause_and_resume(engine) == ["upload"]
    run_next(engine)
    # A workbook closed later queues a validation, never the upload again.
    engine._sync_later(row(engine))
    settle(engine)
    assert [job["action"] for job in engine.queue.values()] == ["validate"]


def test_uploaded_study_link_survives_restart(workspace, tmp_path, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    url = "https://pk-db.example/data/Example2020"
    result = SimpleNamespace(
        created=True, url=url, model_dump=lambda **_: {"created": True}
    )
    client, _ = enable_upload(engine, monkeypatch, lambda _: result)
    client.last_upload_report = None
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    assert job["upload"]["url"] == url
    assert row(engine)["last_upload"]["url"] == url
    engine.close()
    restarted = module.CurationEngine(
        engine.root, state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        assert row(restarted)["last_upload"] == job["upload"]
        assert restarted.snapshot()["studies"][0]["last_upload"]["url"] == url
    finally:
        restarted.close()


def test_confirmed_upload_persistence_survives_later_source_error(
    workspace, monkeypatch
):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    hashes = jobs.source_hashes

    def upload(_):
        locked = Mock(side_effect=OSError("locked"))
        monkeypatch.setattr(jobs, "source_hashes", locked)
        monkeypatch.setattr(workspace_module, "source_hashes", locked)
        return SimpleNamespace(
            created=True, url=None, model_dump=lambda **_: {"created": True}
        )

    client, _ = enable_upload(engine, monkeypatch, upload)
    client.last_upload_report = None
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    monkeypatch.setattr(jobs, "source_hashes", hashes)
    monkeypatch.setattr(workspace_module, "source_hashes", hashes)
    assert job["persistence"] == "created"
    assert job["status"] != "unknown"
    assert row(engine)["_blocked"] is False


def test_real_scientific_validation_and_external_edit(
    workspace, sf_vocabulary, monkeypatch
):
    engine, folder = workspace
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    assert format_folder(folder).ok
    engine.scan()
    engine.enqueue([row(engine)["id"]], "validate")
    assert run_next(engine)["status"] == "succeeded"
    assert row(engine)["status"] == "valid"
    path = folder / "interventions.tsv"
    path.write_text(path.read_text().replace("oral", "rectal"))
    engine.scan()
    settle(engine)
    assert run_next(engine)["status"] == "invalid"
    assert row(engine)["problems"]


def test_pending_manual_job_cannot_bypass_new_unknown_outcome(workspace, monkeypatch):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    client, _ = enable_upload(
        engine, monkeypatch, ClientError("connection lost", persistence="unknown")
    )
    identifier = row(engine)["id"]
    engine.enqueue([identifier], "upload")
    first = engine.queue.pop(identifier)
    engine.enqueue([identifier], "upload")
    engine.run_job(first)
    assert first["status"] == "unknown"
    second = run_next(engine)
    assert second["status"] == "canceled"
    assert row(engine)["status"] == "unknown"
    client.upload.assert_called_once()


def test_save_during_failed_validation_keeps_diagnostics_stale(workspace, monkeypatch):
    from pkdb.schemas.validation import fail

    engine, folder = workspace

    def prepare(*args, **kwargs):
        (folder / "latest.txt").write_text("newer input")
        fail("invalid", "Previous save was invalid")

    monkeypatch.setattr(jobs, "prepare", prepare)
    engine.enqueue([row(engine)["id"]], "validate")
    job = run_next(engine)
    assert job["status"] == "canceled"
    assert row(engine)["status"] == "changed"
    assert row(engine)["stale"] is True
    assert row(engine)["_pending"] is True


def test_old_connection_cannot_restore_account_after_endpoint_change(
    workspace, monkeypatch
):
    engine, _ = workspace
    engine.offline = False
    engine.endpoint = "https://old.test"
    engine.api_key = "key"
    started, release = threading.Event(), threading.Event()

    def client(endpoint, **kwargs):
        value = Mock()
        value.endpoint = endpoint
        value.__enter__ = Mock(return_value=value)
        value.__exit__ = Mock(return_value=False)
        value.identity.return_value = SimpleNamespace(
            username=endpoint, can_upload=True
        )
        return value

    def vocabulary(client, **kwargs):
        if client.endpoint == "https://old.test":
            started.set()
            assert release.wait(3)

    monkeypatch.setattr(jobs, "Client", client)
    monkeypatch.setattr(connection, "Client", client)
    monkeypatch.setattr(engine, "_vocabulary", vocabulary)
    thread = threading.Thread(target=engine.connect)
    thread.start()
    try:
        assert started.wait(3)
        engine.configure(endpoint="https://new.test")
        assert engine.account == "https://new.test"
    finally:
        release.set()
        thread.join(timeout=3)
    assert engine.endpoint == "https://new.test"
    assert engine.account == "https://new.test"


def test_stale_connection_vocabulary_does_not_replace_current_status(
    workspace, monkeypatch
):
    engine, _ = workspace
    vocabulary = jobs.bundled_vocabulary()
    client = Mock()
    client.endpoint = "https://old.test"
    client.capabilities.return_value = SimpleNamespace(
        processing_version=PROCESSING_VERSION,
        vocabulary_hash=vocabulary_hash(vocabulary),
    )
    client.vocabulary.return_value = vocabulary
    monkeypatch.setattr(engine.cache, "load", Mock(return_value=vocabulary))
    engine._connection_generation = 4
    engine.vocabulary = {"status": "offline"}
    engine._vocabulary(client, generation=3)
    assert engine.vocabulary == {"status": "offline"}


def test_invalid_batch_is_not_partially_queued(workspace, monkeypatch):
    engine, folder = workspace
    shutil.copytree(folder, folder.parent / "Other")
    shutil.copytree(folder, folder.parent.parent / "copies" / "caffeine" / "Example")
    engine.scan()
    enable_upload(engine, monkeypatch, None)
    with pytest.raises(ValueError, match="identity of two folders"):
        engine.enqueue(["caffeine/Other", "caffeine/Example"], "upload")
    assert not engine.jobs
    assert not engine.queue


def test_repository_change_validated_and_cached_assignments_reset(workspace):
    engine, _ = workspace
    engine.github.data["users"] = [{"login": "old-user"}]
    engine.configure(repository="another/repository")
    assert engine.repository == "another/repository"
    assert engine.github.data["users"] == []
    with pytest.raises(ValueError):
        engine.configure(repository="invalid")
    assert engine.repository == "another/repository"


def test_invalid_settings_leave_endpoint_and_queue_intact(workspace):
    engine, _ = workspace
    engine.enqueue([row(engine)["id"]], "validate")
    original_endpoint = engine.endpoint
    with pytest.raises(ValueError):
        engine.configure(
            endpoint="https://new.test", github_user="not-an-available-user"
        )
    assert engine.endpoint == original_endpoint
    assert len(engine.queue) == 1


@pytest.mark.parametrize("persistence,attempts", [("not_saved", 2), ("unknown", 1)])
def test_vocabulary_retry_is_bounded_and_never_replays_unknown(
    workspace, monkeypatch, persistence, attempts
):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    error = CompatibilityError("Rules changed", persistence=persistence)
    client, _ = enable_upload(engine, monkeypatch, [error, error])
    job = engine.enqueue([row(engine)["id"]], "upload")[0]
    engine.queue.clear()
    engine.run_job(job)
    assert client.upload.call_count == attempts
    assert job["status"] == ("unknown" if persistence == "unknown" else "failed")
    assert engine.paused


@pytest.mark.parametrize("explicit", [False, True])
def test_environment_connection_defaults(tmp_path, monkeypatch, explicit):
    monkeypatch.setenv("PKDB_ENDPOINT", "https://environment.example/")
    monkeypatch.setenv("PKDB_API_KEY", "environment-secret")
    monkeypatch.setenv("PKDB_USER", "environment-user")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "state.json").write_text(
        json.dumps({"endpoint": "https://saved.example", "user": "saved-user"})
    )
    sources = tmp_path / "sources"
    sources.mkdir()
    engine = module.CurationEngine(
        sources,
        state_dir=state_dir,
        offline=True,
        start=False,
        endpoint="https://explicit.example" if explicit else None,
        api_key="explicit-secret" if explicit else None,
        user="explicit-user" if explicit else None,
    )
    try:
        assert engine.user == ("explicit-user" if explicit else "environment-user")
        assert engine.snapshot()["user"] == engine.user
        assert engine.snapshot()["authenticated"] is True
        assert engine.endpoint == (
            "https://explicit.example" if explicit else "https://environment.example"
        )
        assert engine.api_key == (
            "explicit-secret" if explicit else "environment-secret"
        )
        engine._save()
        for secret in ("environment-secret", "explicit-secret"):
            assert secret not in json.dumps(engine.snapshot())
            assert secret not in (state_dir / "state.json").read_text()
    finally:
        engine.close()


def test_saved_user_is_used_without_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("PKDB_USER", raising=False)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "state.json").write_text(json.dumps({"user": "saved-user"}))
    sources = tmp_path / "sources"
    sources.mkdir()
    engine = module.CurationEngine(
        sources, state_dir=state_dir, offline=True, start=False
    )
    try:
        assert engine.user == "saved-user"
    finally:
        engine.close()


def connection_engine(engine, monkeypatch, *, identity=None, failure=None):
    """Point the engine at a fake server whose checks succeed or fail."""
    engine.offline = False
    engine.endpoint = "https://example.test"
    engine.api_key = "key"
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.identity.return_value = identity or SimpleNamespace(
        username="curator", can_upload=True
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(jobs, "Client", factory)
    monkeypatch.setattr(connection, "Client", factory)

    def vocabulary(client, **kwargs):
        engine.server_version = "99.0.0"
        if failure:
            raise failure

    monkeypatch.setattr(engine, "_vocabulary", vocabulary)
    return client, factory


def test_connection_status_reports_reachable_server(workspace, monkeypatch):
    engine, _ = workspace
    assert engine.snapshot()["connection"] == "offline"
    connection_engine(engine, monkeypatch)
    engine.checked_at = None
    assert engine.snapshot()["connection"] == "connecting"
    engine.connect()
    state = engine.snapshot()
    assert state["connection"] == "connected"
    assert state["account"] == "curator"
    assert state["checked_at"]
    assert state["server_version"] == "99.0.0"
    assert state["update_required"] is True
    assert state["client_version"] == module.__version__
    engine.endpoint = ""
    assert engine.snapshot()["connection"] == "not_configured"


@pytest.mark.parametrize(
    "failure,status,message",
    [
        (
            ClientError("PK-DB request failed", code="unreachable"),
            "error",
            "Cannot reach https://example.test",
        ),
        (
            ClientError("rejected", status_code=503),
            "error",
            "database is unavailable (HTTP 503)",
        ),
        (
            ClientError("rejected", status_code=401),
            "unauthorized",
            "rejected the API key",
        ),
        (
            CompatibilityError("Upgrade pkdb", code="processing_version_mismatch"),
            "incompatible",
            "Run `pkdb update`",
        ),
        (
            CompatibilityError("Server vocabulary changed; validate again"),
            "error",
            "Server vocabulary changed",
        ),
        (
            ClientError("belongs to someone else", code="user_mismatch"),
            "unauthorized",
            "belongs to someone else",
        ),
    ],
)
def test_connection_failures_are_classified(
    workspace, monkeypatch, failure, status, message
):
    engine, _ = workspace
    connection_engine(engine, monkeypatch, failure=failure)
    engine.account, engine.can_upload = "previous", True
    engine.connect()
    state = engine.snapshot()
    assert state["connection"] == status
    assert message in state["connection_error"]
    assert state["account"] is None
    assert state["can_upload"] is False


def test_a_key_of_another_account_refuses_writes_until_it_matches(
    workspace, monkeypatch
):
    engine, _ = workspace
    engine.user = "curator"
    mismatch = ClientError(
        "The API key belongs to PK-DB user 'other', not the expected user 'curator'",
        code="user_mismatch",
    )
    connection_engine(engine, monkeypatch, failure=mismatch)
    engine.connect()
    with pytest.raises(UserMismatch, match="'other'"):
        engine.author()
    connection_engine(
        engine,
        monkeypatch,
        failure=ClientError("PK-DB request failed", code="unreachable"),
    )
    engine.connect()
    # An unreachable server cannot check the key: the configured user writes.
    assert engine.author().user == "curator"
    connection_engine(engine, monkeypatch, failure=mismatch)
    engine.connect()
    connection_engine(engine, monkeypatch)
    engine.connect()
    assert engine.author().user == "curator"
    assert engine.snapshot()["author"] == {"user": "curator", "reason": None}


def test_the_watcher_survives_an_unexpected_scan_failure(workspace, monkeypatch):
    engine, _ = workspace

    class Ticks(threading.Event):
        """A stop event whose wait returns at once."""

        def wait(self, timeout=None):
            return self.is_set()

    engine.stop = Ticks()
    scans = []

    def scan():
        scans.append(len(scans))
        if len(scans) == 1:
            raise RuntimeError("unexpected")
        engine.stop.set()

    monkeypatch.setattr(engine, "scan", scan)
    engine._watch()
    assert scans == [0, 1]


def test_the_watcher_plans_the_workbook_of_a_row_without_a_job(workspace, monkeypatch):
    engine, _ = workspace
    engine.set_mode([row(engine)["id"]], "off")
    assert row(engine)["sync"]["status"] == "not_checked"

    class Ticks(threading.Event):
        """A stop event whose wait returns at once."""

        def wait(self, timeout=None):
            return self.is_set()

    engine.stop = Ticks()
    monkeypatch.setattr(engine, "scan", engine.stop.set)
    engine._watch()
    assert row(engine)["sync"]["status"] == "no_workbook"


def test_rows_that_scheduling_skips_get_their_workbook_planned(workspace):
    engine, _ = workspace
    item = row(engine)
    # An upload on save without an authorized account waits for the account.
    item.update(mode="upload", _initial=False)
    assert item["_pending"] is True
    engine._check_workbooks()
    assert item["sync"]["status"] == "no_workbook"
    settle(engine)
    assert not engine.queue and item["message"].startswith("Upload on save suspended")


def test_a_paused_engine_plans_the_workbooks_of_pending_rows(workspace):
    engine, _ = workspace
    engine.set_paused(True)
    assert row(engine)["_pending"] is True
    engine._check_workbooks()
    assert row(engine)["sync"]["status"] == "no_workbook"


def test_connection_checks_expected_user(workspace, monkeypatch):
    engine, _ = workspace
    _, factory = connection_engine(engine, monkeypatch)
    engine.user = "expected"
    engine.connect()
    assert factory.call_args.kwargs["user"] == "expected"


def test_changing_user_reconnects_and_is_saved(workspace, monkeypatch):
    engine, _ = workspace
    connect = Mock()
    monkeypatch.setattr(engine, "connect", connect)
    engine.configure(user=" curator ")
    assert engine.user == "curator"
    assert json.loads((engine.state_dir / "state.json").read_text())["user"] == (
        "curator"
    )
    connect.assert_called_once()
    engine.configure(user="curator")
    connect.assert_called_once()
    with pytest.raises(ValueError):
        engine.configure(user=1)


def test_reference_preview_save_and_stale_review(workspace):
    import httpx2

    from pkdb.references import ReferenceResolver

    engine, folder = workspace
    xml = (
        "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>"
        "<Article><ArticleTitle>Cached title</ArticleTitle></Article>"
        "</MedlineCitation></PubmedArticle></PubmedArticleSet>"
    )
    with httpx2.Client(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, text=xml))
    ) as client:
        ReferenceResolver(client=client).pubmed("123")
    study = json.loads((folder / "study.json").read_text())
    body = {
        "id": row(engine)["id"],
        "input": {
            "title": "Manual report",
            "authors": [{"organization": "Research team"}],
            "publication_date": "2020",
        },
    }
    original = (folder / "reference.json").read_bytes()
    preview = engine.reference_action("preview", body)
    assert (folder / "reference.json").read_bytes() == original
    assert preview["reference"]["sid"] == "123"
    engine.reference_action("save", {"id": body["id"], "token": preview["token"]})
    assert (
        engine.reference_action("read", body)["reference"]["publication_date"] == "2020"
    )
    with pytest.raises(ValueError, match="expired"):
        engine.reference_action("save", {"id": body["id"], "token": preview["token"]})
    preview = engine.reference_action("preview", body)
    (folder / "study.json").write_text(json.dumps({**study, "name": "changed"}))
    with pytest.raises(ValueError, match="changed since preview"):
        engine.reference_action("save", {"id": body["id"], "token": preview["token"]})


def test_validation_creates_missing_reference_without_requeue(
    workspace, monkeypatch, tmp_path
):
    import httpx2

    from pkdb.references import ReferenceResolver

    engine, folder = workspace
    xml = (
        "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>"
        "<Article><ArticleTitle>Cached title</ArticleTitle></Article>"
        "</MedlineCitation></PubmedArticle></PubmedArticleSet>"
    )
    monkeypatch.setenv("PKDB_CACHE_DIR", str(tmp_path / "cache"))
    with httpx2.Client(
        transport=httpx2.MockTransport(lambda _: httpx2.Response(200, text=xml))
    ) as client:
        ReferenceResolver(client=client).pubmed("123")
    (folder / "reference.json").unlink()
    prepare_mock(monkeypatch)
    engine.scan()
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "succeeded"
    saved = json.loads((folder / "reference.json").read_text())
    assert (saved["sid"], saved["pmid"], saved["title"]) == (
        "123",
        "123",
        "Cached title",
    )
    report = json.loads(
        (engine.state_dir / "reports" / f"{job['id']}.json").read_text()
    )
    assert report["reference_updated"] == "Created reference.json from PubMed 123"
    settle(engine)
    assert not engine.queue
    assert row(engine)["stale"] is False


def test_scan_summarizes_study_and_reference_metadata(workspace):
    engine, folder = workspace
    summary = next(
        s for s in engine.snapshot()["studies"] if s["id"] == row(engine)["id"]
    )["summary"]
    assert summary["creator"] == "curator"
    assert summary["curators"] == ["curator"]
    assert summary["review_status"] == "draft"
    assert row(engine)["reference"]["title"] == "Example study"
    (folder / "reference.json").write_text(json.dumps({"sid": 123, "title": "Paper"}))
    engine.scan()
    assert row(engine)["reference"]["title"] == "Paper"
    assert row(engine)["summary"]["title"] == "Paper"


def test_recent_workspaces_are_ordered_limited_and_persisted(workspace, tmp_path):
    engine, folder = workspace
    root = engine.root
    folders = []
    for index in range(module.RECENT_LIMIT + 2):
        candidate = tmp_path / f"workspace{index}"
        candidate.mkdir()
        folders.append(candidate)
        engine.select_workspace(candidate)
    engine.select_workspace(folders[-3])
    recent = [item["path"] for item in engine.snapshot()["recent_workspaces"]]
    assert len(recent) == module.RECENT_LIMIT
    assert recent[:3] == [str(folders[-3]), str(folders[-1]), str(folders[-2])]
    assert len(set(recent)) == len(recent)
    assert str(root) not in recent
    folders[-1].rmdir()
    restarted = module.CurationEngine(
        folders[-3], state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        entries = restarted.snapshot()["recent_workspaces"]
        assert [item["path"] for item in entries] == recent
        assert entries[1] == {"path": str(folders[-1]), "exists": False}
        assert entries[0]["exists"] is True
        restarted.forget_workspace(str(folders[-1]))
        remaining = [item["path"] for item in restarted.snapshot()["recent_workspaces"]]
        assert str(folders[-1]) not in remaining
        assert len(remaining) == module.RECENT_LIMIT - 1
    finally:
        restarted.close()


def test_select_workspace_explains_unusable_paths(workspace, tmp_path):
    engine, folder = workspace
    with pytest.raises(module.WorkspaceError, match="does not exist"):
        engine.select_workspace(tmp_path / "missing")
    with pytest.raises(module.WorkspaceError, match="not a folder"):
        engine.select_workspace(folder / "study.json")
    with pytest.raises(module.WorkspaceError, match="outside"):
        engine.select_workspace(engine.state_dir.parent)
    engine.active = "job"
    with pytest.raises(module.WorkspaceError, match="Wait for the current job"):
        engine.select_workspace(folder)


def test_list_directories_classifies_and_filters_folders(workspace, tmp_path):
    engine, folder = workspace
    repository = tmp_path / "browse" / "pkdb_data"
    (repository / "studies").mkdir(parents=True)
    (tmp_path / "browse" / "Zeta").mkdir()
    (tmp_path / "browse" / "alpha").mkdir()
    (tmp_path / "browse" / ".git").mkdir()
    (tmp_path / "browse" / "notes.txt").write_text("")
    (tmp_path / "browse" / "linked").symlink_to(repository)
    listing = engine.list_directories(str(tmp_path / "browse"))
    assert listing["path"] == str(tmp_path / "browse")
    assert listing["parent"] == str(tmp_path)
    assert listing["kind"] == "folder"
    assert listing["truncated"] is False
    assert [(e["name"], e["kind"]) for e in listing["entries"]] == [
        ("alpha", "folder"),
        ("linked", "repository"),
        ("pkdb_data", "repository"),
        ("Zeta", "folder"),
    ]
    assert listing["entries"][2]["path"] == str(repository)
    study = engine.list_directories(str(folder))
    assert study["kind"] == "study"
    assert engine.list_directories(str(folder.parent))["entries"][0]["kind"] == "study"


def test_list_directories_defaults_limits_and_rejects(workspace, tmp_path, monkeypatch):
    engine, folder = workspace
    assert engine.list_directories()["path"] == str(engine.root)
    assert engine.list_directories("~")["path"] == str(Path.home())
    root = engine.list_directories(Path(engine.root).anchor)
    assert root["parent"] is None
    many = tmp_path / "many"
    for index in range(5):
        (many / f"d{index}").mkdir(parents=True)
    monkeypatch.setattr(workspace_module, "DIRECTORY_LIMIT", 3)
    limited = engine.list_directories(str(many))
    assert [e["name"] for e in limited["entries"]] == ["d0", "d1", "d2"]
    assert limited["truncated"] is True
    with pytest.raises(module.WorkspaceError, match="absolute"):
        engine.list_directories("relative/path")
    with pytest.raises(module.WorkspaceError, match="does not exist"):
        engine.list_directories(str(tmp_path / "missing"))
    with pytest.raises(module.WorkspaceError, match="not a folder"):
        engine.list_directories(str(folder / "study.json"))
    engine.root = tmp_path / "removed"
    assert engine.list_directories()["path"] == str(Path.home())


def test_missing_remembered_workspace_falls_back_at_startup(
    workspace, tmp_path, monkeypatch
):
    engine, folder = workspace
    removed = tmp_path / "removed"
    removed.mkdir()
    engine.select_workspace(removed)
    engine.close()
    removed.rmdir()
    monkeypatch.chdir(folder)
    restarted = module.CurationEngine(
        state_dir=engine.state_dir, offline=True, start=False
    )
    try:
        assert restarted.root == folder
        recent = restarted.snapshot()["recent_workspaces"]
        assert {"path": str(removed), "exists": False} in recent
    finally:
        restarted.close()


def test_jobs_keep_study_name_after_workspace_switch(workspace, tmp_path):
    engine, folder = workspace
    engine.enqueue([row(engine)["id"]], "validate")
    other = tmp_path / "other"
    other.mkdir()
    engine.select_workspace(other)
    assert engine.snapshot()["jobs"][-1]["study_name"] == "Example"
