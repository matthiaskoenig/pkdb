"""Benchmark correctness: partial or unsuccessful responses are never success."""

import httpx2
import pytest

from tools.backend_migration.benchmark import measure_reads, summarize, wait_visible


def test_visibility_waits_for_complete_expected_rows():
    """Wait for all expected rows rather than any visible result."""
    counts = iter([0, 1, 2])
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx2.Response(200, json={"data": {"count": next(counts), "data": []}})

    with httpx2.Client(
        base_url="http://example.test", transport=httpx2.MockTransport(handler)
    ) as client:
        wait_visible(
            client,
            [{"name": "outputs", "path": "/outputs/", "count": 2}],
            timeout=1,
            sleep=lambda _: None,
        )
    assert len(seen) == 3


def test_read_failures_cannot_be_reported_as_fast_successes():
    """Reject a fast error response."""
    with (
        httpx2.Client(
            base_url="http://example.test",
            transport=httpx2.MockTransport(lambda _: httpx2.Response(500)),
        ) as client,
        pytest.raises(ValueError, match="outputs"),
    ):
        measure_reads(client, [{"name": "outputs", "path": "/outputs/", "count": 2}])


def test_visibility_timeout_is_bounded():
    """An incomplete index must reach the timeout."""
    times = iter([0, 0, 2])
    with (
        httpx2.Client(
            base_url="http://example.test",
            transport=httpx2.MockTransport(
                lambda _: httpx2.Response(200, json={"data": {"count": 1}})
            ),
        ) as client,
        pytest.raises(TimeoutError),
    ):
        wait_visible(
            client,
            [{"name": "outputs", "path": "/outputs/", "count": 2}],
            timeout=1,
            clock=lambda: next(times),
            sleep=lambda _: None,
        )


def test_summary_retains_all_samples_and_concrete_budget():
    """Keep reproducible samples and explicit comparison budgets."""
    result = summarize([5, 1, 3, 2, 4])
    assert result == {
        "samples_seconds": [5, 1, 3, 2, 4],
        "first_seconds": 5,
        "warm_median_seconds": 3,
        "median_seconds": 3,
        "p95_seconds": 5,
        "budget_median_seconds": 3.3,
        "budget_p95_seconds": 5.5,
    }


def test_each_uploaded_study_requires_a_visibility_probe(tmp_path, monkeypatch):
    """Refuse an incomplete workload before making any mutating request."""
    import json

    from tools.backend_migration import benchmark

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "study.json").write_text(json.dumps({"sid": "TEST1"}))
    workload = tmp_path / "workload.json"
    workload.write_text(
        json.dumps([{"name": "empty", "path": "/api/v1/outputs/", "count": 0}])
    )
    monkeypatch.setenv("PKDB_API_TOKEN", "test-token")

    def forbidden_upload(*args, **kwargs):
        raise AssertionError("Upload attempted without study visibility probe")

    monkeypatch.setattr(benchmark, "send_folder", forbidden_upload)
    with pytest.raises(SystemExit):
        benchmark.main(
            [
                "--base-url",
                "http://127.0.0.1:9",
                "--corpus",
                str(corpus),
                "--workload",
                str(workload),
                "--output",
                str(tmp_path / "metrics.json"),
            ]
        )


def test_invalid_visibility_request_fails_without_polling():
    """An invalid query cannot become visible by waiting for indexing."""
    with (
        httpx2.Client(
            base_url="http://example.test",
            transport=httpx2.MockTransport(lambda _: httpx2.Response(400)),
        ) as client,
        pytest.raises(ValueError, match="outputs"),
    ):
        wait_visible(
            client,
            [{"name": "outputs", "path": "/outputs/", "count": 2}],
            timeout=0.001,
            sleep=lambda _: None,
        )


def test_cold_and_warmup_samples_are_separate_from_five_measured_runs(
    tmp_path, monkeypatch
):
    """Never dilute the warm-run budgets with cold or warmup observations."""
    import json

    from tools.backend_migration import benchmark

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "study.json").write_text(json.dumps({"sid": "S"}))
    workload = tmp_path / "workload.json"
    workload.write_text(
        json.dumps([{"name": "study", "path": "/api/v1/studies/S/", "sid": "S"}])
    )
    output = tmp_path / "metrics.json"
    monkeypatch.setenv("PKDB_API_TOKEN", "test-secret-token")
    calls = []

    def upload(*args, **kwargs):
        calls.append(args[0])
        return {"ok": True}

    monkeypatch.setattr(benchmark, "send_folder", upload)
    original = httpx2.Client
    monkeypatch.setattr(
        benchmark.httpx2,
        "Client",
        lambda **kwargs: original(
            **kwargs,
            transport=httpx2.MockTransport(
                lambda _: httpx2.Response(200, json={"sid": "S"})
            ),
        ),
    )
    assert (
        benchmark.main(
            [
                "--base-url",
                "http://example.test",
                "--corpus",
                str(corpus),
                "--workload",
                str(workload),
                "--output",
                str(output),
                "--cold-start",
            ]
        )
        == 0
    )
    report = json.loads(output.read_text())
    assert len(calls) == 7
    assert len(report["runs"]) == len(report["upload"]["samples_seconds"]) == 5
    assert report["cold"]["phase"] == "cold"
    assert report["warmup"]["phase"] == "warmup"
    assert all(row["phase"] == "measured" for row in report["runs"])
    assert "test-secret-token" not in output.read_text()
