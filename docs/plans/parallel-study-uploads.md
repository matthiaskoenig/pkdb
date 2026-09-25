# Parallel study uploads for the Python tool

Status: core implementation available (2026-09-25). `--jobs`, version-3 journals,
`--resume`, shared publication identity locks, one-shot private snapshots, and
client/server timing instrumentation are implemented. The benchmark driver is
`scripts/benchmark_batch_upload.py`; usage and recovery are documented in
`python/README.md`. Real HTTP process-worker overlap and PostgreSQL identity-lock,
revocation, and serial/parallel equivalence tests cover the core contracts.

Remaining measurement work: run representative small/medium/large source corpora
at jobs 1/2/4/8, recording server CPU, lock waits, memory, temporary disk and
connection use for fresh imports and replacements. No deployment speedup or
higher default worker count is claimed before those measurements. The original
implementation sequence below records the design and its broader test matrix.

## Objective

Load a complete source-study collection quickly and reproducibly through the existing study upload API. Preserve per-study atomic publication, validation, access checks, source integrity, and honest reporting of uncertain outcomes. Do not promise a linear speedup before measuring client CPU, server CPU, database lock waits, disk, and network throughput.

## Findings in the current code

- `python/src/pkdb/cli.py` discovers study folders and processes them sequentially. Each study gets a new Client, compatibility request, and connection pool.
- `prepare()` snapshots, hashes, parses, and validates a study. `Client.upload(prepared)` snapshots and validates again to detect changes and avoid trusting mutable prepared objects. The server independently validates the source. Optimization must preserve these guarantees.
- Client state includes `progress`, `last_upload_report`, and cached vocabulary. Do not share one Client between concurrent tasks.
- Terminal progress has one mutable current study/stage. Batch reporting assumes completed studies form a prefix of discovered folders. Both assumptions must change.
- The server already dispatches ingestion through a thread pool and publishes under a per-study advisory lock and a shared vocabulary lock.
- Publication revalidates identity with exclusive locks on both the account and credential rows. These locks remain held during publication: independent studies uploaded by one account serialize at this stage, even with multiple API keys.
- Reference ownership is unique. Duplicate study SIDs and incompatible reference reuse need explicit batch diagnostics.
- The publication-state endpoint and curation outcome reconciliation provide a starting point for safe resume.
- The default local Compose command starts one API worker; client concurrency alone cannot guarantee CPU-parallel server validation.

## Proposed interface

```bash
pkdb upload ./studies --endpoint https://example.org \
  --jobs 4 --report ./deployment-upload.json

pkdb upload ./studies --endpoint https://example.org \
  --jobs 4 --resume ./deployment-upload.json
```

Keep `PKDB_API_KEY` in the environment. Default `--jobs` to 1 for compatibility. Reject zero/negative values; initially expose one concurrency setting rather than separate parse/network pools. Preserve `--fail-fast` and JSON output. Add a reusable `upload_many()` batch API with typed options, study results, and progress events; single-study `Client.upload()` remains supported.

## Architecture choices

| Choice | Assessment |
| --- | --- |
| Bounded thread pool | Smallest initial change; overlaps transfers and server waits. Benchmark as a baseline, but it does not provide Python CPU parallelism for local parsing/validation on a normal GIL-enabled runtime. |
| Bounded process pool | Recommended target for full-corpus loading: each worker prepares and uploads one study at a time, isolating Client state and allowing local CPU parallelism. Higher memory/startup cost must be measured. |
| Async HTTP rewrite | Defer: it does not solve CPU-bound preparation and would enlarge the synchronous client API change. |
| Bulk HTTP endpoint or direct SQL import | Defer: keep existing per-study transactions and validation contracts. |
| Restore a validated database plus attachment snapshot | Separate deployment workflow worth considering when repeatedly deploying an identical, schema-compatible collection. It is not a substitute for ingestion when source data or processing rules change. |

Process workers receive paths and serializable configuration, and construct their own reusable Client and pinned vocabulary. Keep PreparedBundle objects, file handles, and temporary snapshots inside the worker. Use a spawn-compatible entry point; never inherit open HTTP/database connections. The parent alone renders output and writes reports.

## Implementation sequence

### 1. Establish a measured baseline

Instrument preparation, transfer, server validation, and transaction/publication separately. Benchmark a representative small/medium/large corpus with jobs 1, 2, 4, and 8. Measure studies/minute, total duration, peak resident memory, temporary disk consumption, database connection use, lock waits, and server CPU. Measure fresh imports and replacements separately. Use identical sources, vocabulary, processing versions, and server resources.

### 2. Make independent backend publications concurrent

Add an explicit publication read-lock mode to identity revalidation. Evaluate shared row locks for the uploader and credential, while keeping exclusive locks in account/key mutation flows. Preserve ordering (user before credential), live revocation/role checks, study serialization, reference ownership, and vocabulary consistency. Audit API-key last-used updates, reference creation, attachment deduplication/cleanup, and all locks acquired later in publication for contention or lock upgrades.

Use real overlapping PostgreSQL transactions to prove that distinct studies with the same key can publish concurrently, while same-SID writes serialize. Test concurrent revocation, account disabling/role changes, shared references, identical attachments, vocabulary changes, and transaction failure. Do not remove identity locks without preserving the existing authorization guarantees. Make API worker count configurable if benchmarks show server CPU saturation; budget database connections across all workers.

### 3. Extract a single-study runner and add bounded scheduling

Move per-study execution/result construction out of `cli.main()` into a batch module. Maintain the existing sequential behavior through that runner first. Add process workers behind `--jobs`, with no more than the configured number of active studies and a bounded pending queue. Do not prepare the entire corpus in memory. Preflight endpoint capabilities and pinned vocabulary once; retain compatibility headers and server-side checks on every write. Detect duplicate SIDs before writes; report reference conflicts before submission where feasible.

Record stage and persistence state per task, not in the terminal. Use one parent event queue for progress and completion. JSON output emits complete result objects with SID/path; completion order may differ from input order. The final report orders results deterministically by discovery index.

### 4. Preserve failure, interrupt, and resume semantics

Journal each task as queued, preparing, submitting, confirmed, failed, or unknown. Persist the submitting state before network dispatch so a crash cannot turn a possibly committed write into an apparently untouched task. The coordinator writes atomic checkpoints and records endpoint, source identity, source digest, vocabulary/processing versions, request IDs, and confirmed publication digest. Never persist API keys.

Ordinary validation failures may continue unless `--fail-fast` is set. Compatibility/authentication errors, systemic server failures, or unknown persistence stop new submissions. Drain already active requests and report their actual outcomes; fail-fast cannot undo committed studies. On interrupt, stop scheduling, allow a bounded graceful drain, then classify outstanding writes conservatively. An unsuccessful report write also stops new submissions. Track unattempted tasks by identity, not by slicing a completed-result count.

Resume validates endpoint and input identity, rechecks the current server publication for prior successes, and skips only matching source and processing/vocabulary identities. Reconcile unknown writes through the publication endpoint before considering another PUT. If the published identity cannot establish the outcome, stop that study for explicit resolution; do not blindly retry. Reuse the curation reconciliation logic through a shared client method. Extend publication metadata if needed for an unambiguous version/hash comparison.

### 5. Optimize preparation after concurrency works

Add an internal one-shot path that snapshots source files once, validates that private snapshot, and uploads those exact bytes while its lifetime is still active. Avoid retaining a mutable PreparedBundle as trusted evidence. Keep the public prepare-then-upload path's mutation detection and independent server validation. Cache compatibility information only within the batch contract, with server checks authoritative throughout. Benchmark these changes separately from concurrency.

### 6. Test, document, and choose deployment defaults

Test job limits, worker isolation, duplicate inputs, out-of-order completion, interrupted/crashed workers, source changes, cancellation, resume on changed or missing publications, no automatic retries of ambiguous writes, redaction, and sequential compatibility. Include real HTTP subprocess-worker tests and PostgreSQL concurrency tests, plus exact serial/parallel comparisons of published study digests and record counts.

Document the distinction between client jobs and server workers, resource requirements, partial batch success, report recovery, and compatible database initialization. Recommend a measured setting, initially trying four jobs, without silently choosing concurrency from CPU count alone. Deliver in reviewable changes: backend concurrency; batch scheduler/progress; durable resume; snapshot optimization and benchmarks.

## Reference behavior

Python process pools require serializable arguments/results and support explicit worker limits: https://docs.python.org/3.14/library/concurrent.futures.html

PostgreSQL shared row locks can coexist, while conflicting updates wait; lock-mode and ordering choices need concurrency tests: https://www.postgresql.org/docs/17/explicit-locking.html
