"""Save generations, immutable inputs, and recovery in the local workspace."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pkdb.curation import engine as module
from pkdb.errors import ClientError
from pkdb.preparation import source_hashes
from pkdb.progress import ProgressEvent


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "sources"
    folder = root / "apixaban" / "Example2020"
    folder.mkdir(parents=True)
    (folder / "study.json").write_text(
        json.dumps({"sid": "Example2020", "name": "Example"})
    )
    engine = module.CurationEngine(
        root, state_dir=tmp_path / "state", offline=True, start=False
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

    monkeypatch.setattr(module, "prepare", prepare)


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
    monkeypatch.setattr(module, "Client", factory)
    monkeypatch.setattr(
        engine, "_vocabulary", Mock(return_value=module.bundled_vocabulary())
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
    monkeypatch.setattr(module.Client, "_request", request)
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
        with pytest.raises(ValueError):
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
    result = SimpleNamespace(created=True, model_dump=lambda **_: {"created": True})
    client, _ = enable_upload(engine, monkeypatch, lambda _: result)
    client.last_upload_report = {"message": "echoed private-api-key"}
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    assert job["status"] == "succeeded"
    report = engine.report(job["report_id"])
    assert report["server_report"]["message"] == "echoed [redacted]"


def test_confirmed_upload_persistence_survives_later_source_error(
    workspace, monkeypatch
):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    hashes = module.source_hashes

    def upload(_):
        monkeypatch.setattr(
            module, "source_hashes", Mock(side_effect=OSError("locked"))
        )
        return SimpleNamespace(created=True, model_dump=lambda **_: {"created": True})

    client, _ = enable_upload(engine, monkeypatch, upload)
    client.last_upload_report = None
    engine.enqueue([row(engine)["id"]], "upload")
    job = run_next(engine)
    monkeypatch.setattr(module, "source_hashes", hashes)
    assert job["persistence"] == "created"
    assert job["status"] != "unknown"
    assert row(engine)["_blocked"] is False


def test_real_scientific_validation_and_external_edit(
    study_folder, vocabulary, tmp_path, monkeypatch
):
    monkeypatch.setattr(module, "bundled_vocabulary", lambda: vocabulary)
    engine = module.CurationEngine(
        study_folder, state_dir=tmp_path / "app-state", offline=True, start=False
    )
    before = {p.name: p.read_bytes() for p in study_folder.iterdir()}
    try:
        engine.enqueue([row(engine)["id"]], "validate")
        assert run_next(engine)["status"] == "succeeded"
        assert row(engine)["status"] == "valid"
        assert before == {p.name: p.read_bytes() for p in study_folder.iterdir()}
        metadata = json.loads((study_folder / "study.json").read_text())
        metadata["outputset"]["outputs"][0]["mean"] = "col==missing"
        (study_folder / "study.json").write_text(json.dumps(metadata))
        engine.scan()
        settle(engine)
        assert run_next(engine)["status"] == "failed"
        problem = next(
            p for p in row(engine)["problems"] if p["code"] == "unknown_column"
        )
        assert problem["source"]["file"] in {"Example.xlsx", "Results.tsv"}
        assert problem["source"]["row"] in {2, 3}
    finally:
        engine.close()


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

    monkeypatch.setattr(module, "prepare", prepare)
    engine.enqueue([row(engine)["id"]], "validate")
    job = run_next(engine)
    assert job["status"] == "canceled"
    assert row(engine)["status"] == "changed"
    assert row(engine)["stale"] is True
    assert row(engine)["_pending"] is True


def test_old_connection_cannot_restore_account_after_endpoint_change(
    workspace, monkeypatch
):
    import threading

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
        value._request.return_value.json.return_value = {
            "username": endpoint,
            "can_upload": True,
        }
        return value

    def vocabulary(client, **kwargs):
        if client.endpoint == "https://old.test":
            started.set()
            assert release.wait(3)

    monkeypatch.setattr(module, "Client", client)
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
    vocabulary = module.bundled_vocabulary()
    client = Mock()
    client.endpoint = "https://old.test"
    client.capabilities.return_value = SimpleNamespace(
        processing_version=module.PROCESSING_VERSION,
        vocabulary_hash=module.vocabulary_hash(vocabulary),
    )
    client.vocabulary.return_value = vocabulary
    monkeypatch.setattr(engine.cache, "load", Mock(return_value=vocabulary))
    engine._connection_generation = 4
    engine.vocabulary = {"status": "offline"}
    engine._vocabulary(client, generation=3)
    assert engine.vocabulary == {"status": "offline"}


def test_invalid_batch_is_not_partially_queued(workspace, monkeypatch):
    engine, folder = workspace
    second = folder.parent / "Other"
    second.mkdir()
    (second / "study.json").write_text('{"sid":"Other"}')
    engine.scan()
    enable_upload(engine, monkeypatch, None)
    rows = list(engine.studies.values())
    rows[1]["duplicate_sid"] = True
    with pytest.raises(ValueError):
        engine.enqueue([item["id"] for item in rows], "upload")
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


def test_assignment_mapping_overrides_ambiguous_title(workspace):
    engine, folder = workspace
    engine.github.data["issues"] = [{"number": 1, "title": "apixaban/Example2020"}]
    original = row(engine)
    other = dict(
        original,
        id="other",
        _folder=folder.parent.parent / "other" / "apixaban" / folder.name,
    )
    engine.studies["other"] = other
    assert engine.snapshot()["github"]["issues"][0]["study_ids"] == []
    engine.mappings[f"{engine.repository}#1"] = [str(folder)]
    assert engine.snapshot()["github"]["issues"][0]["study_ids"] == [original["id"]]


@pytest.mark.parametrize("persistence,attempts", [("not_saved", 2), ("unknown", 1)])
def test_vocabulary_retry_is_bounded_and_never_replays_unknown(
    workspace, monkeypatch, persistence, attempts
):
    engine, _ = workspace
    prepare_mock(monkeypatch)
    error = module.CompatibilityError("Rules changed", persistence=persistence)
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
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "state.json").write_text(
        json.dumps({"endpoint": "https://saved.example"})
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
    )
    try:
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
