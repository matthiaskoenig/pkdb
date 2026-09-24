"""Opt-in local curation uploads against an isolated schema; sources stay unchanged."""

import os
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pkdb import Client
from pkdb.curation.engine import CurationEngine
from pkdb.preparation import source_hashes, study_folders
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.app import create_app
from pkdb_server.commands.admin import create_admin
from pkdb_server.commands.bootstrap import bootstrap, bootstrap_study
from pkdb_server.commands.user_import import import_roster
from pkdb_server.config import Settings


def test_curation_apixaban_roundtrip(session_factory, tmp_path, monkeypatch):
    value = os.environ.get("PKDB_CURATION_CORPUS")
    if not value:
        pytest.skip("Set PKDB_CURATION_CORPUS to the read-only apixaban directory")
    corpus = Path(value).resolve()
    root = Path(__file__).resolve().parents[1]
    before = source_hashes(corpus)
    assert not bootstrap(root / "bootstrap", session_factory).errors
    create_admin(
        session_factory,
        "mkoenig",
        "curation-test@example.org",
        "Isolated-test-password-42!",
    )
    report = import_roster(
        root / "bootstrap/curator-roster.json",
        session_factory,
        apply=True,
        file_root=tmp_path / "files",
        avatar_root=root.parent / "frontend/public",
    )
    assert report["ok"], report
    for folder in study_folders(corpus):
        try:
            bootstrap_study(folder, session_factory)
        except StudyValidationError:
            pass
    app = create_app(
        Settings(
            database_url=session_factory.kw["bind"].url.render_as_string(
                hide_password=False
            ),
            file_root=tmp_path / "files",
            rate_limits_enabled=False,
        )
    )
    _, actor = app.state.credentials.login("mkoenig", "Isolated-test-password-42!")
    secret = app.state.credentials.create_key(
        actor, "Isolated curation", scopes=("read", "studies:write"), lifetime_days=1
    )["secret"]
    with TestClient(app) as transport:
        monkeypatch.setattr(
            "pkdb.curation.engine.Client",
            lambda *args, **kwargs: Client(*args, transport=transport, **kwargs),
        )
        engine = CurationEngine(
            corpus,
            endpoint="http://testserver",
            api_key=secret,
            state_dir=tmp_path / "state",
            start=False,
        )
        try:
            engine.connect()
            assert engine.account == "mkoenig" and engine.can_upload
            summaries = []
            for _ in range(2):
                counts = Counter()
                for identifier in engine.studies:
                    job = engine.enqueue([identifier], "upload")[0]
                    engine.queue.pop(identifier)
                    engine.run_job(job)
                    assert job["status"] != "unknown", engine.report(job["report_id"])
                    counts[
                        job["persistence"]
                        if job["status"] == "succeeded"
                        else "rejected"
                    ] += 1
                summaries.append(dict(counts))
            assert summaries[0].get("created", 0) > 0
            assert summaries[1].get("replaced", 0) == summaries[0]["created"]
            assert not summaries[1].get("created")
            print(f"Curation corpus outcomes: {summaries}")
        finally:
            engine.close()
    assert source_hashes(corpus) == before
