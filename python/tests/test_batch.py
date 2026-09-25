"""Real HTTP workers and conservative journal recovery."""

import json
import shutil
import threading
import time
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx2
import pytest

from pkdb.batch import BatchOptions, upload_many
from pkdb.domain.validation import PROCESSING_VERSION
from pkdb.domain.vocabulary import vocabulary_hash


def capabilities(vocabulary):
    return dict(
        schema_version=1,
        server_version="test",
        processing_version=PROCESSING_VERSION,
        vocabulary_version=vocabulary.version,
        vocabulary_hash=vocabulary_hash(vocabulary),
        upload_limits=dict(
            max_rows=1000000,
            max_files=256,
            max_upload_bytes=10000000,
            max_attachment_bytes=10000000,
        ),
    )


def copies(source, root, count):
    folders = []
    for index in range(count):
        target = root / str(index) / source.name
        shutil.copytree(source, target)
        for name in ("study", "reference"):
            path = target / f"{name}.json"
            data = json.loads(path.read_text())
            data["sid"] = f"TEST{index}" if name == "study" else 100 + index
            if name == "study":
                data["reference"] = 100 + index
            path.write_text(json.dumps(data))
        folders.append(target)
    return folders


def test_spawn_workers_overlap_and_checkpoint_before_put(
    study_folder, vocabulary, tmp_path
):
    folders = copies(study_folder, tmp_path / "sources", 4)
    report = tmp_path / "report.json"
    active = 0
    maximum = 0
    writes = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def reply(self, value):
            content = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            self.reply(capabilities(vocabulary))

        def do_PUT(self):
            nonlocal active, maximum
            self.rfile.read(int(self.headers["Content-Length"]))
            sid = self.path.rsplit("/", 1)[-1]
            saved = json.loads(report.read_text())
            assert (
                next(r for r in saved["results"] if r["sid"] == sid)["status"]
                == "submitting"
            )
            with lock:
                active += 1
                maximum = max(maximum, active)
                writes.append(sid)
            barrier.wait(timeout=10)
            time.sleep(0.05 if sid.endswith("0") else 0.01)
            self.reply(dict(sid=sid, created=True, digest="digest", counts={}))
            with lock:
                active -= 1

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = upload_many(
            folders,
            endpoint=f"http://127.0.0.1:{server.server_port}",
            api_key="secret",
            vocabulary=vocabulary,
            options=BatchOptions(jobs=2, report=report),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert maximum == 2
    assert len(writes) == 4
    assert all(row["ok"] for row in result["results"])
    assert [r["index"] for r in result["results"]] == list(range(4))
    assert "secret" not in report.read_text()


def test_resume_unknown_reconciles_without_replay(study_folder, vocabulary, tmp_path):
    report = tmp_path / "report.json"
    calls = []
    publication = {}

    def handler(request):
        calls.append(request.method)
        if request.url.path.endswith("capabilities"):
            return httpx2.Response(200, json=capabilities(vocabulary))
        if request.method == "PUT":
            raise httpx2.ReadTimeout("lost", request=request)
        return httpx2.Response(200, json=publication)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        upload = partial(
            upload_many,
            endpoint="https://example.test",
            api_key="secret",
            vocabulary=vocabulary,
            transport=transport,
        )
        result = upload([study_folder], options=BatchOptions(report=report))
        row = result["results"][0]
        assert row["status"] == "unknown"
        publication.update(
            sid=row["sid"],
            digest=row["source_digest"],
            processing_version=PROCESSING_VERSION,
            vocabulary_version=vocabulary.version,
            current_processing_version=PROCESSING_VERSION,
            current_vocabulary_version=vocabulary.version,
        )
        resumed = upload([study_folder], options=BatchOptions(resume=report))
        assert resumed["results"][0]["skipped"]
        assert calls.count("PUT") == 1
        # A changed source must never be silently considered confirmed.
        (study_folder / "study.json").write_text(
            (study_folder / "study.json").read_text() + "\n"
        )
        with pytest.raises(ValueError, match="Source changed"):
            upload([study_folder], options=BatchOptions(resume=report))


def test_duplicate_sid_rejected_before_network(study_folder, vocabulary, tmp_path):
    other = tmp_path / "other"
    shutil.copytree(study_folder, other)
    with pytest.raises(ValueError, match="Duplicate study SID"):
        upload_many(
            [study_folder, other],
            endpoint="https://example.test",
            api_key="secret",
            vocabulary=vocabulary,
        )


def test_checkpoint_failure_prevents_dispatch(
    study_folder, vocabulary, tmp_path, monkeypatch
):
    from pkdb.cache import atomic_json as write

    report = tmp_path / "report.json"
    writes = []

    def checkpoint(path, value):
        if any(row["status"] == "submitting" for row in value["results"]):
            raise OSError("disk full")
        write(path, value)

    def handler(request):
        writes.append(request.method)
        return httpx2.Response(200, json=capabilities(vocabulary))

    monkeypatch.setattr("pkdb.batch.atomic_json", checkpoint)
    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        result = upload_many(
            [study_folder],
            endpoint="https://example.test",
            api_key="secret",
            vocabulary=vocabulary,
            transport=transport,
            options=BatchOptions(report=report),
        )
    assert writes == ["GET"]
    assert result["report_error"] == "disk full"
    assert result["results"][0]["persistence"] == "not_attempted"


def test_unknown_mismatch_never_retries(study_folder, vocabulary, tmp_path):
    report = tmp_path / "report.json"
    puts = []

    def handler(request):
        if request.url.path.endswith("capabilities"):
            return httpx2.Response(200, json=capabilities(vocabulary))
        if request.method == "PUT":
            puts.append(request)
            raise httpx2.ReadTimeout("lost", request=request)
        return httpx2.Response(
            200,
            json=dict(
                sid="TEST1",
                digest="different",
                processing_version=PROCESSING_VERSION,
                vocabulary_version=vocabulary.version,
                current_processing_version=PROCESSING_VERSION,
                current_vocabulary_version=vocabulary.version,
            ),
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        upload = partial(
            upload_many,
            endpoint="https://example.test",
            api_key="secret",
            vocabulary=vocabulary,
            transport=transport,
        )
        upload([study_folder], options=BatchOptions(report=report))
        with pytest.raises(ValueError, match="explicit resolution"):
            upload([study_folder], options=BatchOptions(resume=report))
    assert len(puts) == 1


def test_private_snapshot_is_sent_after_original_changes(study_folder, vocabulary):
    from pkdb.client import Capabilities, Client

    sent = []

    def handler(request):
        sent.append(request.read())
        return httpx2.Response(
            200, json=dict(sid="TEST1", digest="digest", created=True, counts={})
        )

    def change_original(prepared, hashes):
        (study_folder / "study.json").write_text('{"sid": "MUTATED"}')

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            "https://example.test", api_key="secret", transport=transport
        ) as api:
            api._upload_folder(
                study_folder,
                vocabulary,
                Capabilities.model_validate(capabilities(vocabulary)),
                change_original,
            )
    assert b"MUTATED" not in sent[0]
    assert b"TEST1" in sent[0]


def test_worker_exit_stops_without_inventing_commit(
    study_folder, vocabulary, monkeypatch
):
    monkeypatch.setattr("pkdb.batch._worker", lambda *args: None)
    with httpx2.Client(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(200, json=capabilities(vocabulary))
        )
    ) as transport:
        result = upload_many(
            [study_folder],
            endpoint="https://example.test",
            api_key="secret",
            vocabulary=vocabulary,
            transport=transport,
        )
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["persistence"] == "not_attempted"


def test_interrupt_before_dispatch_cancels_worker(study_folder, vocabulary, tmp_path):
    interrupted = False
    methods = []

    def progress(event):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt

    def handler(request):
        methods.append(request.method)
        return httpx2.Response(200, json=capabilities(vocabulary))

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        result = upload_many(
            [study_folder],
            endpoint="https://example.test",
            api_key="secret",
            vocabulary=vocabulary,
            transport=transport,
            progress=progress,
            options=BatchOptions(report=tmp_path / "report.json"),
        )
    assert result["interrupted"]
    assert methods == ["GET"]
    assert result["results"][0]["persistence"] == "not_attempted"
