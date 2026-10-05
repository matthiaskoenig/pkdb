"""Uploads of study format 2 folders: routes, identity, release and rename on re-upload."""

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select

from pkdb import Client, prepare
from pkdb.cache import VocabularyCache
from pkdb.cli import main
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.text import render_tsv
from pkdb_server.db.models.studies import Study

URL = "/api/v2/studies/caffeine/Example"
JSON_FILES = ("study.json", "reference.json")


def tsv(kind, *rows):
    names = TABLES[kind].names
    return render_tsv(
        names, [tuple(row.get(name, "") for name in names) for row in rows]
    )


def write_study(root: Path, name="Example", *, pmid="123", release=None) -> Path:
    """A formatted study format 2 folder at <root>/caffeine/<name>."""
    folder = root / "caffeine" / name
    folder.mkdir(parents=True)
    study = {
        "format": 2,
        "reference": {"pmid": pmid},
        "creator": "curator",
        "curators": [{"user": "curator", "rating": 3}],
        "licence": "closed",
        "access": "private",
        "issue": 2158,
        "descriptions": ["Plasma levels in µg/l."],
    }
    if release:
        study["release"] = {"pkdb_id": release, "date": "2026-09-28"}
    files = {
        "study.json": dump_json(study),
        "reference.json": dump_json(
            {"sid": pmid, "name": name, "pmid": pmid, "title": "Example study"}
        ),
        "review.json": dump_json(
            {
                "status": "in_review",
                "reviewers": ["curator"],
                "items": [
                    {
                        "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
                        "kind": "question",
                        "target": {"file": "outputs_Tab2.tsv", "column": "mean"},
                        "text": "Is the mean read from the table?",
                        "author": "curator",
                        "created": "2026-10-05T10:12:00Z",
                    }
                ],
            }
        ),
        "subjects.tsv": tsv(
            "subjects", {"name": "all", "count": "4", "source": "Tab1"}
        ),
        "interventions.tsv": tsv(
            "interventions",
            {
                "source": "Text",
                "name": "D1",
                "measurement": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "single dose",
                "time": "0",
                "time_unit": "h",
                "mean": "10",
                "unit": "mg",
            },
        ),
        "characteristica.tsv": tsv(
            "characteristica",
            *(
                {"source": "Tab1", "subjects": "all", "measurement": m, "choice": c}
                for m, c in (
                    ("species", "Homo sapiens"),
                    ("sex", "NR"),
                    ("healthy", "Y"),
                )
            ),
        ),
        "outputs_Tab2.tsv": tsv(
            "outputs",
            {
                "subjects": "all",
                "interventions": "D1",
                "measurement": "concentration",
                "substance": "drug",
                "tissue": "plasma",
                "time": "1",
                "time_unit": "h",
                "mean": "2",
                "unit": "mg/l",
            },
        ),
    }
    for file, text in files.items():
        (folder / file).write_text(text, encoding="utf-8", newline="")
    (folder / f"{name}.pdf").write_bytes(b"%PDF-1.4 example")
    (folder / f"{name}_Tab1.png").write_bytes(b"png 1")
    (folder / f"{name}_Tab2.png").write_bytes(b"png 2")
    assert format_folder(folder).ok
    return folder


def multipart(folder: Path, files: dict[str, bytes] | None = None):
    """The parts the client sends: exact JSON text and every other study file.

    `files` replaces or adds file parts.
    """
    attachments = {
        path.name: path.read_bytes()
        for path in sorted(folder.iterdir())
        if path.name not in JSON_FILES
    } | (files or {})
    return {
        "files": [
            *(
                (
                    part,
                    (
                        None,
                        (folder / file).read_text(encoding="utf-8"),
                        "application/json",
                    ),
                )
                for part, file in zip(("study", "reference"), JSON_FILES, strict=True)
            ),
            *(
                ("files", (name, content, "application/octet-stream"))
                for name, content in attachments.items()
            ),
        ]
    }


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
    "path", ["%2E%2E/Example", "caffeine/%2E", "back%5Cslash/Example"]
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
