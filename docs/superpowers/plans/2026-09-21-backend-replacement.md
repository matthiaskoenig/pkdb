# Backend Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Django and Elasticsearch with a validated PostgreSQL backend while preserving study inputs and supported clients.

**Architecture:** One FastAPI application hosts REST and FastMCP over shared services. Pure parsing/scientific functions produce canonical records; SQLAlchemy persists a complete study in one transaction. Build the replacement separately until characterization and compatibility gates pass.

**Tech Stack:** CPython 3.13/3.14, uv, Ruff, ty, pytest, Pydantic v2, FastAPI, FastMCP, SQLAlchemy 2, Psycopg 3, Alembic, PostgreSQL, Pint and the existing numerical libraries.

**Spec:** [Approved design](../specs/2026-09-21-backend-replacement-design.md).

## Global Constraints

- Support CPython 3.13 and 3.14 on standard GIL-enabled builds.
- Declare `requires-python = ">=3.13,<3.15"` and Ruff `target-version = "py313"`.
- A study upload completely replaces that study's previous definition.
- Remove Django, DRF, Elasticsearch, and their integration dependencies.
- PostgreSQL serves all filtering, search, sorting, and aggregation.
- The server always performs its own validation.
- Never share a session between requests or threads.
- Existing study SIDs and vocabulary identifiers remain stable.
- Implementation begins only after review of these plans and selection of an execution method.

## Review Focus

1. Missing, zero, NaN, and empty spreadsheet cells retain distinct scientific meanings — foundation F3/F4.
2. Two uploads for a previously absent SID cannot mix children or produce duplicate roots — ingestion I4.
3. A crash between file staging and SQL commit cannot publish missing attachments — ingestion I3/I4.
4. Filter joins cannot leak private studies or match two conditions on different measurements — interfaces A2.
5. Python 3.14 can install successfully while failing scientific calculations or startup — foundation F2/F4 and cutover A6 test execution, not metadata alone.

## Plan boundaries and order

This change spans independently testable subsystems. Execute the following linked
plans in order; do not treat the first phase as completion of the migration.

| Plan | Tasks | Deliverable | Entry requirement |
| --- | --- | --- | --- |
| [01: Foundations](2026-09-21-backend-01-foundations.md) | F1–F4 | Captured contracts and independently tested importer/scientific core on both Pythons | Written-plan review |
| [02: Ingestion](2026-09-21-backend-02-ingestion.md) | I1–I5 | Fresh PostgreSQL schema and authenticated atomic complete-study API | Foundation artifacts and numerical parity |
| [03: Interfaces and cutover](2026-09-21-backend-03-interfaces-cutover.md) | A1–A6 | Compatible reads/writes, MCP, full rebuild, production-ready replacement | Ingestion transaction and authorization gates |

Each task owns its failing test, implementation, passing verification, and focused
commit. Within broad domain tasks, work one entity/rule/route at a time using the
listed test loop. Do not write a whole subsystem before running its first test.
No deployment, production deletion, or automatic merge is part of plan execution.

## Workspace and package transition

- At execution time use an isolated branch/worktree. Existing untracked files
  include `backend/pkdb_data/`, some tests, and `.env.template`; preserve them.
  Inventory their ownership before copying required sources into an isolated
  checkout. Do not sweep them into commits or discard them.
- Characterize the old application in its existing Python 3.9 environment.
  Its current dependencies must not constrain the new interpreter matrix.
- Build a temporary `backend-next/` project with `src/pkdb/`, `tests/`,
  `pyproject.toml`, `uv.lock`, and Alembic. It is a temporary migration directory,
  not a second long-term service. Name its distribution `pkdb` in its isolated
  environment. Never install it alongside the old distribution in one environment.
- Keep the old deployment runnable from its existing checkout/release while
  comparing. In A6 move the replacement into `backend/` and remove obsolete
  tracked code only after parity gates; preserve unrelated/untracked sources.
- Keep private PDFs, source data, credentials, and account exports outside git.
  Commit synthetic fixtures and manifests/hashes where sharing is permitted.

## Dependency and security decisions

Resolve stable releases during F2 and record exact versions in `backend-next/uv.lock`
and `docs/backend-migration/dependencies.md`; versions are not guessed in this
planning document. The resolution/install/import test on both Pythons is the first
executable gate, before schema or ingestion work. Require SQLAlchemy 2.x and
Pydantic 2.x. Add dependencies only in the task that needs them.

Use `pwdlib[argon2]` for password hashing and Python `secrets` for high-entropy
opaque tokens; store token hashes and explicit expiry/revocation state in SQL.
These choices preserve the existing `Authorization: Token ...` contract without
adding JWT, an identity microservice, or a new auth framework. Reset/verification
tokens are single-use and purpose-bound. Email uses configured SMTP with an
injected test transport. Do not send real messages during tests.

Use PostgreSQL 18 as the initial test/deployment major, matching the current test
service. Pin a supported patch image/digest at execution and record it. No new
runtime requires Elasticsearch, even during comparison.

## Test commands and artifact contracts

Run commands from the repository root unless stated otherwise. Tests must use
separate test database credentials; never fall back to production defaults.

```bash
uv run --project backend-next --python 3.13 --locked pytest backend-next/tests -q
uv run --project backend-next --python 3.14 --locked pytest backend-next/tests -q
uv run --project backend-next --locked ruff check backend-next
uv run --project backend-next --locked ruff format --check backend-next
(cd backend-next && uv run --python 3.13 --locked ty check)
(cd backend-next && uv run --python 3.14 --locked ty check)
```

Set ty's project root explicitly in its configuration or run its command from
`backend-next/`; it must not accidentally check the old package. After A6 the
same commands use `backend` instead of `backend-next`. Separate matrix jobs have
separate virtual environments and databases.

Required recorded artifacts:

- `docs/backend-migration/contracts.json`: method/path/query, request/response
  shape, status, permissions, old owner, new owner, test, intentional exceptions.
- `docs/backend-migration/corpus-manifest.json`: file hashes, study counts,
  expected dispositions, fixture provenance; no confidential file contents.
- `docs/backend-migration/dependencies.md`: resolved versions, both-interpreter
  evidence, scientific package compatibility and replacement decisions.
- `docs/backend-migration/performance.json`: baseline hardware, corpus hashes,
  stage timings, peak RSS, query counts, repetitions, and executable budgets.
- `docs/backend-migration/acceptance.md`: every spec requirement mapped to tests,
  corpus results, compatibility exceptions, and release evidence.

Performance policy: five warm measured runs after one warmup, plus a separately
reported cold run. At matched load, new median complete-upload time and p95 read
latency must be no more than 1.10 times the legacy baseline; a larger difference
requires explanation and review, not automatic acceptance. The 10% band is a
noise allowance, not the target. Record absolute baseline values before ingestion
implementation. Measure RSS against the configured memory limit and upload
concurrency; do not infer memory safety from a successful small fixture.

## Specification coverage

| Spec sections | Owning tasks |
| --- | --- |
| 1–3: stack and compatibility evidence, Python support | F1, F2, A6 |
| 4: architecture and domain isolation | F2–F4, I5, A5 |
| 5: schema/ownership/provenance | I1, I2, I4 |
| 6: validation and scientific logic | F3, F4, I2, I5 |
| 7: atomic replacement and files | I3, I4 |
| 8: input/read/write compatibility | F1, F3, A1–A4 |
| 9: PostgreSQL queries and exports | A2, A3 |
| 10: auth, files, MCP | I2, A1, A5 |
| 11: rebuild, bootstrap, deployment | I2, A4, A6 |
| 12: correctness/performance/release gates | All task tests; F1 baselines; A6 integrated evidence |
| 13: staged delivery | This plan index and linked plans |

## Completion and handoff

- [ ] Review all three plans against the specification; approve intentional
  compatibility limits around destructive legacy clients and generated IDs.
- [ ] Choose native execution or subagent-driven task execution.
- [ ] Execute F1–A6 with focused commits and evidence; update completed checkboxes.
- [ ] Review the entire implementation and acceptance report before deployment.

Native execution is recommended initially: contracts, canonical schemas, and the
scientific code have closely coupled interfaces. Review gates remain between
phases, with a final independent review before integration.
