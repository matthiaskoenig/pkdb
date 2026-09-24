import json

from pkdb import Client
from pkdb.curation.engine import CurationEngine


def test_context_requires_identity_and_returns_only_own_assignments(
    client, creator_headers
):
    assert client.get("/api/v2/curation-context").status_code == 401
    response = client.get("/api/v2/curation-context", headers=creator_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"]
    assert data["can_upload"]
    assert data["studies"] == []
    assert "email" not in data


def test_local_engine_validates_uploads_and_observes_saves(
    client,
    creator_headers,
    valid_bundle,
    tmp_path,
    monkeypatch,
):
    folder = tmp_path / valid_bundle.study["name"]
    folder.mkdir()
    (folder / "study.json").write_text(json.dumps(valid_bundle.study))
    (folder / "reference.json").write_text(json.dumps(valid_bundle.reference))
    (folder / "notes.txt").write_text("Original attachment")
    monkeypatch.setattr(
        "pkdb.curation.engine.Client",
        lambda *args, **kwargs: Client(*args, transport=client, **kwargs),
    )
    engine = CurationEngine(
        folder,
        endpoint="http://testserver",
        api_key=creator_headers["Authorization"].split()[1],
        state_dir=tmp_path / "app-state",
        start=False,
    )
    try:
        engine.connect()
        assert engine.account
        identifier = next(iter(engine.studies))
        validation = engine.enqueue([identifier], "validate_remote")[0]
        engine.queue.clear()
        engine.run_job(validation)
        assert validation["status"] == "succeeded", engine.report(
            validation["report_id"]
        )
        assert validation["persistence"] == "not_attempted"
        assert (
            client.get(
                f"/api/v2/studies/{valid_bundle.study['sid']}", headers=creator_headers
            ).status_code
            == 404
        )
        engine.set_mode([identifier], "upload")
        job = engine.enqueue([identifier], "upload")[0]
        engine.queue.clear()
        engine.run_job(job)
        assert job["status"] == "succeeded", engine.report(job["report_id"])
        assert job["persistence"] == "created"
        assert (
            client.get(
                f"/api/v2/studies/{valid_bundle.study['sid']}", headers=creator_headers
            ).status_code
            == 200
        )
        # A real external edit becomes one pending upload of the newest snapshot.
        (folder / "notes.txt").write_text("Saved externally")
        engine.scan()
        engine.studies[identifier]["_changed_at"] -= 2
        engine.schedule_changes()
        job = engine.queue.pop(identifier)
        assert job["automatic"] and job["action"] == "upload"
        engine.run_job(job)
        assert job["persistence"] == "replaced", engine.report(job["report_id"])
        # Invalid saved JSON is diagnosed and cannot replace the uploaded study.
        (folder / "study.json").write_text("{")
        engine.scan()
        engine.studies[identifier]["_changed_at"] -= 2
        engine.schedule_changes()
        job = engine.queue.pop(identifier)
        engine.run_job(job)
        assert job["status"] == "failed"
        assert job["persistence"] == "not_attempted"
        assert engine.studies[identifier]["problems"]
    finally:
        engine.close()


def test_context_personal_key_scope_and_private_assignment_boundary(
    client, session_factory
):
    from pkdb_server.db.models.studies import Study, StudyGrant
    from pkdb_server.db.models.users import User
    from tests.api.test_upload_visibility import key_for

    with session_factory.begin() as session:
        reader = User(username="context-reader", role="user", active=True)
        writer = User(username="context-write-only", role="curator", active=True)
        session.add_all([reader, writer])
        session.flush()
        read_headers = key_for(session, reader, scopes=("read",))
        write_headers = key_for(session, writer, scopes=("studies:write",))
        own = Study(
            sid="ASSIGNED",
            name="Assigned",
            creator_id=writer.id,
            access="private",
            licence="closed",
        )
        hidden = Study(
            sid="HIDDEN",
            name="Hidden",
            creator_id=writer.id,
            access="private",
            licence="closed",
        )
        session.add_all([own, hidden])
        session.flush()
        session.add(StudyGrant(study_id=own.id, user_id=reader.id, role="curator"))
    data = client.get("/api/v2/curation-context", headers=read_headers).json()
    assert data["username"] == "context-reader"
    assert not data["can_upload"]
    assert data["studies"] == [{"sid": "ASSIGNED", "name": "Assigned"}]
    assert (
        client.get("/api/v2/curation-context", headers=write_headers).status_code == 403
    )
