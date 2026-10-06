"""The read routes of a study page on a real loopback server over a real engine."""

import json
import threading

import pytest
from curation_http import authenticate, request
from digitize_fixtures import GOOD, png, project

from pkdb.curation.engine import CurationEngine
from pkdb.curation.server import create_server
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.ulid import new_ulid

DETAIL = "/local/studies/caffeine/Example"


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
    moved = tmp_path_factory.mktemp("outside") / "Example"
    folder.rename(moved)
    folder.symlink_to(moved, target_is_directory=True)
    # The scan skips a symlinked folder and keeps its row.
    engine.scan()
    assert request(server, "GET", path, headers=authenticate(server))[0] == 404


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
    assert status == 409 and "identity of two folders" in json.loads(data)["error"]


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
