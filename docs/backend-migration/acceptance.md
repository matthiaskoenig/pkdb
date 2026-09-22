# Backend replacement execution evidence

Implementation branch: `backend/fastapi-replacement`.

## Verified foundation evidence

- Legacy test suite: 108 passed on Python 3.9 against isolated PostgreSQL/Elasticsearch.
- Contract evidence tooling: 17 passed; inventory contains 178 route/method pairs.
- Read-only corpus inventory: 1,579 study folders; 1,559 parseable identities,
  20 malformed JSON files, 20 duplicate normalized-ID groups. All 30 apixaban
  folders have parseable identities. Integer IDs preserve legacy string conversion.
- New package: locked installation, runtime tests, type checks and clean-wheel
  scientific imports passed on Python 3.13.1 and 3.14.6.

## Outstanding acceptance gates

Populated-study baseline timings and golden payloads, canonical importer,
scientific parity, PostgreSQL schema/transactions, REST compatibility, MCP,
complete corpus dispositions, container builds, restore/cutover, and final review
are not complete. The legacy backend remains unchanged and is not retired.

## Importer and scientific checkpoint

- 52 unit/runtime tests pass on each Python 3.13 and 3.14; Ruff and ty pass.
- Tests cover source provenance, zero/missing distinctions, duplicate headers,
  row limits, subject statistics, graph references, normalization and PK curves.
- Apixaban parser gate: 28 passed, 2 failed. Frost2013a references missing
  `Frost2013a_Tab3.png`; Wang2016 Tab3 maps a missing `label` column.
  Inputs were not changed or excluded. Full scientific parity remains pending.

## Persistence and HTTP checkpoint

- 156 tests pass on each supported interpreter, including real PostgreSQL tests.
- Verified stable-root replacement, rollback after deletion/before commit,
  concurrent first publication, old-reader snapshots, vocabulary/user rechecks,
  protected file lifecycle, bounded SQL counts and multipart workbook ingestion.
- PostgreSQL-only test compose and dual-Python CI include Alembic upgrade/check.
- Offline bootstrap contains 2,147 vocabulary nodes; 11 optional metadata lookups
  were not cached and are recorded in `backend-next/bootstrap/provenance.json`.
- Updated apixaban gate: 28/30 parse; 24/30 pass scientific validation.
  No source studies were edited or excluded. Full-corpus and legacy-output parity
  remain open; these counts are not cutover acceptance.

## Public-read and search checkpoint (2026-09-22)

- 218 regular tests pass on both supported interpreters; Ruff and ty pass.
- Persisted Frost2014 public study, reference, subject, intervention, output and
  timecourse arrays match captured legacy goldens. Scientific output comparison
  covers all 782 records with explicit numeric tolerances.
- Three real caffeine studies publish with exact scatter pairings, attachments,
  comments and canonical readback on both interpreters.
- Vocabulary reads match captured legacy serializer examples. PostgreSQL handles
  text search, synonym lookup, inherited-characteristic filters and visibility.
  Four GIN expression indexes pass upgrade/downgrade/schema-drift checks.
- Vocabulary pages use five SQL statements for both 1 and 100 results. This is
  query-count evidence, not a matched end-to-end performance claim.
- Remaining interfaces, full corpus dispositions, measured workload parity,
  MCP, exports, legacy drafts, containers and cutover gates remain open.

## Validated-upload and MCP checkpoint

- 245 regular tests pass on each Python 3.13/3.14, including 11 real HTTP MCP
  transport tests. Exactly four explicit authenticated tools are exposed.
- MCP reuses REST scientific validation, query, authorization and publication
  services. Tests cover bearer-token revocation, private-study isolation,
  cross-owner/expired handles, filesystem-path rejection, byte limits, integrity,
  cancellation, responsive health checks and clean ASGI shutdown.
- Malformed nested uploads return structured errors with accurate counts and
  preserve existing publications. Full real-study golden/publication checks
  remain green after stricter input validation.
- Remaining account/read details, analysis exports, legacy draft adapters, CLI,
  full rebuild, performance, image/restore/browser gates and final review remain
  outstanding. This checkpoint does not authorize cutover.

## Corpus and unchanged-uploader checkpoint

- 290 regular tests pass on each Python 3.13/3.14. Four real-study
  publication/public/analysis/scatter gates pass on 3.13.
- The full read-only scientific audit accounts for all 1,579 source folders:
  1,047 validate, 532 return structured validation errors, zero unexpected
  exceptions. These are validation outcomes, not accepted exclusions or a
  successful complete rebuild. Remaining failures require compatibility review
  and explicit source dispositions.
- Restored external-field aliases and subject/intervention image provenance.
  Restricted-dose eligibility follows the legacy calculation code; unsupported
  volume/rate/area doses retain dose-independent PK results. All-zero curves
  return source-located errors rather than crashing.
- The unchanged uploader publishes copied Frost2014 data through actual local
  HTTP: 782 measurements, 70 individuals and four normalized curves (eight
  canonical reported/normalized curves). Original source hashes remain unchanged.
  Run `corpus_tests/test_legacy_client.py` with `PKDB_LEGACY_CLIENT_PYTHON`,
  `PKDB_LEGACY_CLIENT_ROOT`, `PKDB_STUDY_CORPUS` and `PKDB_TEST_DATABASE_URL`.
- Legacy Hall1976 replay fails at its string-based unit-dimension lookup during
  AUC normalization. This is not evidence of complete Hall1976 legacy parity.
- Full compatibility coverage, corpus dispositions, matched performance,
  container/restore/browser gates and final branch review remain outstanding.

## Full rebuild and runtime checkpoint

- 305 regular tests pass on each actual Python 3.13 and 3.14. Ruff, formatting
  and ty pass. Both pinned, non-root container builds pass REST publication,
  authenticated attachment access, MCP, analytical PK and graceful shutdown.
- Real PostgreSQL dump plus attachment restore passes on both interpreters,
  preserving scientific records and authorization and accepting another atomic
  replacement. This is a small fixture rehearsal; full-corpus restore remains open.
- Full HTTP rebuild accounts for all 1,579 folders: 1,072 published, 446 failed
  (400 API validation rejections and 46 local bundle failures), 61 blocked
  (41 duplicate-SID folders and 20 malformed identities), zero pending and zero
  HTTP 500 responses. See rebuild-checkpoint.json for report fingerprint. These
  outcomes are not accepted exclusions; complete remains false.
- Existing frontend browser checks pass login, study browsing, Frost2014 search,
  detail/figure display, scientific output rows and selected-study archive HTTP
  response. Compatibility fixes accept format=json and search_multi_match;
  explicit CORS also covers upload-limit errors. Browser tests use a temporary
  frontend copy with node-sass replaced by sass for Node 22; application source
  remains unchanged. Downloaded archive contents remain covered by API tests.
- Local create-admin bootstraps a verified administrator using a hidden prompt
  or explicit stdin, rejecting existing identities instead of changing accounts.
- Full compatibility coverage, source dispositions, matched performance, full
  corpus restore and final branch review still block cutover and legacy retirement.

## Full snapshot restore checkpoint

- Restored the complete rebuild snapshot into a separate PostgreSQL database:
  all 33 tables and 1,470,887 rows have identical ordered row fingerprints.
  All 11,916 stored files (2,618,745,722 bytes) match their database size and
  SHA256 metadata. The restored application readiness endpoint succeeds.
  Evidence: restore-checkpoint.json. The dump uses an exported repeatable-read
  snapshot shared with the source fingerprint queries. Original publications
  and source files remain unchanged.
- This closes the full snapshot integrity rehearsal, not corpus acceptance: the
  507 failed/blocked source folders still require compatibility review and
  disposition. Other compatibility, performance and final-review gates remain.
- CLI redaction regressions for JSON literals and escaped strings fail before
  the fix and pass afterward on both interpreters; all 12 CLI upload tests pass.

## Processing version 5 compatibility checkpoint

- 314 regular tests pass on each Python 3.13 and 3.14; Ruff, formatting and ty
  pass. Latest images build on both versions. The combined explicit runtime,
  restore and Frost/scatter corpus run has 24 passing and five failing tests on
  each interpreter; the failures are the existing corpus blockers below.
- Numeric labels and categorical choices now follow legacy CharField conversion
  at the source boundary, retaining zero and rejecting boolean coercion. Five
  regression cases fail before the fix and pass afterward. Unchanged Levy1983
  and McCrea1999 now both publish through actual HTTP (201); see
  numeric-source-checkpoint.json. Matthaei2016 advances past numeric choices but
  still fails its unknown CYP1A2 genotype measurement definition.
- Frost corpus blockers remain: Frost2013a references missing Tab3 imagery
  (both parse and scientific tests fail); Frost2014a uses unknown measurement
  names; Frost2015 has a negative concentration mean; Frost2018 has missing
  method/measurement definitions, negative values forbidden by its vocabulary,
  and percent data against an ETP-relative definition specifying hours. These
  are not approved exclusions or evidence of complete apixaban acceptance.
- Browser checks additionally render all four Frost2014 timecourse plots and
  successfully fetch a protected TSV through the existing frontend control.
- Earlier full rebuild/restore artifacts remain evidence for processing version
  4. Two new publications use version 5; a fresh complete rebuild/resume is still
  required after compatibility and vocabulary dispositions are settled.

## Administrative, account-error and analysis-detail checkpoint

- 330 regular tests pass on each actual Python 3.13 and 3.14; Ruff/format/ty pass.
  Administrator-only user creation and name/role updates use verified email,
  password hashing, and transaction-level privilege checks. Existing tokens
  observe role changes immediately; duplicate creation rolls back.
- Captured legacy account required/blank/email errors now return HTTP400 field
  mappings without echoing supplied passwords. Administrator permissions are
  checked before model-field validation and again within the transaction.
- Analysis detail reads for studies, interventions and timecourses match list
  rows, including JSON suffixes and saved-filter/private visibility. Association
  detail identities for groups/individuals/outputs/data remain to be resolved.
- Processing5 read-only corpus audit:1,579 folders,1,093 valid,486 invalid,zero
  unexpected exceptions. See corpus-audit-v5.json and corpus-failures-v5.tsv.
  Error codes/locations are sampled at ten issues per folder; error_count retains
  the complete count reported by validation. No source edits or exclusions.
- This audit is not a repeated complete HTTP rebuild. The full rebuild report
  remains at its earlier checkpoint plus two separately verified publications.

## Machine handoff checkpoint (2026-09-22)

- 337 regular tests passed on each supported Python at commit4499eb8a. Both rebuilt
  runtime images pass REST/MCP/protected-file/shutdown and PostgreSQL/files restore
  tests (two system tests each). Ruff/format/ty passed at that checkpoint.
- Performance evidence now includes separate fresh-application cold runs, excluded
  warmups and five measured warm runs per runtime. All measured median/p95 budgets
  pass; see performance.json and performance/README.md for scope and limitations.
- Subsequent fixed-role catalogue addition passes six focused tests on Python3.13.
  Full suites and images must be rerun for this final addition. Custom group writes
  remain unresolved. No complete compatibility or cutover acceptance is claimed.
- Work stopped at the user's request. See handoff.md and execution-ledger.md.


## Transferred-machine native verification (2026-09-22)

- Deferred role-catalogue verification is complete: 343 regular tests pass on each
  Python before the next fix, and both runtime/restore gates pass on each image.
- Legacy upload authentication now precedes malformed/non-object body validation
  across reference POST/PATCH, study POST/PATCH and update_index. Ten HTTP
  regressions cover the observed 422-before-401 defect. Existing successful upload
  and staged publication tests remain green.
- After this fix, 353 regular tests pass on each CPython 3.13.15 and 3.14.6.
  Ruff/format, both type checks, sdist/wheel builds, clean-wheel scientific imports
  and Alembic upgrade/check/downgrade/upgrade pass. Each rebuilt image passes two
  runtime/restore system tests. The independent migration tooling suite passes
  16 tests per interpreter. Image IDs and test-environment caveats are in the ledger.
- Published editable source roundtrips, remaining administrative and association
  contracts, corpus dispositions, a current complete HTTP rebuild and final review
  remain open. This checkpoint does not authorize legacy retirement or deployment.
