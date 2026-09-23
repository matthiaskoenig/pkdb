"""Exercise the installed public API and CLI against real FastAPI routes."""

import json
import zipfile

import pytest
from sqlalchemy import select

from pkdb import Client, prepare
from pkdb.cache import VocabularyCache
from pkdb.cli import main
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.db.models.studies import Study


@pytest.fixture
def study_folder(tmp_path, valid_bundle):
    folder = tmp_path / valid_bundle.study["name"]
    folder.mkdir()
    (folder / "study.json").write_text(json.dumps(valid_bundle.study))
    (folder / "reference.json").write_text(json.dumps(valid_bundle.reference))
    (folder / "notes.txt").write_text("Original attachment")
    return folder


def test_public_client_prepare_upload_query_download(
    client,
    creator_headers,
    study_folder,
    tmp_path,
    session_factory,
):
    api = Client(
        endpoint="http://testserver",
        api_key=creator_headers["Authorization"].split(" ", 1)[1],
        transport=client,
        cache=VocabularyCache(tmp_path / "cache"),
    )
    vocabulary = api.vocabulary()
    assert api.vocabulary(refresh=False) == vocabulary
    prepared = prepare(study_folder, vocabulary=vocabulary)
    result = api.upload(prepared)
    assert result.created
    stored = api.studies.get(prepared.study.sid)
    assert [item.statistics for item in stored.measurements] == [
        item.statistics for item in prepared.study.measurements
    ]
    assert stored.source_digest == prepared.study.source_digest
    page = api.studies.list(sid=stored.sid)
    assert page.count == 1
    assert page.items[0].sid == stored.sid
    for entity in ("outputs", "groups", "interventions", "references"):
        assert api.query(entity).count > 0
    destination = api.download(tmp_path / "dataset.zip", studies__sid=stored.sid)
    with zipfile.ZipFile(destination) as archive:
        assert "studies.csv" in archive.namelist()
        assert stored.sid in archive.read("studies.csv").decode()
    anonymous = Client(endpoint="http://testserver", api_key="", transport=client)
    assert anonymous.studies.list(sid=stored.sid).count == 0
    with session_factory.begin() as session:
        study = session.scalar(select(Study).where(Study.sid == stored.sid))
        study.access = "public"
    assert anonymous.studies.list(sid=stored.sid).count == 1
    assert anonymous.studies.get(stored.sid).sid == stored.sid


def test_public_client_rejects_modified_source_before_request(
    client,
    creator_headers,
    study_folder,
    tmp_path,
    monkeypatch,
):
    api = Client(
        endpoint="http://testserver",
        api_key=creator_headers["Authorization"].split(" ", 1)[1],
        transport=client,
        cache=VocabularyCache(tmp_path / "cache"),
    )
    prepared = prepare(study_folder, vocabulary=api.vocabulary())
    (study_folder / "notes.txt").write_text("Modified after preparation")

    def unexpected_request(*args, **kwargs):
        pytest.fail("Changed source must fail locally before any request")

    monkeypatch.setattr(client, "request", unexpected_request)
    with pytest.raises((StudyValidationError, ValueError)):
        api.upload(prepared)


def test_public_cli_upload_with_environment_and_pinned_vocabulary(
    client,
    creator_headers,
    study_folder,
    tmp_path,
    monkeypatch,
    capsys,
):
    token = creator_headers["Authorization"].split(" ", 1)[1]
    api = Client(
        endpoint="http://testserver",
        api_key=token,
        transport=client,
        cache=VocabularyCache(tmp_path / "cache"),
    )
    snapshot = tmp_path / "vocabulary.lock.json"
    api.vocabulary().save(snapshot)
    monkeypatch.setenv("PKDB_ENDPOINT", "http://testserver")
    monkeypatch.setenv("PKDB_API_KEY", token)
    assert (
        main(
            [
                "upload",
                str(study_folder),
                "--vocabulary",
                str(snapshot),
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
            client=client,
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["created"]
    assert api.studies.get(report["sid"]).sid == report["sid"]


def test_public_cli_preserves_rejected_upload_report(
    client, creator_headers, study_folder, tmp_path, monkeypatch, capsys
):
    path = study_folder / "study.json"
    data = json.loads(path.read_text())
    data["curators"].append({"user": "missing-attribution-user"})
    path.write_text(json.dumps(data))
    token = creator_headers["Authorization"].split(" ", 1)[1]
    api = Client(endpoint="http://testserver", api_key=token, transport=client)
    snapshot = tmp_path / "vocabulary.lock.json"
    api.vocabulary().save(snapshot)
    monkeypatch.setenv("PKDB_ENDPOINT", "http://testserver")
    monkeypatch.setenv("PKDB_API_KEY", token)

    assert (
        main(
            ["upload", str(study_folder), "--vocabulary", str(snapshot)], client=client
        )
        == 1
    )
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status_code"] == 422
    assert "unknown_user" in result["error"]
    assert result["report"]["issues"][0]["code"] == "unknown_user"
    assert result["report"]["error_count"] == 1
    assert token not in output
