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
