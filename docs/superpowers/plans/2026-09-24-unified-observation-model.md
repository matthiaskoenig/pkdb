---
search:
  exclude: true
---

# Unified observation storage implementation

Status: Implemented and verified locally. Implements the approved simplification of internal scientific storage while retaining curation files and API response shapes.

## Design

- A single `subjects` table stores groups and individuals, with explicit kind, count, and parent. Individual count is one; singleton groups remain distinct. Observations reference one subject.
- A single `observations` table stores characteristic and output identity/context. `observation_values` stores reported, normalized, or calculated numerical representations, retaining original values, units, provenance, and statistical meaning. Characteristics and outputs use the same storage and value handling. Compatibility ORM projections serve existing read APIs.
- One `datasets` table stores dataset containers and ordered series. Ordered observation representation IDs and scatter row identifiers are PostgreSQL arrays, preserving pairing and ordering without timecourse-point, subset-point, or subset-dimension tables. Array expansion is an adapter only for existing flat exports and selection APIs; no point entities are persisted.
- Preserve reported data, individual identity, group hierarchy, explicit series membership, derivation links, zero/missing distinctions, and study-local reference integrity. Initialize an empty database directly without historical ID mappings.
- Keep source-file and public response contracts stable. Avoid loading unrelated users/vocabulary and duplicate dataset response projections. Do not modify deployment data during implementation.

## Execution

1. Establish current scientific/upload regression fixtures and write the initial schema design.
2. Implement shared models and fresh-install baseline migration, including array integrity checks and migration tests.
3. Replace persistence and reconstruction with shared subject/observation handling and array dataset storage.
4. Adapt filtering, statistics, legacy responses, exports, and analysis without physical point entities.
5. Harmonize scientific record handling, retaining source interfaces; add round-trip and individual/group edge cases.
6. Run full Python/PostgreSQL regression checks, migration round-trips, real apixaban corpus uploads/replacements, lint/types/docs, and storage/performance comparisons. Document measured results and limitations.

## Verification results

Before migration consolidation, the complete backend suite passed: 620 tests, including concurrency, provenance, selection-reference, and public-read checks. The client/scientific suite passed 333 tests; the additional duplicate-observation-key case also passed in the final full backend run. Ruff lint/format, backend and client type checks, the clean Zensical build, and public wheel/source-distribution builds passed. The Frost2014 scientific golden/export comparison and 18 related frontend/subject/dataset tests pass. Expected newly completed group SE/CV values are checked independently, including inherited characteristics; the original measurement values remain checked against the legacy fixture.

After migration consolidation, all 615 backend tests and the apixaban curation corpus test passed. Ruff, both type checks, offline migration SQL generation, and the clean documentation build passed. Following the decision to upload from scratch, historical upgrade tests and ID conversion code were removed. The single initial migration is tested for fresh installation, model/schema agreement, downgrade, and recreation. Schema tests cover malformed arrays, cross-study references, immutable kinds, and concurrent membership insertion versus deletion in both orders.

The apixaban corpus produced the same results before and after: 24 studies created, the same 24 replaced, and six rejected with validation reports. All original source hashes were unchanged. Known invalid corpus inputs were not relabeled or edited to make validation pass.

## Measured comparison

[Machine-readable measurements](../benchmarks/2026-09-25-unified-observations.json) compare the previous committed model (`91e96916`) with this implementation, using fresh isolated PostgreSQL schemas and the same local apixaban checkout.

| Measurement | Previous | Unified |
| --- | ---: | ---: |
| Scientific storage tables | 12 | 6 |
| Scientific rows | 30,800 | 24,763 |
| Allocated scientific table/index bytes | 23,035,904 | 18,595,840 |
| Create pass, seconds | 23.68 | 22.06 |
| Replacement pass, seconds | 26.23 | 24.20 |
| Studies page, milliseconds | 28.5 | 26.9 |
| Outputs page, milliseconds | 10.8 | 13.5 |
| Groups page, milliseconds | 19.3 | 20.9 |
| Individuals page, milliseconds | 14.2 | 18.6 |
| Datasets page, milliseconds | 73.7 | 62.4 |

The model removes about 20% of scientific rows and 19% of allocated scientific storage in this measurement, and halves intervention associations (11,364 to 5,682). All 12,058 numerical representations remain, sharing 6,029 observation contexts. Ordered arrays replace 6,384 point/membership rows. Upload and dataset-page timings improved in this local run; some scalar/subject read timings increased. These are single-host observations, not latency guarantees, and timing varied under concurrent test load. Read measurements use one warm-up and the mean of five authenticated requests with page size 100. Allocated sizes include indexes and post-replacement dead space.

## Compatibility and rollout

Source curation formats and API response shapes remain supported through adapters. Characteristics and outputs now share subject count defaults and statistical completion, identified by processing version 6. The user selected a clean database and fresh upload, so historical migrations and migration-only `legacy_id` fields were removed. Numeric resource references and saved selections must be recreated after upload.

Migration `p001initial` directly creates the current schema, indexes, sequences, and integrity triggers. It supports downgrade to an empty schema and subsequent recreation. Existing database revisions are not an upgrade path to this baseline. Dataset membership writes use READ COMMITTED with key-share locks; incompatible write isolation is explicitly rejected, while read-only repeatable-read snapshots remain supported. No deployment database, Docker volume, or study source was modified. See [the data-model guide](../../data-model.md) for fresh setup details.
