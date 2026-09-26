# Reference resolution (#837)

## Design

Accept a PMID, DOI, or manual citation. Resolve through direct HTTP APIs (NCBI E-utilities, DOI CSL JSON, Crossref bibliographic search), without a provider SDK. Manual searches return candidates and never select one automatically. Manual references remain usable offline without an identifier.

An explicit reference resolve action produces a reviewable snapshot. Saving writes `reference.json` atomically, preserves the study's reference SID, and rejects changes since preview. Normal validation/upload never retrieve metadata. A persistent cache stores provider responses and retrieval timestamps independently of saved references; refresh is explicit. Successful cache entries survive transient failures; not-found entries expire. Concurrent lookups in a process are coalesced and requests have timeouts, rate limiting, bounded retries.

Reference records retain existing fields and add partial ISO publication dates and structured provenance (input, overrides, provider timestamps, previous resolved values). Exact legacy dates remain supported. Corporate authors are identified explicitly. Provider XML parsing preserves nested text and every abstract section, reads DOI identifiers, and uses publication dates rather than indexing completion dates. Curator edits take precedence during refresh. Conflicting identifiers fail visibly.

Preserve existing study/reference ownership for #837. Shared-publication ownership affects replacement, authorization, and visibility semantics and remains a separate design decision.

## Implementation sequence

1. Reproduce missing CLI capability; add provider fixtures and resolver tests.
2. Implement normalization, retrieval, caching, manual search, override preservation, and preview/save APIs.
3. Extend scientific and response schemas and add an additive database migration; round-trip metadata through uploads, reads, and exports.
4. Add `pkdb reference resolve` and `pkdb reference search`; default to JSON previews, require `--write` to save a study reference.
5. Add Reference controls to local curation using the same resolver, with candidate selection, preview, and explicit save.
6. Document workflows and verify Python tests, backend integration tests, migration round trip, lint/types, and browser smoke tests.

## Acceptance cases

PMID-only and DOI-only input; complete and partial publication dates; nested titles and structured abstracts; corporate authors; manual unmatched citations; explicit candidate selection; DOI/PMID conflicts; cached/offline retrieval; refresh failures; local overrides; source modification after preview; old reference JSON compatibility; metadata persistence and export; no network in scientific preparation; authenticated curation actions.

## Verification

Implemented the resolver, persistent response cache, explicit search/preview/save workflows, CLI, local curation dialog, schemas, additive `p003reference` migration, API/canonical round trips, and documentation. No provider SDK was added. Existing curator fields are preserved conservatively; an explicit reset option previews provider metadata without saved corrections.

- Python client suite: 220 passed.
- Backend suite: 644 passed (one existing Starlette/AnyIO deprecation warning).
- Database migration upgrade/downgrade and enriched-reference round trips passed.
- Browser smoke covers candidate selection, safe metadata rendering, preview invalidation, save, and desktop/mobile layout.
- Python lint, formatting, and client/backend type checks passed.
- Hosted frontend type check and changed-component lint passed.
- Documentation build passed without issues.
- Public API smoke: PMID 6138080 and DOI 10.1111/j.1365-2125.1983.tb02270.x both resolved to the same publication and PMID; no enrichment warnings.

No existing study corpus was rewritten and no database outside isolated test schemas was migrated.
