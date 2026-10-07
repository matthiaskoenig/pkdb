"""The read and write routes of a study page on a real loopback server over a real engine."""

import json
import threading

import openpyxl
import pytest
from curation_http import authenticate, request
from digitize_fixtures import GOOD, png, project

from pkdb.curation import studies
from pkdb.curation.engine import CurationEngine
from pkdb.curation.server import create_server
from pkdb.identity import Author, IdentityError
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.sync import sync_study
from pkdb.studyformat.ulid import new_ulid
from pkdb.studyformat.workbook.base import workbook_path

DETAIL = "/local/studies/caffeine/Example"
METADATA = {"format": 2, "creator": "curator", "licence": "open", "access": "private"}


@pytest.fixture
def api(tmp_path_factory, make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "Example_Tab2.tsv": "cmax\t2.5 ± 0.5\n",
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
        }
    )
    assert format_folder(folder).ok
    engine = CurationEngine(
        folder.parent.parent,
        state_dir=tmp_path_factory.mktemp("state"),
        offline=True,
        start=False,
    )
    engine.user = "curator"
    server = create_server(engine)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, engine, folder
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_study_detail(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, data = request(server, "GET", DETAIL, headers=headers)
    assert status == 200
    detail = json.loads(data)
    assert detail["id"] == "caffeine/Example"
    assert detail["metadata"]["value"]["licence"] == "open"
    assert detail["metadata"]["revision"] and detail["metadata"]["issues"] == []
    assert detail["review"]["value"]["status"] == "draft"
    assert {s["source"] for s in detail["sources"]} >= {"Fig1", "Tab2"}
    assert "Example_Fig1.wpd.json" in detail["files"]
    etag = response_headers["ETag"]
    again = request(server, "GET", DETAIL, headers={**headers, "If-None-Match": etag})
    assert again[0] == 304 and again[2] == b"" and again[1]["ETag"] == etag
    (folder / "study.json").write_text(
        (folder / "study.json").read_text().replace('"open"', '"closed"')
    )
    engine.scan()
    changed = request(server, "GET", DETAIL, headers={**headers, "If-None-Match": etag})
    assert changed[0] == 200 and changed[1]["ETag"] != etag
    assert json.loads(changed[2])["metadata"]["value"]["licence"] == "closed"


def test_detail_etag_changes_with_a_job(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, _ = request(server, "GET", DETAIL, headers=headers)
    assert status == 200
    engine.enqueue(["caffeine/Example"], "validate")
    status, changed_headers, data = request(
        server,
        "GET",
        DETAIL,
        headers={**headers, "If-None-Match": response_headers["ETag"]},
    )
    assert status == 200 and changed_headers["ETag"] != response_headers["ETag"]
    detail = json.loads(data)
    assert detail["status"] == "queued"
    assert [job["status"] for job in detail["jobs"]] == ["queued"]


def test_invalid_documents_keep_their_revision(api):
    server, engine, folder = api
    (folder / "review.json").write_text('{"status": "finished"}')
    detail = json.loads(request(server, "GET", DETAIL, headers=authenticate(server))[2])
    assert detail["review"]["value"] is None and detail["review"]["revision"]
    assert detail["review"]["issues"][0]["code"] == "invalid_review_json"
    assert detail["metadata"]["value"]["licence"] == "open"


def test_symlinked_review_json_is_not_read(api, tmp_path_factory):
    server, engine, folder = api
    outside = tmp_path_factory.mktemp("outside") / "review.json"
    outside.write_text('{"status": "in_review"}')
    (folder / "review.json").unlink()
    (folder / "review.json").symlink_to(outside)
    status, _, data = request(server, "GET", DETAIL, headers=authenticate(server))
    assert status == 200
    review = json.loads(data)["review"]
    assert review["value"] is None and review["revision"] is None
    assert "symlink" in {issue["code"] for issue in review["issues"]}


def test_directory_named_review_json_is_reported(api):
    server, engine, folder = api
    (folder / "review.json").unlink()
    (folder / "review.json").mkdir()
    status, _, data = request(server, "GET", DETAIL, headers=authenticate(server))
    assert status == 200
    detail = json.loads(data)
    assert detail["review"]["value"] is None
    assert {"unknown_directory", "missing_file"} <= {
        issue["code"] for issue in detail["review"]["issues"]
    }
    assert detail["metadata"]["value"]["licence"] == "open"


def test_missing_study_json_has_the_absent_revision(api):
    server, engine, folder = api
    (folder / "study.json").unlink()
    detail = json.loads(request(server, "GET", DETAIL, headers=authenticate(server))[2])
    assert detail["metadata"]["value"] is None
    assert detail["metadata"]["revision"] == "absent"
    assert detail["metadata"]["issues"][0]["code"] == "missing_file"


@pytest.mark.parametrize(
    ("limit", "value", "code"),
    [("MAX_ROWS", 3, "row_limit"), ("MAX_FILES", 2, "file_limit")],
)
def test_upload_limits_bound_the_read_routes(api, monkeypatch, limit, value, code):
    server, engine, folder = api
    monkeypatch.setattr(studies, limit, value)
    headers = authenticate(server)
    status, _, data = request(server, "GET", DETAIL, headers=headers)
    assert status == 200
    detail = json.loads(data)
    assert detail["metadata"]["value"]["licence"] == "open"
    assert detail["review"]["value"]["status"] == "draft"
    assert detail["problems"][0]["code"] == code
    assert detail["sources"] == [] and detail["files"] == []
    for path in (f"{DETAIL}/tables/timecourses_Fig1.tsv", f"{DETAIL}/sources/Fig1"):
        status, _, data = request(server, "GET", path, headers=headers)
        assert status == 413 and "more than" in json.loads(data)["error"]


def test_detail_lists_sync_conflicts(api, sf_vocabulary, monkeypatch):
    server, engine, folder = api
    # The bundled vocabulary lacks the substance of the test study.
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    headers = authenticate(server)
    assert (
        json.loads(request(server, "GET", DETAIL, headers=headers)[2])["conflicts"]
        == []
    )
    assert sync_study(folder, sf_vocabulary).ok
    book = openpyxl.load_workbook(workbook_path(folder))
    sheet = book["timecourses_Fig1"]
    header = [cell.value for cell in sheet[1]]
    sheet.cell(3, header.index("mean") + 1).value = 5
    book.save(workbook_path(folder))
    table = folder / "timecourses_Fig1.tsv"
    lines = table.read_text().splitlines()
    cells = lines[2].split("\t")
    cells[lines[0].split("\t").index("mean")] = "7"
    lines[2] = "\t".join(cells)
    table.write_text("\n".join(lines) + "\n")
    engine.scan()
    detail = json.loads(request(server, "GET", DETAIL, headers=headers)[2])
    assert detail["sync"]["status"] == "conflict"
    [conflict] = detail["conflicts"]
    assert conflict["file"] == "timecourses_Fig1.tsv"
    assert conflict["workbook_rows"][0]["row"] == 3
    assert conflict["table_lines"][0]["line"] == 3


def test_acknowledged_warnings_are_listed_until_dismissed(api):
    server, engine, folder = api
    created = "2026-10-01T10:00:00Z"
    acknowledged, dismissed = new_ulid(), new_ulid()
    target = {"file": "timecourses_Fig1.tsv", "rows": {"time": "1"}, "column": "mean"}
    review = {
        "status": "draft",
        "items": [
            {
                "id": acknowledged,
                "kind": "issue",
                "state": "resolved",
                "target": target,
                "acknowledges": "digitized_mismatch",
                "text": "The figure is blurred here",
                "author": "curator",
                "created": created,
                "resolved_by": "curator",
                "resolved": created,
            },
            {
                "id": dismissed,
                "kind": "issue",
                "state": "dismissed",
                "acknowledges": "digitized_mismatch",
                "text": "Withdrawn",
                "author": "curator",
                "created": created,
                "resolved_by": "curator",
                "resolved": created,
            },
            {
                "id": new_ulid(),
                "kind": "question",
                "text": "Which dose was given?",
                "author": "curator",
                "created": created,
            },
        ],
    }
    (folder / "review.json").write_text(json.dumps(review))
    detail = json.loads(request(server, "GET", DETAIL, headers=authenticate(server))[2])
    assert detail["acknowledged"] == [
        {
            "id": acknowledged,
            "code": "digitized_mismatch",
            "target": target,
            "text": "The figure is blurred here",
            "author": "curator",
            "resolved_by": "curator",
            "resolved": created,
        }
    ]


def test_tables_sources_and_images(api):
    server, engine, folder = api
    headers = authenticate(server)
    table = json.loads(
        request(
            server, "GET", f"{DETAIL}/tables/timecourses_Fig1.tsv", headers=headers
        )[2]
    )
    assert table["kind"] == "table" and table["rows"][0]["line"] == 2
    assert table["rows"][0]["cells"][table["header"].index("label")] == "drug_plasma"
    raw = json.loads(
        request(server, "GET", f"{DETAIL}/tables/Example_Tab2.tsv", headers=headers)[2]
    )
    assert raw["kind"] == "raw"
    assert raw["rows"] == [{"line": 1, "cells": ["cmax", "2.5 ± 0.5"]}]
    source = json.loads(
        request(server, "GET", f"{DETAIL}/sources/Fig1", headers=headers)[2]
    )
    assert source["image_url"] == f"{DETAIL}/files/Example_Fig1.png"
    assert source["overlay"]
    status, image_headers, data = request(
        server, "GET", source["image_url"], headers=headers
    )
    assert status == 200 and image_headers["Content-Type"] == "image/png"
    assert data.startswith(b"\x89PNG") and "ETag" not in image_headers


@pytest.mark.parametrize(
    "path", [f"{DETAIL}/tables/timecourses_Fig1.tsv", f"{DETAIL}/sources/Fig1"]
)
def test_tables_and_sources_answer_304(api, path):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, _ = request(server, "GET", path, headers=headers)
    assert status == 200
    again = request(
        server,
        "GET",
        path,
        headers={**headers, "If-None-Match": response_headers["ETag"]},
    )
    assert again[0] == 304 and again[2] == b""


def test_a_table_304_does_not_load_the_study(api, monkeypatch):
    server, engine, folder = api
    headers = authenticate(server)
    path = f"{DETAIL}/tables/timecourses_Fig1.tsv"
    etag = request(server, "GET", path, headers=headers)[1]["ETag"]
    loads = []
    monkeypatch.setattr(
        studies, "load_study", lambda *args, **kwargs: loads.append(args)
    )
    assert (
        request(server, "GET", path, headers={**headers, "If-None-Match": etag})[0]
        == 304
    )
    assert loads == []


def test_table_etag_changes_with_the_table(api):
    server, engine, folder = api
    headers = authenticate(server)
    path = f"{DETAIL}/tables/Example_Tab2.tsv"
    etag = request(server, "GET", path, headers=headers)[1]["ETag"]
    (folder / "Example_Tab2.tsv").write_text("cmax\t3.5 ± 0.5\n")
    engine.scan()
    status, response_headers, data = request(
        server, "GET", path, headers={**headers, "If-None-Match": etag}
    )
    assert status == 200 and response_headers["ETag"] != etag
    assert json.loads(data)["rows"][0]["cells"] == ["cmax", "3.5 ± 0.5"]


@pytest.mark.parametrize(
    "path",
    [
        f"{DETAIL}/files/..%2Fstudy.json",
        f"{DETAIL}/files/study.json",
        f"{DETAIL}/files/%2Fetc%2Fpasswd",
        f"{DETAIL}/files/%2E%2E",
        f"{DETAIL}/files/..%5Cstudy.json",
        f"{DETAIL}/files/Example_Fig1.png%00",
        f"{DETAIL}/files/",
        "/local/studies/caffeine/../Example",
        f"{DETAIL}/tables/Example.pdf",
        f"{DETAIL}/tables/..%2F..%2FExample%2Fsubjects.tsv",
        "/local/studies/caffeine/Missing",
        "/local/studies/caffeine",
        f"{DETAIL}/sources/Fig9",
        f"{DETAIL}/notes/Fig1",
    ],
)
def test_crafted_paths_are_not_found(api, path):
    server, engine, folder = api
    assert request(server, "GET", path, headers=authenticate(server))[0] == 404


def test_symlinked_image_is_refused(api, tmp_path):
    server, engine, folder = api
    outside = tmp_path / "outside.png"
    outside.write_bytes((folder / "Example_Fig1.png").read_bytes())
    (folder / "Example_Fig3.png").symlink_to(outside)
    engine.scan()
    status = request(
        server, "GET", f"{DETAIL}/files/Example_Fig3.png", headers=authenticate(server)
    )[0]
    assert status == 404


@pytest.mark.parametrize(
    "path",
    [
        DETAIL,
        f"{DETAIL}/files/Example_Fig1.png",
        f"{DETAIL}/tables/Example_Tab2.tsv",
        f"{DETAIL}/sources/Fig1",
    ],
)
def test_study_folder_replaced_by_a_symlink_is_refused(api, tmp_path_factory, path):
    server, engine, folder = api
    headers = authenticate(server)
    etag = request(server, "GET", path, headers=headers)[1].get("ETag")
    moved = tmp_path_factory.mktemp("outside") / "Example"
    folder.rename(moved)
    folder.symlink_to(moved, target_is_directory=True)
    # The scan skips a symlinked folder and keeps its row.
    engine.scan()
    assert request(server, "GET", path, headers=headers)[0] == 404
    if etag:
        cached = {**headers, "If-None-Match": etag}
        assert request(server, "GET", path, headers=cached)[0] == 404


def test_duplicate_identity_answers_409(api, valid_files):
    server, engine, folder = api
    copy = engine.root / "copies" / "caffeine" / "Example"
    copy.mkdir(parents=True)
    for file, content in valid_files.items():
        (copy / file).write_bytes(
            content if isinstance(content, bytes) else content.encode()
        )
    engine.scan()
    status, _, data = request(server, "GET", DETAIL, headers=authenticate(server))
    body = json.loads(data)
    assert status == 409 and "identity of two folders" in body["error"]
    # The app lists the folders without parsing the message.
    assert sorted(body["paths"]) == ["caffeine/Example", "copies/caffeine/Example"]


def test_ambiguous_study_counts_and_lists_its_folders():
    error = studies.AmbiguousStudy(
        "caffeine/Example", ["a, b/caffeine/Example", "c", "d"]
    )
    assert str(error) == (
        "caffeine/Example is the identity of 3 folders: "
        "a, b/caffeine/Example, c, d; rename all but one"
    )
    assert error.paths == ["a, b/caffeine/Example", "c", "d"]


def test_study_routes_require_the_session(api):
    server, engine, folder = api
    assert request(server, "GET", DETAIL)[0] == 401
    assert request(server, "GET", f"{DETAIL}/files/Example_Fig1.png")[0] == 401


def test_state_etag(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, _ = request(
        server, "GET", "/local/state", headers=headers
    )
    assert status == 200
    again = request(
        server,
        "GET",
        "/local/state",
        headers={**headers, "If-None-Match": response_headers["ETag"]},
    )
    assert again[0] == 304 and again[2] == b""
    engine.set_paused(True)
    changed = request(
        server,
        "GET",
        "/local/state",
        headers={**headers, "If-None-Match": response_headers["ETag"]},
    )
    assert changed[0] == 200 and changed[1]["ETag"] != response_headers["ETag"]


def _detail(server, headers):
    return json.loads(request(server, "GET", DETAIL, headers=headers)[2])


def test_metadata_write_and_conflict(api):
    server, engine, folder = api
    headers = authenticate(server)
    detail = _detail(server, headers)
    metadata = {**detail["metadata"]["value"], "licence": "closed"}
    body = {
        "study": "caffeine/Example",
        "revision": detail["metadata"]["revision"],
        "metadata": metadata,
    }
    status, _, data = request(server, "POST", "/local/studies/metadata", body, headers)
    assert status == 200
    assert json.loads((folder / "study.json").read_text())["licence"] == "closed"
    written = json.loads(data)
    assert written == {
        "revision": written["revision"],
        "reference": None,
        "reference_error": None,
    }
    stale = request(server, "POST", "/local/studies/metadata", body, headers)
    assert stale[0] == 409
    conflict = json.loads(stale[2])
    assert conflict["file"] == "study.json"
    assert conflict["revision"] == written["revision"]
    assert json.loads(conflict["content"])["licence"] == "closed"
    invalid = {
        **body,
        "revision": written["revision"],
        "metadata": {**metadata, "licence": "maybe"},
    }
    rejected = request(server, "POST", "/local/studies/metadata", invalid, headers)
    assert rejected[0] == 422
    issues = json.loads(rejected[2])["issues"]
    assert issues and issues[0]["code"] == "invalid_study_json"
    assert json.loads((folder / "study.json").read_text())["licence"] == "closed"


def test_review_actions_and_approval_refusal(api):
    server, engine, folder = api
    headers = authenticate(server)
    revision = _detail(server, headers)["review"]["revision"]
    status, _, data = request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": revision,
            "action": "add",
            "kind": "question",
            "text": "Why?",
            "target": {"file": "timecourses_Fig1.tsv", "column": "mean"},
        },
        headers,
    )
    assert status == 200
    item, revision = json.loads(data)["item"], json.loads(data)["revision"]
    assert item["author"] == "curator" and item["state"] == "open"
    assert item["target"] == {
        "file": "timecourses_Fig1.tsv",
        "rows": {},
        "column": "mean",
    }
    refused = request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": revision,
            "action": "status",
            "status": "approved",
        },
        headers,
    )
    assert refused[0] == 422 and json.loads(refused[2])["code"] == "approval_refused"
    for action, extra in [
        ("reply", {"text": "Because."}),
        ("resolve", {}),
        ("reopen", {"text": "Not yet."}),
        ("dismiss", {"text": "Withdrawn."}),
    ]:
        done = request(
            server,
            "POST",
            "/local/studies/review",
            {
                "study": "caffeine/Example",
                "revision": revision,
                "action": action,
                "item": item["id"],
                **extra,
            },
            headers,
        )
        assert done[0] == 200, action
        assert set(json.loads(done[2])) == {"revision"}
        revision = json.loads(done[2])["revision"]
    [stored] = read_review(folder).review.items
    assert stored.state == "dismissed" and len(stored.thread) == 3
    assert stored.resolved_by == "curator"
    status, _, data = request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": revision,
            "action": "status",
            "status": "in_review",
        },
        headers,
    )
    assert status == 200 and read_review(folder).review.status == "in_review"


def test_review_write_errors(api):
    server, engine, folder = api
    headers = authenticate(server)
    revision = _detail(server, headers)["review"]["revision"]
    review = {"study": "caffeine/Example", "revision": revision}

    def post(body):
        status, _, data = request(
            server, "POST", "/local/studies/review", {**review, **body}, headers
        )
        return status, json.loads(data)

    status, data = post({"action": "add", "kind": "praise", "text": "Nice."})
    assert status == 422 and data["issues"][0]["code"] == "invalid_review_json"
    status, data = post(
        {"action": "add", "kind": "issue", "text": "?", "target": {"column": "mean"}}
    )
    assert status == 422 and data["issues"]
    status, data = post({"action": "resolve", "item": new_ulid()})
    assert status == 422 and "does not exist" in data["error"]
    assert post({"action": "close", "item": new_ulid()})[0] == 400
    status, data = post({"action": "add", "kind": "issue", "text": ""})
    assert status == 422 and data["issues"][0]["field"] == "text"
    assert post({"action": "add", "kind": "issue"})[0] == 400
    assert (
        post({"action": "add", "kind": "issue", "text": "?", "revision": None})[0]
        == 400
    )
    stale = post({"action": "add", "kind": "issue", "text": "?", "revision": "0" * 64})
    assert stale[0] == 409 and stale[1]["file"] == "review.json"
    assert json.loads(stale[1]["content"]) == {"status": "draft"}
    assert read_review(folder).review.items == []


def test_writes_need_a_user(api):
    server, engine, folder = api
    engine.user = ""
    headers = authenticate(server)
    response = request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": None,
            "action": "add",
            "kind": "question",
            "text": "?",
        },
        headers,
    )
    assert response[0] == 403 and json.loads(response[2])["error"] == "no_user"
    assert "Connection settings" in json.loads(response[2])["message"]
    detail = _detail(server, headers)
    metadata = request(
        server,
        "POST",
        "/local/studies/metadata",
        {
            "study": "caffeine/Example",
            "revision": detail["metadata"]["revision"],
            "metadata": detail["metadata"]["value"],
        },
        headers,
    )
    assert metadata[0] == 403 and json.loads(metadata[2])["error"] == "no_user"
    for body in [
        {"action": "open"},
        {"action": "sync"},
        {"action": "resolve", "keep": "workbook"},
        {"action": "add", "raw": "Tab3"},
    ]:
        tables = request(
            server,
            "POST",
            "/local/studies/tables",
            {"study": "caffeine/Example", **body},
            headers,
        )
        assert tables[0] == 403, body["action"]
        assert json.loads(tables[2])["error"] == "no_user"
    assert not workbook_path(folder).exists()


def test_the_author_is_the_account_of_a_checked_key(api):
    server, engine, folder = api
    assert engine.author() == Author("curator")
    assert engine.author("claude-opus-5-5") == Author("curator", "claude-opus-5-5")
    assert engine.snapshot()["author"] == {"user": "curator", "reason": None}
    engine.offline, engine.endpoint = False, "https://pk-db.test"
    engine.api_key, engine.account, engine.checked_at = "key", "account", "now"
    assert engine.author() == Author("account")
    engine.connection_error = "The server rejected the API key."
    assert engine.author() == Author("curator")
    # The last check found that the key belongs to another account than the user.
    engine.connection_error = engine.user_mismatch = (
        "The API key belongs to PK-DB user 'other', not the expected user 'curator'"
    )
    with pytest.raises(IdentityError, match="belongs to PK-DB user 'other'"):
        engine.author()
    assert engine.snapshot()["author"] == {
        "user": None,
        "reason": engine.user_mismatch,
    }
    engine.connection_error = engine.user_mismatch = None
    engine.api_key = None
    assert engine.author() == Author("curator")
    engine.user = ""
    with pytest.raises(IdentityError, match="PK-DB user name is required"):
        engine.author()
    assert engine.snapshot()["author"]["user"] is None
    assert "Connection settings" in engine.snapshot()["author"]["reason"]
    engine.user = "two words"
    with pytest.raises(IdentityError, match="not a PK-DB user name"):
        engine.author()


def test_writes_with_a_key_of_another_account_are_refused(api):
    server, engine, folder = api
    engine.offline, engine.endpoint, engine.api_key = False, "https://pk-db.test", "key"
    engine.user_mismatch = "The API key belongs to PK-DB user 'other'"
    headers = authenticate(server)
    review = _detail(server, headers)["review"]
    response = request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": review["revision"],
            "action": "add",
            "kind": "question",
            "text": "?",
        },
        headers,
    )
    assert response[0] == 403
    assert json.loads(response[2]) == {
        "error": "user_mismatch",
        "message": "The API key belongs to PK-DB user 'other'",
    }
    assert read_review(folder).review.items == []


def test_write_after_the_job_formatted_the_file_conflicts(api):
    server, engine, folder = api
    headers = authenticate(server)
    revision = _detail(server, headers)["metadata"]["revision"]
    study = json.loads((folder / "study.json").read_text())
    # An external edit, which the watcher job then formats.
    (folder / "study.json").write_text(
        dump_json({**study, "descriptions": ["Edited outside the app."]})
    )
    format_folder(folder)
    response = request(
        server,
        "POST",
        "/local/studies/metadata",
        {
            "study": "caffeine/Example",
            "revision": revision,
            "metadata": METADATA,
        },
        headers,
    )
    assert response[0] == 409
    assert json.loads((folder / "study.json").read_text())["descriptions"] == [
        "Edited outside the app."
    ]


def test_a_write_changes_the_detail_etag(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, data = request(server, "GET", DETAIL, headers=headers)
    etag = response_headers["ETag"]
    response = request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": json.loads(data)["review"]["revision"],
            "action": "add",
            "kind": "question",
            "text": "Which dose?",
        },
        headers,
    )
    assert response[0] == 200
    status, changed, data = request(
        server, "GET", DETAIL, headers={**headers, "If-None-Match": etag}
    )
    assert status == 200 and changed["ETag"] != etag
    assert json.loads(data)["summary"]["open_items"] == 1


def test_acknowledge_one_warning(api, sf_vocabulary, monkeypatch):
    server, engine, folder = api
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    timecourses = folder / "timecourses_Fig1.tsv"
    lines = timecourses.read_text().splitlines()
    header = lines[0].split("\t")
    for index in (2, 3):  # the means at times 1 and 2 lie outside their range
        row = lines[index].split("\t")
        row[header.index("min")], row[header.index("max")] = "3", "4"
        lines[index] = "\t".join(row)
    timecourses.write_text("\n".join(lines) + "\n")
    headers = authenticate(server)
    body = {
        "study": "caffeine/Example",
        "revision": _detail(server, headers)["review"]["revision"],
        "action": "acknowledge",
        "code": "outside_range",
        "file": "timecourses_Fig1.tsv",
        "text": "As printed.",
    }
    status, _, data = request(server, "POST", "/local/studies/review", body, headers)
    assert status == 422
    assert json.loads(data)["error"] == (
        "2 warnings [outside_range] match in timecourses_Fig1.tsv at line 3 column "
        "mean, line 4 column mean; give the line and column of one"
    )
    missing = {**body, "code": "missing_image"}
    status, _, data = request(server, "POST", "/local/studies/review", missing, headers)
    assert status == 422
    assert json.loads(data)["error"] == (
        "No warning [missing_image] in timecourses_Fig1.tsv matches"
    )
    status, _, data = request(
        server, "POST", "/local/studies/review", {**body, "line": 4}, headers
    )
    assert status == 200
    item = json.loads(data)["item"]
    assert item["acknowledges"] == "outside_range" and item["state"] == "resolved"
    assert item["target"]["rows"] == {"label": "drug_plasma", "time": "2"}
    assert json.loads(data)["revision"] == read_review(folder).revision


def test_tables_open_uses_the_opener(api, monkeypatch):
    server, engine, folder = api
    opened = []
    monkeypatch.setattr(
        "pkdb.curation.studies.open_path", lambda path, **kw: opened.append(path)
    )
    headers = authenticate(server)
    status, _, data = request(
        server,
        "POST",
        "/local/studies/tables",
        {"study": "caffeine/Example", "action": "open"},
        headers,
    )
    assert status == 200 and opened == [folder / "Example.xlsx"]
    result = json.loads(data)
    assert result["ok"] and result["workbook_action"] == "created"
    assert result["changes"] == [] and result["conflicts"] == []


def test_tables_sync_resolve_and_add(api, sf_vocabulary, monkeypatch):
    server, engine, folder = api
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    headers = authenticate(server)

    def tables(**body):
        status, _, data = request(
            server,
            "POST",
            "/local/studies/tables",
            {"study": "caffeine/Example", **body},
            headers,
        )
        return status, json.loads(data)

    status, result = tables(action="sync")
    assert status == 200 and result["workbook_action"] == "created"
    book = openpyxl.load_workbook(workbook_path(folder))
    sheet = book["timecourses_Fig1"]
    column = [cell.value for cell in sheet[1]].index("mean") + 1
    sheet.cell(3, column).value = 5
    book.save(workbook_path(folder))
    table = folder / "timecourses_Fig1.tsv"
    lines = table.read_text().splitlines()
    cells = lines[2].split("\t")
    cells[lines[0].split("\t").index("mean")] = "7"
    lines[2] = "\t".join(cells)
    table.write_text("\n".join(lines) + "\n")
    status, result = tables(action="sync")
    assert status == 200 and not result["ok"]
    assert [c["file"] for c in result["conflicts"]] == ["timecourses_Fig1.tsv"]
    assert tables(action="resolve")[0] == 400
    assert tables(action="resolve", keep="neither")[0] == 400
    status, result = tables(action="resolve", keep="workbook")
    assert status == 200 and result["ok"]
    assert result["conflicts"][0]["kept"] == "workbook"
    assert (
        table.read_text()
        .splitlines()[2]
        .split("\t")[lines[0].split("\t").index("mean")]
        == "5"
    )
    status, result = tables(action="add", raw="Tab3")
    assert status == 200 and result["ok"] and result["table"] == "Example_Tab3"
    assert "Example_Tab3" in openpyxl.load_workbook(workbook_path(folder)).sheetnames
    status, result = tables(action="add", table="outputs_Tab3")
    assert status == 200 and result["ok"]
    status, result = tables(action="add", table="nonsense")
    assert status == 200 and not result["ok"]
    assert result["issues"][0]["code"] == "invalid_table_name"
    assert tables(action="add")[0] == 400
    assert tables(action="add", table="outputs_Tab4", raw="Tab4")[0] == 400
    assert tables(action="close")[0] == 400


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/local/studies/metadata", {"revision": "absent", "metadata": {}}),
        ("/local/studies/review", {"revision": "absent", "action": "status"}),
        ("/local/studies/tables", {"action": "sync"}),
    ],
)
def test_write_routes_refuse_an_ambiguous_identity(api, valid_files, path, body):
    server, engine, folder = api
    copy = engine.root / "copies" / "caffeine" / "Example"
    copy.mkdir(parents=True)
    for file, content in valid_files.items():
        (copy / file).write_bytes(
            content if isinstance(content, bytes) else content.encode()
        )
    engine.scan()
    headers = authenticate(server)
    status, _, data = request(
        server, "POST", path, {"study": "caffeine/Example", **body}, headers
    )
    refused = json.loads(data)
    assert status == 409 and "identity of two folders" in refused["error"]
    assert len(refused["paths"]) == 2
    for route, existing in [
        ("/local/jobs", {"ids": ["caffeine/Example"], "action": "validate"}),
        ("/local/mode", {"ids": ["caffeine/Example"], "mode": "off"}),
        ("/local/files/open", {"study_id": "caffeine/Example"}),
    ]:
        assert request(server, "POST", route, existing, headers)[0] == 409, route


def test_write_routes_answer_404_for_an_unknown_study(api):
    server, engine, folder = api
    headers = authenticate(server)
    for path, body in [
        ("/local/studies/metadata", {"revision": "absent", "metadata": {}}),
        ("/local/studies/review", {"revision": "absent", "action": "status"}),
        ("/local/studies/tables", {"action": "sync"}),
    ]:
        response = request(
            server, "POST", path, {"study": "caffeine/Missing", **body}, headers
        )
        assert response[0] == 404, path


@pytest.mark.parametrize(
    ("file", "path", "body"),
    [
        ("study.json", "/local/studies/metadata", {"metadata": METADATA}),
        (
            "review.json",
            "/local/studies/review",
            {"action": "add", "kind": "question", "text": "?"},
        ),
    ],
)
def test_writes_refuse_a_symlinked_document(api, tmp_path_factory, file, path, body):
    server, engine, folder = api
    outside = tmp_path_factory.mktemp("outside") / file
    original = (folder / file).read_bytes()
    outside.write_bytes(original)
    (folder / file).unlink()
    (folder / file).symlink_to(outside)
    status, _, data = request(
        server,
        "POST",
        path,
        {"study": "caffeine/Example", "revision": "0" * 64, **body},
        authenticate(server),
    )
    assert status == 422
    refused = json.loads(data)
    assert "symlink" in {issue["code"] for issue in refused["issues"]}
    assert "content" not in refused
    assert (folder / file).is_symlink() and outside.read_bytes() == original


def test_curator_roster(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, data = request(
        server, "GET", "/local/curators", headers=headers
    )
    assert status == 200
    curators = {
        curator["username"]: curator for curator in json.loads(data)["curators"]
    }
    assert curators["mkoenig"]["display_name"] == "Matthias König"
    assert curators["mkoenig"]["avatar_url"] == "/avatars/matthias_koenig.webp"
    assert curators["Ahmed-fub"]["avatar_url"] is None
    assert all(
        {"username", "display_name", "avatar_url"} <= set(curator)
        for curator in curators.values()
    )
    again = request(
        server,
        "GET",
        "/local/curators",
        headers={**headers, "If-None-Match": response_headers["ETag"]},
    )
    assert again[0] == 304
    assert request(server, "GET", "/local/curators")[0] == 401


def test_detail_has_the_people_with_their_profiles(api):
    server, engine, folder = api
    study = json.loads((folder / "study.json").read_text())
    (folder / "study.json").write_text(
        dump_json(
            {
                **study,
                "creator": "mkoenig",
                "curators": [{"user": "mkoenig", "rating": 4.5}, {"user": "curator"}],
                "collaborators": ["Jane Doe"],
            }
        )
    )
    engine.scan()
    people = _detail(server, authenticate(server))["people"]
    assert people["creator"]["display_name"] == "Matthias König"
    assert people["creator"]["avatar_url"] == "/avatars/matthias_koenig.webp"
    assert [(c["user"], c["rating"]) for c in people["curators"]] == [
        ("mkoenig", 4.5),
        ("curator", 0),
    ]
    assert people["curators"][0]["profile"]["username"] == "mkoenig"
    assert people["curators"][1]["profile"]["display_name"] == "curator"
    assert [c["display_name"] for c in people["collaborators"]] == ["Jane Doe"]


def test_app_writes_are_listed_in_the_activity(api, sf_vocabulary, monkeypatch):
    server, engine, folder = api
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    monkeypatch.setattr("pkdb.curation.studies.open_path", lambda path, **kw: None)
    headers = authenticate(server)
    detail = _detail(server, headers)
    request(
        server,
        "POST",
        "/local/studies/metadata",
        {
            "study": "caffeine/Example",
            "revision": detail["metadata"]["revision"],
            "metadata": {**detail["metadata"]["value"], "licence": "closed"},
        },
        headers,
    )
    added = json.loads(
        request(
            server,
            "POST",
            "/local/studies/review",
            {
                "study": "caffeine/Example",
                "revision": detail["review"]["revision"],
                "action": "add",
                "kind": "question",
                "text": "Why?",
            },
            headers,
        )[2]
    )
    item = added["item"]["id"]
    request(
        server,
        "POST",
        "/local/studies/review",
        {
            "study": "caffeine/Example",
            "revision": added["revision"],
            "action": "resolve",
            "item": item,
        },
        headers,
    )
    for body in [
        {"action": "open"},
        {"action": "sync"},
        {"action": "add", "raw": "Tab3"},
    ]:
        request(
            server,
            "POST",
            "/local/studies/tables",
            {"study": "caffeine/Example", **body},
            headers,
        )
    # Recording a write starts nothing; the watcher validates the changed files.
    assert engine.queue == {}
    writes = [
        job for job in _detail(server, headers)["jobs"] if job["action"] == "write"
    ]
    assert [job["message"] for job in writes] == [
        "Added raw table Example_Tab3",
        "Synced the workbook and the tables",
        "Opened the workbook",
        f"Resolved review item {item}",
        f"Added review item {item}",
        "Saved study.json",
    ]
    assert {job["status"] for job in writes} == {"succeeded"}
    assert all(
        job["study_id"] == "caffeine/Example"
        and job["study_name"] == "Example"
        and job["created_at"]
        for job in writes
    )
    saved = json.loads((engine.state_dir / "state.json").read_text())["jobs"]
    assert [job["message"] for job in saved if job["action"] == "write"][0] == (
        "Saved study.json"
    )


def test_detail_has_the_reference_and_the_state_of_the_row(api):
    server, engine, folder = api
    headers = authenticate(server)
    detail = _detail(server, headers)
    assert detail["reference"]["title"] == "Example study"
    assert detail["reference"]["pmid"] == "123"
    assert detail["reference_match"] is True
    assert detail["message"] is None and detail["last_upload"] is None
    reference = json.loads((folder / "reference.json").read_text())
    (folder / "reference.json").write_text(
        dump_json({**reference, "pmid": "456", "doi": "10.1000/ABC"})
    )
    engine.scan()
    assert _detail(server, headers)["reference_match"] is False
    study = json.loads((folder / "study.json").read_text())
    (folder / "study.json").write_text(
        dump_json({**study, "reference": {"doi": "10.1000/abc"}})
    )
    engine.scan()
    assert _detail(server, headers)["reference_match"] is True
    del study["reference"]
    (folder / "study.json").write_text(dump_json(study))
    engine.scan()
    assert _detail(server, headers)["reference_match"] is None
    etag = request(server, "GET", DETAIL, headers=headers)[1]["ETag"]
    upload = {"persistence": "created", "at": "2026-10-07T10:00:00+00:00"}
    with engine.lock:
        row = engine.studies["caffeine/Example"]
        row["message"] = "Upload on save suspended: connect an authorized account"
        row["last_upload"] = upload
    status, _, data = request(
        server, "GET", DETAIL, headers={**headers, "If-None-Match": etag}
    )
    assert status == 200
    detail = json.loads(data)
    assert detail["message"].startswith("Upload on save suspended")
    assert detail["last_upload"] == upload


def test_tables_refuse_a_symlinked_workbook(api, tmp_path_factory, monkeypatch):
    server, engine, folder = api
    opened = []
    monkeypatch.setattr(
        "pkdb.curation.studies.open_path", lambda path, **kw: opened.append(path)
    )
    outside = tmp_path_factory.mktemp("outside") / "Example.xlsx"
    outside.write_bytes(b"not for the app")
    workbook_path(folder).symlink_to(outside)
    headers = authenticate(server)
    for body in [
        {"action": "open"},
        {"action": "sync"},
        {"action": "resolve", "keep": "tables"},
        {"action": "add", "raw": "Tab3"},
    ]:
        status, _, data = request(
            server,
            "POST",
            "/local/studies/tables",
            {"study": "caffeine/Example", **body},
            headers,
        )
        assert status == 400, body
        assert "Example.xlsx is a symlink" in json.loads(data)["error"]
    assert opened == [] and outside.read_bytes() == b"not for the app"


def test_a_write_succeeds_when_the_rescan_fails(api, monkeypatch):
    server, engine, folder = api

    def broken():
        raise RuntimeError("unexpected")

    monkeypatch.setattr(engine, "scan", broken)
    headers = authenticate(server)
    detail = _detail(server, headers)
    status, _, _ = request(
        server,
        "POST",
        "/local/studies/metadata",
        {
            "study": "caffeine/Example",
            "revision": detail["metadata"]["revision"],
            "metadata": {**detail["metadata"]["value"], "licence": "closed"},
        },
        headers,
    )
    assert status == 200
    assert json.loads((folder / "study.json").read_text())["licence"] == "closed"
