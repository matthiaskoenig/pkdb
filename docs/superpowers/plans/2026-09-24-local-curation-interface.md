---
search:
  exclude: true
---

# Local curation implementation plan

Status: Implemented and verified locally. Implements [#826](https://github.com/matthiaskoenig/pkdb/issues/826) and the [agreed specification](../specs/2026-09-24-local-curation-interface-design.md).

1. Build a package-owned workspace and background job engine using existing preparation, reports, vocabulary cache, and upload code. Persist settings/history outside source folders; watch settled source changes, coalesce jobs, and enforce validated snapshots and uncertain-write blocking.
2. Add GitHub read integration with repository-user selection, issue pagination/cache, exact/manual study mapping, and offline behavior. Add a small API-key-compatible server identity/curation-context read endpoint.
3. Add a loopback HTTP service with launch-session authentication, CSRF/Origin/Host checks, constrained default-app file opening, and `pkdb curation` CLI lifecycle.
4. Bundle an accessible local browser UI with workspace selection, assignments, diagnostic/file actions, save modes, queue activity, and connection settings. Use dependency-free browser modules and the Python standard-library HTTP runtime to keep the normal package self-contained without a build-time dependency on the hosted frontend. This refines the specification's suggested Vue reuse without changing user workflows.
5. Test concurrency, file changes, invalid inputs, credentials, uncertain writes, GitHub failures, and local transport boundaries. Exercise the app in a browser against real local study files and isolated upload data, preserving original sources.
6. Replace documentation mockups with screenshots from the running app; verify clean wheel packaging, supported entry points, repository checks, and documentation builds. Record actual results and limits below.


## Verification

The local browser app was exercised against all 30 apixaban folders in `pkdb_data`. Screenshots in the user guide are captures of that running app. An isolated PostgreSQL integration test created 24 studies and replaced those same 24 on a second pass; six studies failed validation on each pass. Source hashes were unchanged. These counts describe the tested checkout and vocabulary, not permanent corpus expectations.

The full backend regression suite passed (594 tests before the final curation-specific additions). The final combined public-client and curation API suite passed (139 tests), including real server validation without persistence, externally saved changes followed by replacement, invalid-source rejection, personal-key scope enforcement, and private assignment isolation. Additional tests cover GitHub failures, source snapshots, save coalescing, ambiguous outcomes, credential redaction, local HTTP protections, and bounded vocabulary refresh. Browser checks passed for uploads, assignments, diagnostics, cancellation, history, unknown-outcome review, and responsive layout. Ruff, both Python type checks, and the clean Zensical documentation build passed. The wheel and source distribution built successfully; an isolated wheel installation includes all browser assets and exposes `pkdb curation --help`.

## Implementation boundaries

The initial implementation uses a single serialized worker for validation and uploads, one-second filesystem polling, and browser polling for state updates. GitHub refresh is explicit or at startup, caches complete results, and stops with visible cached data on service errors; conditional ETag requests and automatic retry scheduling remain follow-up work. Pagination is bounded to 10,000 entries per resource. The selector uses repository assignees with issue-assignee fallback, not a search across every GitHub account; it displays available logins/names without fetching avatars.

Finished job history retains the latest 100 records while preserving queued, running, and unknown jobs. Explicit history clearing removes finished reports. Independent validation failures continue the queue; there is no separate stop-on-first-validation-error setting yet. Systemic failures pause work. Default-application dispatch is tested with mocked OS launchers; actual spreadsheet/PDF applications require verification on the curator's desktop. The bundled app requires an updated server for authenticated curation context. No existing deployment database or source study files were changed.
