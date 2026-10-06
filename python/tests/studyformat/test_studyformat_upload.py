"""Uploads of study format 2 folders: exact files, the study route and batch identity."""

import json
import re
import shutil

import httpx2
import pytest

from pkdb.batch import BatchOptions, upload_many
from pkdb.cache import VocabularyCache
from pkdb.client import Client
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.errors import ClientError, SourceChangedError
from pkdb.preparation import prepare
from pkdb.schemas.validation import StudyValidationError
from pkdb.studyformat.jsonio import dump_json

ENDPOINT = "https://example.test"
JSON_FILES = {"study.json", "reference.json"}


def capabilities(vocabulary, *, max_rows=1_000_000):
    return {
        "schema_version": 1,
        "server_version": "0.10.2",
        "processing_version": PROCESSING_VERSION,
        "vocabulary_version": vocabulary.version,
        "vocabulary_hash": vocabulary_hash(vocabulary),
        "upload_report_versions": [1, 2],
        "upload_limits": {
            "max_rows": max_rows,
            "max_files": 256,
            "max_upload_bytes": 100_000_000,
            "max_attachment_bytes": 100_000_000,
        },
    }


def form_parts(request) -> list[tuple[str, str | None, bytes]]:
    """Name, file name and exact content of each part of a multipart request."""
    boundary = request.headers["content-type"].split("boundary=", 1)[1].encode()
    parts = []
    for chunk in request.read().split(b"--" + boundary)[1:-1]:
        head, _, content = chunk.removeprefix(b"\r\n").partition(b"\r\n\r\n")
        disposition = head.decode()
        name = re.search(r'name="([^"]*)"', disposition)
        filename = re.search(r'filename="([^"]*)"', disposition)
        assert name is not None
        parts.append(
            (
                name.group(1),
                filename.group(1) if filename else None,
                content.removesuffix(b"\r\n"),
            )
        )
    return parts


def confirmation(sid="caffeine/Example", created=True):
    return {"sid": sid, "created": created, "digest": "digest", "counts": {}}


def client_for(handler, **kwargs) -> Client:
    transport = httpx2.Client(transport=httpx2.MockTransport(handler))
    return Client(endpoint=ENDPOINT, api_key="secret", transport=transport, **kwargs)


def copy_study(study, root, name="Example", *, pmid="123"):
    """A copy of the study at <root>/caffeine/<name> that names PubMed ID `pmid`."""
    target = root / "caffeine" / name
    shutil.copytree(study, target)
    for file, key in (("study.json", "reference"), ("reference.json", None)):
        path = target / file
        data = json.loads(path.read_text(encoding="utf-8"))
        if key:
            data[key] = {"pmid": pmid}
        else:
            data.update(sid=pmid, pmid=pmid)
        path.write_text(dump_json(data), encoding="utf-8", newline="")
    return target


@pytest.fixture
def study(valid_study):
    """The valid study with text that JSON serializers would write differently."""
    path = valid_study / "study.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["descriptions"] = ["Plasma levels in µg/l after 100 mg; see “Table 2”."]
    path.write_text(dump_json(data), encoding="utf-8", newline="")
    return valid_study


def test_upload_sends_the_exact_files_to_the_study_route(study, sf_vocabulary):
    # Neither the generated workbook nor editor files belong to the study.
    (study / "Example.xlsx").write_bytes(b"generated workbook")
    (study / ".DS_Store").write_bytes(b"finder")
    prepared = prepare(study, vocabulary=sf_vocabulary)
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            assert request.url.path == "/api/v2/capabilities"
            return httpx2.Response(200, json=capabilities(sf_vocabulary))
        return httpx2.Response(201, json=confirmation())

    with client_for(handler) as client:
        result = client.upload(prepared)
    assert result.sid == "caffeine/Example"
    get, put = requests
    assert put.method == "PUT"
    assert put.url.raw_path == b"/api/v2/studies/caffeine/Example"
    assert put.headers["authorization"] == "Token secret"
    assert put.headers["X-PKDB-Vocabulary-Hash"] == vocabulary_hash(sf_vocabulary)
    assert put.headers["X-PKDB-Processing-Version"] == PROCESSING_VERSION
    assert put.headers["X-PKDB-Report-Version"] == "2"
    parts = form_parts(put)
    # Files, not text fields: the server checks the exact bytes.
    assert parts[:2] == [
        ("study", "study.json", (study / "study.json").read_bytes()),
        ("reference", "reference.json", (study / "reference.json").read_bytes()),
    ]
    files = {filename: content for name, filename, content in parts[2:]}
    assert {name for name, _, _ in parts[2:]} == {"files"}
    assert files == {
        path.name: path.read_bytes()
        for path in study.iterdir()
        if path.name not in JSON_FILES | {"Example.xlsx", ".DS_Store"}
    }
    assert set(files) == {item.name for item in prepared.study.attachments}


def test_upload_of_a_folder_path(study, sf_vocabulary, tmp_path):
    cache = VocabularyCache(tmp_path / "cache")
    cache.store(ENDPOINT, sf_vocabulary)
    paths = []

    def handler(request):
        paths.append(request.url.raw_path)
        if request.method == "GET":
            return httpx2.Response(200, json=capabilities(sf_vocabulary))
        return httpx2.Response(201, json=confirmation())

    with client_for(handler, cache=cache) as client:
        assert client.upload(study).sid == "caffeine/Example"
    assert paths == [b"/api/v2/capabilities", b"/api/v2/studies/caffeine/Example"]


def test_upload_requires_the_server_to_confirm_the_study(study, sf_vocabulary):
    prepared = prepare(study, vocabulary=sf_vocabulary)

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(200, json=capabilities(sf_vocabulary))
        return httpx2.Response(201, json=confirmation(sid="Example"))

    with client_for(handler) as client:
        with pytest.raises(ClientError, match="did not confirm") as error:
            client.upload(prepared)
    assert error.value.persistence == "unknown"


@pytest.mark.parametrize("change", ["edit", "add", "remove"])
def test_changed_folder_never_reaches_the_network(study, sf_vocabulary, change):
    prepared = prepare(study, vocabulary=sf_vocabulary)
    if change == "edit":
        path = study / "Example.pdf"
        path.write_bytes(path.read_bytes() + b"changed")
    elif change == "add":
        (study / "notes.txt").write_text("new attachment")
    else:
        (study / "Example_Tab1.png").unlink()

    def handler(request):
        pytest.fail("A changed source must not reach the network")

    with client_for(handler) as client:
        with pytest.raises(SourceChangedError):
            client.upload(prepared)


def test_server_row_limit_applies_before_the_upload(study, sf_vocabulary):
    prepared = prepare(study, vocabulary=sf_vocabulary)
    methods = []

    def handler(request):
        methods.append(request.method)
        return httpx2.Response(200, json=capabilities(sf_vocabulary, max_rows=3))

    with client_for(handler) as client:
        with pytest.raises(StudyValidationError) as error:
            client.upload(prepared)
    assert error.value.report.issues[0].code == "row_limit"
    assert methods == ["GET"]


def test_curation_app_validates_on_the_study_route(study, sf_vocabulary, tmp_path):
    from pkdb.curation.engine import CurationEngine

    study = copy_study(study, tmp_path / "sources")
    prepared = prepare(study, vocabulary=sf_vocabulary)
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, json={"report_version": 2, "valid": True})

    engine = CurationEngine(
        tmp_path / "sources", state_dir=tmp_path / "state", offline=True, start=False
    )
    try:
        with client_for(handler) as client:
            assert engine._server_validate(client, prepared)["valid"]
    finally:
        engine.close()
    [request] = requests
    assert request.method == "POST"
    assert request.url.raw_path == b"/api/v2/studies/caffeine/Example/validate"
    parts = form_parts(request)
    assert parts[0] == ("study", "study.json", (study / "study.json").read_bytes())
    assert {filename for _, filename, _ in parts[2:]} == {
        item.name for item in prepared.study.attachments
    }


def no_network(request):
    pytest.fail(f"Unexpected request: {request.url}")


@pytest.mark.parametrize(
    ("copies", "message"),
    [
        (
            [("a", "Example", "123"), ("b", "Example", "456")],
            "Duplicate study SID: caffeine/Example",
        ),
        (
            [("a", "Example", "123"), ("a", "Other", "123")],
            "Multiple studies claim reference 123",
        ),
    ],
)
def test_batch_checks_identities_before_uploading(
    study, sf_vocabulary, tmp_path, copies, message
):
    folders = [
        copy_study(study, tmp_path / root, name, pmid=pmid)
        for root, name, pmid in copies
    ]
    with httpx2.Client(transport=httpx2.MockTransport(no_network)) as transport:
        with pytest.raises(ValueError, match=message):
            upload_many(
                folders,
                endpoint=ENDPOINT,
                api_key="secret",
                vocabulary=sf_vocabulary,
                transport=transport,
            )


def test_batch_reference_keys_compare_normalized_dois(study, sf_vocabulary, tmp_path):
    folders = []
    for name, doi in (("Example", "10.1234/ABC"), ("Other", "10.1234/abc")):
        target = copy_study(study, tmp_path / "copies", name)
        path = target / "study.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["reference"] = {"doi": doi}
        path.write_text(dump_json(data), encoding="utf-8", newline="")
        folders.append(target)
    with httpx2.Client(transport=httpx2.MockTransport(no_network)) as transport:
        with pytest.raises(ValueError, match="Multiple studies claim reference"):
            upload_many(
                folders,
                endpoint=ENDPOINT,
                api_key="secret",
                vocabulary=sf_vocabulary,
                transport=transport,
            )


def test_batch_uploads_and_resumes_by_substance_and_name(
    study, sf_vocabulary, tmp_path
):
    # A workbook of study format 1 must not be exported into hidden tables.
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Tab2"
    sheet.append(["description"])
    sheet.append(["measurement_type", "mean"])
    sheet.append(["cmax", 2.5])
    workbook.save(study / "Example.xlsx")
    before = sorted(path.name for path in study.iterdir())
    report = tmp_path / "report.json"
    requests = []
    digest = {}

    def handler(request):
        requests.append((request.method, request.url.raw_path))
        if request.url.path == "/api/v2/capabilities":
            return httpx2.Response(200, json=capabilities(sf_vocabulary))
        if request.method == "PUT":
            return httpx2.Response(201, json=confirmation())
        return httpx2.Response(
            200,
            json={
                "sid": "caffeine/Example",
                "digest": digest["value"],
                "processing_version": PROCESSING_VERSION,
                "vocabulary_version": sf_vocabulary.version,
                "current_processing_version": PROCESSING_VERSION,
                "current_vocabulary_version": sf_vocabulary.version,
            },
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        result = upload_many(
            [study],
            endpoint=ENDPOINT,
            api_key="secret",
            vocabulary=sf_vocabulary,
            options=BatchOptions(report=report, reference_cache=tmp_path / "refs"),
            transport=transport,
        )
        [row] = result["results"]
        assert row["ok"] and row["sid"] == "caffeine/Example", row
        assert ("PUT", b"/api/v2/studies/caffeine/Example") in requests
        assert row["url"] == f"{ENDPOINT}/api/v1/studies/caffeine/Example/"
        assert sorted(path.name for path in study.iterdir()) == before
        digest["value"] = json.loads(report.read_text())["results"][0]["source_digest"]
        requests.clear()
        resumed = upload_many(
            [study],
            endpoint=ENDPOINT,
            api_key="secret",
            vocabulary=sf_vocabulary,
            options=BatchOptions(
                resume=report,
                report=tmp_path / "resumed.json",
                reference_cache=tmp_path / "refs",
            ),
            transport=transport,
        )
    [row] = resumed["results"]
    assert row["skipped"] and row["ok"]
    assert ("GET", b"/api/v2/studies/caffeine/Example/publication") in requests
    assert not any(method == "PUT" for method, _ in requests)
