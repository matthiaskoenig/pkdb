"""Rebuild accounting and resume require local and remote evidence."""

import json

import httpx

from tools.backend_migration.rebuild import rebuild


def study(root, name, sid):
    """Create a minimal source folder."""
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "study.json").write_text(json.dumps({"sid": sid, "name": name}))
    (folder / "reference.json").write_text('{"sid":"reference"}')
    return folder


def state(sid="A", **changes):
    """Return a current publication metadata fixture."""
    return dict(
        sid=sid,
        digest="source-digest",
        processing_version="1",
        vocabulary_version="vocabulary-digest",
        current_processing_version="1",
        current_vocabulary_version="vocabulary-digest",
        **changes,
    )


def test_every_folder_accounted_duplicates_never_overwrite(tmp_path):
    """Do not upload either side of an ambiguous study identity."""
    corpus = tmp_path / "corpus"
    study(corpus, "valid", "A")
    study(corpus, "duplicate1", "B")
    study(corpus, "duplicate2", "B")
    bad = study(corpus, "malformed", "C")
    (bad / "study.json").write_text("{")
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        return (
            httpx.Response(201, json={"sid": "A", "digest": "source-digest"})
            if request.method == "PUT"
            else httpx.Response(200, json=state())
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = rebuild(
            corpus,
            "http://local.test",
            tmp_path / "report.json",
            "secret-token",
            client,
        )
    assert len(result["results"]) == 4
    assert {x["path"]: x["status"] for x in result["results"]} == {
        "valid": "published",
        "duplicate1": "blocked",
        "duplicate2": "blocked",
        "malformed": "blocked",
    }
    assert [path for method, path in calls if method == "PUT"] == ["/api/v2/studies/A"]
    assert not result["complete"]


def test_resume_requires_current_remote_versions_and_unchanged_source(tmp_path):
    """Recheck source and server evidence before skipping an upload."""
    corpus = tmp_path / "corpus"
    source = study(corpus, "valid", "A")
    report = tmp_path / "report.json"
    calls = []
    remote = state()

    def handler(request):
        calls.append(request.method)
        return (
            httpx.Response(201, json={"sid": "A", "digest": "source-digest"})
            if request.method == "PUT"
            else httpx.Response(200, json=remote)
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = rebuild(corpus, "http://local.test", report, "secret-token", client)
        assert first["complete"]
        calls.clear()
        second = rebuild(corpus, "http://local.test", report, "secret-token", client)
        assert second["complete"] and second["results"][0]["resumed"]
        assert calls == ["GET"]
        remote["current_processing_version"] = "2"
        calls.clear()
        third = rebuild(corpus, "http://local.test", report, "secret-token", client)
        assert "PUT" in calls
        assert not third["complete"]  # Publication still claims old processing.
        remote["processing_version"] = "2"
        rebuild(corpus, "http://local.test", report, "secret-token", client)
        (source / "reference.json").write_text('{"sid":"changed"}')
        calls.clear()
        rebuild(corpus, "http://local.test", report, "secret-token", client)
        assert "PUT" in calls


def test_interruption_leaves_accounting_for_unattempted_studies(tmp_path):
    """Persist pending entries before any network side effect."""
    import pytest

    corpus = tmp_path / "corpus"
    study(corpus, "first", "A")
    study(corpus, "second", "B")
    report = tmp_path / "report.json"

    def handler(request):
        raise KeyboardInterrupt()

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(KeyboardInterrupt),
    ):
        rebuild(corpus, "http://local.test", report, "secret-token", client)
    saved = json.loads(report.read_text())
    assert len(saved["results"]) == 2
    assert all(x["status"] == "pending" for x in saved["results"])
    assert not saved["complete"]
    assert "secret-token" not in report.read_text()


def test_concurrent_replacement_cannot_be_counted_as_our_publication(tmp_path):
    """Require the published digest to match the upload response."""
    corpus = tmp_path / "corpus"
    study(corpus, "valid", "A")

    def handler(request):
        if request.method == "PUT":
            return httpx.Response(201, json={"sid": "A", "digest": "our-digest"})
        return httpx.Response(200, json=state())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        report = rebuild(
            corpus,
            "http://local.test",
            tmp_path / "report.json",
            "secret-token",
            client,
        )
    assert not report["complete"]
    assert report["results"][0]["status"] == "failed"
