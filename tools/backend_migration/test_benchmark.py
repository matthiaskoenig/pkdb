"""Benchmark correctness: partial or unsuccessful responses are never success."""

import httpx
import pytest

from tools.backend_migration.benchmark import measure_reads, summarize, wait_visible


def test_visibility_waits_for_complete_expected_rows():
    """Wait for all expected rows rather than any visible result."""
    counts = iter([0, 1, 2])
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"data": {"count": next(counts), "data": []}})

    with httpx.Client(
        base_url="http://example.test", transport=httpx.MockTransport(handler)
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
        httpx.Client(
            base_url="http://example.test",
            transport=httpx.MockTransport(lambda _: httpx.Response(500)),
        ) as client,
        pytest.raises(ValueError, match="outputs"),
    ):
        measure_reads(client, [{"name": "outputs", "path": "/outputs/", "count": 2}])


def test_visibility_timeout_is_bounded():
    """An incomplete index must reach the timeout."""
    times = iter([0, 0, 2])
    with (
        httpx.Client(
            base_url="http://example.test",
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"data": {"count": 1}})
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
        "warm_median_seconds": 2.5,
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
                "--profile",
                "replacement",
            ]
        )


def test_invalid_visibility_request_fails_without_polling():
    """An invalid query cannot become visible by waiting for indexing."""
    with (
        httpx.Client(
            base_url="http://example.test",
            transport=httpx.MockTransport(lambda _: httpx.Response(400)),
        ) as client,
        pytest.raises(ValueError, match="outputs"),
    ):
        wait_visible(
            client,
            [{"name": "outputs", "path": "/outputs/", "count": 2}],
            timeout=0.001,
            sleep=lambda _: None,
        )
