# Frontend modernization verification

Implementation branch: `feat/frontend-modernization`. Baseline: `0562a566` (`develop`). Work was authorized after the specification and implementation plan were written. This report distinguishes local implementation evidence from deployment checks requiring the live environment.

## Toolchain and dependency graph

Node 24.21.0 and npm 12.1.0 were used. Exact packages and compatibility evidence are in `docs/superpowers/plans/2026-09-23-frontend-modernization-versions.json`; `package-lock.json` is the reproducible installed graph. Vue 3.5.43, Vuetify 4.2.1, Router 5.3.1, Pinia 4.0.3, Vite 8.3.0 and TypeScript 6.0.3 are pinned. TypeScript 7 is excluded by the selected ESLint peer range, rather than installed with a peer override.

`npm ci` succeeds inside the pinned production container, including strict type checking and the production build. `npm ls --all` passes. The npm advisory check reports zero vulnerabilities. No lockfile package has a `deprecated` marker. These are dated observations, not a guarantee about future advisories. npm 12 blocks the optional `@parcel/watcher` source-build install hook; the supported prebuilt dependencies suffice and installation/build succeed without approving that hook.

Strict checking includes libraries, Vue templates, source, tests and configuration. Exact-version, exact-shape checked declaration corrections address defects in current Vuetify/Router declarations; [details and removal procedure](declaration-corrections.md) explain each correction. No runtime compatibility shim, `skipLibCheck`, global string index signature, explicit application `any`, or unchecked JavaScript source remains. Compile-time component-prop tests protect the precision of the corrected declarations.

The implementation uses an explicit list of Vuetify components in its application plugin. Theme is a safe local preference managed by Vuetify; there is no unnecessary duplicated UI store. Account and search state use separate Pinia stores. Creator/curator suggestions use profiles exposed by visible study responses; exact username entry is supported because the current backend has no public `/users/` directory. Measurement-type suggestions use the supported `dtype__exclude=abstract` parameter.

## Local checks

Run frontend commands from `frontend/`, with the pinned Node/npm versions:

```bash
npm ci
npm run test:source
npm run typecheck
npm run lint
npm run test:unit
npm run build
npm ls --all
npm audit --json
npx playwright install --with-deps
npm run test:e2e
```

- The source inventory, strict `vue-tsc`, and ESLint checks pass. The source check parses SFCs and TypeScript, requires typed script setup, rejects JavaScript application/test files, explicit `any` and blanket suppressions. Temporary migration exclusions were removed.
- 84 Vitest unit/component tests pass. Coverage includes query validation/canonicalization, unfinished draft input, all-off filters, applied exports, request/identity races, expiry/page recovery, session/CSRF boundaries, account behavior, details/files, vocabulary, plot lifecycle/scientific precision, home statistics, and keyboard/position helpers.
- The production build passes. Plotly remains a large dynamic chunk and Vite reports its standard chunk-size warning; the warning is not suppressed or mistaken for an initial-load regression.
- The production container installs from the lockfile and preserves the artifact-only `/vue` handoff. It does not silently replace the deployment's HTTP server.

Backend/repository commands, from the repository root:

```bash
uv sync --project backend --locked --python 3.14
PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test \
  backend/.venv/bin/pytest backend/tests -q -x
backend/.venv/bin/python -m pytest tools/backend_migration -q -x
backend/.venv/bin/ruff check .
backend/.venv/bin/ruff format --check .
backend/.venv/bin/ty check --project backend
backend/.venv/bin/python scripts/check_curator_roster.py
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
backend/.venv/bin/python scripts/llms_txt.py
```

The full backend suite passes: **500 tests**, including **13 frontend scientific contract cases**. Migration tooling: **27 tests passed**. Ruff, formatting, ty, curator assets and documentation build/generation pass. The backend suite reports three existing upstream warnings (Starlette's AnyIO portal alias and two Pydantic MCP serialization warnings). The initial local environment contained pymetadata 0.6.4 although the lockfile pins 0.6.5; synchronizing to the lockfile resolved the metadata-cache test failure without changing backend implementation.

## Real backend and browser evidence

`npm run test:e2e` owns only the disposable `pkdb-frontend-test` Compose project. It starts PostgreSQL, the real backend with full vocabulary and guarded artificial fixtures, and Nginx serving `dist/` on port 18184. It resets and cleans that isolated project, including on failure. It does not touch the default deployment. Browsers run serially with separate ordinary accounts to avoid cross-browser login throttling. MFA credentials, encryption keys and passwords in these fixtures are explicitly test-only. Browser traces are disabled; account tests also disable screenshots while secrets are displayed.

**90 browser tests passed** (30 each): Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6, using Playwright 1.63.0. The fresh harness completed successfully and removed its containers/network. The final production image was built and its `/vue` files inspected: `sha256:e1b5bc7aa983da89ef047e730a7c264f57bd0a9695fe4ea40e2f52999ed5a8d1`.

The browser suite covers:

- Direct entry and refresh for every preserved route, JSON/backend routing, absent assets, immutable hashed assets, HTML revalidation, cookies and CSRF, and API documentation routing.
- Draft versus applied criteria, browser history, independent table refinement, seven entity tabs, live autocomplete query construction, ZIP download, unknown/prototype-shaped URL rejection and invalid manual identifier recovery.
- The actual difference between oral intervention plus drug-b measured substance in matching scope (zero) and whole-study scope (one study, two scalar measurements). This is a cross-record scientific distinction, not a presentation-only count change.
- Keyboard tab navigation, refined study-detail return with restored row focus/input, narrow filter dialog focus, and WCAG accessibility checks after asynchronous rendering settles.
- Lazy Plotly requests, normalized coordinates/units, timecourse/scatter navigation, and vocabulary term detail.
- Ordinary account profile/privacy, key creation/rotation/revocation, session revocation/logout, curator/reviewer boundaries, and administrator recovery MFA, users, grants and audit. Mounted tests additionally cover provider callbacks/invitations, reauthentication, failed logout, private activity cleanup and reviewed-contact invitation delivery/retry.

The 13 PostgreSQL contracts verify exact scientific IDs, subject union/inheritance and same-characteristic conjunction, all-off categories, normalized type selection, visibility revocation, expired UUIDs, contextual subset points, table-refinement independence, and ZIP member/CSV identifier/value parity. Full-vocabulary browser fixtures normalize 2.125 mg/l to 0.002125 gram/liter; minimal contract fixtures retain 2.125 mg/l. The frontend preserves either server representation, including zero and null, with no unit conversion or recalculation. CV stays in the accessible data table instead of being incorrectly used as dimensional error bars.

## Visual and delivery review

Desktop, narrow, light, dark, filter dialog, scientific table and plot screenshots were inspected locally. Tables scroll within their container; native controls have explicit styling; labels meet contrast checks; mobile filters have persistent Close and Apply actions. Missing data stays distinct from zero. Search can supersede an in-flight query; invalid unfinished draft controls do not break rendering. `__proto__`-shaped URL keys are rejected before dictionary assignment. Returning from study detail restores table refinement text as well as results and focus.

The comparable baseline entry-asset measurements and retained legacy artifact/checksum are in [the baseline](modernization-baseline.md), with the recovered package graph and asset sizes under `baseline/`. Initial JS/CSS gzip payload falls by approximately 83%; Plotly is requested only after Show plot. Measurements exclude fonts/images/maps and route chunks for both builds. The legacy artifact was recovered locally, not claimed to be the actual deployed image; no retrospective legacy visual inspection is claimed.

## Deployment gates and limitations

Implementation and local acceptance do not deploy or create a new release. Before production cutover:

1. Preserve the actual deployed static artifact/image in durable release storage. The recovered local tar under `/tmp/pkdb-frontend-legacy` is useful migration evidence, not durable production rollback storage.
2. Verify the real reverse proxy, browser origin, cookie attributes, CSP and history fallback with the selected artifact. The checked-in Nginx fixture and `/vue` handoff are tested; the operator's production proxy is external to this repository.
3. Exercise live GitHub/ORCID redirects and SMTP delivery in staging using configured service credentials. Controlled callback/UI and backend tests cannot establish delivery by those external services.
4. Require the repository CI checks, including the newly mandatory frontend job, before merging and publishing. Recheck package advisories/versions deliberately without silently upgrading the tested artifact.

No database migration is required. Restore the retained production artifact atomically to roll back the frontend.

Local logs: `/tmp/pkdb-frontend-e2e-final.log`, `/tmp/pkdb-frontend-docker-final.log`, `/tmp/pkdb-modern-unit.log`, `/tmp/pkdb-integrated-typecheck.log`, `/tmp/pkdb-modern-backend-tests.log`, and `/tmp/pkdb-modern-docs.log`. Inspected screenshots: `/tmp/pkdb-modern-desktop.png`, `/tmp/pkdb-modern-dark.png`, `/tmp/pkdb-modern-mobile.png`, `/tmp/pkdb-modern-mobile-filters.png`, and `/tmp/pkdb-modern-plot.png`. CI preserves failure reports/screenshots and the modern static artifact; local `/tmp` paths are not durable release storage.
