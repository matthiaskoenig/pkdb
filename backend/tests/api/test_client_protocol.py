import json
from pathlib import Path

import pytest
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import Vocabulary, vocabulary_hash

from pkdb_server.db.bootstrap import (
    Snapshot,
    bootstrap,
    load_vocabulary,
    vocabulary_from_snapshot,
)
from pkdb_server.db.models.vocabulary import VocabularyNode


def test_snapshot_and_capabilities_are_public_and_consistent(client):
    response = client.get("/api/v2/vocabulary")
    assert response.status_code == 200
    envelope = response.json()
    vocabulary = Vocabulary.model_validate(envelope["vocabulary"])
    assert envelope["schema_version"] == 1
    assert envelope["vocabulary_hash"] == vocabulary_hash(vocabulary)
    assert response.headers["etag"] == f'"{vocabulary_hash(vocabulary)}"'
    capabilities = client.get("/api/v2/capabilities").json()
    assert capabilities["vocabulary_hash"] == envelope["vocabulary_hash"]
    assert capabilities["vocabulary_version"] == vocabulary.version
    assert capabilities["processing_version"] == PROCESSING_VERSION
    assert capabilities["upload_limits"]["max_files"] > 0
    assert client.get("/api/v2/vocabulary").json() == envelope


@pytest.mark.parametrize(
    "header,code",
    [
        ("X-PKDB-Vocabulary-Hash", "vocabulary_mismatch"),
        ("X-PKDB-Processing-Version", "processing_version_mismatch"),
    ],
)
def test_stale_client_rejected_before_multipart_parse(
    client, creator_headers, header, code, monkeypatch
):
    from starlette.requests import Request

    def unexpected_parse(*args, **kwargs):
        pytest.fail("Stale upload must not parse multipart")

    monkeypatch.setattr(Request, "form", unexpected_parse)
    response = client.put(
        "/api/v2/studies/TEST1",
        headers={**creator_headers, header: "stale"},
        content=b"malformed",
    )
    assert response.status_code == 409
    assert response.json()["detail"] == code


def test_matching_client_uploads_and_publication_rechecks_hash(
    client, creator_headers, valid_bundle, monkeypatch, session_factory
):
    capabilities = client.get("/api/v2/capabilities").json()
    headers = {
        **creator_headers,
        "X-PKDB-Vocabulary-Hash": capabilities["vocabulary_hash"],
        "X-PKDB-Processing-Version": capabilities["processing_version"],
    }
    files = {
        "study": (None, json.dumps(valid_bundle.study), "application/json"),
        "reference": (None, json.dumps(valid_bundle.reference), "application/json"),
    }
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    response = client.put(url, headers=headers, files=files)
    assert response.status_code == 201, response.text
    ingestion = client.app.state.ingestion
    original = ingestion._publish

    def changed_vocabulary(*args, **kwargs):
        # Deliberately keep the authored version unchanged: publication must
        # compare full content, not just the version label.
        with session_factory.begin() as session:
            session.add(
                VocabularyNode(sid="new-tissue", name="new tissue", kind="tissue")
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(ingestion, "_publish", changed_vocabulary)
    response = client.put(url, headers=headers, files=files)
    assert response.status_code == 409
    assert response.json()["detail"] == "vocabulary_mismatch"


def test_offline_snapshot_projection_matches_database(session_factory, tmp_path):
    snapshot = Snapshot.model_validate(
        {
            "version": "authored-label",
            "nodes": [
                {"sid": "root", "name": "Root", "kind": "info_node"},
                {
                    "sid": "drug",
                    "name": "Drug",
                    "kind": "substance",
                    "definition": {"mass": 100},
                    "parents": ["root"],
                    "terms": {"synonyms": ["a", "a", "b"]},
                },
                {
                    "sid": "weight",
                    "name": "weight",
                    "kind": "measurement",
                    "definition": {"units": ["kg"]},
                },
            ],
        }
    )
    (tmp_path / "users.json").write_text("[]")
    (tmp_path / "vocabulary.json").write_text(snapshot.model_dump_json())
    with session_factory.begin() as session:
        assert not bootstrap(tmp_path, session).errors
        actual = load_vocabulary(session)
    expected = vocabulary_from_snapshot(snapshot)
    assert actual == expected
    assert vocabulary_hash(actual) == vocabulary_hash(expected)


def test_bundled_snapshot_matches_authored_source():
    root = Path(__file__).resolve().parents[3]
    source = Snapshot.model_validate_json(
        (root / "backend/bootstrap/vocabulary.json").read_text()
    )
    envelope = json.loads((root / "python/src/pkdb/data/vocabulary.json").read_text())
    vocabulary = vocabulary_from_snapshot(source)
    assert envelope["vocabulary"] == vocabulary.model_dump(mode="json")
    assert envelope["vocabulary_hash"] == vocabulary_hash(vocabulary)
