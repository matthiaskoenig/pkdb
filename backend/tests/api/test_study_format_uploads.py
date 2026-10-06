"""Uploads of study format 2 folders: routes, identity, release and rename on re-upload."""

import json
from datetime import date

import pytest
from sqlalchemy import func, select

from pkdb import Client, prepare
from pkdb.cache import VocabularyCache
from pkdb.cli import main
from pkdb.studyformat.jsonio import dump_json
from pkdb_server.db.models.studies import Study
from tests.fixtures.study_folders import JSON_FILES, multipart, write_study

URL = "/api/v2/studies/caffeine/Example"


def format_1(bundle):
    return {
        "files": {
            "study": (None, json.dumps(bundle.study), "application/json"),
            "reference": (None, json.dumps(bundle.reference), "application/json"),
        }
    }


@pytest.fixture
def folder(tmp_path):
    return write_study(tmp_path / "sources")


def stored(session_factory, **filters):
    with session_factory() as session:
        return session.scalars(select(Study).filter_by(**filters)).all()


def count(session_factory):
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(Study))


def test_upload_reads_back_with_identity_release_issue_and_review(
    client, creator_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources", release="PKDB00198")
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["sid"], body["created"]) == ("caffeine/Example", True)
    assert body["url"] == f"{client.app.state.browser_origin}/data/caffeine/Example"
    study = client.get(URL, headers=creator_headers).json()
    assert study["sid"] == "caffeine/Example"
    metadata = study["metadata"]
    assert (metadata["name"], metadata["date"], metadata["issue"]) == (
        "Example",
        "2026-09-28",
        2158,
    )
    assert metadata["release"] == {"pkdb_id": "PKDB00198", "date": "2026-09-28"}
    assert metadata["review"]["status"] == "in_review"
    assert metadata["review"]["reviewers"] == ["curator"]
    assert [item["text"] for item in metadata["review"]["items"]] == [
        "Is the mean read from the table?"
    ]
    assert metadata["descriptions"] == [{"text": "Plasma levels in µg/l."}]
    assert sorted(item["name"] for item in study["attachments"]) == sorted(
        path.name for path in folder.iterdir() if path.name not in JSON_FILES
    )
    [row] = stored(session_factory)
    assert (row.sid, row.name, row.pkdb_id, row.issue, row.review_status) == (
        "caffeine/Example",
        "Example",
        "PKDB00198",
        2158,
        "in_review",
    )
    assert str(row.date) == str(row.release_date) == "2026-09-28"
    publication = client.get(URL + "/publication", headers=creator_headers)
    assert publication.status_code == 200
    assert publication.json()["sid"] == "caffeine/Example"


def test_identical_upload_is_a_replacement(
    client, creator_headers, folder, session_factory
):
    first = client.put(URL, headers=creator_headers, **multipart(folder))
    second = client.put(URL, headers=creator_headers, **multipart(folder))
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["created"] is False
    assert second.json()["digest"] == first.json()["digest"]
    assert count(session_factory) == 1


def test_validation_route_does_not_publish(
    client, creator_headers, folder, session_factory
):
    response = client.post(
        URL + "/validate", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 200, response.text
    assert response.json()["valid"] is True
    assert count(session_factory) == 0


def test_negotiated_reports_name_the_study(client, creator_headers, folder):
    headers = {**creator_headers, "X-PKDB-Report-Version": "2"}
    for method, url, operation, persistence in (
        ("post", URL + "/validate", "validate", "not_attempted"),
        ("put", URL, "upload", "created"),
    ):
        response = getattr(client, method)(url, headers=headers, **multipart(folder))
        body = response.json()
        assert (body["operation"], body["persistence"]) == (operation, persistence)
        assert body["study"] == {"sid": "caffeine/Example", "name": "Example"}


def test_non_canonical_file_is_rejected(client, creator_headers, folder):
    table = (folder / "outputs_Tab2.tsv").read_bytes().replace(b"\n", b"\r\n")
    response = client.put(
        URL,
        headers=creator_headers,
        **multipart(folder, {"outputs_Tab2.tsv": table}),
    )
    assert response.status_code == 422
    [issue] = response.json()["issues"]
    assert (issue["code"], issue["source"]["file"]) == (
        "not_formatted",
        "outputs_Tab2.tsv",
    )


@pytest.mark.parametrize(
    "name", ["study.json", "reference.json", "Example.xlsx", ".DS_Store"]
)
def test_only_study_files_are_accepted(client, creator_headers, folder, name):
    response = client.put(
        URL, headers=creator_headers, **multipart(folder, {name: b"{}"})
    )
    assert response.status_code == 422
    [issue] = response.json()["issues"]
    assert issue["code"] == "invalid_filename"
    assert name in issue["message"]


@pytest.mark.parametrize(
    "path",
    [
        "%2E%2E/Example",
        "caffeine/%2E",
        "back%5Cslash/Example",
        # Folder names of more than 255 bytes, and a sid of more than 255 characters.
        "caffeine/" + "A" * 256,
        "caffeine/" + "µ" * 128,
        "c" * 100 + "/" + "E" * 160,
    ],
    ids=["dots", "dot", "backslash", "long", "long_bytes", "long_sid"],
)
def test_study_location_must_name_folders(client, creator_headers, folder, path):
    for method, url in (
        ("put", f"/api/v2/studies/{path}"),
        ("post", f"/api/v2/studies/{path}/validate"),
    ):
        response = getattr(client, method)(
            url, headers=creator_headers, **multipart(folder)
        )
        assert response.status_code == 422, response.text
        assert response.json()["issues"][0]["code"] == "invalid_study_location"


def test_route_follows_the_study_format(client, creator_headers, folder, valid_bundle):
    for method, url in (
        ("put", "/api/v2/studies/Example"),
        ("post", "/api/v2/studies/validate"),
    ):
        response = getattr(client, method)(
            url, headers=creator_headers, **multipart(folder)
        )
        assert response.status_code == 422
        assert response.json()["issues"][0]["code"] == "study_format_route"
    sid = valid_bundle.study["sid"]
    for method, url in (
        ("put", f"/api/v2/studies/caffeine/{sid}"),
        ("post", f"/api/v2/studies/caffeine/{sid}/validate"),
    ):
        response = getattr(client, method)(
            url, headers=creator_headers, **format_1(valid_bundle)
        )
        assert response.status_code == 422
        assert response.json()["issues"][0]["code"] == "study_format_route"


def test_study_files_are_sent_as_files(client, creator_headers, folder):
    # Text fields lose the exact bytes: Starlette decodes them as Latin-1 when needed.
    parts = multipart(folder)["files"]
    for index, file in enumerate(JSON_FILES):
        parts[index] = (
            parts[index][0],
            (None, (folder / file).read_text(encoding="utf-8")),
        )
    response = client.put(URL, headers=creator_headers, files=parts)
    assert response.status_code == 422
    assert response.json()["issues"][0]["code"] == "bundle_fields"


def test_study_json_bytes_are_checked(client, creator_headers, folder):
    content = (folder / "study.json").read_bytes()
    latin_1 = content.replace("µ".encode(), b"\xb5")
    assert latin_1 != content
    for method, url in (("post", URL + "/validate"), ("put", URL)):
        response = getattr(client, method)(
            url,
            headers=creator_headers,
            **multipart(folder, json_files={"study.json": latin_1}),
        )
        assert response.status_code == 422
        [issue] = response.json()["issues"]
        assert (issue["code"], issue["source"]["file"]) == (
            "invalid_encoding",
            "study.json",
        )


def test_non_canonical_study_json_is_rejected(client, creator_headers, folder):
    compact = json.dumps(json.loads((folder / "study.json").read_text())).encode()
    response = client.put(
        URL,
        headers=creator_headers,
        **multipart(folder, json_files={"study.json": compact}),
    )
    assert response.status_code == 422
    [issue] = response.json()["issues"]
    assert (issue["code"], issue["source"]["file"]) == ("not_formatted", "study.json")


def test_doi_without_normalized_form_is_refused(client, creator_headers, folder):
    # The pattern accepts the DOI, but it has no normalized form for the server.
    doi = "10.1234/a%20b"
    study = json.loads((folder / "study.json").read_text())
    study["reference"] = {"doi": doi}
    reference = json.loads((folder / "reference.json").read_text())
    reference.update(sid=doi, doi=doi)
    del reference["pmid"]
    replaced = {
        "study.json": dump_json(study).encode(),
        "reference.json": dump_json(reference).encode(),
    }
    headers = {**creator_headers, "X-PKDB-Report-Version": "2"}
    for method, url in (("post", URL + "/validate"), ("put", URL)):
        response = getattr(client, method)(
            url, headers=headers, **multipart(folder, json_files=replaced)
        )
        assert response.status_code == 422, response.text
        found = {
            (issue["code"], issue["source"]["file"], issue["field"])
            for issue in response.json()["report"]["issues"]
        }
        assert found == {
            ("invalid_study_json", "study.json", "reference.doi"),
            ("invalid_reference_json", "reference.json", "doi"),
        }


def test_format_1_doi_without_normalized_form_is_refused(
    client, creator_headers, valid_bundle
):
    valid_bundle.reference["doi"] = "10.1234/a%20b"
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    headers = {**creator_headers, "X-PKDB-Report-Version": "2"}
    for method, path in (("post", "/api/v2/studies/validate"), ("put", url)):
        response = getattr(client, method)(
            path, headers=headers, **format_1(valid_bundle)
        )
        assert response.status_code == 422, response.text
        [issue] = response.json()["report"]["issues"]
        assert (issue["code"], issue["source"]["file"], issue["field"]) == (
            "invalid_publication_identifier",
            "reference.json",
            "doi",
        )


def test_format_1_pubmed_id_of_any_length_is_a_validation_error(
    client, creator_headers, valid_bundle
):
    valid_bundle.reference["pmid"] = "1" * 5000
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    headers = {**creator_headers, "X-PKDB-Report-Version": "2"}
    for method, path in (("post", "/api/v2/studies/validate"), ("put", url)):
        response = getattr(client, method)(
            path, headers=headers, **format_1(valid_bundle)
        )
        assert response.status_code == 422, response.text
        [issue] = response.json()["report"]["issues"]
        assert (issue["code"], issue["field"]) == (
            "invalid_publication_identifier",
            "pmid",
        )


def test_mixed_study_parts_are_bundle_fields(client, creator_headers, folder):
    parts = multipart(folder)["files"]
    parts[1] = ("reference", (None, (folder / "reference.json").read_text()))
    response = client.put(URL, headers=creator_headers, files=parts)
    assert response.status_code == 422
    [issue] = response.json()["issues"]
    assert issue["code"] == "bundle_fields"
    assert "as files" in issue["message"]


@pytest.fixture
def limited_server(ingestion_context, session_factory):
    """Start servers with upload limits; each one stops at the end of the test."""
    from contextlib import ExitStack

    from fastapi.testclient import TestClient

    from pkdb_server.app import create_app
    from pkdb_server.config import Settings

    ingestion, _ = ingestion_context

    def start(**limits):
        settings = Settings(
            database_url=session_factory.kw["bind"].url.render_as_string(
                hide_password=False
            ),
            file_root=ingestion.file_store.root,
            rate_limits_enabled=False,
            **limits,
        )
        return stack.enter_context(TestClient(create_app(settings)))

    with ExitStack() as stack:
        yield start


@pytest.fixture
def limited_client(limited_server):
    """A server that accepts as many files as the study folder has attachments."""
    return limited_server(upload_max_files=8)


def test_file_limit_counts_attachments_only(
    limited_client, creator_headers, folder, valid_bundle
):
    # study.json and reference.json of study format 2 are files but no attachments.
    assert len(list(folder.iterdir())) - len(JSON_FILES) == 8
    response = limited_client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    # Study format 1 keeps its exact limit of attachment files.
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    for count, status in ((8, 201), (9, 422)):
        parts = [
            *format_1(valid_bundle)["files"].items(),
            *(
                ("files", (f"notes{index}.txt", b"note", "text/plain"))
                for index in range(count)
            ),
        ]
        response = limited_client.put(url, headers=creator_headers, files=parts)
        assert response.status_code == status, response.text
    assert response.json()["issues"][0]["code"] == "invalid_bundle"


def test_row_limit_stops_a_format_2_upload(
    limited_server, creator_headers, folder, session_factory
):
    rows = sum(len(path.read_text().splitlines()) - 1 for path in folder.glob("*.tsv"))
    for limit, status in ((rows, 201), (rows - 1, 422)):
        server = limited_server(upload_max_rows=limit)
        response = server.put(URL, headers=creator_headers, **multipart(folder))
        assert response.status_code == status, response.text
    [issue] = response.json()["issues"]
    assert (issue["code"], issue["message"]) == (
        "row_limit",
        f"The study tables have more than {rows - 1} rows",
    )
    validation = server.post(
        URL + "/validate", headers=creator_headers, **multipart(folder)
    )
    assert validation.status_code == 422
    assert validation.json()["issues"][0]["code"] == "row_limit"


def test_long_file_names_are_refused(client, creator_headers, folder, valid_bundle):
    name = "A" * 252 + ".pdf"
    parts = format_1(valid_bundle)["files"]
    format_1_parts = [
        *((part, value) for part, value in parts.items()),
        ("files", (name, b"%PDF", "application/pdf")),
    ]
    for url, request in (
        (URL, multipart(folder, {name: b"%PDF"})),
        ("/api/v2/studies/" + valid_bundle.study["sid"], {"files": format_1_parts}),
    ):
        response = client.put(url, headers=creator_headers, **request)
        assert response.status_code == 422, response.text
        [issue] = response.json()["issues"]
        assert issue["code"] == "invalid_filename"
        assert "255 bytes" in issue["message"]


@pytest.mark.parametrize("part", ["study", "reference"])
def test_huge_json_integers_are_invalid_json(client, creator_headers, part):
    parts = {
        "study": (None, '{"sid": "TEST1"}', "application/json"),
        "reference": (None, '{"sid": "REF1"}', "application/json"),
    }
    parts[part] = (None, '{"sid": ' + "1" * 5000 + "}", "application/json")
    response = client.post(
        "/api/v2/studies/validate", headers=creator_headers, files=parts
    )
    assert response.status_code == 422
    assert response.json()["issues"][0]["code"] == "invalid_json"


def upload_format_1(client, headers, valid_bundle, sid):
    valid_bundle.study["sid"] = sid
    return client.put(
        f"/api/v2/studies/{sid}", headers=headers, **format_1(valid_bundle)
    )


def test_released_study_takes_over_its_format_1_row(
    client, creator_headers, tmp_path, valid_bundle, session_factory
):
    assert (
        upload_format_1(client, creator_headers, valid_bundle, "PKDB00198").status_code
        == 201
    )
    # The single-segment publication route keeps its meaning next to two-segment routes.
    old = client.get("/api/v2/studies/PKDB00198/publication", headers=creator_headers)
    assert old.status_code == 200 and old.json()["sid"] == "PKDB00198"
    [before] = stored(session_factory)
    folder = write_study(tmp_path / "sources", release="PKDB00198")
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 200, response.text
    assert response.json()["created"] is False
    assert response.json()["renamed_from"] == "PKDB00198"
    [after] = stored(session_factory)
    assert (after.id, after.sid, after.pkdb_id) == (
        before.id,
        "caffeine/Example",
        "PKDB00198",
    )
    assert client.get(URL, headers=creator_headers).status_code == 200
    # A study format 1 bundle cannot bring the renamed study back under its old sid.
    response = upload_format_1(client, creator_headers, valid_bundle, "PKDB00198")
    assert response.status_code == 422
    [issue] = response.json()["issues"]
    assert issue["code"] == "duplicate_pkdb_id"
    assert "caffeine/Example" in issue["message"]
    assert count(session_factory) == 1


def test_renamed_folder_takes_over_its_released_row(
    client, creator_headers, tmp_path, session_factory
):
    original = write_study(tmp_path / "before", release="PKDB00198")
    assert (
        client.put(URL, headers=creator_headers, **multipart(original)).status_code
        == 201
    )
    [before] = stored(session_factory)
    renamed = write_study(tmp_path / "after", "Renamed", release="PKDB00198")
    response = client.put(
        "/api/v2/studies/caffeine/Renamed",
        headers=creator_headers,
        **multipart(renamed),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["sid"], body["created"], body["renamed_from"]) == (
        "caffeine/Renamed",
        False,
        "caffeine/Example",
    )
    [after] = stored(session_factory)
    assert (after.id, after.sid, after.name, after.pkdb_id) == (
        before.id,
        "caffeine/Renamed",
        "Renamed",
        "PKDB00198",
    )
    assert client.get(URL, headers=creator_headers).status_code == 404
    again = client.put(
        "/api/v2/studies/caffeine/Renamed",
        headers=creator_headers,
        **multipart(renamed),
    )
    assert again.status_code == 200 and again.json()["renamed_from"] is None


def test_pkdb_identifier_names_one_study(
    client, creator_headers, tmp_path, session_factory
):
    first = write_study(tmp_path / "a", release="PKDB00198")
    assert (
        client.put(URL, headers=creator_headers, **multipart(first)).status_code == 201
    )
    second = write_study(tmp_path / "b", "Other", pmid="456")
    other = "/api/v2/studies/caffeine/Other"
    assert (
        client.put(other, headers=creator_headers, **multipart(second)).status_code
        == 201
    )
    released = write_study(tmp_path / "c", "Other", pmid="456", release="PKDB00198")
    for method, url in (("post", other + "/validate"), ("put", other)):
        response = getattr(client, method)(
            url, headers=creator_headers, **multipart(released)
        )
        assert response.status_code == 422
        [issue] = response.json()["issues"]
        assert issue["code"] == "duplicate_pkdb_id"
        assert (
            "PKDB00198" in issue["message"] and "caffeine/Example" in issue["message"]
        )
        assert issue["source"]["file"] == "study.json"
    assert {row.sid: row.pkdb_id for row in stored(session_factory)} == {
        "caffeine/Example": "PKDB00198",
        "caffeine/Other": None,
    }


def test_refusals_name_only_readable_studies(
    client, creator_headers, tmp_path, session_factory
):
    from pkdb_server.db.models.users import User
    from pkdb_server.services.authentication import issue_token

    private = write_study(tmp_path / "a", release="PKDB00198")
    assert (
        client.put(URL, headers=creator_headers, **multipart(private)).status_code
        == 201
    )
    with session_factory.begin() as session:
        user = User(username="other", role="curator", active=True)
        session.add(user)
        session.flush()
        other = {"Authorization": f"Token {issue_token(user, session)}"}
    url = "/api/v2/studies/caffeine/Other"
    own = write_study(tmp_path / "b", "Other", pmid="456")
    assert client.put(url, headers=other, **multipart(own)).status_code == 201
    claim = write_study(tmp_path / "c", "Other", pmid="456", release="PKDB00198")
    response = client.put(url, headers=other, **multipart(claim))
    assert response.status_code == 422, response.text
    [issue] = response.json()["issues"]
    assert issue["code"] == "duplicate_pkdb_id"
    assert issue["message"].startswith("Another study already uses PKDB00198")
    assert "caffeine/Example" not in response.text


def test_ambiguous_pkdb_identifier_is_refused(
    client, creator_headers, tmp_path, valid_bundle, session_factory
):
    # A study format 1 row still uses the identifier that a renamed study holds.
    first = write_study(tmp_path / "a", release="PKDB00198")
    assert (
        client.put(URL, headers=creator_headers, **multipart(first)).status_code == 201
    )
    with session_factory.begin() as session:
        row = session.scalar(select(Study))
        row.pkdb_id = row.release_date = None
    valid_bundle.reference["sid"] = valid_bundle.study["reference"] = "REF2"
    assert (
        upload_format_1(client, creator_headers, valid_bundle, "PKDB00198").status_code
        == 201
    )
    with session_factory.begin() as session:
        row = session.scalar(select(Study).where(Study.sid == "caffeine/Example"))
        row.pkdb_id, row.release_date = "PKDB00198", date(2026, 9, 28)
    renamed = write_study(tmp_path / "b", "Renamed", release="PKDB00198")
    response = client.put(
        "/api/v2/studies/caffeine/Renamed",
        headers=creator_headers,
        **multipart(renamed),
    )
    assert response.status_code == 422
    [issue] = response.json()["issues"]
    assert issue["code"] == "duplicate_pkdb_id"
    assert "more than one" in issue["message"]
    assert "PKDB00198" in issue["message"] and "caffeine/Example" in issue["message"]


def test_public_client_and_cli_upload_format_2(
    client, creator_headers, folder, tmp_path, monkeypatch, capsys
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
    arguments = [
        "upload",
        str(folder),
        "--vocabulary",
        str(snapshot),
        "--cache-dir",
        str(tmp_path / "cache"),
        "--format",
        "json",
    ]
    assert main(arguments, client=client) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["created"], report
    assert report["sid"] == "caffeine/Example"
    assert report["url"].endswith("/data/caffeine/Example")
    stored_study = api.studies.get("caffeine/Example")
    assert stored_study.metadata.release is None
    assert stored_study.metadata.review is not None
    assert api.publication("caffeine/Example").sid == "caffeine/Example"
    result = api.upload(prepare(folder, vocabulary=api.vocabulary()))
    assert (result.sid, result.created) == ("caffeine/Example", False)
    assert json.loads((folder / "study.json").read_text())["format"] == 2
