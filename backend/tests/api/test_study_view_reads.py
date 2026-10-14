"""The routes of the study pages of the website, per audience (#963)."""

import json

import pytest
from sqlalchemy import delete, select

from pkdb_server.api.study_views import matches
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import User
from pkdb_server.db.models.views import StudyView
from pkdb_server.services.authentication import issue_token
from tests.fixtures.study_folders import multipart, write_study

URL = "/api/v2/studies/caffeine/Example"
VIEW = URL + "/view"


def account(session_factory, username, role):
    with session_factory.begin() as session:
        user = User(username=username, role=role, active=True)
        session.add(user)
        session.flush()
        return user.id, {"Authorization": f"Bearer {issue_token(user, session)}"}


def set_access(session_factory, access):
    with session_factory.begin() as session:
        session.scalar(
            select(Study).where(Study.sid == "caffeine/Example")
        ).access = access


@pytest.fixture
def uploaded(client, creator_headers, tmp_path, session_factory):
    folder = write_study(tmp_path / "sources", issue=2158)
    assert (
        client.put(URL, headers=creator_headers, **multipart(folder)).status_code == 201
    )
    return folder


def test_the_public_view_of_a_public_study(client, uploaded, session_factory):
    set_access(session_factory, "public")
    response = client.get(VIEW)
    assert response.status_code == 200, response.text
    page = response.json()
    assert (page["id"], page["audience"]) == ("caffeine/Example", "public")
    assert page["review"] is None
    assert page["issue"] is None
    assert page["problems"] == []
    assert page["counts"] == {"errors": 0, "warnings": 0}
    assert page["papers"] == [] and page["files"] == []
    assert all(source["image_url"] is None for source in page["sources"])
    assert [c["rating"] for c in page["people"]["curators"]] == [None]
    assert page["people"]["curators"][0]["profile"]["username"] == "curator"
    assert page["tables"] and all(t["kind"] != "raw" for t in page["tables"])


def test_the_curator_view(client, creator_headers, uploaded):
    page = client.get(VIEW, headers=creator_headers).json()
    assert page["audience"] == "curator"
    assert page["review"]["status"] == "in_review"
    assert page["issue"] == {
        "number": 2158,
        "state": None,
        "labels": [],
        "assignees": [],
        "url": "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
    }
    assert [c["rating"] for c in page["people"]["curators"]] == [3]
    assert [paper["file"] for paper in page["papers"]] == ["Example.pdf"]
    [paper] = page["papers"]
    assert paper["url"] == VIEW + "/files/Example.pdf"
    assert paper["bytes"] == len(b"%PDF-1.4 example")
    source = next(s for s in page["sources"] if s["source"] == "Tab2")
    assert source["image_url"] == VIEW + "/files/Example_Tab2.png"


def test_who_gets_which_view(client, creator_headers, uploaded, session_factory):
    _, reader = account(session_factory, "reader", "user")
    reviewer_id, reviewer = account(session_factory, "reviewer", "reviewer")
    _, other_curator = account(session_factory, "other", "curator")
    # Private: only assigned curators and admins read it; nobody else learns it exists.
    for headers in ({}, reader, reviewer, other_curator):
        assert client.get(VIEW, headers=headers).status_code == 404
    set_access(session_factory, "public")
    assert client.get(VIEW).json()["audience"] == "public"
    assert client.get(VIEW, headers=reader).json()["audience"] == "public"
    assert client.get(VIEW, headers=other_curator).json()["audience"] == "public"
    # A reviewer may write every public study.
    assert client.get(VIEW, headers=reviewer).json()["audience"] == "curator"
    set_access(session_factory, "private")
    with session_factory.begin() as session:
        study = session.scalar(select(Study).where(Study.sid == "caffeine/Example"))
        session.add(StudyGrant(study_id=study.id, user_id=reviewer_id, role="curator"))
    assert client.get(VIEW, headers=reviewer).json()["audience"] == "curator"


def test_an_admin_gets_the_curator_view(client, admin_headers, uploaded):
    assert client.get(VIEW, headers=admin_headers).json()["audience"] == "curator"


def test_format_1_and_unknown_studies_have_no_view(client, creator_headers):
    assert client.get("/api/v2/studies/caffeine/Nothing/view").status_code == 404


def test_tables_and_sources(client, creator_headers, uploaded, session_factory):
    set_access(session_factory, "public")
    table = client.get(VIEW + "/tables/outputs_Tab2.tsv").json()
    assert table["kind"] == "table" and table["rows"]
    assert client.get(VIEW + "/tables/nothing.tsv").status_code == 404
    source = client.get(VIEW + "/sources/Tab2").json()
    assert source["image_url"] is None and source["layout"] == "side_by_side"
    curator = client.get(VIEW + "/sources/Tab2", headers=creator_headers).json()
    assert curator["image_url"] == VIEW + "/files/Example_Tab2.png"
    assert client.get(VIEW + "/sources/Fig99").status_code == 404


def test_files_only_for_curators(client, creator_headers, uploaded, session_factory):
    set_access(session_factory, "public")
    assert client.get(VIEW + "/files/Example.pdf").status_code == 404
    response = client.get(VIEW + "/files/Example.pdf", headers=creator_headers)
    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 example"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    ranged = client.get(
        VIEW + "/files/Example.pdf", headers={**creator_headers, "Range": "bytes=0-3"}
    )
    assert (ranged.status_code, ranged.content) == (206, b"%PDF")
    for name in (
        "outputs_Tab2.tsv",
        "study.json",
        "review.json",
        "../x.png",
        "Other.png",
    ):
        assert (
            client.get(VIEW + "/files/" + name, headers=creator_headers).status_code
            == 404
        ), name


def test_etag_differs_by_audience(client, creator_headers, uploaded, session_factory):
    set_access(session_factory, "public")
    curator = client.get(VIEW, headers=creator_headers)
    etag = curator.headers["etag"]
    assert curator.headers["cache-control"] == "no-store"
    again = client.get(VIEW, headers={**creator_headers, "If-None-Match": etag})
    assert again.status_code == 304
    public = client.get(VIEW, headers={"If-None-Match": etag})
    assert public.status_code == 200
    assert public.headers["etag"] != etag
    assert public.headers["cache-control"] == "private, no-cache"


def test_study_rows(client, creator_headers, uploaded, session_factory):
    _, reader = account(session_factory, "reader", "user")
    assert client.get("/api/v2/study-rows", headers=reader).json()["rows"] == []
    body = client.get("/api/v2/study-rows", headers=creator_headers).json()
    [row] = body["rows"]
    assert (row["id"], row["name"], row["substance"], row["curator"]) == (
        "caffeine/Example",
        "Example",
        "caffeine",
        True,
    )
    assert row["substances"][0] == "caffeine"
    assert row["issue"]["number"] == 2158
    assert row["summary"]["review_status"] == "in_review"
    assert "curator" in body["profiles"]
    set_access(session_factory, "public")
    [row] = client.get("/api/v2/study-rows").json()["rows"]
    assert row["curator"] is False and row["issue"] is None
    assert "review_status" not in row["summary"]
    assert row["counts"] == {"errors": 0, "warnings": 0}


def test_etag_comparison():
    etag = '"abc"'
    assert matches('"abc"', etag) and matches('W/"abc"', etag)
    assert matches('"x", W/"abc" , "y"', etag) and matches("*", etag)
    assert not matches('"x", "y"', etag)
    assert not matches(None, etag) and not matches("", etag)


def test_a_nul_in_a_path_is_not_found(client, creator_headers, uploaded):
    assert client.get("/api/v2/studies/caf%00feine/X/view").status_code == 404
    assert client.get("/api/v2/studies/caf%00feine/X").status_code == 404
    assert (
        client.get(VIEW + "/files/Exa%00mple.pdf", headers=creator_headers).status_code
        == 404
    )


def test_format_1_study_has_no_view(
    client, creator_headers, valid_bundle, ingestion_context
):
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    files = {
        name: (None, json.dumps(getattr(valid_bundle, name)), "application/json")
        for name in ("study", "reference")
    }
    assert client.put(url, headers=creator_headers, files=files).status_code == 201
    assert client.get(url + "/view", headers=creator_headers).status_code == 404
    assert (
        client.get("/api/v2/study-rows", headers=creator_headers).json()["rows"] == []
    )


def test_a_study_without_stored_views_is_hidden(
    client, creator_headers, uploaded, session_factory
):
    with session_factory.begin() as session:
        session.execute(delete(StudyView))
    assert client.get(VIEW, headers=creator_headers).status_code == 404
    assert (
        client.get("/api/v2/study-rows", headers=creator_headers).json()["rows"] == []
    )


def test_rows_by_the_audience_of_each_study(
    client, creator_headers, uploaded, tmp_path, session_factory
):
    second = write_study(tmp_path / "second", "Second", pmid="124", issue=7)
    assert (
        client.put(
            "/api/v2/studies/caffeine/Second",
            headers=creator_headers,
            **multipart(second),
        ).status_code
        == 201
    )
    set_access(session_factory, "private")
    with session_factory.begin() as session:
        session.scalar(
            select(Study).where(Study.sid == "caffeine/Second")
        ).access = "public"
        user = User(username="reader", role="curator", active=True)
        session.add(user)
        session.flush()
        example = session.scalar(select(Study).where(Study.sid == "caffeine/Example"))
        session.add(StudyGrant(study_id=example.id, user_id=user.id, role="curator"))
        headers = {"Authorization": f"Bearer {issue_token(user, session)}"}
    rows = {
        r["id"]: r
        for r in client.get("/api/v2/study-rows", headers=headers).json()["rows"]
    }
    assert set(rows) == {"caffeine/Example", "caffeine/Second"}
    assert rows["caffeine/Example"]["curator"] and rows["caffeine/Example"]["issue"]
    assert "review_status" in rows["caffeine/Example"]["summary"]
    assert not rows["caffeine/Second"]["curator"]
    assert rows["caffeine/Second"]["issue"] is None
    assert "review_status" not in rows["caffeine/Second"]["summary"]


def test_ratings_stay_in_the_json_api_but_not_on_the_page(
    client, uploaded, session_factory
):
    set_access(session_factory, "public")
    metadata = client.get(URL).json()["metadata"]
    assert [curator["rating"] for curator in metadata["curators"]] == [3]
    [row] = client.get("/api/v2/studies").json()["items"]
    assert [curator["rating"] for curator in row["curators"]] == [3]
    page = client.get(VIEW).json()
    assert [curator["rating"] for curator in page["people"]["curators"]] == [None]
