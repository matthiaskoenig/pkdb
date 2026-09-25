"""Readable output, durable reports, and negotiated wire compatibility."""

import json

import httpx2
import pytest

from pkdb.cli import main
from pkdb.client import Client
from pkdb.errors import ClientError


def test_human_validation_and_batch_report(study_folder, vocabulary, tmp_path, capsys):
    lock = tmp_path / "vocabulary.json"
    vocabulary.save(lock)
    report = tmp_path / "report.json"
    assert (
        main(
            [
                "validate",
                str(study_folder),
                "--vocabulary",
                str(lock),
                "--format",
                "human",
                "--report",
                str(report),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "PK-DB" in output and "Validating study" in output and "Summary" in output
    saved = json.loads(report.read_text())
    assert saved["summary"]["validated"] == 1
    assert saved["summary"]["unattempted"] == 0
    assert saved["results"][0]["persistence"] == "not_attempted"
    assert (
        main(
            [
                "validate",
                str(study_folder),
                "--vocabulary",
                str(lock),
                "--report",
                str(report),
            ]
        )
        == 1
    )
    assert json.loads(report.read_text()) == saved


def test_report_inside_source_rejected(study_folder, capsys):
    report = study_folder / "report.json"
    assert main(["validate", str(study_folder), "--report", str(report)]) == 1
    assert not report.exists()
    assert "outside" in capsys.readouterr().err


def test_future_report_fields_and_envelope_are_preserved():
    body = {
        "report_version": 2,
        "request_id": "request-123",
        "stage": "server_validation",
        "persistence": "not_saved",
        "report": {
            "issues": [
                {
                    "code": "new_code",
                    "message": "Fix this value",
                    "future_field": True,
                    "source": {"file": "study.json", "future_coordinate": 1},
                }
            ],
            "error_count": 1,
            "future_metadata": 1,
        },
    }
    with httpx2.Client(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(422, json=body))
    ) as transport:
        with Client("https://example.test", transport=transport) as client:
            with pytest.raises(ClientError) as caught:
                client._request("PUT", "/api/v2/studies/TEST")
    error = caught.value
    assert error.report is not None
    assert error.report.issues[0].message == "Fix this value"
    assert error.request_id == "request-123"
    assert error.persistence == "not_saved"
    assert error.envelope == body


def test_connection_loss_does_not_claim_upload_failed():
    def handler(request):
        raise httpx2.ReadTimeout("lost response", request=request)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client("https://example.test", transport=transport) as client:
            with pytest.raises(ClientError) as caught:
                client._request("PUT", "/api/v2/studies/TEST")
    assert caught.value.persistence == "unknown"


def test_interrupt_saves_partial_report(
    study_folder, vocabulary, tmp_path, monkeypatch, capsys
):
    lock = tmp_path / "vocabulary.json"
    vocabulary.save(lock)
    report = tmp_path / "report.json"

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("pkdb.cli.prepare", interrupt)
    assert (
        main(
            [
                "validate",
                str(study_folder),
                "--vocabulary",
                str(lock),
                "--report",
                str(report),
            ]
        )
        == 130
    )
    saved = json.loads(report.read_text())
    assert saved["results"][0]["error"] == "Interrupted"
    assert saved["results"][0]["persistence"] == "not_attempted"


def test_terminal_does_not_interpret_source_markup(capsys):
    from pkdb.terminal import Terminal

    terminal = Terminal(True)
    terminal.result(
        {"ok": False, "error": "[bold]bad[/bold]\x1b[31m", "report": {"issues": []}}
    )
    output = capsys.readouterr().out
    assert "[bold]bad[/bold]" in output
    assert "\x1b" not in output


def test_negotiated_upload_stream_reports_real_bytes(study_folder, vocabulary):
    from pkdb import prepare
    from pkdb.domain.validation import PROCESSING_VERSION

    prepared = prepare(study_folder, vocabulary=vocabulary)
    events = []
    body_lengths = []

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(
                200,
                json={
                    "schema_version": 1,
                    "server_version": "test",
                    "processing_version": PROCESSING_VERSION,
                    "vocabulary_version": vocabulary.version,
                    "vocabulary_hash": prepared.vocabulary_hash,
                    "upload_report_versions": [1, 2],
                    "upload_limits": {
                        "max_rows": 1000000,
                        "max_files": 256,
                        "max_upload_bytes": 100000000,
                        "max_attachment_bytes": 100000000,
                    },
                },
            )
        assert request.headers["X-PKDB-Report-Version"] == "2"
        body_lengths.append(len(request.read()))
        return httpx2.Response(
            201,
            json={
                "report_version": 2,
                "request_id": "abc",
                "result": {
                    "sid": "TEST1",
                    "created": True,
                    "digest": "digest",
                    "counts": {},
                },
            },
        )

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        with Client(
            "https://example.test",
            api_key="test",
            transport=transport,
            progress=events.append,
        ) as client:
            result = client.upload(prepared)
            assert result.created
            assert client.last_upload_report["request_id"] == "abc"
    transfers = [event for event in events if event.stage == "transfer"]
    assert transfers[-1].completed == body_lengths[0]
    assert transfers[-1].total == body_lengths[0]
    assert [event.stage for event in events][-2:] == ["server_validation", "complete"]


def test_legacy_internal_error_has_unknown_persistence():
    with httpx2.Client(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(500, json={"detail": "Internal error"})
        )
    ) as transport:
        with Client("https://example.test", transport=transport) as client:
            with pytest.raises(ClientError) as caught:
                client._request("PUT", "/api/v2/studies/TEST")
    assert caught.value.persistence == "unknown"


def test_shared_auth_failure_stops_batch_and_records_remaining(
    study_folder, vocabulary, tmp_path, monkeypatch, capsys
):
    import shutil

    from pkdb import prepare
    from pkdb.domain.validation import PROCESSING_VERSION

    second = tmp_path / "nested" / study_folder.name
    shutil.copytree(study_folder, second)
    _identity(second, "TEST2", 124)
    lock = tmp_path / "vocabulary.json"
    vocabulary.save(lock)
    prepared = prepare(study_folder, vocabulary=vocabulary)
    monkeypatch.setenv("PKDB_API_KEY", "pkdb_live_redact-me")
    report = tmp_path / "report.json"
    writes = []

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(
                200,
                json={
                    "schema_version": 1,
                    "server_version": "test",
                    "processing_version": PROCESSING_VERSION,
                    "vocabulary_version": vocabulary.version,
                    "vocabulary_hash": prepared.vocabulary_hash,
                    "upload_limits": {
                        "max_rows": 1000000,
                        "max_files": 256,
                        "max_upload_bytes": 100000000,
                        "max_attachment_bytes": 100000000,
                    },
                },
            )
        writes.append(request)
        return httpx2.Response(401, json={"detail": "Invalid pkdb_live_redact-me"})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        assert (
            main(
                [
                    "upload",
                    str(tmp_path),
                    "--endpoint",
                    "https://example.test",
                    "--vocabulary",
                    str(lock),
                    "--report",
                    str(report),
                ],
                client=transport,
            )
            == 1
        )
    assert len(writes) == 1
    result = json.loads(report.read_text())
    assert result["summary"]["attempted"] == 1
    assert result["summary"]["unattempted"] == 1
    assert len(result["unattempted"]) == 1
    assert "pkdb_live_redact-me" not in report.read_text()
    assert "pkdb_live_redact-me" not in capsys.readouterr().out


def test_terminal_groups_repeated_errors_and_shows_null(capsys):
    from pkdb.terminal import Terminal

    terminal = Terminal(True)
    terminal.result(
        {
            "ok": False,
            "report": {
                "issues": [
                    {
                        "code": "bad",
                        "message": "Value required",
                        "actual": None,
                        "source": {
                            "file": "data.xlsx",
                            "sheet": "Results",
                            "row": row,
                            "cell": f"A{row}",
                        },
                    }
                    for row in (3, 4)
                ]
            },
        }
    )
    output = capsys.readouterr().out
    assert output.count("Value required") == 1
    assert "2 occurrences: A3, A4" in output
    assert "Received: empty (null)" in output


def test_confirmed_commit_error_is_not_reported_as_unsaved(capsys):
    from pkdb.terminal import Terminal

    Terminal(True).result(
        {"ok": False, "persistence": "created", "error": "Response failure"}
    )
    output = capsys.readouterr().out
    assert "Save confirmed" in output
    assert "did not save" not in output


def test_human_output_includes_json_pointer_and_transfer_completion(capsys):
    from pkdb.progress import ProgressEvent
    from pkdb.terminal import Terminal

    terminal = Terminal(True)
    terminal.progress(ProgressEvent("transfer", 0, 100))
    terminal.progress(ProgressEvent("transfer", 100, 100))
    terminal.result(
        {
            "ok": False,
            "report": {
                "issues": [
                    {
                        "code": "unknown_image",
                        "message": "Image missing",
                        "source": {
                            "file": "study.json",
                            "path": ["outputset", "outputs", 3, "image"],
                        },
                    }
                ]
            },
        }
    )
    output = capsys.readouterr().out
    assert "100 bytes / 100 (100%)" in output
    assert "/outputset/outputs/3/image" in output


@pytest.mark.parametrize("broken", [False, True])
def test_batch_paths_distinguish_same_named_studies(
    study_folder, vocabulary, tmp_path, capsys, broken
):
    import shutil

    root = tmp_path / "studies"
    for substance in ("apixaban", "caffeine"):
        folder = root / substance / "Example"
        shutil.copytree(study_folder, folder)
        if broken:
            (folder / "study.json").write_text("{")
    lock = tmp_path / "vocabulary.json"
    vocabulary.save(lock)
    report = tmp_path / "batch.json"
    assert main(
        [
            "validate",
            str(root),
            "--vocabulary",
            str(lock),
            "--format",
            "human",
            "--report",
            str(report),
        ]
    ) == int(broken)
    output = capsys.readouterr().out
    assert "[1/2] apixaban/Example" in output
    assert "[2/2] caffeine/Example" in output
    results = json.loads(report.read_text())["results"]
    assert [row["relative_path"] for row in results] == [
        "apixaban/Example",
        "caffeine/Example",
    ]
    assert [row["name"] for row in results] == ["Example", "Example"]
    assert all(row["ok"] is not broken for row in results)


@pytest.mark.parametrize("persistence", ["created", "replaced", "unknown", "not_saved"])
def test_object_summary_only_claims_confirmed_uploads(capsys, persistence):
    from pkdb.terminal import Terminal

    terminal = Terminal(True)
    terminal.result(
        {
            "ok": False,
            "relative_path": "apixaban/Frost2013",
            "persistence": persistence,
            "counts": {"measurements": 12, "groups": 3, "individuals": 0},
        }
    )
    output = capsys.readouterr().out
    assert "apixaban/Frost2013" in output
    if persistence in {"created", "replaced"}:
        assert "Uploaded: groups=3, individuals=0, measurements=12" in output
        assert "Save confirmed" in output
    else:
        assert "Uploaded:" not in output


@pytest.mark.parametrize(
    "status,fail_fast,attempts",
    [
        (403, False, 2),
        (403, True, 1),
        (429, False, 1),
        (401, False, 1),
        (503, False, 1),
    ],
)
def test_batch_continues_after_forbidden_but_stops_on_systemic_failures(
    study_folder, vocabulary, tmp_path, monkeypatch, capsys, status, fail_fast, attempts
):
    import shutil

    from pkdb.domain.validation import PROCESSING_VERSION
    from pkdb.domain.vocabulary import vocabulary_hash

    root = tmp_path / "studies"
    for index, name in enumerate(("a/Example", "b/Example")):
        shutil.copytree(study_folder, root / name)
        _identity(root / name, f"TEST{index + 1}", 123 + index)
    lock = tmp_path / "vocabulary.json"
    vocabulary.save(lock)
    monkeypatch.setenv("PKDB_API_KEY", "pkdb_live_secret")
    calls = []

    def handler(request):
        if request.method == "GET":
            return httpx2.Response(
                200,
                json={
                    "schema_version": 1,
                    "server_version": "test",
                    "processing_version": PROCESSING_VERSION,
                    "vocabulary_version": vocabulary.version,
                    "vocabulary_hash": vocabulary_hash(vocabulary),
                    "upload_limits": {
                        "max_rows": 1000000,
                        "max_files": 256,
                        "max_upload_bytes": 100000000,
                        "max_attachment_bytes": 100000000,
                    },
                },
            )
        calls.append(request.method)
        if len(calls) == 1:
            # Also handle plain-text rejections from an older server/proxy.
            return httpx2.Response(
                status,
                text="Rejected",
                headers={"X-Request-ID": "request-test", "Retry-After": "30"},
            )
        return httpx2.Response(
            201,
            json={
                "sid": request.url.path.rsplit("/", 1)[-1],
                "created": True,
                "digest": "abc",
                "counts": {"groups": 1},
            },
        )

    report = tmp_path / "batch.json"
    with httpx2.Client(transport=httpx2.MockTransport(handler)) as transport:
        assert (
            main(
                [
                    "upload",
                    str(root),
                    "--endpoint",
                    "https://example.test",
                    "--vocabulary",
                    str(lock),
                    "--report",
                    str(report),
                    *(["--fail-fast"] if fail_fast else []),
                ],
                client=transport,
            )
            == 1
        )
    assert len(calls) == attempts
    data = json.loads(report.read_text())
    first = data["results"][0]
    assert first["status_code"] == status
    assert first["retry_after"] == "30"
    assert first["request_id"] == "request-test"
    assert data["summary"]["unattempted"] == 2 - attempts
    if status == 403:
        assert first["code"] == "upload_forbidden"
        assert first["persistence"] == "not_saved"
        if not fail_fast:
            assert data["results"][1]["persistence"] == "created"
    if status == 429:
        assert first["code"] == "rate_limit"
        assert "rate limit reached" in first["error"]
    assert "pkdb_live_secret" not in capsys.readouterr().out


def test_client_preserves_safe_permission_detail():
    with httpx2.Client(
        transport=httpx2.MockTransport(
            lambda request: httpx2.Response(
                403,
                json={
                    "code": "licence_change_forbidden",
                    "detail": "The upload would change the licence.",
                },
            )
        )
    ) as transport:
        with Client("https://example.test", transport=transport) as api:
            with pytest.raises(ClientError) as caught:
                api._request("PUT", "/api/v2/studies/TEST")
    assert caught.value.code == "licence_change_forbidden"
    assert "would change the licence" in str(caught.value)


def _identity(folder, sid, reference):
    path = folder / "study.json"
    data = json.loads(path.read_text())
    data.update(sid=sid, reference=reference)
    path.write_text(json.dumps(data))
    path = folder / "reference.json"
    data = json.loads(path.read_text())
    data["sid"] = reference
    path.write_text(json.dumps(data))
