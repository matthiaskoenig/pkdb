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
