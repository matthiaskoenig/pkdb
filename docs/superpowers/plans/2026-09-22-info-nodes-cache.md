---
search:
  exclude: true
---

# Info nodes cache consolidation

**Goal:** Integrate all remaining `backend/pkdb_data` content into `backend/info_nodes`, refresh public metadata from scratch, and enforce explicit cache lifetimes.

**Architecture:** Keep definitions, conversion, and cache management in `info_nodes`, with cache data directly in `info_nodes/cache`. Normal generation refreshes stale metadata; `--offline` and `--check` use committed cache content without network requests. `--refresh-cache` starts from an empty staging cache. Persist retrieval timestamps rather than using checkout-dependent file modification times. Use 60 days for ontology/chemical records and 24 hours for identifiers.org and UniChem source registries. Publish staged caches and generated snapshots only after validation.

**Constraints:** Preserve current uncommitted curation. Never hand-edit generated bootstrap JSON. Do not reuse old responses during a forced refresh. Report failed remote lookups explicitly. Merge the package READMEs, update live imports/documentation/tests, and retain historical migration evidence.

- [x] Move conversion and package configuration into `info_nodes`; relocate the cache and remove `pkdb_data`.
- [x] Add tested cache age/read/write handling and scoped pymetadata integration, including strict expiry and offline behavior.
- [x] Update generation options and tests for staged refresh and offline reproducibility.
- [x] Fetch all active metadata into an empty cache, inspect failures, validate scientific properties, and regenerate bootstrap outputs.
- [x] Merge documentation and verify generation, unit/API/integration tests, lint, types, and docs.

Verified: 489 backend tests passed; 206 upstream pymetadata tests passed. Offline generation check, Ruff, type checks, and documentation build passed. Refreshed 2,254 metadata responses with no unresolved metadata issues. Upstream FMA fix: https://github.com/matthiaskoenig/pymetadata/pull/90.
