from pkdb import Client
from pkdb.curation.engine import CurationEngine
from tests.fixtures.study_folders import write_study


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
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    folder = write_study(workspace)
    (folder / "notes.txt").write_text("Original attachment")
    identity = "caffeine/Example"
    url = f"/api/v2/studies/{identity}"

    def bound(*args, **kwargs):
        return Client(*args, transport=client, **kwargs)

    # Jobs and the connection check each open their own client.
    monkeypatch.setattr("pkdb.curation.jobs.Client", bound)
    monkeypatch.setattr("pkdb.curation.connection.Client", bound)
    engine = CurationEngine(
        workspace,
        endpoint="http://testserver",
        api_key=creator_headers["Authorization"].split()[1],
        state_dir=tmp_path / "app-state",
        start=False,
    )
    try:
        engine.connect()
        assert engine.account
        assert [row["id"] for row in engine.studies.values()] == [identity]
        validation = engine.enqueue([identity], "validate_remote")[0]
        engine.queue.clear()
        engine.run_job(validation)
        assert validation["status"] == "succeeded", engine.report(
            validation["report_id"]
        )
        assert validation["persistence"] == "not_attempted"
        # The server validated the folder under its identity and stored nothing.
        server = engine.report(validation["report_id"])["server_report"]
        assert (server["operation"], server["status"], server["study"]["sid"]) == (
            "validate",
            "succeeded",
            identity,
        )
        assert client.get(url, headers=creator_headers).status_code == 404
        engine.set_mode([identity], "upload")
        job = engine.enqueue([identity], "upload")[0]
        engine.queue.clear()
        engine.run_job(job)
        assert job["status"] == "succeeded", engine.report(job["report_id"])
        assert job["persistence"] == "created"
        assert client.get(url, headers=creator_headers).status_code == 200
        # A real external edit becomes one pending upload of the newest snapshot.
        (folder / "notes.txt").write_text("Saved externally")
        engine.scan()
        engine._row_of(identity)["_changed_at"] -= 2
        engine.schedule_changes()
        job = engine.queue.pop(identity)
        assert job["automatic"] and job["action"] == "upload"
        engine.run_job(job)
        assert job["persistence"] == "replaced", engine.report(job["report_id"])
        # Invalid saved JSON is diagnosed and cannot replace the uploaded study.
        (folder / "study.json").write_text("{")
        engine.scan()
        engine._row_of(identity)["_changed_at"] -= 2
        engine.schedule_changes()
        job = engine.queue.pop(identity)
        engine.run_job(job)
        # A check that ran and found problems, not a failure of the job.
        assert (job["status"], job["message"]) == (
            "invalid",
            "Validation found problems",
        )
        assert job["persistence"] == "not_attempted"
        problems = engine._row_of(identity)["problems"]
        assert [(issue["code"], issue["source"]["file"]) for issue in problems] == [
            ("invalid_json", "study.json")
        ]
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
