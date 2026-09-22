# Frontend modernization and researcher search experience

Date: 2026-09-23. Status: Written specification awaiting user review. This document describes intended behavior, not completed implementation.

## 1. Intent and agreed scope

Modernize the PK-DB frontend to the latest stable compatible Vue and Vuetify releases, remove obsolete npm dependencies, and adopt current Vue application practices. Migrate all maintained frontend application source and tests to TypeScript. Improve the interface broadly, with researchers constructing searches and understanding results as the primary design audience.

The user approved staged migration of the existing frontend, full TypeScript adoption, grouped filters with a persistent query summary, an explicit Search action, shareable applied searches, clearer result scope, and behavior-focused verification. Existing research, account, and curation workflows remain available. Researcher needs determine layout priorities; account and curation pages receive the same technical migration and shared visual conventions.

Success means researchers can construct a query, understand what was applied, interpret returned data in scientific context, explore details without losing their place, and download the intended selection. Maintainers receive a supported, typed application with clear boundaries and reproducible checks.

Implementation defaults specified below make the agreed design concrete. They remain subject to review of this document.

## 2. Existing foundation

| Location | Current structure and migration concern |
| --- | --- |
| `frontend/package.json` | Vue 2, Vuetify 2, Vue Router 3, Vuex 3, Vue CLI tooling, old HTTP and Vue plugin dependencies, and Mocha-based component tests. Declared ranges are not evidence of installed versions. |
| `frontend/src/main.js` | Vue 2 bootstrap, global components, and plugin registration. |
| `frontend/src/store.js` | One store combines session, filter criteria, result counts, endpoints, and presentation state. |
| `frontend/src/http.js` | Cookie sessions, CSRF acquisition, and authentication error handling already exist and must be preserved. |
| `frontend/src/search.js` | Filter serialization and downloads are coupled to store state and mixins. |
| `frontend/src/components/search/` | Existing domain filter groups and autocomplete controls; scope is labeled ambiguously as “Concise.” |
| `frontend/src/components/tables/` | Entity-specific tables with shared request, pagination, and presentation mixins. |
| `frontend/src/components/plots/` | Plotly wrappers and Vega integration require compatibility and scientific-output checks. |
| `backend/src/pkdb/api/exports.py` | Existing filter creation, selection-based reads, and export contracts. |
| `backend/src/pkdb/db/selection.py` | Authoritative distinction between measurement-constrained selections and whole-study selections. |

The migration must inspect actual usage before classifying a dependency as unused or deprecated. Vue 2 incompatibility, npm deprecation, maintenance status, and redundancy are separate reasons for replacement and must be recorded separately.

## 3. Technical architecture

### 3.1 Toolchain and versions

Use Vite, Vue Single-File Components, TypeScript in strict mode, a compatible current Vue Router, and Pinia. Replace Vue CLI and obsolete Webpack/Babel/loader configuration. Use supported Node.js tooling, declare its required version, retain npm as the package manager, and commit a reproducible lockfile.

At implementation start, verify npm stable tags, peer dependencies, engine requirements, and official migration guides. Record exact selected versions and verification date in the implementation plan. Use the latest stable compatible Vue and Vuetify releases; do not silently substitute an older major or a prerelease. A compatibility blocker requires a documented resolution before locking the stack. Recheck versions before release and assess changes rather than applying untested upgrades automatically.

Move environment configuration to Vite conventions and update development proxies, container builds, static asset paths, and deployment configuration together. Preserve history-route fallback and existing same-origin API deployment behavior. Client environment variables contain public configuration only.

### 3.2 TypeScript and component conventions

Use `<script setup lang="ts">` for maintained components. Type props, emits, composable results, store actions, route inputs, and API boundaries. Replace reusable mixins with focused composables and prefer explicit component imports to broad global registration.

Migrate maintained application scripts and tests completely; do not leave JavaScript islands behind as the completion strategy. Configuration uses TypeScript where supported, with tool-required JavaScript exceptions documented. Strict checking includes Vue templates through `vue-tsc`; production compilation alone is insufficient.

Use `unknown` and narrowing for untrusted values. Do not suppress migration errors with blanket `any`, `@ts-nocheck`, or broad casts. Narrow third-party declaration exceptions must be explained locally. API type declarations do not replace runtime checks of critical response shapes.

### 3.3 Feature boundaries and state

Organize application code into search, results, study/detail exploration, plots, account, and curation feature areas, with shared components and a centralized API layer. Each feature owns its components and composables; shared code must have an actual cross-feature responsibility.

Use separate Pinia stores for session, search, and shared UI preferences. Keep transient component state local. Search state explicitly separates editable draft criteria from applied criteria. Result requests and counts are associated with the applied selection and cannot be updated by obsolete requests.

The URL is the durable representation of applied criteria and result-view state. Backend selection identifiers are derived request state, not the sole durable search representation. Do not persist credentials or unrestricted API result caches in browser storage. Clear permission-sensitive state on logout or identity changes.

### 3.4 API and resource lifecycle

Provide one typed request layer with domain-specific methods. Default to a current supported Axios release to preserve the existing session integration, replacing legacy cancellation with `AbortController`. Remove `vue-resource` after migrating or proving absence of its callers.

Preserve cookie credentials, CSRF acquisition and invalidation, expected anonymous browsing, login/profile initialization, and authorization behavior. Limit credentials and CSRF headers to the intended API origin. Differentiate unauthenticated, forbidden, missing, invalid-input, and network/server failures in the UI.

Components release subscriptions, listeners, object URLs, chart instances, and obsolete requests on replacement or unmount. Large plot dependencies load only when their feature is needed; lazy-load route components where appropriate.

## 4. Researcher search experience

### 4.1 Layout and controls

Provide a consistent application shell with a filter panel, persistent applied-query summary, result area, and contextual detail view. On narrow screens the filter panel becomes an accessible drawer and details use available screen space. Tables may scroll horizontally; surrounding controls and navigation must remain usable without page-wide overflow.

Group filters into Studies, Subjects, Interventions, and Measurements. Preserve currently supported criteria, including licence, subject category, and output-type selection. Use domain labels and contextual help, with terminology descriptions available by keyboard and touch rather than hover alone. Keep existing useful example searches and update their explanations to verified semantics.

Use shared spacing, typography, form, button, dialog, and table conventions. Preserve light/dark behavior where currently available and verify contrast in supported themes. Visual cleanup must retain the density needed for scientific tables.

### 4.2 Draft and applied query behavior

1. Editing a control changes the draft only. Autocomplete suggestions may update while typing; this does not execute the full search.
2. Show “Changes not applied” whenever the draft differs from the applied criteria. Existing rows, counts, and download actions remain explicitly associated with the applied query.
3. Search validates the draft, applies it, resets pagination, updates the URL, and requests counts and rows for that selection. Prevent duplicate submissions of the same in-flight operation.
4. Display removable draft selections and an always-identifiable applied summary. Removing a draft selection or using Reset updates the draft; Search applies that change. Reset restores documented default criteria and matching-measurement scope.
5. On initial navigation, execute the URL criteria, or the default unfiltered query if none are supplied. Restoring an applied URL does not require another click on Search.

Provide semantic, accessible controls and a visible Search button. Filter-combination explanations must follow the backend's field-specific semantics; do not assume every multiselect means OR or every cross-category match refers to the same entity.

### 4.3 URL and navigation contract

Serialize applied filters using stable identifiers rather than display labels, plus scope, active result tab, supported ordering, page, and page size. Use a versioned, deterministic URL representation with validation and explicit defaults. Preserve existing `/data` and `/data/:sid` entry points.

Browser Back/Forward restores applied criteria and result-view state, replacing the draft with the restored applied query. Refresh reconstructs the selection against current permissions and data. A shared URL represents criteria, not a frozen scientific dataset or an access grant. Invalid or unsupported parameters produce an actionable message rather than silently broadening a search.

Opening and closing details preserves filters, tab, pagination, and result position. If data changes make a restored page invalid, reset to a valid page with a brief explanation. No server-side user-saved-search feature is required for shareable URLs.

## 5. Result meaning and presentation

### 5.1 Selection scope

Replace “Concise” with a clearly labeled scope control, defaulting to **Matching measurements and related records** (`concise=true`). Explain that measurement constraints determine the selected measurements, with studies, subjects, and interventions derived from their relationships. Related records are context and must not all be labeled direct filter matches.

The alternative is **All data from qualifying studies** (`concise=false`). Explain that studies qualify through the configured study-level existence conditions, then their data is included more broadly. Conditions may be satisfied by different records in a study; this mode must not imply that every returned measurement jointly satisfies all selected filters.

These descriptions follow the current selection implementation. Before shipping, fixture-based backend checks must confirm exact field-combination, subject, intervention, and subset behavior. Preserve existing scientific semantics; discovering a discrepancy requires correcting the frontend description or explicitly reviewing a backend change.

### 5.2 Tables, counts, and exploration

Retain result categories for studies, groups, individuals, interventions, measurements, timecourses, and scatter data. Label each count by its entity and current selection scope. Do not sum heterogeneous counts into an invented total number of matches. Counts and rows must correspond to the same applied criteria and permission context.

Choose columns by result type. Measurement rows prioritize measurement type, substance, value and unit, subject context, and study provenance where supplied by the API. Make additional dose, route, and intervention context accessible through columns or details without inventing missing relationships. Study rows distinguish whole-study metadata/counts from selected-data counts when both are available.

Distinguish missing values from zero and preserve scientific precision, units, relationships, and provenance. Plot migration preserves series values, axes, units, uncertainty information, and supported interactions. Avoid unsupported client-side unit conversion or recalculation.

Do not introduce a “why this matched” explanation that the API cannot substantiate. Show the applied criteria and verified context; label broader study content explicitly. Use server-backed pagination and ordering where supported. Do not present sorting of one loaded page as sorting of the full result set.

### 5.3 Loading, failure, and download states

Cancel superseded requests and also use request identity checks so cancellation races cannot overwrite current state. When applying a new search, do not present previous counts or rows as its completed results. Distinguish initial loading, updating, successful empty results, and failures; offer retry for recoverable failures. Never translate a failed count request into zero matches.

Downloads use the applied query and scope, never unapplied draft changes. State that an export covers the selected dataset rather than only the visible page. Disable download while its applied selection is unresolved. Preserve backend permission and licence checks, supported export formats, and existing cancellation behavior. An explicit full-study download is labeled separately from a filtered selection export.

## 6. Dependency cleanup

Create an inventory of direct dependencies and relevant transitive deprecations, actual callers, replacement decisions, and compatibility evidence. Audit Vue-specific Plotly wrappers, multiselect, text highlighting, authenticated-image handling, Vuex persistence, icon packages, and old build/test loaders in particular.

Prefer modern Vuetify controls where they cover existing multiselect behavior. Use a small typed chart integration if the existing Vue wrapper has no supported migration path; retain chart engines where appropriate. Migrate authenticated images through the existing session model without introducing persistent bearer tokens. Remove redundant dependencies only after their behavior is accounted for.

Do not make “zero npm warnings” an unverified promise. Remove deprecated direct dependencies; resolve transitive deprecations through supported upgrades or replacements where possible. Record any unavoidable transitive exceptions with the dependency chain, impact, and follow-up. Keep audit findings separate from deprecation status and evaluate remediation rather than applying forced upgrades blindly.

## 7. Migration and release strategy

Use the existing frontend as the migration base. Deliver reviewable stages on development branches and release the completed application together. Intermediate stages need not be independently deployable, but their limitations and checks must be explicit.

1. Capture representative current behavior, routes, API contracts, and dependency usage; distinguish existing defects from required compatibility.
2. Establish Vite, strict TypeScript, supported framework versions, test tooling, and CI/build integration.
3. Migrate the API/session layer, router, and focused stores; introduce typed query serialization and draft/applied separation.
4. Migrate shared components and the researcher search/results experience, followed by details, plots, and exports.
5. Complete account, administration, and curation pages; remove obsolete source, packages, configuration, and temporary shims.
6. Run acceptance checks, review visual behavior, and produce the release evidence and deployment instructions.

Deploy through the existing static frontend delivery model. Preserve the previous deployable frontend artifact for rollback; this work does not require a database migration. Coordinate any discovered backend contract changes separately. Do not alter authentication policy or scientific selection semantics as an incidental frontend refactor.

## 8. Verification and acceptance criteria

Use Vitest and Vue Test Utils for unit/component behavior, and Playwright for browser workflows, after confirming compatibility in the selected toolchain. Rework useful existing tests rather than discarding their coverage. Use controlled representative data and backend integration checks; mocked browser responses alone cannot prove scientific selection semantics.

| Area | Required evidence |
| --- | --- |
| Query behavior | Round-trip URL serialization, defaults, invalid inputs, combined filters, subject/output-type toggles, reset, draft/applied separation, and both scope modes. |
| Result correctness | Counts and rows agree for representative selections; missing versus zero, units, provenance, related records, and whole-study context are distinguishable. |
| Concurrency and errors | Rapid searches cannot install stale results; empty, failed, unauthorized, and forbidden responses render correctly; retry works. |
| Researcher journey | Assemble and submit search, change tabs, paginate/order, open details and plots, return without losing context, refresh/share URL, and use browser Back/Forward. |
| Exports and plots | Export uses applied scope despite draft edits; representative exported identifiers/data match selection; chart data, labels, and supported interactions remain correct. |
| Account and curation | Existing registration, verification, login/provider flows, recovery, MFA, profile, invitations, keys, administration, and curation behavior remains available where currently implemented and authorized. |
| Accessibility and layout | Keyboard-only search and exploration, dialog/drawer focus management, visible focus, labels, error announcements, contrast, and usable wide/narrow layouts. |
| Build and deployment | Reproducible clean install, strict `vue-tsc` check, lint, unit/component and browser tests, production build, and direct history-route navigation through deployment configuration. |

CI must enforce type checking, linting, tests, and production build. Run existing repository checks affected by documentation and configuration changes as well. Record the commands, fixtures, environment, and results used for release verification; do not claim unexecuted checks passed.

Completion requires all maintained frontend source and tests to use TypeScript, no temporary Vue migration/compatibility shims, no unexplained type-check suppressions, resolved direct dependency deprecations, documented transitive exceptions, and verified researcher/account workflows. Review initial bundle and lazy-loaded chart behavior against the baseline and investigate material regressions without inventing an unsupported performance target.

## 9. Scope boundaries

This project does not introduce a new backend, a query language, a guided search wizard, account-saved searches, SSR/Nuxt, new scientific calculations, or a wholesale replacement of chart engines. UI cleanup is broader than a mechanical component upgrade, but new scientific capabilities and unrelated backend changes require separate scope decisions.

## 10. Reference guidance and review handoff

The architectural direction follows the official [Vue tooling guide](https://vuejs.org/guide/scaling-up/tooling), [TypeScript guidance](https://vuejs.org/guide/typescript/overview), [Composition API guidance](https://vuejs.org/guide/extras/composition-api-faq.html), and [Pinia recommendation](https://vuejs.org/guide/scaling-up/state-management.html#pinia). Verify current Vuetify release and migration guidance against the selected stable version during implementation planning.

After user review and approval of this written specification, prepare the implementation plan with exact version choices, package replacement decisions, file/task boundaries, backend-semantic verification fixtures, and stage-specific checks. Writing this specification does not authorize skipping that review or beginning product implementation.
