# Backend simplification review — 2026-09-25

Reviewed checkout: `25574a4a`; backend baseline: `8c51b48e` (unified scientific storage). This is a code and dependency review, with targeted execution checks. This report records the review before implementation. Follow-up changes fix shared-row analysis filtering, retire ineffective reader grants and the legacy upload lifecycle, and remove inactive quota reporting/MCP plumbing and unused helpers. The other optimization proposals remain recommendations.

The backend already has the right basic architecture: one PostgreSQL database, shared scientific validation with the Python client, atomic study replacement, and a small REST/MCP service layer. The best next step is to retire obsolete contracts and reduce repeated work inside that architecture. Another storage rewrite would carry substantially more risk than the opportunities below.

## Evidence and limits

Inspected application wiring, REST/MCP endpoints, authentication and authorization, ingestion, storage and cleanup, query construction, serializers, exports, database models/migration constraints, frontend/Python callers, and associated tests. Repository searches identify current in-tree consumers; they cannot establish whether external clients still use a route.

Executed:

- `backend/.venv/bin/pytest backend/tests/unit -q`: **188 passed**.
- Compiled identical study predicates through the normal and analysis SQL builders: normal query has **one related-measurement EXISTS**, analysis has **two separate EXISTS**.
- Executed authorization with a private study and a user present only in `collaborator_ids`: **read denied**.

PostgreSQL integration tests and new workload benchmarks were not run. Performance recommendations are based on observable code paths, not measured speedup claims. Historical [performance evidence](../backend-migration/performance/README.md) predates the current storage baseline and should not be treated as current capacity evidence.

## Priority order

| Priority | Change | Primary benefit | Compatibility / risk |
| --- | --- | --- | --- |
| P1 | Unify related-measurement predicate semantics | Correct query results | Analysis results can change to match intended criteria |
| P1 | Remove or implement ineffective reader grants | Honest access-management behavior | Product/policy decision; do not silently broaden access |
| P2 | Retire legacy staged upload and suffix adapters | Remove a complete alternate lifecycle | Verify external clients and deployment flags |
| P2 | Remove inactive authenticated quota machinery | Less dead code and misleading configuration/UI | Preserve current unthrottled-account policy |
| P2 | Stream export query results without repeated OFFSET | Less database work on large exports | Preserve snapshot, stable order and expanded-row semantics |
| P2 | Separate study summaries from full details | Bounded response work and smaller payloads | Introduce a summary contract and migrate callers |
| P2 | Reuse versioned vocabulary snapshots | Less repeated querying, model construction and hashing | Preserve transaction-time compatibility check |
| P2 | Consolidate upload clients and report construction | One protocol and diagnostic path | Backend CLI currently consumes old response format |
| P2 | Remove saved-query persistence from one-shot exports | Eliminate unnecessary database writes | Keep current browser UUID selections until migrated |
| P3 | Scope insertion lookups and batch updates | Shorter publication transactions | Verify provenance and graph equivalence |
| P3 | Reuse request identity, retain write-time checks | Fewer authentication queries | Do not cache identity across requests |
| P3 | Bound cleanup batches and simplify account throttling | Less request/maintenance lock work | Keep cleanup/publication race protections |
| P3 | Tighten scientific projections and inheritance scope | Less unused data/recursive work | Measure plans and preserve inheritance semantics |
| P3 | Isolate SMTP delivery from account transactions | Avoid network latency holding database locks | Requires explicit delivery/retry semantics |

## Findings

### 1. Related-measurement filters disagree between read interfaces

**Sources:** [analysis statement builder](../../backend/src/pkdb_server/db/analysis.py#L46), [normal predicate builder](../../backend/src/pkdb_server/db/queries.py), [flat analysis route](../../backend/src/pkdb_server/api/exports.py#L12).

`conditions()` deliberately groups `outputs.*` predicates into one correlated EXISTS. `analysis.statement()` loops over the same study predicates and calls `conditions()` separately for each unsupported direct field. This loses the shared-row requirement.

Example: measurement A has substance `drug`, measurement B has type `concentration`, and no measurement has both. A study query requiring both rejects the study; the flat study analysis query can include it. Compilation reproduced exactly this difference. This applies to study predicates passed through the analysis builder; it is not a claim that every ZIP selection is wrong. `FilterSpec` selection uses the normal builder.

**Change:** pass the related predicates together through the shared builder, while retaining the separate expansion rules for flat outputs/subjects. Add a database regression with the two unrelated measurements, then a positive case where one measurement satisfies both. Share semantic filtering logic, not merely field-name constants.

### 2. Reader grants are a persisted feature with no authorization effect

**Sources:** [access API](../../backend/src/pkdb_server/api/management.py#L30), [visibility](../../backend/src/pkdb_server/db/queries.py#L197), [authorization](../../backend/src/pkdb_server/services/authorization.py#L29), [frontend administration](../../frontend/src/features/admin/useAdministration.ts).

The admin API accepts `reader_ids`, stores them as `StudyGrant(role="collaborator")`, and returns them again. Both SQL visibility and object authorization only recognize curator assignments for private-study reads. `StudyAccess.collaborator_ids` is populated but not used by authorization. A direct execution check confirmed denial.

**Recommendation:** remove the reader-grant control, input/output field and unused access-grant role if the current curator-only policy is intentional. Preserve collaborator **attribution** in `StudyUser` and source metadata: that is a different concept. If private read-only sharing is required, implement it consistently for lists, details, exports and attachments with a policy matrix. Do not infer expanded permission from historical design documents.

### 3. Retire the legacy staged-upload lifecycle as a unit

**Sources:** [legacy transport](https://github.com/matthiaskoenig/pkdb/blob/25574a4a/backend/src/pkdb_server/api/legacy_uploads.py), [draft service](https://github.com/matthiaskoenig/pkdb/blob/25574a4a/backend/src/pkdb_server/services/drafts.py), [bundle materialization](https://github.com/matthiaskoenig/pkdb/blob/25574a4a/backend/src/pkdb_server/services/bundles.py), [staging route](https://github.com/matthiaskoenig/pkdb/blob/25574a4a/backend/src/pkdb_server/api/staging.py), [draft models](https://github.com/matthiaskoenig/pkdb/blob/25574a4a/backend/src/pkdb_server/db/models/drafts.py), [router aliases](../../backend/src/pkdb_server/api/compatibility.py), [application wiring](../../backend/src/pkdb_server/app.py#L437).

The current Python client sends one complete multipart bundle. The legacy path still implements separate reference staging, integer attachment aliases, study generations, ordered patches, sealing when `dataset` arrives, expiry, advisory locks, and finalize. Finalization holds a draft transaction while calling ingestion that opens separate transactions. This is a substantial lifecycle solely to emulate the retired uploader.

These six files total **659 lines**, before `replace_staged()`, application wiring, cleanup branches, old account/admin adapters and compatibility tests. Most of the transport is already disabled by default. `/api/v2/files` is also gated by the legacy flag, and no current REST/MCP complete-bundle endpoint consumes its UUID handles; the surviving staged-bundle publication caller is `DraftService`.

**Change:** after confirming no supported external client needs it, remove the legacy upload/staging routes, draft service, alias models and staged-bundle branch together. Remove `.json` and `.json/` aliases as a separate explicit contract retirement. Drop obsolete tables through a new migration; do not edit the existing baseline for deployed databases.

Keep the immutable file store: complete-bundle ingestion still uses its staging and publication protections internally.

**Do not delete all `/api/v1` routes.** The current frontend uses browser search, details, vocabulary, authentication and administration there. The API version prefix does not identify dead code.

### 4. Quota configuration, usage reporting and MCP bookkeeping no longer match policy

**Sources:** [settings](../../backend/src/pkdb_server/config.py#L25), [quota service](../../backend/src/pkdb_server/services/quotas.py#L25), [HTTP quota middleware](../../backend/src/pkdb_server/api/quotas.py), [body/admission limits](../../backend/src/pkdb_server/api/limits.py), [MCP execution wrapper](../../backend/src/pkdb_server/mcp/server.py#L18), [policy tests](../../backend/tests/integration/test_quotas.py).

Authenticated principals return immediately from `charge()` and `acquire()`. The retained account/key/upload/export quota settings do not govern authenticated work. `usage(user_id)` still queries account buckets that this implementation no longer charges, while the admin frontend still requests usage. MCP requires authentication, so its quota acquisition, Event/Thread heartbeat and lease cleanup are unreachable under the current policy.

`UploadLimits` additionally combines two different jobs: limiting bytes for every POST/PUT/PATCH, and acquiring an upload semaphore for anonymous requests. Consequently anonymous `POST /api/v2/query` competes for an upload slot while authenticated uploads bypass admission. Names and configuration suggest a global upload cap that is not actually enforced for accounts.

**Change:** delete MCP quota/heartbeat plumbing, retire inactive account-budget settings and usage UI, and name the remaining middleware around its actual responsibilities. Keep anonymous abuse controls and byte limits. Treat any new global capacity protection as a separate policy decision; do not reintroduce account quotas during cleanup.

### 5. Export batching repeatedly scans preceding rows

**Source:** [AnalysisService.iter_rows](../../backend/src/pkdb_server/services/analysis.py#L36).

Exports fetch 500 rows with OFFSET 0, 500, 1000, and so on. At the one-million-row limit, 2,000 nonempty batches imply about **999.5 million cumulative preceding-row offsets**, plus the final empty fetch. This is an illustration of the query pattern, not a measured count of physical reads; actual cost depends on the plan.

**Change:** use one streamed ordered query with bounded partitions, or keyset pagination over the full stable ordering tuple. Flat outputs expand interventions, so measurement ID alone is not a sufficient cursor. Keep serialization batches, row/byte limits and the existing repeatable-read snapshot. Verify exact row order/count and multi-intervention/timecourse exports. Measure latency, peak RSS and query count at increasing sizes.

### 6. Study lists and flat exports assemble full study details

**Sources:** [study serializer](../../backend/src/pkdb_server/db/study_responses.py#L28), [QueryService](../../backend/src/pkdb_server/services/queries.py#L35), [analysis serializer](../../backend/src/pkdb_server/db/analysis.py#L204), [frontend columns](../../frontend/src/features/results/columns.ts).

Every study page loads IDs for all groups, individuals, normalized interventions, outputs and subsets in the selected studies, alongside notes, people, grants and attachments. Counts are obtained from Python list lengths; calculated-output counts iterate one row per output. A bounded number of studies therefore does not bound work or response size. The flat study export also calls this full serializer and discards most of the result.

This is **not an N+1 finding**: the code already batches queries, and there are fixed-query-count tests. The issue is rows and bytes fetched per query.

**Change:** introduce a study summary projection with only required fields and SQL aggregate counts; keep full detail assembly for explicit details. Give flat study export its own small projection. Preserve old response shapes until callers migrate. Add a test where one study has many outputs, measuring fetched rows/serialized bytes as well as query count.

### 7. A normal upload rebuilds the vocabulary repeatedly

**Sources:** [upload route](../../backend/src/pkdb_server/app.py#L222), [ingestion](../../backend/src/pkdb_server/services/ingestion.py#L73), [vocabulary loader](../../backend/src/pkdb_server/db/bootstrap.py#L208), [graph insertion](../../backend/src/pkdb_server/db/replace.py#L48).

For a report-v2 upload carrying an expected vocabulary hash, the call graph loads/projects the full vocabulary for: report metadata, route compatibility, `replace()` compatibility, validation, and publication compatibility. That is **five full projection loads**, followed by another full vocabulary-node lookup in graph insertion. Capabilities/vocabulary requests from the client add separate work.

**Change:** create a versioned immutable vocabulary snapshot containing the projected model, digest and lookup maps. Reuse it within an operation; optionally cache by committed vocabulary version per process. During publication, keep the shared vocabulary lock and reread the version to reject a changed snapshot. Cache identity must include the database/source context; do not use an unversioned global object or confuse authored vocabulary version with projected vocabulary hash.

### 8. Two upload clients and two report shapes keep each other alive

**Sources:** [backend upload command](../../backend/src/pkdb_server/commands/upload.py), [public client](../../python/src/pkdb/client.py#L336), [report middleware](../../backend/src/pkdb_server/api/upload_reports.py), [application upload handler](../../backend/src/pkdb_server/app.py).

The backend CLI has its own folder discovery, multipart construction, credential-scheme selection, response checks and error handling. It does not negotiate the richer report envelope; the public client does. The API then maintains old and new response paths, captures and decodes its own JSON response in middleware, validates it into another model, and serializes it again. Success envelopes repeat diagnostics under both `report.issues` and `result.warnings`.

**Change:** consolidate transport and response decoding in the public client. Preserve the distinction between local validation and explicit server-only validation; a thin CLI wrapper need not silently change semantics. Once the backend CLI and supported external clients consume one report format, build that report directly at the endpoint/exception boundary. Retain a small outer adapter for middleware-generated size/quota failures and preserve unknown-persistence handling. Removing report v1 now would break the current backend CLI.

### 9. One-shot exports unnecessarily persist saved searches

**Sources:** [v2 export endpoint](../../backend/src/pkdb_server/api/data.py#L99), [saved filters](../../backend/src/pkdb_server/services/exports.py#L57), [browser filter endpoint](../../backend/src/pkdb_server/api/exports.py#L106), [frontend search](../../frontend/src/api/search.ts#L32).

`POST /api/v2/exports` creates a SavedQuery, deletes expired rows, commits, then immediately loads that SavedQuery to generate one archive. Persistence adds no reuse for this path. Browser search is different: `GET /api/v1/filter/` writes a saved selection and the frontend passes its UUID across result tabs.

**Change now:** let export accept validated criteria directly under its export snapshot, without a transient SavedQuery. Move expiry sweeping out of query creation into maintenance.

**Later:** migrate browser selections to explicit typed criteria (or retain a POST-based saved-selection resource if reusable handles are useful). Do not delete saved selections before changing the frontend. There is no production HTTP/MCP caller of the service's single-entity CSV branch in the inspected tree; either expose it intentionally or remove that branch and its QuerySpec/FilterSpec storage union.

### 10. Publication still contains global lookups and per-row updates

**Source:** [insert_graph](../../backend/src/pkdb_server/db/replace.py#L48).

Every publication loads every User and every VocabularyNode, despite ingestion already loading and locking the relevant contributors. Group-parent links and intervention derivation links execute individual UPDATE statements. Most other insertion paths already use bulk operations.

**Change:** pass the validated contributor and vocabulary lookup maps into insertion, or fetch only referenced keys. Batch parent/derived updates after generated IDs are known. Preserve author/comment resolution, dependency order and database constraints. Benchmark at large group/intervention counts; do not assume this is the dominant workload cost.

File publication also copies/hashes attachments at several stages, including verification while publication locks are held. Consolidating immutable upload materialization may reduce I/O, but this is a second-stage optimization requiring cleanup-race, interruption and corruption tests. Do not simply delete the final integrity check.

### 11. Identity is resolved repeatedly in the same HTTP request

**Sources:** [quota authentication](../../backend/src/pkdb_server/api/quotas.py#L36), [principal resolution](../../backend/src/pkdb_server/app.py#L184), [credential API actor](../../backend/src/pkdb_server/api/credentials.py#L128), [session verification](../../backend/src/pkdb_server/services/credentials.py#L32).

Quota middleware authenticates to decide whether an account is exempt. Endpoints authenticate again. Several account routes then run a separate session check before the service repeats that check in its transaction.

**Change:** centralize request-scoped principal resolution in a dependency and reuse that result in middleware/routes. Retain service-side credential revalidation, recent-authentication checks and locks at mutation boundaries. These defend revocation/role changes during the operation and are not interchangeable with request authentication. Test deactivation/revocation between request entry and commit.

### 12. Cleanup and account throttling perform global or per-object maintenance

**Sources:** [account throttle](../../backend/src/pkdb_server/services/accounts.py#L47), [file cleanup](../../backend/src/pkdb_server/files/cleanup.py), [maintenance command](../../backend/src/pkdb_server/commands/cleanup.py).

Each account throttle operation deletes all expired throttle rows, even though only one bucket is relevant. Saved-filter creation similarly sweeps expired rows. File cleanup selects expired stored files, locks them, then separately checks attachment references for each row. Published attachments keep old expiry times and can be reconsidered on every cleanup run. Untracked-file cleanup performs an existence query per file.

**Change:** upsert/reset only the active throttle bucket; sweep globally in maintenance. Filter referenced files with NOT EXISTS before locking, use bounded cleanup batches, and batch storage-key existence checks. Preserve SKIP LOCKED, leases, crash-recovery grace periods and publication's row-lock protocol. Verify concurrent publication/download/cleanup before rollout.

### 13. Query projections still carry compatibility costs into scientific reads

**Sources:** [observation adapter](../../backend/src/pkdb_server/db/models/measurements.py#L183), [public projection](../../backend/src/pkdb_server/db/serialize.py#L21), [analysis queries](../../backend/src/pkdb_server/db/analysis.py#L46), [inherited characteristic SQL](../../backend/src/pkdb_server/db/subject_filters.py#L10).

Public output serialization already defers source JSON and the correlated subject-kind lookup. Analysis queries load full Measurement/Characteristic objects, including those compatibility fields, then frequently build nested public responses before flattening them. Inherited-characteristic SQL seeds its recursive lineage from all subjects of the selected type before final visibility/filtering.

**Change:** give flat analysis explicit column projections and join subject kind once where needed. Seed inheritance calculations with relevant visible study/subject IDs where semantics allow. Centralize the additive inheritance policy (`disease`, `abstinence`) shared by SQL and Python representations, with cross-interface tests. Use current EXPLAIN ANALYZE evidence before replacing joins or adding indexes.

### 14. SMTP calls hold account transactions open

**Sources:** [account token delivery](../../backend/src/pkdb_server/services/accounts.py#L90), [primary-email change](../../backend/src/pkdb_server/services/accounts.py#L358), [invitations](../../backend/src/pkdb_server/services/invitations.py#L28), [SMTP transport](../../backend/src/pkdb_server/services/mailer.py).

Registration, reset, invitations and email changes call synchronous SMTP while database transactions (sometimes user row locks) are open. Slow delivery occupies workers and connections. Delivery and database commit cannot be made atomic by keeping the transaction open: an email can still be sent before a later rollback.

**Recommendation:** if these flows see meaningful traffic, use a small transactional outbox with bounded delivery/retry and explicit status. This adds a small worker and is not a net simplicity win for a very low-volume deployment; defer it unless latency/operational evidence justifies it. Never move delivery after commit without addressing retries, duplicate delivery and token validity.

## Additional feature decisions and small removals

| Candidate | Recommendation | Constraint |
| --- | --- | --- |
| Legacy API tokens / `/api-token-auth/` | Retire after API-key migration and cutoff verification | Keep one-use verification/reset/invitation tokens; they share the Token table |
| Legacy `_users` / `_user_groups` admin facade | Remove with obsolete compatibility clients | Current `/api/v1/admin/...` UI is a separate active interface; `require_admin()` is shared with invitations |
| MCP `search_studies` | Consider deprecating in favor of `query_data(entity="studies")` | Existing MCP clients/tool configurations may reference the old tool name |
| MCP transport itself | Keep if used; make optional only if deployments need that | Avoid a second runtime mode purely for aesthetics |
| `authenticate_password()` | Remove unused implementation | Repository search found no callers; active login uses dummy-hash verification elsewhere |
| `ExportService.queries` | Remove unused injected dependency | Export service stores it but never reads it |
| `Dataset.row_metadata` | Candidate for removal until a real producer/consumer exists | Schema trigger references it; requires migration and external-data audit |
| Secondary email support | Keep unless product explicitly wants one-address accounts | Current frontend uses it; verification and recovery behavior must survive simplification |
| Reviewer role | Keep pending an explicit permissions decision | It currently grants public-study write access beyond per-study curator assignment |
| Avatar management / historical user import | Keep | Current frontend and setup depend on these; migration-oriented naming is not evidence of dead code |
| Dual researcher/full API documentation | Low-priority polish only | Full schema can be cached, but removing the split offers little runtime benefit |
| Python 3.15-specific dependency branches | Review support policy separately | Do not drop an explicitly supported interpreter as incidental cleanup |

## What should remain protected

- Shared scientific validation and parsing in `python/src/pkdb`; do not recreate a server-specific scientific engine.
- Atomic complete-study replacement, per-study locking, permission rechecks and vocabulary-version checks.
- Separation of contributor attribution from actual access grants.
- Reported/normalized/calculated provenance and inherited-characteristic semantics.
- Byte/row limits and explicit unknown upload outcomes.
- Immutable attachment storage and publication/download/cleanup coordination.
- Unified observation/value storage and dataset array integrity constraints. The recent schema consolidation already reduced duplication; changing it again needs measured evidence and corpus equivalence.
- PostgreSQL-native search and typed allowlisted predicates. There is no demonstrated need to restore a separate search service or add a generic repository framework.

## Suggested implementation sequence

1. **Correctness:** fix shared-row analysis predicates; resolve reader-grant product behavior. Add focused PostgreSQL/authorization regressions.
2. **Deletion:** remove unused password helper, unused export dependency and unreachable MCP quota code. Retire inert quota UI/config deliberately. Inventory external legacy consumers before deleting their protocol.
3. **Legacy retirement:** remove obsolete upload/admin/auth/suffix contracts, migrate tests to current API keys/default app configuration, and add a migration for obsolete tables. Preserve browser v1 routes.
4. **Read/export performance:** add summary projections, direct one-shot exports and streaming/keyset export iteration. Benchmark response size, rows fetched, query counts, RSS and latency.
5. **Upload performance:** reuse vocabulary snapshots, consolidate CLI/client/report code and batch insertion lookups/updates. Measure preparation, compatibility, staging, lock-held publication and response phases separately.
6. **Maintenance:** bound cleanup; optimize relevant inheritance/projections after inspecting current query plans. Consider mail outbox only if operational demand warrants it.

Use small independent PRs. A sensible target architecture has one complete-bundle write protocol, one scientific predicate implementation with explicit presentation projections, one credential implementation for each genuinely different credential kind, and clearly identified browser-only contracts.

## Verification required for implementation

The broad API fixture currently enables legacy routes and disables request quotas. There are separate default-surface tests, but retirement work should make current defaults/API keys the main fixture and isolate remaining compatibility tests explicitly.

Run PostgreSQL API/integration tests for same-row predicates, private visibility across every read path, exports, credential revocation, concurrent replacement and file cleanup. Preserve golden scientific/provenance tests and corpus checks when changing ingestion/storage. Extend existing fixed-query-count tests to bound returned rows and payload size. Test export ordering and repeated measurements with multiple interventions. Test vocabulary change during validation/publication and cache separation between databases.

Record a fresh benchmark on the current schema with small and large studies, anonymous and authenticated browsing, multi-entity filters, study summaries, and large exports. Report measured improvements only after that run; the review does not claim production latency or capacity figures.
