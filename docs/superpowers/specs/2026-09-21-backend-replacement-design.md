---
search:
  exclude: true
---

# PK-DB backend replacement specification

Date: 2026-09-21 Status: Approved for implementation planning, with Python 3.13/3.14 support added at user request. Implementation awaits plan review. Scope: Replace the Django backend with a simpler, validated, reproducible backend.

## 1. Purpose and agreed decisions

Build a fast backend that accepts the existing PK-DB study corpus, preserves its scientific meaning and supported public interfaces, and is straightforward to operate and maintain.

The following decisions were explicitly agreed during design:

- FastAPI and Pydantic form the API and validation foundation.
- Support CPython 3.13 and 3.14 on standard GIL-enabled builds.
- SQLAlchemy 2, Alembic, and PostgreSQL replace Django persistence.
- Use a fresh schema and reupload the complete study corpus from `../pkdb_data/studies`; do not migrate legacy study tables.
- A study upload completely replaces that study's previous definition.
- Remove Django, DRF, Elasticsearch, and their integration dependencies.
- PostgreSQL serves all filtering, search, sorting, and aggregation.
- Expose an MCP server using the same application logic as REST.
- Preserve existing study files and scientific behavior; minimize infrastructure and framework overhead.

The detailed choices below are proposed implementation requirements for review. This is an architectural specification, not an executable implementation plan.

## 2. Current system and compatibility evidence

The current implementation distributes behavior across models, serializers, managers, views, scientific helpers, and an upload client. Replacing the ORM alone would omit substantial behavior.

| Existing location | Behavior to characterize and transfer |
| --- | --- |
| `backend/pkdb_data/management/upload_studies.py` | Folder loading, attachments, source resolution, references, multi-request uploads |
| `backend/pkdb_data/management/tsv.py` | Workbook parsing, sheet conventions, tabular validation, missing values |
| `backend/pkdb_app/studies/serializers.py` | Study relationships, curator formats, duplicate detection, reference rules |
| `backend/pkdb_app/subjects/` | Groups, individuals, hierarchy, characteristics |
| `backend/pkdb_app/interventions/` | Interventions, dosing, files |
| `backend/pkdb_app/outputs/`, `data/` | Measurements, timecourses, subsets, scatter data, normalization, PK calculations |
| `backend/pkdb_app/behaviours.py`, `error_measures.py` | Shared measurement rules and statistical transformations |
| `backend/pkdb_app/info_nodes/`, `backend/pkdb_data/info_nodes/` | Vocabulary, units, choices, annotations, cross-references |
| `backend/pkdb_app/users/`, `storage.py`, `views.py` | Authentication, authorization, protected files |
| `backend/pkdb_app/studies/views.py`, `statistics.py`, `urls.py` | Search, filtering, downloads, statistics, API surface |
| `backend/tests/` and frontend API consumers | Existing expectations and regression evidence |

For example, `apixaban/Frost2021a/study.json` contains `source: "TabGroups"`, `count: "col==group_count"`, and `mean: "col==mean"`. These are importer instructions, not scalar measurement values. Preserve their interpretation, associated workbook conventions, image resolution, and reference handling.

The existing uploader creates files and references, POSTs a study core, PATCHes related sets, and calls `update_index/`. It also has delete-before-upload and failure-cleanup paths. An unchanged destructive client cannot provide the new atomic replacement guarantee; section 8 explicitly defines this boundary.

## 3. Technology and operational footprint

| Concern | Selected design |
| --- | --- |
| Project management | uv, one backend `pyproject.toml`, committed `uv.lock` |
| Quality | Ruff for lint/format/imports, ty for type checking, pytest |
| REST | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Persistence | SQLAlchemy 2 typed declarative models, Psycopg 3, PostgreSQL |
| Schema changes | Alembic, including an initial clean-schema migration |
| MCP | Standalone FastMCP mounted in the same ASGI application |
| Science | Preserve required Pint, NumPy, SciPy, and PK analysis behavior |
| Tabular input | Preserve existing pandas-based interpretation initially |
| Attachments | Persistent filesystem volume, metadata in PostgreSQL |
| Diagnostics | Structured logs, request IDs, stage timings and query counts |

Support CPython 3.13 and 3.14 on standard GIL-enabled builds. Declare `requires-python = ">=3.13,<3.15"` and Ruff `target-version = "py313"`. Use Python 3.14 as the default development and deployment interpreter; 3.13 is an equally required supported target. Free-threaded builds and Python 3.15 are outside this support contract. Do not use Python 3.14-only syntax or standard-library APIs without a tested Python 3.13-compatible path.

Resolve and lock stable dependencies that install and run on both interpreters, including compiled numerical, database, validation, and spreadsheet dependencies. Test installation, package build, CLI/API startup, scientific behavior, PostgreSQL integration, MCP, and container builds on both versions. Run Ruff and ty with the minimum supported language version and run type checking in both environments. An unavailable dependency on either interpreter blocks release; do not silently skip that matrix entry or lower the support promise. Preserve the legacy runtime in a separate environment for characterization rather than forcing Django 3.1 onto these interpreters. Remove obsolete Django-specific stubs and test plugins at retirement.

Run one application deployment and one PostgreSQL service, plus persistent file storage. Multiple Uvicorn processes may serve the same application. Start without Redis, Celery, a message broker, external search, or a generic repository framework. Do not introduce SQLModel or a second validation framework. Polars is deferred unless profiling establishes a concrete benefit that justifies an importer change.

Use synchronous SQLAlchemy sessions and explicit transaction scopes initially. REST blocking handlers run through FastAPI's thread-pool support; async MCP handlers offload blocking service calls using the framework's supported mechanism. Never share a session between requests or threads. CPU-heavy scientific work must not execute on the ASGI event loop. Bounded upload concurrency protects memory and database capacity; introduce process-based compute only if measurements require it.

## 4. Application structure

Use one Python package with focused modules:

```text
pkdb/
  app.py             # application composition and lifecycle
  config.py
  schemas/           # input, canonical records, reports, response models
  importers/         # folder/workbook/tabular parsing and legacy adapters
  domain/            # scientific rules, vocabulary, units, calculations
  services/          # validate, replace, query, export, authorize
  db/                # SQLAlchemy models, sessions, explicit SQL operations
  api/               # REST routes, legacy response adapters
  mcp/               # small explicit MCP tool surface
  files/             # staging, protected reads, cleanup
  cli.py             # upload, validation, bootstrap and maintenance commands
```

REST and MCP are thin adapters over the same services. The CLI uploads through REST; local validation may reuse the pure parsing and domain code. The server always performs its own validation. Domain functions must not import FastAPI, FastMCP, Django, or SQLAlchemy. Pydantic input schemas remain separate from ORM models and public response schemas.

Prefer plain functions and explicit SQL to abstraction layers. Introduce an interface only when there are multiple actual implementations or a concrete testing need.

## 5. New schema and ownership

Use relational tables for queryable scientific entities and explicit foreign keys. Do not store the complete scientific graph solely as JSONB.

Required entity families:

- Studies, references, ordered authors, curator ratings, collaborators, descriptions, comments, and study attachment associations.
- Groups and parent relationships, individuals and memberships, characteristics.
- Interventions and their subject/output associations.
- Reported measurements, normalized measurements, derived PK outputs, timecourses, timecourse points, scatter/subset relationships.
- Vocabulary nodes, allowed choices, units, substances, synonyms, annotations, cross-references, and hierarchy edges.
- Users, roles, authentication credentials, and file metadata.

Keep scientific measurements in typed columns, including applicable value, mean, median, minimum, maximum, SD, SE, CV, count, units, and measurement type. Preserve missing-value meaning and floating-point behavior. Use explicit source and derivation relationships to distinguish reported, normalized, and calculated records. Retain original units and values and identify calculation/normalization versions. JSONB is appropriate for source manifests and diagnostic details.

The study SID is its stable public identity. Replacement retains the study root and replaces all study-owned children and associations transactionally. Omitted optional sets become empty; omission never means retain the old set. Shared users and vocabulary are not deleted. References and authors retain their existing uniqueness/association semantics, characterized before implementation.

Use indexed ownership keys, foreign keys, uniqueness constraints, and meaningful check constraints. Enforce study-local relationships with constraints where possible and domain checks otherwise. Timecourse points retain explicit order; values and time coordinates cannot become misaligned.

Legacy numeric row IDs may change after a rebuild or replacement. Responses must remain internally consistent, but old database-generated IDs are not permanent identities. Existing study SIDs and vocabulary identifiers remain stable. Record this compatibility limit in release notes and client documentation.

## 6. Validation and scientific processing

One pipeline serves dry-run validation and committed replacement:

1. Authenticate and authorize; enforce request/file size and count limits.
2. Parse input and resolve workbook/tabular expressions into canonical records.
3. Validate structure with Pydantic: required keys, permitted keys, types, null/missing semantics, and supported discriminated record variants.
4. Load required vocabulary, users, and shared identifiers in bounded queries.
5. Validate the study graph: duplicates, unresolved references, hierarchy cycles, invalid group/individual associations, interventions, and attachment links.
6. Validate scientific constraints: dimensions, measurement-specific choices, statistics, counts, timecourse shape, and calculation prerequisites.
7. Normalize and calculate using the transferred scientific functions. Validate generated results as well as reported inputs.
8. Return a report or persist the validated graph atomically.

Perform database lookups outside Pydantic field validators. Reuse vocabulary maps, unit registries, and type adapters where safe; bound caches and invalidate them when their underlying vocabulary version changes. Do not query once per row. Parsing or normalization must never evaluate spreadsheet expressions as Python.

An error report contains severity, stable rule code, message, study SID, input path, and file/sheet/row/column coordinates when available. Preserve provenance through transformation so scientific errors can point back to their source. Collect independent actionable errors up to a documented cap, reporting truncation. Do not fabricate coordinates for errors without a source location.

Existing scientific validation remains required. Additional quality rules that would reject previously valid corpus entries initially produce warnings, unless the condition prevents safe interpretation or database integrity. Explicit legacy coercions belong in the importer; canonical records do not silently accept arbitrary coercion. Never weaken established integrity rules just to pass a corpus.

Dry-run validation writes no published study data and cleans temporary uploads. It cannot guarantee a later commit succeeds: recheck permissions and mutable database-dependent invariants in the write transaction.

## 7. Complete replacement and attachment lifecycle

Provide a new `PUT /api/v2/studies/{sid}` operation accepting a complete multipart bundle: study JSON, reference JSON, and named files. The path SID must match the payload SID. The input can represent the current folder without editing its files. Provide `POST /api/v2/studies/validate` using the same bundle format.

Replacement procedure:

1. Stage files and validate/prepare the complete study before deleting anything.
2. Begin a database transaction and acquire a per-SID transaction lock, including for a previously absent SID. Recheck write authorization and relevant reference constraints under the transaction's concurrency policy.
3. Retain/create the study root; delete previous study-owned records and insert the replacement in dependency order using batch operations.
4. Persist source provenance, warnings, content digest, and version metadata.
5. Commit and return the completed result. Success means the study is queryable.

Same-SID replacements serialize; different studies can proceed concurrently. The last successfully committed authorized replacement wins. Identical uploads must not accumulate duplicate scientific records. A digest-based fast path is optional and must include vocabulary and scientific processing versions.

Any validation, computation, or SQL failure before commit leaves the previously published study intact. Initial upload failure leaves no published study. Reads must not assemble mixed old/new children: multi-query detail/export reads use a consistent database snapshot. An explicit DELETE is separate and really deletes.

Store new attachment bytes durably at immutable paths before committing their database references. Paths are server-generated, never trusted client paths. Uncommitted files remain inaccessible. Commit activates the new associations; old attachments are not removed before that commit. A maintenance command removes unreferenced files after a grace period, protecting active uploads and reads. Recovery tests cover crashes before and after commit. The filesystem and database are not one transaction; this protocol prevents broken references without a queue.

Use ordinary SQLAlchemy bulk inserts first. PostgreSQL COPY with staging tables is an optional measured optimization, not a requirement for initial correctness.

## 8. Compatibility contract

### Study input and scientific outputs

The existing folder corpus, including apixaban, must work without source edits. Preserve JSON aliases, curator encodings, workbook headers, skipped/comment rows, NA conventions, source expressions, units, and filename resolution. Preserve calculation outputs within explicit quantity-specific numeric tolerances.

### Public reads

Retain supported `/api/v1/` routes, response shapes, field names, null handling, query parameters, pagination envelopes, downloads, statistics, and permissions. Inventory actual routes and frontend/client usage into a contract matrix before coding their replacements. Include studies, references, subjects, interventions, outputs, subsets, info nodes, `pkdata/*`, `filter/`, statistics, and protected media. Record expected status/error behavior per route; do not expose FastAPI defaults where they would break an existing client.

### Existing multi-request write protocol

The maintained upload CLI switches to the complete-bundle endpoint and stops deleting studies before replacement. This change is necessary for the atomic replacement guarantee and does not require editing study source files.

Provide a narrow compatibility adapter for the existing core-POST/set-PATCH sequence: store unpublished drafts in PostgreSQL keyed by authenticated actor and study SID. Stage legacy reference/file writes with the same authorization checks; never modify a published reference in advance of publication. Draft reads from write endpoints are restricted to their owner. Reject overlapping ambiguous same-actor/same-study uploads rather than mixing their payloads. Abandoned drafts expire through a maintenance command.

The legacy `POST /api/v1/update_index/` route finalizes the draft using the same complete validation/replacement service. If no draft exists, it verifies access and returns the compatible success result for an existing study. It performs no external indexing. Implement only characterized request variants; reject unknown actions explicitly. Validation errors never report publication success.

This preserves the standard legacy upload sequence, but intentionally changes partial-write visibility: public reads see only completed studies. Document this boundary. Standalone legacy PATCH clients must finalize their draft or upgrade. An old client's explicit DELETE remains destructive; no server can preserve the deleted study on a later failed upload while also honoring DELETE semantics. Therefore unmodified delete-before-upload clients are not covered by the atomic replacement guarantee. This exception must be visible in upgrade guidance.

## 9. PostgreSQL search and exports

Translate existing filters to parameterized SQL with an explicit allowed field and operator registry. Implement nested relationship filters carefully: predicates that refer to one measurement must match the same measurement row. Apply study visibility before counts, facets, statistics, downloads, and pagination.

Use B-tree indexes for exact/range filters and joins. Use PostgreSQL text search with GIN indexes where full-text behavior is required; add pg_trgm only for an identified substring/fuzzy contract. Maintain any search vectors in the same database transaction. There is no external index, synchronization process, or eventual-consistency dependency.

Preserve membership/filter semantics and documented ordering. Exact Elasticsearch relevance scores are not a compatibility target; document any relevance-order change and use deterministic tie-breaks. Benchmark representative joins and aggregations with PostgreSQL query plans before adding denormalized tables.

Preserve download schemas, filenames/content types where clients rely on them, unit conventions, and relationship consistency. Stream large exports within a consistent snapshot. Support existing saved-filter/download identifiers using PostgreSQL records if the contract inventory confirms their use; recheck access on every download and expire records without Redis.

## 10. Authentication, authorization, and MCP

Preserve functional account creation, login, token authentication, verification, reset, roles, curator/collaborator relationships, and protected media behavior used by clients. Implement account flows with maintained security primitives; do not implement password hashing or token cryptography from scratch. Keep the existing client-facing token contract where required. Select the concrete auth dependency during the implementation plan against the characterized flows.

Port intended permissions rather than blindly copying accidental method handling. For example, legacy code treats PUT alongside safe methods; the replacement must authorize every mutation as a write. Include anonymous, basic, reviewer, curator, creator, collaborator, and administrator cases in an explicit policy matrix. File access must satisfy both study visibility and applicable licence/role rules. Policy corrections that tighten legacy behavior must be documented and tested.

Expose explicit MCP tools for search, study retrieval, validation, and complete replacement. Use the same principal, authorization service, schemas, transactions, and error codes as REST. Large uploads use owned, staged attachment handles rather than embedding PDFs or spreadsheets in tool arguments. Handles cannot grant access to another user's files. The MCP mount has authenticated transport and does not automatically expose every REST route as a tool.

## 11. Rebuild, bootstrap, and deployment

Rebuild sequence:

1. Create PostgreSQL schema with Alembic.
2. Load versioned vocabulary, unit definitions, and required reference data.
3. Bootstrap roles and user identities referenced by studies from explicit input.
4. Validate and upload the corpus with bounded concurrency and a resumable report.
5. Compare counts, relationships, scientific results, and API behavior.
6. Switch application traffic after acceptance checks and operational review.

User identity bootstrap must not assign working passwords automatically. Existing tokens need not survive the fresh rebuild; communicate reauthentication. Study folders may not contain all accounts, comments, ratings, or permissions currently in production. Before cutover, inventory database-only content and either include it in an explicit bootstrap/export input or obtain an explicit decision to discard it. Rebuilding studies is not authorization to lose unrelated user data.

The new application can run alongside the old deployment for comparison without sharing writes. It never depends on an Elasticsearch service. Keep the previous deployment and backups available for rollback; after new writes begin, rollback requires accounting for those writes, not merely switching traffic.

At retirement remove Django/DRF/Elasticsearch runtime code and dependencies, obsolete index commands, settings, containers, environment variables, CI services, and deployment documentation. Alembic remains for future schema evolution. Provide readiness/liveness checks and documented database/file backup and restore.

## 12. Performance and verification requirements

Do not claim a speedup from framework choice alone. Establish an executable baseline using the existing uploader and representative read/query workloads, then measure the replacement on the same hardware and input versions.

Benchmark the apixaban corpus, large timecourses, large study graphs, invalid inputs with many errors, repeat replacements, concurrent distinct studies, and conflicting same-SID writes. Record wall time, CPU, peak memory, database statement count, rows/sec, attachment bytes, and p50/p95 read latency. Separate workbook parsing, validation, scientific calculations, persistence, and response encoding. Compare time until data is actually queryable, not merely upload acknowledgement.

Before implementation of the ingestion path, record numerical acceptance budgets in the implementation plan from this baseline. The design sets these minimum requirements: no unexplained regression on matched representative workloads, bounded memory relative to configured study limits/concurrency, and no per-record database lookup pattern. Optimize measured bottlenecks while retaining validation.

Acceptance gates:

- Every inventoried backend behavior has a destination and regression test, or a documented intentional removal approved as part of compatibility review.
- Apixaban uploads without file edits; the full corpus has an explicit result for every study and no unexplained loss or silent skipped records.
- Structurally/scientifically invalid inputs fail with actionable diagnostics.
- Existing valid calculations match characterized results within declared tolerances; normalization preserves original data and provenance.
- Replacement removes omitted old children; identical uploads do not duplicate data; validation/SQL failures retain the previous study.
- Concurrent readers/writers and attachment crash recovery satisfy section 7.
- API/frontend contract tests cover filters, pagination, exports, errors, and account/file access. REST and MCP enforce equivalent domain permissions.
- Real PostgreSQL integration tests cover constraints and transactions; SQLite is not used as a substitute for these tests.
- Python 3.13 and 3.14 both pass clean locked installation, package/container builds, CLI/API/MCP startup, scientific regression, and PostgreSQL tests.
- Ruff, ty, unit tests, contract tests, scientific regression tests, and measured performance budgets pass in CI or a reproducible benchmark environment.
- A clean deployment, full rebuild, backup restore, and rollback rehearsal work without Django or Elasticsearch in the new runtime.

## 13. Delivery boundaries

Implement in reviewable stages, each maintaining executable evidence:

1. Behavior/contract inventory, corpus manifest, and performance baseline.
2. Pure importer, canonical schemas, scientific validation/calculation parity.
3. Fresh schema, bootstrap, atomic replacement, attachment lifecycle.
4. PostgreSQL queries, REST compatibility, auth, exports, and legacy upload adapter.
5. MCP tools, end-to-end corpus rebuild, performance work, and deployment cutover.
6. Retire legacy runtime and verify a clean independent installation.

Do not start implementation from this specification alone. Review this written design, then produce an implementation plan with concrete files, test cases, dependency versions, endpoint contracts, performance budgets, and execution order.

## 14. Technical references

- [uv project management](https://docs.astral.sh/uv/)
- [Ruff](https://docs.astral.sh/ruff/) and [ty](https://docs.astral.sh/ty/)
- [Pydantic performance](https://docs.pydantic.dev/latest/concepts/performance/)
- [FastAPI concurrency](https://fastapi.tiangolo.com/async/)
- [SQLAlchemy bulk DML](https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html)
- [Alembic migration review](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html)
- [FastMCP integration](https://gofastmcp.com/integrations/fastapi)
