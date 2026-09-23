"""Network boundaries, local validation, and reproducible uploads."""

import json

import httpx2
import pytest

from pkdb import Client, Vocabulary, prepare
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.errors import CompatibilityError, SourceChangedError
from pkdb.schemas.validation import StudyValidationError


def capabilities(prepared):
    return {
        "schema_version": 1,
        "server_version": "0.10.2",
        "processing_version": PROCESSING_VERSION,
        "vocabulary_version": prepared.prepared.vocabulary_version,
        "vocabulary_hash": prepared.vocabulary_hash,
        "upload_limits": {
            "max_rows": 1_000_000,
            "max_files": 256,
            "max_upload_bytes": 100_000_000,
            "max_attachment_bytes": 100_000_000,
        },
    }


def test_upload_checks_compatibility_and_sends_original_files(study_folder, vocabulary):
    prepared = prepare(study_folder, vocabulary=vocabulary)
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "GET":
            assert request.url.path == "/api/v2/capabilities"
            return httpx2.Response(200, json=capabilities(prepared))
        assert request.method == "PUT"
        assert request.url.path == "/api/v2/studies/TEST1"
        assert request.headers["authorization"] == "Token secret"
        assert request.headers["X-PKDB-Vocabulary-Hash"] == prepared.vocabulary_hash
        assert request.headers["X-PKDB-Processing-Version"] == PROCESSING_VERSION
        body = request.read()
        assert b'name="study"' in body and b'name="reference"' in body
        for path in study_folder.iterdir():
            if path.suffix in {".xlsx", ".tsv"}:
                assert path.read_bytes() in body
        return httpx2.Response(
            201,
            json={"sid": "TEST1", "created": True, "digest": "digest", "counts": {}},
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            assert client.upload(prepared).sid == "TEST1"
    assert [r.method for r in calls] == ["GET", "PUT"]


def test_mismatched_vocabulary_prevents_write(study_folder, vocabulary):
    prepared = prepare(study_folder, vocabulary=vocabulary)
    calls = []

    def handler(request):
        calls.append(request.method)
        payload = capabilities(prepared)
        payload["vocabulary_hash"] = "0" * 64
        return httpx2.Response(200, json=payload)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            with pytest.raises(CompatibilityError):
                client.upload(prepared)
    assert calls == ["GET"]


def test_vocabulary_changed_during_upload_has_actionable_error(
    study_folder, vocabulary
):
    prepared = prepare(study_folder, vocabulary=vocabulary)

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(200, json=capabilities(prepared))
        return httpx2.Response(409, json={"detail": "vocabulary_mismatch"})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            with pytest.raises(CompatibilityError, match="synchronize vocabulary"):
                client.upload(prepared)


@pytest.mark.parametrize("change", ["edit", "add", "remove"])
def test_source_mutation_prevents_network(study_folder, vocabulary, change):
    prepared = prepare(study_folder, vocabulary=vocabulary)
    if change == "edit":
        path = study_folder / "study.json"
        path.write_text(path.read_text() + "\n")
    elif change == "add":
        (study_folder / "attachment.txt").write_text("new attachment")
    else:
        (study_folder / "reference.json").unlink()

    def handler(request):
        pytest.fail("Changed source must not reach the network")

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            with pytest.raises(SourceChangedError):
                client.upload(prepared)


def test_invalid_folder_never_reaches_network(study_folder):
    path = study_folder / "study.json"
    value = json.loads(path.read_text())
    value["unexpected"] = True
    path.write_text(json.dumps(value))

    def handler(request):
        pytest.fail("Invalid local study must not reach the network")

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            with pytest.raises(StudyValidationError):
                client.upload(study_folder)


def test_snapshot_roundtrip_and_tamper_detection(tmp_path, vocabulary):
    path = tmp_path / "vocabulary.lock.json"
    vocabulary.save(path)
    assert Vocabulary.load(path) == vocabulary
    envelope = json.loads(path.read_text())
    envelope["vocabulary"]["version"] = "tampered"
    path.write_text(json.dumps(envelope))
    with pytest.raises(ValueError):
        Vocabulary.load(path)


def test_typed_get_and_query_filter_serialization(study_folder, vocabulary):
    prepared = prepare(study_folder, vocabulary=vocabulary)

    def handler(request):
        assert "authorization" not in request.headers
        if request.url.path == "/api/v2/studies/TEST1":
            return httpx2.Response(200, json=prepared.study.model_dump(mode="json"))
        assert request.url.path == "/api/v1/studies/"
        assert dict(request.url.params) == {
            "substance": "a,b",
            "concise": "true",
            "page": "2",
        }
        return httpx2.Response(
            200,
            json={"data": {"data": [], "count": 0}, "current_page": 2, "last_page": 2},
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="", transport=transport
        ) as client:
            assert client.studies.get("TEST1") == prepared.study
            page = client.studies.list(
                substance=["a", "b"], concise=True, page=2, ignored=None
            )
            assert page.items == []
            assert page.page == 2


@pytest.mark.parametrize("failure", ["redirect", "html", "timeout", "wrong_sid"])
def test_ambiguous_upload_is_never_retried(study_folder, vocabulary, failure):
    from pkdb.errors import ClientError

    prepared = prepare(study_folder, vocabulary=vocabulary)
    writes = []

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(200, json=capabilities(prepared))
        writes.append(request)
        if failure == "redirect":
            return httpx2.Response(307, headers={"location": "https://other.test"})
        if failure == "html":
            return httpx2.Response(502, text="secret debugging data")
        if failure == "timeout":
            raise httpx2.ReadTimeout("secret timeout", request=request)
        return httpx2.Response(
            201,
            json={"sid": "OTHER", "created": True, "digest": "digest", "counts": {}},
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            with pytest.raises(ClientError) as error:
                client.upload(prepared)
    assert "secret" not in str(error.value)
    assert len(writes) == 1


@pytest.mark.parametrize("success", [True, False])
def test_download_authentication_and_atomic_destination(tmp_path, success):
    from pkdb.errors import ClientError

    destination = tmp_path / "dataset.zip"
    destination.write_bytes(b"previous")

    def handler(request):
        assert request.headers["authorization"] == "Bearer pkdb_live_secret"
        assert request.url.path == "/api/v1/filter/"
        assert request.url.params["download"] == "true"
        if success:
            return httpx2.Response(
                200,
                content=b"PK\x03\x04test",
                headers={"content-type": "application/zip"},
            )
        return httpx2.Response(307, headers={"location": "https://other.test"})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test",
            api_key="pkdb_live_secret",
            transport=transport,
        ) as client:
            if success:
                assert client.download(destination) == destination
            else:
                with pytest.raises(ClientError):
                    client.download(destination)
    assert destination.read_bytes() == (b"PK\x03\x04test" if success else b"previous")
    assert list(tmp_path.iterdir()) == [destination]


def test_download_uses_same_filter_serialization_as_queries(tmp_path):
    def handler(request):
        assert dict(request.url.params) == {
            "studies__sid": "PK1,PK2",
            "download": "true",
            "concise": "true",
        }
        return httpx2.Response(
            200, content=b"PKtest", headers={"content-type": "application/zip"}
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            client.download(
                tmp_path / "data.zip",
                studies__sid=["PK1", "PK2"],
                concise=True,
                ignored=None,
            )


def test_caller_owns_supplied_http_client():
    transport = httpx2.Client(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(200))
    )
    with Client(endpoint="https://example.test", transport=transport):
        pass
    try:
        assert not transport.is_closed
    finally:
        transport.close()


def test_interrupted_download_preserves_existing_file(tmp_path):
    from pkdb.errors import ClientError

    class BrokenStream(httpx2.SyncByteStream):
        def __iter__(self):
            yield b"partial zip"
            raise httpx2.ReadError("connection interrupted")

    destination = tmp_path / "data.zip"
    destination.write_bytes(b"original")

    def handler(request):
        return httpx2.Response(
            200, stream=BrokenStream(), headers={"content-type": "application/zip"}
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            endpoint="https://example.test", api_key="secret", transport=transport
        ) as client:
            with pytest.raises(ClientError, match="destination was not replaced"):
                client.download(destination)
    assert destination.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [destination]
