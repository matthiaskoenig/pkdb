# Backend Interfaces and Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver compatible client interfaces, MCP, and a verified corpus rebuild, then retire the legacy runtime.

**Architecture:** Thin REST/MCP adapters use the ingestion, authorization, and query services. PostgreSQL owns all queryable state, including temporary legacy drafts and saved exports. Replacement remains a single application deployment.

**Tech Stack:** FastAPI, FastMCP, Pydantic v2, SQLAlchemy 2, PostgreSQL, HTTPX, pytest, uv/Ruff/ty, Python 3.13 and 3.14.

**Spec:** [Backend design](../specs/2026-09-21-backend-replacement-design.md). Depends on [ingestion](2026-09-21-backend-02-ingestion.md); read the [index](2026-09-21-backend-replacement.md).

## Global Constraints

- Support CPython 3.13 and 3.14 on standard GIL-enabled builds.
- Declare `requires-python = ">=3.13,<3.15"` and Ruff `target-version = "py313"`.
- PostgreSQL serves all filtering, search, sorting, and aggregation.
- Remove Django, DRF, Elasticsearch, and their integration dependencies.
- A study upload completely replaces that study's previous definition.
- Existing study SIDs and vocabulary identifiers remain stable.
- Public reads see only completed studies.

## Review Focus

1. Two predicates accidentally match different related measurements — A2.
2. Private studies leak through counts, aggregates, files, or saved downloads — A1–A3.
3. A legacy finalization retry publishes an incomplete draft — A4.
4. MCP exposes an upload or file handle under a different principal — A5.
5. A rebuild succeeds but omits private corpus/account content or breaks one Python image — A6.

## File and interface map

- `src/pkdb/api/`: `accounts.py`, `media.py`, `reads.py`, `exports.py`, `legacy_uploads.py`, `staging.py`.
- `src/pkdb/services/`: `accounts.py`, `queries.py`, `exports.py`, `drafts.py`.
- `src/pkdb/db/`: `queries.py`; models for draft/saved-query state added explicitly.
- `src/pkdb/schemas/`: `queries.py`, `accounts.py`, `legacy.py`.
- `src/pkdb/mcp/`: `server.py`, `authentication.py`.
- `src/pkdb/cli.py`; `src/pkdb/commands/`: `upload.py`, `bootstrap.py`, `cleanup.py`.
- Deployment: Dockerfile, replacement test compose, existing develop/production compose at cutover, CI workflows, `docs/development.md`, `backend/README.md`.

### A1: Preserve account and protected-media contracts

**Files:** Create API account/media and service/schema account modules above; `tests/api/test_accounts.py`, `tests/api/test_media.py`; extend user/token models and add reviewed Alembic migration. Update contract matrix account rows.

**Interfaces:** `AccountService(session_factory, mailer)` supports `login(username: str, password: str) -> str`, `request_reset(email: str) -> None`, `complete_reset(token: str, new_password: str) -> None`, and `verify_email(token: str) -> None`. `Mailer.send(recipient: str, subject: str, body: str) -> None` is injected; tests use a recording fake, runtime uses SMTP. Registration uses the exact fields captured in F1 and creates no elevated role. `account_service`, `account_user`, and `mailbox` fixtures create a test user, service and fake mailbox. New opaque tokens reuse I2's storage policy.

- [ ] Write the one-use reset test:

```python
import pytest
from pkdb.services.authentication import AuthenticationFailed

def test_reset_token_cannot_be_reused(account_service, account_user, mailbox):
    account_service.request_reset(account_user.email)
    token = mailbox.reset_token_for(account_user.email)
    account_service.complete_reset(token, 'New-test-password-42!')
    with pytest.raises(AuthenticationFailed):
        account_service.complete_reset(token, 'Another-test-password-43!')
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/api/test_accounts.py -q`; expect missing service. Implement transactions for token consumption, expiry, purpose checking and password updates. Revoke sessions on reset. Use I2's Argon2 hashes and constant-shape responses for unknown reset emails. Add PostgreSQL-backed bounded login/reset throttling, tested with an injected clock; keep its state small and expirable rather than introducing Redis.
- [ ] Add legacy login/token/account routes with exact F1 payload/error shapes; preserve browser Authorization headers. Test valid, incorrect, expired, revoked, disabled-user, duplicate account, and registration privilege-escalation cases. Sending email occurs through the injected transport; failures return a retryable result and do not leave an unusable account or publish a success falsely.
- [ ] Serve `/media/...` via authenticated lookup and `FileStore`, never raw file path concatenation. Tests cross every role/access/licence matrix cell, including filenames guessed from another study and Range/download behavior if present in the contract. Browser-facing CORS/CSRF behavior follows the auth transport; cookie-backed sessions require CSRF checks if retained by the contract.
- [ ] Run both interpreter API suites; commit as `feat: preserve account flows and protected attachment access`.

### A2: Implement PostgreSQL read/search/filter/statistics contracts

**Files:** Create `schemas/queries.py`, `services/queries.py`, `db/queries.py`, `api/reads.py`, `tests/api/test_read_contracts.py`, `tests/integration/test_filters.py`, `tests/integration/test_statistics.py`. Create reviewed query-index migrations and update each owned contract row.

**Interfaces:** `QuerySpec` has entity, typed predicates, search text, sort, page and page_size; its parser accepts only F1's allowed field/operator mappings. `Page` has items, count, next and previous. `QueryService(session_factory)` provides `search(query: QuerySpec, principal: Principal) -> Page` and `statistics(principal: Principal) -> dict[str, int]` for characterized count keys. `crossed_measurements` fixture seeds study X with (substance A,value 1) and (substance B,value 10), and study Y with (substance A,value 10).

- [ ] Write the relationship semantics test:

```python
from pkdb.schemas.queries import QuerySpec, Predicate

def test_predicates_bind_to_same_measurement(queries, crossed_measurements, creator):
    query = QuerySpec(entity='studies', predicates=[
        Predicate(field='outputs.substance', operator='eq', value='A'),
        Predicate(field='outputs.value', operator='gte', value=10),
    ])
    page = queries.search(query, creator)
    assert [item['sid'] for item in page.items] == ['Y']
```

  Define `queries` fixture as `QueryService(session_factory)` and model Predicate values as the allowed scalar/list union. Query responses are serialized mappings according to each entity's explicit Pydantic response schema.
- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/integration/test_filters.py -q`; expect missing query layer. Implement parameterized predicates with correct join scopes/EXISTS; apply allowed study visibility before count, limit, sorting, statistics, and aggregation. Whitelist sort columns, null ordering, and tie-break by stable key. Clamp/validate page limits according to F1 contracts.
- [ ] Work through contract rows for studies/references/groups/individuals, interventions/outputs/subsets/info_nodes and statistics one route at a time: add a failing golden request, implement its query/response adapter, rerun it. Include empty results, duplicate join rows, null filters, synonyms, hierarchies, negative pagination, unknown operators, and attempted SQL injection as data.
- [ ] Implement text search using PostgreSQL tsvector/GIN only where needed; add pg_trgm for characterized substring matching only. Preserve result membership and explicit order; report permitted relevance-order differences. Search vectors update in the replacement transaction, never in an index job.
- [ ] Add unauthorized count/facet/statistics tests and consistent multi-query snapshots. Run F1 query workloads with EXPLAIN ANALYZE on representative data; meet recorded budgets and eliminate N+1 loads before adding caching.
- [ ] Run both interpreter suites; commit as `feat: replace search and public reads with PostgreSQL queries`.

### A3: Preserve analysis/download and saved-filter behavior

**Files:** Create `services/exports.py`, `api/exports.py`, `tests/api/test_exports.py`, `tests/integration/test_saved_queries.py`, `db/models/saved_queries.py` and migration. Update `pkdata/*`/filter contract rows.

**Interfaces:** `ExportService(session_factory, queries)` provides `create_filter(query: QuerySpec, principal: Principal) -> UUID` and `stream_export(filter_id: UUID, format: str, principal: Principal) -> Iterator[bytes]`. Store filter criteria and owner/expiry, not an enduring authorization decision. Export formats, columns, archive members, and content types come from F1 captures. Fixtures `exports` and `private_query` construct the service and private selection.

- [ ] Write revoked-access regression:

```python
import pytest
from pkdb.services.authorization import AuthorizationDenied

def test_saved_filter_is_not_a_capability(exports, private_query, creator, anonymous):
    filter_id = exports.create_filter(private_query, creator)
    with pytest.raises(AuthorizationDenied):
        next(exports.stream_export(filter_id, 'csv', anonymous))
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/api/test_exports.py -q`; expect missing export service. Implement analysis serializers preserving fields, units, group/intervention association expansion and scalar/timecourse/scatter representations. Apply permissions again when the download begins.
- [ ] Stream under a consistent read snapshot, close sessions on disconnect, and spool formats requiring seek to bounded temporary files with cleanup. Apply limits to export concurrency/temporary storage. Save criteria/expiry in SQL; the maintenance command deletes expired saved-query rows.
- [ ] Test revoked access after creation, expired IDs, concurrent replacement, empty exports, numeric precision, column order, filenames/MIME types, and client cancellation. Compare download contents with F1 fixtures; normalize only documented volatile archive metadata, never values or record counts.
- [ ] Run both interpreter tests and commit as `feat: preserve analysis exports and saved filters without external state`.

### A4: Support legacy drafts and replace the maintained uploader

**Files:** Create `services/drafts.py`, `schemas/legacy.py`, `api/legacy_uploads.py`, `db/models/drafts.py`, reviewed migration, `cli.py`, `commands/upload.py`, `commands/bootstrap.py`, `commands/cleanup.py`, `tests/api/test_legacy_upload.py`, `tests/cli/test_upload.py`. Update maintained uploader integration only after identifying ownership of the currently untracked `backend/pkdb_data` sources; do not silently commit them.

**Interfaces:** `DraftService(session_factory, ingestion)` provides `begin(sid: str, principal: Principal, core: dict) -> dict`, `patch(sid: str, principal: Principal, values: dict) -> dict`, `finalize(sid: str, principal: Principal) -> ReplacementResult`. Draft rows store typed legacy payload plus source handles; actor/SID uniquely identifies an active generation. Every begin starts an empty complete-study draft, not a merge into published children. `legacy_client`/`legacy_payloads` fixtures replay F1's core, related-set, file and reference requests under creator auth.

- [ ] Write public-visibility regression:

```python

def test_legacy_draft_is_invisible_until_finalization(legacy_client, legacy_payloads):
    sid = legacy_payloads['sid']
    legacy_client.post('/api/v1/_studies/', json=legacy_payloads['core'])
    assert legacy_client.get(f'/api/v1/studies/{sid}/').status_code == 404
    for payload in legacy_payloads['sets']:
        legacy_client.patch(f'/api/v1/_studies/{sid}/', json=payload)
    result = legacy_client.post('/api/v1/update_index/', json={'sid': sid})
    assert result.status_code == 200
    assert legacy_client.get(f'/api/v1/studies/{sid}/').status_code == 200
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/api/test_legacy_upload.py -q`; expect missing legacy routes. Implement file/reference staging and POST/PATCH adapters with captured response shapes. Restrict draft/file reads to the actor; reference edits remain unpublished until finalization. Reject second active begin with 409; serialize PATCH/finalize and seal a generation during commit.
- [ ] Finalization calls I4 replacement. Successful retries with no draft return the legacy success shape for an existing authorized study; failed drafts remain unpublished. Unknown actions fail explicitly. A stale retry cannot publish a newer incomplete draft: serialize generation transitions and enforce completeness before any commit; overlapping sessions without generation IDs are unsupported and rejected where detectable, as documented in the compatibility contract.
- [ ] Add interruption/retry/expiry, same actor conflict, wrong actor, malformed sets, missing references, and retained-old-study tests. Test explicit DELETE really deletes and document why delete-before-upload clients must upgrade.
- [ ] Implement argparse commands `pkdb upload PATH --api-url URL`, `pkdb validate PATH --api-url URL`, `pkdb bootstrap DIRECTORY`, and `pkdb cleanup`. Upload sends one bundle PUT, waits for publication, reports all study outcomes, and exits nonzero on any failure. Token comes from environment or a protected credential input, never a logged command argument. Bootstrap and cleanup are explicitly local administrator operations.
- [ ] Test CLI against HTTPX MockTransport: exactly one PUT per study, no DELETE, retry only replay-safe operations, errors propagate to exit status, no edits to the input folder. Run actual API round-trip fixtures on both Pythons; commit as `feat: support staged legacy uploads and complete-bundle CLI`.

### A5: Mount explicit authenticated MCP tools

**Files:** Create `mcp/server.py`, `mcp/authentication.py`, `api/staging.py`, `tests/mcp/test_tools.py`, `tests/mcp/test_transport.py`; modify app lifecycle and pyproject/lock with stable standalone FastMCP. Pin its resolved SDK dependency.

**Interfaces:** `create_mcp(ingestion: IngestionService, queries: QueryService, file_store: FileStore, session_factory)` returns the mounted MCP server. Tools: `search_studies(query)`, `get_study(sid)`, `validate_study(bundle)`, `replace_study(sid, bundle)`. Bundle inputs carry JSON plus owned staged handle IDs, never arbitrary server paths. `/api/v2/files` creates authenticated staged handles. `mcp_client` is an authenticated test transport client using the creator's token; `mcp_anonymous` lacks credentials. Both fixtures exercise the mounted HTTP app.

- [ ] Add a transport/tool-surface test:

```python
import pytest

@pytest.mark.anyio
async def test_only_explicit_tools_are_exposed(mcp_client):
    tools = await mcp_client.list_tools()
    assert {tool.name for tool in tools} == {
        'search_studies', 'get_study', 'validate_study', 'replace_study'
    }
```

- [ ] Run `uv run --project backend-next --locked pytest backend-next/tests/mcp -q`; expect missing fixture/server. Mount Streamable HTTP at `/mcp` with coordinated ASGI lifespans; authenticate transport tokens through I2, mapping to the same Principal as REST. Use Bearer token transport for MCP while retaining Token headers for legacy REST; both use the same token verification/revocation service.
- [ ] Implement explicit typed tools delegating to shared services. Offload sync SQL/scientific calls without sharing a Session across workers. Map validation issues to structured tool results and restrict tool output to authorized data. Do not generate tools for every legacy route or accept filesystem paths.
- [ ] Test same input yields the same scientific report over REST and MCP; anonymous requests and cross-owner handles fail; token revocation takes effect; concurrent tool calls cannot share principals/sessions. Test actual Streamable HTTP initialization, list, call, cancellation and shutdown, not just Python calls.
- [ ] Run both interpreter suites, including event-loop responsiveness while a controlled blocking ingestion runs; commit as `feat: expose shared services through MCP`.

### A6: Rebuild, measure, package both Pythons, and retire legacy runtime

**Files:** Create `backend-next/Dockerfile`, `tests/system/test_runtime.py`, `tests/system/test_rebuild.py`, `tests/system/test_restore.py`, `tools/backend_migration/rebuild.py`, `docs/backend-migration/runbook.md`. Modify `docs/backend-migration/acceptance.md`, existing compose/CI, `docs/development.md`, backend README and version tooling. After gates pass, move `backend-next/` contents to `backend/` and update paths.

**Interfaces:** `python tools/backend_migration/rebuild.py --corpus PATH --api-url URL --report PATH` uses the upload CLI/service contract, records a result for every manifest study, and can resume by comparing source/processing/vocabulary digests. `rebuild_report` fixture reads a completed system-test report; no synthetic fallback when the explicit full-corpus environment is absent.

- [ ] Add the corpus accounting test:

```python

def test_rebuild_accounts_for_every_study(rebuild_report):
    expected = set(rebuild_report['expected_sids'])
    results = rebuild_report['results']
    assert {item['sid'] for item in results} == expected
    assert len(results) == len(expected)
    assert all(item['status'] == 'published' for item in results)
```

- [ ] Run the explicit system test expecting failure before the rebuild exists. Start a disposable PostgreSQL-only service, apply Alembic, bootstrap vocabulary and disabled user identities, and upload apixaban then the complete authorized corpus. Compare counts, relationships, warnings, PK values and every F1 contract. Investigate existing invalid studies; never edit sources or downgrade rules just to obtain green results. Record approved dispositions rather than hiding failures; the all-published test remains the target for a valid release corpus.
- [ ] Run full suites and five-run benchmarks on both Pythons using F1 inputs; record absolute/relative results and stage profiles. Fix demonstrated SQL, parsing or calculation bottlenecks; only add COPY/process workers after a benchmark demonstrates need and their fault tests pass.
- [ ] Build images with `ARG PYTHON_VERSION=3.14` and a tested 3.13 override. Use the lockfile, copy/install the built package, run as a non-root user and start Uvicorn `pkdb.app:create_app --factory`; I5 defines the optional Settings argument so this factory loads runtime configuration. Both images must pass health, authenticated upload, scientific smoke and MCP transport tests. Test signal shutdown releases files/sessions. Pin base/uv image digests during execution, recording updates through normal dependency review.
- [ ] Test pg_dump/restore plus attachment-volume restore into a disposable environment; re-run scientific and protected-file reads. Rehearse interrupted uploads and cleanup. Write bootstrap steps for database-only content and require an explicit disposition for each category before cutover.
- [ ] Move the replacement into `backend/` only after acceptance evidence is complete. Remove tracked Django/DRF/Elasticsearch modules and runtime config; retain required pure scientific/importer functionality under the new package. Preserve unrelated/untracked files. Update bump/version config to the new version source without inventing a release number; retain the repository release version.
- [ ] Replace the old Python 3.9/tox path with direct uv matrix jobs for 3.13/3.14. Keep the required `tests` aggregate check name, failing if either matrix entry or image fails. Remove Elasticsearch CI/compose services, obsolete env vars, generated-Django-migration steps, stubs and dependencies. Run Ruff/ty/tests, package/wheel installation and containers on both targets from a fresh checkout.
- [ ] Audit imports and locked runtime dependencies for django, DRF and elasticsearch; verify no new runtime connects to a search service. Update API docs, CLI usage, compatibility exceptions, deployment and rollback guidance. Run the existing frontend against the new API for login, browse/filter, study details, downloads and file permissions using synthetic test accounts.
- [ ] Commit as `refactor: retire legacy backend after verified corpus rebuild`. Present final acceptance evidence and deployment instructions for review; do not deploy or discard the old production data as part of this task.

## Phase acceptance

- [ ] Every contract row maps to a passing test or a reviewed intentional exception.
- [ ] Both Python versions pass installation, scientific/API/MCP tests and images.
- [ ] Every authorized corpus study is accounted for; no unexplained dropped data.
- [ ] No new runtime needs Django or Elasticsearch; reads/search use PostgreSQL.
- [ ] Backup/restore, authorization changes, atomic replacement and cleanup races are verified on real PostgreSQL and persistent file storage.
- [ ] Final review covers the whole branch before integration or deployment.
