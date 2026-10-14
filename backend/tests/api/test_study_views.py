"""The study pages of the website: stored at upload, served by audience (#963)."""

import json

import pytest
from sqlalchemy import select

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.views import VIEW_VERSION
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.users import User
from pkdb_server.db.models.views import StudyView
from pkdb_server.services.authentication import issue_token
from tests.fixtures.study_folders import multipart, write_study

URL = "/api/v2/studies/caffeine/Example"


@pytest.fixture
def folder(tmp_path):
    return write_study(tmp_path / "sources")


def views(session_factory, sid="caffeine/Example"):
    with session_factory() as session:
        study = session.scalar(select(Study).where(Study.sid == sid))
        rows = session.scalars(
            select(StudyView).where(StudyView.study_id == study.id)
        ).all()
        return study, {(row.kind, row.key): row for row in rows}


def test_upload_stores_the_texts_and_the_views(
    client, creator_headers, folder, session_factory
):
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    study, stored = views(session_factory)
    assert study.study_json == (folder / "study.json").read_text(encoding="utf-8")
    assert study.reference_json == (folder / "reference.json").read_text(
        encoding="utf-8"
    )
    assert {kind for kind, _ in stored} == {"study", "row", "table", "source"}
    assert ("study", "") in stored and ("row", "") in stored
    assert ("table", "outputs_Tab2.tsv") in stored
    assert ("source", "Tab2") in stored
    assert {row.version for row in stored.values()} == {VIEW_VERSION}
    page = stored[("study", "")].document
    assert page["review"]["status"] == "in_review"
    assert stored[("row", "")].document["summary"] == page["summary"]
    assert (
        stored[("row", "")].document["warnings"]
        == study.validation_report["warning_count"]
    )


def test_reupload_replaces_the_views(client, creator_headers, folder, session_factory):
    table, image = folder / "outputs_Tab3.tsv", folder / "Example_Tab3.png"
    table.write_bytes((folder / "outputs_Tab2.tsv").read_bytes())
    image.write_bytes(b"png 3")
    assert format_folder(folder).ok
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    _, stored = views(session_factory)
    assert ("table", "outputs_Tab3.tsv") in stored
    assert ("source", "Tab3") in stored
    table.unlink()
    image.unlink()
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 200, response.text
    _, stored = views(session_factory)
    assert ("table", "outputs_Tab3.tsv") not in stored
    assert ("source", "Tab3") not in stored
    assert ("table", "outputs_Tab2.tsv") in stored


def test_validation_alone_stores_nothing(
    client, creator_headers, folder, session_factory
):
    response = client.post(
        URL + "/validate", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 200, response.text
    with session_factory() as session:
        assert session.scalars(select(StudyView)).all() == []


def test_clear_children_deletes_the_views(
    client, creator_headers, folder, session_factory
):
    from pkdb_server.db import replace

    assert (
        client.put(URL, headers=creator_headers, **multipart(folder)).status_code == 201
    )
    study, _ = views(session_factory)
    with session_factory.begin() as session:
        replace.clear_children(session, study.id)
    _, stored = views(session_factory)
    assert stored == {}


def test_format_1_upload_keeps_no_texts_and_no_views(
    client, creator_headers, valid_bundle, session_factory
):
    files = {
        name: (None, json.dumps(getattr(valid_bundle, name)), "application/json")
        for name in ("study", "reference")
    }
    sid = valid_bundle.study["sid"]
    response = client.put(
        f"/api/v2/studies/{sid}", headers=creator_headers, files=files
    )
    assert response.status_code == 201, response.text
    study, stored = views(session_factory, sid)
    assert study.study_json is None
    assert study.reference_json is None
    assert stored == {}


def headers_of(session_factory, username, role):
    with session_factory.begin() as session:
        user = User(username=username, role=role, active=True)
        session.add(user)
        session.flush()
        return {"Authorization": f"Token {issue_token(user, session)}"}


def publish(client, creator_headers, folder, session_factory):
    """Upload the study and make it public, so that every account may read it."""
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    with session_factory.begin() as session:
        session.scalar(
            select(Study).where(Study.sid == "caffeine/Example")
        ).access = "public"


def test_the_json_read_has_no_curation_for_readers_who_may_not_write(
    client, creator_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources", issue=2158)
    publish(client, creator_headers, folder, session_factory)
    reader = headers_of(session_factory, "reader", "user")
    for headers in ({}, reader):
        metadata = client.get(URL, headers=headers).json()["metadata"]
        assert metadata.get("review") is None
        assert metadata.get("issue") is None
        # Released clients need the ratings (#963): only the website pages hide them.
        assert [c["rating"] for c in metadata["curators"]] == [3]
    metadata = client.get(URL, headers=creator_headers).json()["metadata"]
    assert metadata["review"]["status"] == "in_review"
    assert metadata["issue"] == 2158
    assert [c["rating"] for c in metadata["curators"]] == [3]


def test_the_study_lists_have_no_curation_for_readers_who_may_not_write(
    client, creator_headers, admin_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources", issue=2158)
    publish(client, creator_headers, folder, session_factory)
    reader = headers_of(session_factory, "reader", "user")

    def curation(headers):
        [row] = client.get("/api/v2/studies", headers=headers).json()["items"]
        return (
            row["issue"],
            row["review_status"],
            row["open_review_items"],
            [c["rating"] for c in row["curators"]],
        )

    for headers in ({}, reader):
        assert curation(headers) == (None, None, 0, [3])
    assert curation(creator_headers) == (2158, "in_review", 1, [3])
    assert curation(admin_headers) == (2158, "in_review", 1, [3])
    with session_factory.begin() as session:
        session.scalar(
            select(Study).where(Study.sid == "caffeine/Example")
        ).creator_id = None
    assert curation(admin_headers) == (2158, "in_review", 1, [3])
    assert curation(reader) == (None, None, 0, [3])
    record = client.get("/api/v1/studies/caffeine%2FExample/").json()
    assert (record["issue"], record["review_status"], record["open_review_items"]) == (
        None,
        None,
        0,
    )
    assert [c["rating"] for c in record["curators"]] == [3]


def test_a_reviewer_reads_the_curation_of_a_public_study(
    client, creator_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources", issue=2158)
    publish(client, creator_headers, folder, session_factory)
    reviewer = headers_of(session_factory, "reviewer", "reviewer")
    metadata = client.get(URL, headers=reviewer).json()["metadata"]
    assert metadata["review"]["status"] == "in_review"
    assert metadata["issue"] == 2158


def test_review_json_is_only_for_who_may_write_the_study(
    client, creator_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources", issue=2158)
    publish(client, creator_headers, folder, session_factory)
    with session_factory.begin() as session:
        session.scalar(
            select(Study).where(Study.sid == "caffeine/Example")
        ).licence = "open"
    reader = headers_of(session_factory, "reader", "user")

    def files(headers):
        [row] = client.get("/api/v2/studies", headers=headers).json()["items"]
        return {file["name"]: file["file"] for file in row["files"]}

    def record(headers):
        response = client.get("/api/v1/studies/caffeine%2FExample/", headers=headers)
        return {file["name"] for file in response.json()["files"]}

    def attachments(headers):
        return {
            a["name"] for a in client.get(URL, headers=headers).json()["attachments"]
        }

    written = files(creator_headers)
    review, paper = written["data/review.json"], written["data/Example.pdf"]
    assert "data/review.json" in record(creator_headers)
    assert "review.json" in attachments(creator_headers)
    for headers in ({}, reader):
        assert set(files(headers)) == set(written) - {"data/review.json"}
        assert "data/review.json" not in record(headers)
        assert "data/Example.pdf" in record(headers)
        assert attachments(headers) == attachments(creator_headers) - {"review.json"}
    # As for any file that the account may not read: 401 without and 403 with an account.
    assert client.get(review).status_code == 401
    assert client.get(review, headers=reader).status_code == 403
    assert client.get(paper, headers=reader).status_code == 200
    response = client.get(review, headers=creator_headers)
    assert response.status_code == 200
    assert response.content == (folder / "review.json").read_bytes()


def test_an_upload_whose_page_cannot_be_built_keeps_the_study(
    client,
    creator_headers,
    folder,
    session_factory,
    ingestion_context,
    monkeypatch,
    caplog,
):
    from fastapi.testclient import TestClient

    from pkdb_server.app import create_app
    from pkdb_server.commands.views import stale_view_count
    from pkdb_server.config import Settings
    from pkdb_server.services import study_views

    def broken(*args, **kwargs):
        raise KeyError("series")

    monkeypatch.setattr(study_views, "build_views", broken)
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    study, stored = views(session_factory)
    assert study.study_json == (folder / "study.json").read_text(encoding="utf-8")
    assert study.reference_json == (folder / "reference.json").read_text(
        encoding="utf-8"
    )
    assert stored == {}
    with session_factory() as session:
        assert stale_view_count(session) == 1
    [record] = [r for r in caplog.records if "caffeine/Example" in r.getMessage()]
    assert "KeyError" in record.getMessage() and record.exc_info
    # The server counts the study when it starts.
    ingestion, _ = ingestion_context
    settings = Settings(
        database_url=session_factory.kw["bind"].url.render_as_string(
            hide_password=False
        ),
        file_root=ingestion.file_store.root,
    )
    caplog.clear()
    with TestClient(create_app(settings)):
        pass
    assert (
        "1 studies have no study page of this version; run pkdb-server rebuild-views"
        in caplog.messages
    )


def test_the_row_counts_the_warnings_of_the_report(
    client, creator_headers, folder, session_factory, monkeypatch
):
    from pkdb_server.services.ingestion import IngestionService

    validate = IngestionService.validate

    def truncated(self, *args, **kwargs):
        prepared = validate(self, *args, **kwargs)
        # A truncated report counts more warnings than it lists.
        prepared.report.warning_count = len(prepared.report.issues) + 5
        return prepared

    monkeypatch.setattr(IngestionService, "validate", truncated)
    response = client.put(URL, headers=creator_headers, **multipart(folder))
    assert response.status_code == 201, response.text
    study, stored = views(session_factory)
    count = study.validation_report["warning_count"]
    assert count == len(study.validation_report["issues"]) + 5
    assert stored[("row", "")].document["warnings"] == count
