# Local migration performance evidence

One fresh-application run, one excluded warmup, then five sequential measured complete-study replacements per runtime, on the same machine, with identical source hashes and expected read counts. The legacy duration includes the unchanged uploader subprocess, its indexing child, and complete query visibility. The replacement uses one complete-bundle HTTP request and the same visibility probes.

| Runtime | Upload-to-visible median | Upload p95 | Study read median | Output page median | Analysis page median |
| --- | ---: | ---: | ---: | ---: | ---: |
| legacy | 19.8239 s | 19.9043 s | 0.0596 s | 0.0283 s | 0.0214 s |
| py313 | 1.7748 s | 1.8090 s | 0.0123 s | 0.0200 s | 0.0192 s |
| py314 | 1.4851 s | 1.5607 s | 0.0150 s | 0.0168 s | 0.0194 s |

Both replacement versions meet every measured median and nearest-rank p95 budget (legacy value × 1.10), including timecourse and text-search reads. Raw samples, workload paths, input hashes, interpreter versions, and RSS/high-water observations are in the three runtime JSON files. `budget-results.json` records every comparison.

These are development-server measurements: Django runserver versus single-process Uvicorn. Cold observations and warmup are recorded separately from all five measured warm samples. Cold upload-to-visible times were legacy: 20.622 s, py313: 2.809 s, py314: 2.385 s. Cold means a freshly started application with no preparation HTTP request; the study was already published. OS/database/search caches were not forcibly cleared, so there is no controlled cold-cache or production-load claim. Server memory excludes PostgreSQL and the legacy search sidecar. Five observations are a small regression sample, not a robust capacity or tail-latency estimate.

Full-corpus PostgreSQL evidence uses 1,074 published studies and 361,534 measurements. The four actual query profiles and all EXPLAIN ANALYZE/BUFFERS plans are retained in `full-corpus-query-plans.json`: public study search 0.327 s, filtered outputs 0.102 s, same-output predicates 0.064 s, and statistics 0.141 s. These are single observations, not matched full-corpus legacy benchmarks. Study-page SQL statement count is also tested to stay constant as page size grows.

Run with the replacement environment installed:

```bash
python tools/backend_migration/benchmark.py --profile replacement \
  --base-url http://127.0.0.1:8000 --corpus /path/to/Frost2014 \
  --workload workload.json --output metrics.json --runs 5 --cold-start
```

Set `PKDB_API_TOKEN` in the environment. Legacy mode additionally requires `PKDB_LEGACY_CLIENT_PYTHON` and `PKDB_LEGACY_CLIENT_ROOT`; it copies sources before running the unchanged uploader. Each workload entry needs `name`, an `/api/v1/` `path`, and expected `count` or `sid`. Every uploaded SID must have a visibility probe. `--server-pid` enables Linux process-memory observations. Use isolated services: timed runs replace the supplied study SIDs. Source files are hash-checked.

Use `--cold-start` only immediately after restarting the application. Without it, the tool still excludes one warmup but does not label any run cold.
