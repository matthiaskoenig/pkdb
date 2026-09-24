---
search:
  exclude: true
---

# Issue 822: API simplification and read-only MCP

Status: Implemented and verified locally. User approved the proposed restructuring with the requirement that MCP expose only reads, never validation, staging, uploads, or replacement.

## Implementation sequence

1. Inventory published routes and first-party consumers. Baseline: 93 OpenAPI operations across 79 paths, all untagged. Distinguish current researcher access, browser/account operations, administration, and legacy compatibility.
2. Make MCP structurally read-only: remove mutation/validation tools and ingestion/staging dependencies; retain authorized search and complete study retrieval, and expose shared read queries. Test tool discovery, attempted removed-tool calls, and visibility boundaries.
3. Add a compact typed REST data interface: studies, measurements, advanced query, and exports, using consistent page responses and existing authorization/scientific query semantics. Preserve complete-study retrieval and atomic REST uploads.
4. Group current OpenAPI operations by task. Move browser-only endpoints out of the default researcher reference, provide a separate full reference, and make obsolete authentication/upload/staging/suffix compatibility routes opt-in. Migrate current email management and Python client consumers to canonical routes. Retain browser-required legacy read/filter routes until equivalent query behavior is migrated safely.
5. Add executable Python/curl examples and deterministic tested outputs. Document REST versus MCP, simple versus advanced filters, pagination, authentication, and migration settings.
6. Verify REST and MCP contracts, public/private visibility, exports, Python client behavior, frontend account paths, documentation generation, and the published route inventory. Record actual outcomes and remaining compatibility boundaries below.

## Constraints

Reuse the existing services and source of authorization decisions. Do not turn a measurement-level match into a study-level expansion implicitly. Do not break canonical study/vocabulary/report schemas just to normalize spelling. Retired write APIs must not be reintroduced as MCP tools. Compatibility endpoints retained for deployment transition must be explicit and documented rather than cluttering the primary reference.

This branch starts from the already-pushed authenticated quota exemption changes.

## Implementation results

MCP exposes exactly `search_studies`, `get_study`, and `query_data`, with read-only annotations. Validation and replacement tools and ingestion dependencies were removed. Transport tests verify discovery, rejected write calls, unchanged study data, current authentication, and private-study visibility.

The compact REST interface provides study and measurement lists, typed advanced queries, and authenticated dataset exports. Pagination uses `items`, `total`, `page`, `page_size`, `next`, and `previous`. Scientific selection and permission checks reuse the existing services. The Python client uses the v2 query/export routes while preserving its public result-page interface and keyword filter semantics. Browser email management now uses `/api/v1/me/emails/`.

The default deployment publishes 74 operations across 65 paths, compared with the previous 93 operations across 79 paths. Its primary researcher reference presents 39 operations across 31 paths, grouped into Data, Curation, Vocabulary, Authentication, My account, and System. `/docs/all` and `/openapi/all.json` add browser support, administration, and health operations. Legacy aliases, underscore CRUD, staged-file upload, and JSON suffix compatibility are disabled by default and explicitly enabled with `PKDB_LEGACY_API_ENABLED=true` when needed.

Browser scientific search and saved-filter endpoints remain available because they carry existing selection semantics; hiding them from the researcher reference is not claimed as removal. MCP write tools remain unavailable even when REST compatibility is enabled. Existing REST source validation and atomic study upload remain available to authorized curators.

Executable Python and curl examples are documented. The Python example runs against seeded real API routes and its observed result is checked against `tools/api_examples/expected-fixture.json`; the fixture is not presented as hosted database statistics.

## Verification

- Backend regression suite: 589 passed. Final email/reference checks: 14 passed, including both legacy and canonical owner-scoped email workflows.
- New REST data suite: 14 passed; public Python-client integration: 4 passed; MCP suite: 12 passed, including rejected writes and visibility boundaries.
- Python client suite: 102 passed. Backend migration-tool suite: 27 passed.
- Frontend: 82 unit tests passed; type checking and lint passed.
- Repository Ruff lint and formatting, backend and Python typing, and Zensical documentation build passed.
- A dependency deprecation warning remains from Starlette importing AnyIO's older `BlockingPortal` alias; tests have no failures.

Tests used isolated PostgreSQL schemas. Existing deployment containers and study data were not rebuilt or reset. These changes are local on `feat/822-api-simplification`; publishing and deployment are separate steps.
