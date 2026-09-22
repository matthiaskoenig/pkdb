# Local migration performance evidence

Five sequential complete-study replacements per runtime, on the same machine,
with identical source hashes and expected read counts. The legacy duration includes
the unchanged uploader subprocess, its indexing child, and complete query visibility.
The replacement uses one complete-bundle HTTP request and the same visibility probes.

| Runtime | Upload-to-visible median | Upload p95 | Study read median | Output page median | Analysis page median |
| --- | ---: | ---: | ---: | ---: | ---: |
| legacy | 19.1880 s | 21.1865 s | 0.0578 s | 0.0281 s | 0.0234 s |
| py313 | 1.7529 s | 1.7833 s | 0.0107 s | 0.0169 s | 0.0181 s |
| py314 | 1.4829 s | 1.5398 s | 0.0124 s | 0.0168 s | 0.0170 s |

Both replacement versions meet every measured median and nearest-rank p95 budget
(legacy value × 1.10), including timecourse and text-search reads. Raw samples,
workload paths, input hashes, interpreter versions, and RSS/high-water observations
are in the three runtime JSON files. `budget-results.json` records every comparison.

These are development-server measurements: Django runserver versus single-process
Uvicorn. First observations and subsequent warm medians are retained; caches were
not forcibly cleared, so there is no controlled cold-cache or production-load claim.
Server memory excludes PostgreSQL and the legacy search sidecar. Five observations
are a small regression sample, not a robust capacity or tail-latency estimate.

Full-corpus PostgreSQL evidence uses 1,074 published studies and 361,534 measurements.
The four actual query profiles and all EXPLAIN ANALYZE/BUFFERS plans are retained in
`full-corpus-query-plans.json`: public study search 0.327 s, filtered outputs 0.102 s,
same-output predicates 0.064 s, and statistics 0.141 s. These are single observations,
not matched full-corpus legacy benchmarks. Study-page SQL statement count is also
tested to stay constant as page size grows.

Run with the replacement environment installed:

```bash
python tools/backend_migration/benchmark.py --profile replacement \
  --base-url http://127.0.0.1:8000 --corpus /path/to/Frost2014 \
  --workload workload.json --output metrics.json --runs 5
```

Set `PKDB_API_TOKEN` in the environment. Legacy mode additionally requires
`PKDB_LEGACY_CLIENT_PYTHON` and `PKDB_LEGACY_CLIENT_ROOT`; it copies sources before
running the unchanged uploader. Each workload entry needs `name`, an `/api/v1/`
`path`, and expected `count` or `sid`. Every uploaded SID must have a visibility
probe. `--server-pid` enables Linux process-memory observations. Use isolated
services: timed runs replace the supplied study SIDs. Source files are hash-checked.
