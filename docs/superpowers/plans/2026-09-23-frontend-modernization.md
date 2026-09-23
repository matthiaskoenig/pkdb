# Frontend modernization implementation plan

Date: 2026-09-23. Status: Implemented; final local acceptance is recorded in [the verification report](https://github.com/matthiaskoenig/pkdb/blob/develop/frontend/docs/modernization-verification.md). Specification: [Frontend modernization and researcher search experience](../specs/2026-09-23-frontend-modernization-design.md). Baseline: `0562a566` on `develop`. The user subsequently authorized implementation without interruption. Deployment and a new release remain separate from this implementation request.

## Goal and execution rules

Migrate the maintained frontend in place to Vue 3, Vuetify 4, Vite, strict TypeScript, Vue Router, and Pinia. Deliver grouped draft filters, explicit Search, shareable applied criteria, meaningful selection scope, trustworthy tables/plots/exports, and preserved account, administration, and curation behavior. Release the completed application together; intermediate migration commits are not deployable replacements.

Follow `CLAUDE.md`, the applicable `AGENTS.md`, and `docs/development.md`. Use a topic branch from current `develop`, reviewable commits, and a pull request. Preserve a reproducible legacy artifact before changing the toolchain. Do not deploy partial routes, introduce a second backend, change authorization or scientific calculations, or modify production data to create test fixtures. Backend changes in this plan are tests and isolated fixture tooling, unless a separately reviewed contract correction becomes necessary.

Each task below specifies prerequisites, file boundaries, behavior, and a completion gate. Write a meaningful failing test for new behavior or a reproduced defect, implement the smallest coherent change, run that task's checks, and commit it. Mark checkboxes only after execution with evidence. Stop dependent work at a failed gate; continue independent tasks where possible. Do not use passing production compilation as evidence that TypeScript, accessibility, or scientific behavior is correct.

## 1. Version decisions and evidence

Public npm registry stable tags, selected-version metadata, peer ranges, and the Node.js release index were queried on **2026-09-23, Europe/Berlin**. These are exact planning selections, not claims that the future application has already installed or passed tests with them. Task 2 must resolve the complete graph and exercise the smallest real Vue/Vuetify/TypeScript application before committing the lockfile. Recheck stable tags at implementation start and again before release; record deliberate changes and rerun affected checks.

| Area | Selected exact versions | Compatibility decision |
| --- | --- | --- |
| Runtime/package manager | Node `24.21.0`, npm `12.1.0` | Node 24 is the verified LTS line. This Node version meets npm, Vite, Vitest, ESLint, and jsdom engine ranges. Pin `.nvmrc`, Docker/CI tooling, `engines`, and `packageManager` consistently. |
| Framework | `vue@3.5.43`, `vuetify@4.2.1` | Both are the verified `latest` stable tags. Vuetify accepts Vue `^3.5.0`; Vue 3.6 prereleases and Vuetify's older-major tags are not the target. |
| Routing/state | `vue-router@5.3.1`, `pinia@4.0.3` | Router accepts Vue `^3.5.34`, Vite 8, and Pinia 4. Pinia accepts Vue `^3.5.11`; its required `@vue/devtools-api` peer must resolve in the lockfile. Use explicit route definitions, not new experimental loaders or file-based routing. |
| Build | `vite@8.3.0`, `@vitejs/plugin-vue@6.0.9`, `vite-plugin-vuetify@2.1.3` | Published peer ranges overlap. Configure explicit component imports; do not enable blanket application auto-imports. |
| Vue compiler | `@vue/compiler-sfc@3.5.43`, `@vue/compiler-dom@3.5.43` | Match Vue exactly where directly needed by build/test tooling; avoid duplicate compiler versions. |
| Type checking | `typescript@6.0.3`, `vue-tsc@3.3.11`, `@types/node@24.13.6` | TypeScript `7.0.2` is latest, but `typescript-eslint@8.70.1` requires `>=4.8.4 <6.1.0`. Select stable 6.0.3 deliberately; this resolves the known peer blocker without forcing dependencies. Node types match Node's major. |
| HTTP | `axios@1.20.0` | Preserve the cookie/CSRF model with an isolated Axios instance and `AbortController`. |
| Lint | `eslint@10.11.0`, `@eslint/js@10.0.1`, `eslint-plugin-vue@10.11.0`, `vue-eslint-parser@10.4.1`, `typescript-eslint@8.70.1`, `jiti@2.7.0` | Flat `eslint.config.ts`, using jiti for TypeScript configuration loading. Check typed Vue template/script parsing in Task 2. No need for an additional Vue ESLint preset package. |
| Unit/component tests | `vitest@5.0.1`, `@vue/test-utils@2.5.1`, `jsdom@30.1.1` | Vitest supports Vite 8; VTU supports Vue 3. jsdom requires at least Node 24.15 on this LTS line. |
| Browser/accessibility tests | `@playwright/test@1.63.0`, `@axe-core/playwright@4.13.0` | Install matching Playwright browser binaries in CI; automated accessibility checks supplement manual keyboard/visual review. |
| Styles/icons | `sass@1.105.0`, `@fortawesome/fontawesome-free@7.3.1` | Retain the existing icon family and SCSS use; map renamed icons explicitly and check rendering. |
| Active plotting | `plotly.js-dist-min@4.1.1` | Remove the Vue 2 wrapper. Use a lazy, narrow typed adapter for the actually used Plotly functions and trace fields. The registry's `@types/plotly.js@3.0.13` targets a different major: do not install it and broadly cast a v4 module to make errors disappear. Task 12 owns documented local declarations and real-browser validation. |

Metadata sources: [npm registry](https://registry.npmjs.org/), [Vue stable metadata](https://registry.npmjs.org/vue/latest), [Vuetify stable metadata](https://registry.npmjs.org/vuetify/latest), [TypeScript ESLint metadata](https://registry.npmjs.org/typescript-eslint/8.70.1), and [Node release index](https://nodejs.org/dist/index.json). Exact selections and relevant peer evidence are recorded in the adjacent [version evidence](2026-09-23-frontend-modernization-versions.json).

Use the official [Vue tooling guide](https://vuejs.org/guide/scaling-up/tooling.html) and [Vue 3 breaking changes](https://v3-migration.vuejs.org/breaking-changes/) for bootstrap, models, slots, and lifecycle migration. Apply both [Vue Router's Vue 2 migration](https://router.vuejs.org/guide/migration/) and [Router 5 guidance](https://router.vuejs.org/guide/migration/v4-to-v5.html). Use the [Pinia Vuex migration guide](https://pinia.vuejs.org/cookbook/migration-vuex.html), [Vuetify installation](https://vuetifyjs.com/en/getting-started/installation/) and [upgrade guide](https://vuetifyjs.com/en/getting-started/upgrade-guide/), [Vite guide](https://vite.dev/guide/), and [Vitest guide](https://vitest.dev/guide/). Vuetify's guide is client-rendered and did not expose its detailed migration text to the planning reader: read the selected v4 guidance and linked v2/v3 changes during Task 2, then record the component-specific decisions; do not claim that review already passed.

## 2. Dependency disposition

The current `frontend/package.json` has no committed npm lockfile. Its ranges do not establish the old installed dependency graph. The following conclusions come from source reachability, not from inferred npm deprecation status.

| Current package(s) | Caller evidence | Planned action |
| --- | --- | --- |
| Vue, Vuetify, Router, Axios, Font Awesome | Bootstrap and maintained feature components | Upgrade to the selected stack; preserve behavior through focused tests. |
| `vuex` | `store.js`, store mixins, component callers | Replace with session/search/UI Pinia stores. |
| `vue-multiselect` | `search/{InfoNodeSearch,ReferenceSearch,UserSearch,StudySearch}.vue` | Replace with typed Vuetify autocomplete controls, retaining multiselect, suggestions, labels, and keyboard behavior. |
| `vue-text-highlight` | `tables/{StudiesTable,InfoNodeTable}.vue` | Replace with a small escaped-text `HighlightText.vue`; never interpolate untrusted HTML. |
| `@statnett/vue-plotly` | `plots/{ScatterPlot,TimecoursePlot}.vue` | Replace wrapper with lazy Plotly adapter; preserve plotted scientific values and interactions. |
| `vue-resource`, `vue-auth-image` | Registered in `main.js`; no active `$http`/directive caller found | Remove registration and dependencies after Task 1 confirms template/dynamic usage. Actual authenticated images use Axios in `GetFile.vue`. |
| `acorn`, `base-64`, `vuex-persist`, `vue-plotly` | No maintained application/test caller found | Remove unused direct declarations. Do not confuse `vue-plotly` with the active Statnett wrapper. |
| `vega`, `vega-lite`, `vega-embed` | Sole chart consumer `StatisticsVegaPlot.vue` has no active caller; Home reference is commented | Remove after baseline reachability confirmation. Do not spend this migration upgrading an unused chart feature. If a real entry point is discovered, retain the feature and document compatible engine choices before removal. |
| `sass` | `App.vue` uses SCSS | Retain current Dart Sass. |
| Vue CLI/Babel/Webpack plugins, `vue-template-compiler`, Chai, CSS/style/Sass/Stylus loaders, Stylus, CLI Vuetify plugin | Old build and Mocha harness; no Stylus source found | Replace with Vite/Vitest/VTU and remove configurations once replacements work. Vite does not need Webpack loaders. |

Task 1 records each declared package, actual resolved version if recoverable, caller, npm `deprecated` field, Vue-major compatibility, replacement, and removal verification in `frontend/docs/dependency-audit.md`. Audit findings are separate from deprecation findings. For transitive deprecations, record the full chain, upstream evidence, impact, and follow-up after resolving the new lockfile. No `--force`, `--legacy-peer-deps`, blanket overrides, or promises of zero warnings.

## 3. Application and API contracts

### Proposed source boundaries

Configuration, test, and package paths below are relative to `frontend/` unless explicitly repository-root paths such as `backend/`, `docs/`, `.github/`, `tools/`, or `compose.frontend-test.yaml`. In task lists, source shorthand (`api/`, `stores/`, `features/`, `components/`, `plugins/`, `router.js`, `store.js`, `http.js`, and other current application scripts) is relative to `frontend/src/`; paths already starting with `src/` are frontend-relative. Move and refactor the existing components into these boundaries; preserve their useful behavior rather than replacing them with placeholders.

```text
src/
  main.ts, App.vue, env.d.ts
  router/index.ts
  plugins/vuetify.ts
  api/{client,errors,contracts,session,search,results,files,account,admin}.ts
  stores/{session,search,ui}.ts
  features/
    search/{model,defaults,fields,codec,serialize,useSearchController}.ts
    search/components/*.vue
    results/{types,columns,useResultPage}.ts
    results/components/*.vue
    details/{types,useDetailNavigation}.ts
    details/components/*.vue
    plots/{types,plotly,usePlot}.ts
    plots/components/*.vue
    exports/{useSelectionExport,useFileDownload}.ts
    account/{useAccountActivity,useProfile,useCredentials}.ts
    account/components/*.vue
    admin/{useAdministration}.ts
    admin/components/*.vue
    curation/{useVocabulary}.ts
    curation/components/*.vue
  components/{layout,common}/*.vue
  styles/{tokens,app}.scss
  types/plotly-dist-min.d.ts
```

Use discriminated unions for result/loading/error states, typed props/emits, and `unknown` plus narrowing at external boundaries. Keep declarations for the supported response envelopes and critical scientific fields in `api/contracts.ts`; these do not substitute for runtime validation. Do not add a generic schema framework merely to type a few known responses. All maintained SFC scripts use `<script setup lang="ts">`; configuration, tests, and application scripts use TypeScript where supported.

### Durable search state

Adopt `/data?v=1&q=<percent-encoded canonical JSON>&scope=matching&tab=studies&page=1&pageSize=20`, with optional `order=<allowlisted field>` and `tableSearch=<encoded text>`. `q` contains only stable filter values, subject toggles, licence toggles, and output-type toggles. Use fixed field ordering, sorted/deduplicated set-valued arrays, and `URLSearchParams`; do not use base64, display labels, or selection UUIDs. Scope values are `matching` and `studies`, translated to `concise=true/false`. Tabs are `studies`, `groups`, `individuals`, `interventions`, `measurements`, `timecourses`, and `scatters`.

Canonical defaults: empty criteria, both subject categories, both licences, all three output types, matching scope, studies tab, page 1, page size 20, backend default ordering, and empty table search. Restrict page size to the documented UI choices 20/50/100. Reject unknown versions/keys, malformed JSON, unsupported filters/order fields, nonpositive or fractional pages, and invalid enum values with an actionable error; do not issue an unfiltered query after decoding failure. A user explicitly choosing Reset can recover. Show unknown/unavailable selected identifiers without silently dropping them and broadening the query.

Draft edits, chip removal, and Reset affect only the draft, including its scope. Search validates and freezes the applied criteria, resets page, pushes the URL once, and requests a selection. Tab/page/order actions operate on the applied query and push result-view state without applying draft edits. Back/Forward restores applied criteria and replaces the draft. Initial valid URL navigation automatically executes; parameter-free navigation uses the defaults. Do not push another history entry while reacting to a route change.

Retain `/data/:sid` as a study entry point with the originating query parameters when reached from results. Detail navigation stores the originating row key, scroll position, and focus target in router history/local view state. Closing returns to that location; a direct detail entry has a deterministic results fallback. If a path SID and URL criteria disagree, display the path's study as separately labeled context while retaining the applied query; never silently rewrite the search.

Preserve the existing server-backed “Search table” (`search_multi_match`) as an explicit table refinement, with its own local draft and Apply/Enter action. Its applied text lives in `tableSearch`, resets the page when changed, and affects only that entity request. On tab changes clear table search and reset the page; on main Search clear table refinement. Show the refined row count separately from the selection-wide entity badge, and label dataset exports as excluding this table-only refinement. Include that distinction beside the refinement and export controls. Back/Forward restores the applied table search; typing alone does not reload rows or change dataset selection. Do not promote this refinement into scientific selection criteria without a separately verified backend contract.

A request generation combines applied-query identity, current identity/permission epoch, entity/tab, page, page size, ordering, table search, and all endpoint-specific row filters (including subset data type). Abort superseded requests and check this generation before installing either success or failure. Identity changes invalidate selections, result/count caches, details, exports, CSRF state, and outstanding callbacks. A `ready` selection must belong to the current epoch. No credentials or unrestricted result data are stored persistently.

### Verified endpoint boundaries

| Operation | Existing contract to use |
| --- | --- |
| Apply criteria/counts | `GET /api/v1/filter/?format=json&concise=true&<entity-prefixed criteria>` returns `uuid`, `studies`, `groups`, `individuals`, `interventions`, `outputs`, `timecourses`, `scatters`. |
| Entity tables | `/api/v1/{studies,groups,individuals,interventions,outputs}/?uuid=...&page=...&page_size=...&ordering=...`; unwrap `{current_page,last_page,next_page_url,prev_page_url,data:{count,data}}`. |
| Timecourses/scatters | `/api/v1/subsets/?uuid=...&data_type=timecourse` or `data_type=scatter`; one displayed row per subset. There is no `/pkdata/scatters/` route. |
| Flat scientific rows | `/api/v1/pkdata/{entity}/`; relationship expansion means row counts can differ from entity counts. Do not feed these counts into table badges. |
| Selected export | `/api/v1/filter/?<applied criteria>&concise=...&download=true` produces ZIP and recreates a selection. This route does not accept selection UUIDs. No new CSV button is promised by an internal CSV writer. |
| Ordinary details | Existing `/api/v1/{entity}/{identifier}/`; these are permission-scoped and generally not restricted by `uuid`. Label whole-study/detail context explicitly. |

`__in` uses `__` separators in the existing API; serialize through a field registry with `URLSearchParams`, not string concatenation. Distinguish SID and display-name fields. Repeated predicates/different fields are conjunctive; `in` alternatives are disjunctive. Subject and characteristic relations have additional semantics specified in the fixture matrix below. Reject values that cannot be faithfully represented by the existing delimiter contract rather than silently changing their meaning.

Saved UUIDs expire after 24 hours and have ownership/permission constraints. On confirmed expiry, reconstruct once from applied criteria, show that results were refreshed, and bound retries. On authorization change, clear protected data and show the appropriate state rather than retrying around access control. An empty first page succeeds; an invalid later page returns 404. Only treat a verified pagination failure as a reason to reset to page 1; do not conflate missing studies or selections with pagination errors.

Counts, rows, and exports are live re-evaluations, not a transactional snapshot. Fixed-fixture tests require exact agreement. If real data changes between requests, reconcile counts or reload with an explanation; never promise a frozen scientific dataset or access grant in a shared URL.

## 4. Scientific verification fixture

Task 4 adds `backend/tests/fixtures/frontend_search.py` and `backend/tests/api/test_frontend_search_contract.py`, extending existing `test_exports.py`, `integration/test_filter_selection.py`, `test_subject_filters.py`, and `test_combined_subjects.py` where that avoids duplication. Use stable scientific keys and resolve generated database IDs in assertions. The browser fixture loader reuses this controlled data; do not use private production studies.

| Case | Concrete fixture and required assertion |
| --- | --- |
| Joint match versus qualifying study | A study has oral I1 linked only to substance-A O1 and IV I2 linked only to substance-B O2. Query oral plus substance B: matching scope yields no selected measurements/study; whole-study scope qualifies the study via different records and includes broader normalized data. |
| Related intervention context | Add substance-B O3 linked to both I1 and I2. Matching oral+B selects O3 and includes both related interventions; IV I2 must not be labeled a direct route match. |
| Same intervention | Requested substance and route occur on different interventions, neither satisfying both: no intervention qualifies. |
| Subject union and toggles | Include matching group and individual outputs, inherited characteristics, and a nonmatching individual. Test both/group-only/individual-only/neither; explicitly exclude disabled categories, using verified no-match predicates such as `groups__id__in=0`, not omission. |
| Characteristic conjunction | Put sex and species in separate characteristic rows. Choice plus measurement type must match the same effective characteristic; test inheritance and overrides. Do not invent arbitrary cross-row subject conjunction. |
| Subset context | One selected and one nonmatching timecourse point; a scatter with selected X and contextual Y. Selected subset arrays retain context, so plot captions cannot claim every point matched. |
| Types and origin | Include scalar `output`, `timecourse`, `array` and raw/calculated counterparts. Check all output toggles, including none; maintain the backend's normalized selection semantics. |
| Licence and visibility | Equivalent public-open, public-closed, and private studies. Assert licence and access separately; closed-licence public metadata visibility does not imply attachment download access. Test anonymous, ordinary, assigned curator, reviewer, and administrator contexts where applicable. |
| Counts versus expanded rows | One output with two interventions and a group with three characteristics: nested/overview counts count entities; flat export rows expand relationships. |
| Pagination/order/precision | Multiple pages, duplicate sort values, nulls, zero, small/large values and units. Assert stable ID ordering, no duplicates, null handling, supported sort fields, and explicit invalid-page recovery. |
| ZIP parity | Export applied criteria after changing the draft. Compare deduplicated scientific IDs, preserve the eight existing CSV members plus README/terms, and account for full vocabulary context and the existing empty-CSV representation. |
| Revocation/expiry/races | Expire UUID, revoke visibility, switch users, and delay old responses. No protected state survives identity changes; recreated criteria reflect current access. |

Existing frontend defects to correct, not preserve: Reset aliases mutable defaults and omits licence/concise handling; all licences off emits invalid unprefixed `licence__in=0`; table ordering is currently commented out. Add regression cases for fresh defaults, `studies__licence__in=0`, and entity-specific server ordering.

## Implementation record

Tasks 2-15 and the local implementation/acceptance work in Task 16 are implemented. The final local evidence is 84 unit/component tests, 90 real-backend browser cases across three engines, 500 backend tests (including 13 scientific contract cases), 27 migration-tooling tests, strict type/lint/source checks, a clean production container build, and documentation/asset validation. See the linked verification report for commands and limitations.

Checkmarks below record resulting implementation coverage, not a claim that development followed every proposed chronological step. Task 1 recovered the legacy source/artifact, package graph and bundle measurements; a historical authenticated visual baseline was not available and is not claimed. The modern interface was inspected directly in both themes and viewport sizes. Production provider/SMTP/proxy/rollback gates and merging/releasing remain separate, explicitly unchecked actions. No deployment or new release was performed.

## 5. Ordered implementation tasks

### Task 1: Capture the baseline and migration ledger

**Depends on:** Nothing. **Files:** Create `frontend/docs/{modernization-baseline,dependency-audit,migration-coverage}.md`; inspect all `frontend/src`, `frontend/tests`, Dockerfiles, `docs/{installation,deployment,local-upload-testing}.md`, and existing workflows.

- [x] Inventory every maintained route/component/test and map it to a destination task. Include dynamic/global component registrations, asset references, and aliases, not only static imports.
- [ ] Capture researcher searches, account/admin screens, vocabulary browsing, wide/narrow layouts, both themes, console errors, initial bundle sizes, and lazy plot behavior. Record actual commands and environment; mark pre-existing failures explicitly.
- [x] Recover the last deployable artifact/lockfile from trusted build evidence if available. If unavailable, reproduce a legacy build in an isolated directory with its supported old toolchain, record the resolved graph and limitations, and retain the artifact/checksum before cutover. Do not treat today's unconstrained `npm install` as the historical baseline.
- [x] Record package removal evidence and confirm unreachable `_deprecated/StudyDetail.vue`, `TimecoursesPlot.vue`, and `StatisticsVegaPlot.vue`. Preserve public avatar paths consumed by `scripts/check_curator_roster.py`.
- [x] List all routes: `/`, `/data`, `/data/:sid`, `/curation`, `/invitation`, `/account`, `/verification/:id`, `/registration`, `/request-password-reset`, `/reset-password/:id`, `/404`, and catch-all. `/curation` currently browses vocabulary; do not invent an upload editor.

**Gate:** Every maintained behavior has an owner and fixture/check; rollback artifact is identified or explicitly blocks final release. Commit the baseline and ledger, not generated build output or credentials.

### Task 2: Prove and install the selected toolchain

**Depends on:** Task 1. **Files:** Modify `package.json`; create `package-lock.json`, `.nvmrc`, `.npmrc`, `tsconfig*.json`, `vite.config.ts`, `vitest.config.ts`, `eslint.config.ts`, `src/env.d.ts`, `plugins/vuetify.ts`, and root `index.html`. Migrate `main.js` to `main.ts` and bootstrap in `App.vue`.

- [x] Verify the version table again. Resolve peers with normal npm behavior in a disposable directory first; check strict SFC compilation, a Vuetify form/dialog/table, a Pinia store, a Router route, a VTU mount, and a Vitest test. Record the graph and any upstream deprecations. Do not lock a combination that merely installs but cannot type-check.
- [x] Configure `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, bundler module resolution, and Vue template checks. Include source, unit/component/browser tests, and TypeScript configuration in explicit projects; use compatible DOM/Node libraries without blanket suppressions.
- [x] Define scripts `dev`, `build`, `preview`, `typecheck`, `lint`, `test:unit`, `test:e2e`, and `test:source`. Set exact direct versions, lockfile-driven `npm ci`, and `packageManager: npm@12.1.0`. Node 24.21.0 bundles npm 11.19.0: explicitly bootstrap npm 12.1.0 (for example `npm install --global npm@12.1.0` in the selected Node environment) and assert `node --version`/`npm --version` before installation in local instructions, Docker, and CI; `packageManager` alone does not switch npm. Keep a documented `serve` alias only if current operator commands need it.
- [x] Replace Vue 2 bootstrap with `createApp`, Pinia, router, and Vuetify 4. Migrate actual shell components as the first slice; maintain a ledger of unported routes. No Vue compatibility runtime, fake completed screens, or deployment of this partial graph.
- [x] Replace Vue CLI HTML interpolation and `process.env.VUE_APP_API_BASE` with typed public Vite configuration. Keep development port 8080, same-origin proxies, and public asset paths. Document temporary unported source exclusions and remove them in Task 16.

**Gate:** Clean install, strict sample/template checks, lint, component tests, and Vite build pass on pinned tooling. Partial-feature limitations are explicit. Retire obsolete build configuration once its replacement is in place, with final removal verified in Task 16.

### Task 3: Establish the test and CI harness

**Depends on:** Task 2. **Files:** Create `tests/{setup.ts,fixtures/*}`, `tests/e2e/*.spec.ts`, `scripts/check-source.ts`, `tests/deployment/nginx.conf`, `playwright.config.ts`, `.github/workflows/frontend.yml`, and `compose.frontend-test.yaml`; modify `.github/workflows/ci-cd.yml` and `.gitignore` for test artifacts.

- [x] Configure Vitest/jsdom and Vue Test Utils with real Vuetify mounting helpers, necessary browser API stubs, and deterministic timers. Separate mocked UI tests from real-backend browser tests.
- [x] Create the minimal static-server/reverse-proxy fixture now, and Playwright setup serving production-built assets. Begin with an anonymous shell/direct-route smoke using a minimally bootstrapped test backend; attach Task 4's scientific fixture loader after that task is complete. Add test-only mail/provider doubles when account tests arrive. Pin browser versions through the Playwright package; save traces/screenshots on failure without tokens/passwords.
- [x] Use an isolated Compose project, dedicated test database/storage and ports, health readiness, and guarded fixture loading. Do not connect this harness to an existing deployment or delete unrelated volumes. Reuse the repository's isolated-schema approach.
- [x] Add a reusable frontend workflow called from CI-CD. Bootstrap/assert the selected Node/npm versions. Enforce `npm ci`, source coverage, strict type checking, lint, unit/component tests, build, and browser tests. Extend the existing `tests` aggregate to require the frontend job on PRs, develop, and release tags; keep backend checks intact.
- [x] Create the ledger-aware `scripts/check-source.ts` and wire `test:source` now; temporarily allow only explicitly inventoried unported modules, and make new unexplained JS or suppressions fail. Start with one real mounted shell test and one real browser route smoke. Unmigrated feature checks stay visibly incomplete in the ledger; they must not be represented by permanently skipped acceptance tests.

**Gate:** CI fails on a deliberate type/test/build error and can run the isolated browser smoke reproducibly. This gate proves the harness, not full feature completion.

### Task 4: Lock down scientific API semantics

**Depends on:** Task 1; browser fixture sharing uses Task 3. **Files:** Backend fixture/contract tests named in section 4; create `frontend/tests/fixtures/search-contract.ts` and test-only fixture loading support under `tools/frontend_testing/`.

- [x] Implement the complete fixture matrix through existing ingestion/services and PostgreSQL, with public/private roles and stable scientific identities. Browser seeding requires an explicitly named test database and fails closed without it.
- [x] Confirm field allowlists, nested response envelopes, ordering, subject unions, related records, subsets, all-off toggles, and export members through actual API requests.
- [x] Record authoritative endpoint/field examples for the TypeScript boundary. Use backend response fixtures as evidence, not as a replacement for integration tests.
- [x] Resolve discrepancies by correcting frontend labels/serialization or proposing a separate backend contract change. Do not weaken expected scientific results to match a convenient UI implementation.

**Gate:** Targeted PostgreSQL contract tests pass, and expected scientific IDs/counts are documented for both scope modes. Tasks 7–12 use these fixtures.

### Task 5: Migrate HTTP, sessions, and permission-sensitive state

**Depends on:** Tasks 2–3. **Files:** Replace `http.js` with `api/{client,errors,contracts,session}.ts`; create `stores/session.ts`; migrate session portions of `store.js` and consumers. Tests: `tests/unit/{http-client,session-store}.spec.ts`.

- [x] Test intended API origin restrictions, single in-flight CSRF acquisition, cookie credentials, unsafe-method headers, CSRF invalidation, anonymous startup, 401 versus 403, malformed responses, aborts, and retryable errors before replacing interceptors.
- [x] Use an isolated Axios instance and domain methods; never attach credentials/CSRF to an arbitrary externally supplied URL. Preserve cleanup of old `token`, `username`, and `vuex` browser-storage entries.
- [x] Model unknown/loading/anonymous/authenticated/error states and an identity epoch. Login, logout, revocation, and failed session refresh must not be mistaken for ordinary empty result sets.
- [x] Guard CSRF/session in-flight completions against identity changes; clear selection, details, exports, and activity state through explicit store/composable reset contracts. Preserve password and MFA-secret cleanup and failed-logout feedback.

**Gate:** Mounted/unit tests prove session behavior and cross-origin header isolation. No persistent bearer credentials or duplicate global interceptors remain.

### Task 6: Migrate routing, layout, and shared conventions

**Depends on:** Tasks 2, 5. **Files:** Replace `router.js`, `icons.js`, `components/navigation/*`; migrate `App.vue`, Home/Page404, maintained `home/*`, and shared `lib/*` into layout/common components. Create `stores/ui.ts` and styles.

- [x] Preserve all routes from Task 1 using lazy route imports and a Vue Router catch-all. Keep login/provider callback and reset/verification route parameters intact. Unknown paths remain explicit 404s.
- [x] Implement shared responsive navigation, typography/spacing, buttons/forms/dialogs, focus styles, density, and accessible status messages. Persist only documented safe UI preferences such as theme.
- [x] Replace implicit global registrations and mixin formatting with explicit imports and typed helpers. Map Font Awesome names and preserve custom scatter icon meaning.
- [x] Test drawer/dialog focus trap, escape/close behavior, return focus, keyboard navigation, both themes, and narrow screens without page-wide overflow.

**Gate:** Route smoke and shell component/browser checks pass. Remaining route limitations are still recorded; no account or curation workflow is declared complete yet.

### Task 7: Implement the query model, serializer, and URL codec

**Depends on:** Tasks 4–6. **Files:** Create `features/search/{model,defaults,fields,codec,serialize}.ts`, `api/search.ts`, and `tests/unit/{query-codec,query-serialization}.spec.ts`; replace serialization in `search.js`.

- [x] Define typed criteria for every existing filter in `store.js`, including creator/curators, licences, subject categories/characteristics, intervention substance/route/type/application/form, measurement substance/tissue/type/method, and scalar/timecourse/scatter toggles.
- [x] Implement the versioned URL contract in section 3 with deterministic canonicalization and actionable parsing failures. Test round trips, escaped identifiers, default omission/canonical emission, invalid/unknown keys, and missing vocabulary labels.
- [x] Implement an allowlisted serializer to existing entity-prefixed API filters; verify no-match cases, particularly disabled subject categories and all licences/output types off, using Task 4 fixtures.
- [x] Generate fresh defaults on every reset; never reuse mutable initial arrays. Keep display labels out of equality and URL persistence.

**Gate:** Round-trip/serialization tests pass and serialized examples produce the expected real-backend selection. Reset regressions are fixed without changing backend semantics.

### Task 8: Implement draft/applied state and request ownership

**Depends on:** Tasks 5, 7. **Files:** Create `stores/search.ts`, `features/search/useSearchController.ts`, `features/results/useResultPage.ts`, and `tests/unit/{search-state,result-concurrency}.spec.ts`; remove corresponding Vuex/mixin state as callers move.

- [x] Separate draft, applied criteria, applied scope, selection status, counts, and view state. Use `idle/loading/ready/error` unions; counts are absent while unresolved, not fabricated zeroes.
- [x] Implement Search, reset-draft, draft removal, initial URL application, Back/Forward, tab/page/page-size/order/table-refinement transitions, and retry. Deduplicate the same in-flight submission; allow a distinct new query to supersede it.
- [x] Abort obsolete requests and reject outdated generation/identity completions for success, error, counts, rows, downloads, and suggestion lists. New searches visibly invalidate previous completed results.
- [x] Handle UUID expiry, permissions, and invalid restored pages with bounded explicit recovery. Avoid watcher loops and accidental query application on typing.

**Gate:** Delayed and reversed response tests prove stale work cannot overwrite current state. Browser navigation restores the exact applied state and replaces draft edits. Include reversed page-size and table-refinement responses in the regression tests.

### Task 9: Build the researcher filter interface

**Depends on:** Tasks 6–8. **Files:** Migrate `Data.vue`, all maintained `components/search/*`, `lib/SearchAuto.vue`, and search/reset/help buttons into `features/search/components`; create `tests/components/search-panel.spec.ts`.

- [x] Group filters as Studies, Subjects, Interventions, Measurements. Replace multiselect with Vuetify autocomplete, preserving identifiers, remote suggestions, loading/error state, selected chips, and keyboard/touch help.
- [x] Implement persistent applied-query summary, distinct removable draft chips, “Changes not applied,” visible Search, and Reset-to-default-draft behavior.
- [x] Replace “Concise” with the two specified scope labels and fixture-verified explanations. Explain related records and cross-record study qualification accurately.
- [x] Preserve useful example searches and supported licence/subject/output-type controls. Search validation errors are announced and focusable; label all fields.
- [x] Provide a narrow-screen filter drawer without changing the meaning of draft/apply operations; restore focus to its trigger on close.

**Gate:** Mounted tests and browser search construction prove typing does not execute the search, reset/chips stay draft-only, and applied results/downloads remain identifiable.

### Task 10: Migrate entity tables and result states

**Depends on:** Tasks 4, 8–9. **Files:** Migrate `components/tables/*` except vocabulary into `features/results/components`; replace `tables/mixins.js`, `apiInteraction.js`, and pagination mixins with typed API/composables. Tests: `tests/components/results.spec.ts`, `tests/e2e/research-search.spec.ts`.

- [x] Implement seven entity tabs using the correct endpoints; measurements map to outputs and timecourses/scatters map to filtered subsets. Show per-entity counts and scope without summing them.
- [x] Preserve “Search table” through `search_multi_match` using the URL/view-state contract, distinct refined counts, and clear export labeling. Define typed per-entity columns and server-order allowlists. Disable sort affordances when the server cannot support that field; do not sort one page and claim global ordering.
- [x] Prioritize scientific type/substance/value/unit, subject and study provenance, with dose/route/intervention context where actually supplied. Distinguish null from zero, whole-study from selected counts, and related records from direct matches.
- [x] Cover initial loading, updating, genuine empty success, invalid query, missing, unauthenticated, forbidden, and server/network errors. Count failure is not zero. Retry retains the applied query.
- [x] Preserve useful table density, horizontal table scrolling, accessible headers, and narrow-screen toolbar usability.

**Gate:** Fixed-fixture counts reconcile with displayed entity rows; paging and ordering preserve expected IDs; delayed requests and errors produce correct UI states.

### Task 11: Migrate detail exploration and authenticated files

**Depends on:** Tasks 5–6, 10. **Files:** Migrate `components/detail/*`, `navigation/DetailDrawer.vue`, `components/api/{GetData,GetFile,GetPaginatedData,VPaginator}.vue`, file buttons/chips, and `info_node/*` into details/shared/API boundaries. Create `features/details/useDetailNavigation.ts`, `features/exports/useFileDownload.ts` and detail browser tests.

- [x] Preserve study/reference, subject/characteristics, intervention, output, timecourse, scatter, vocabulary, and attachment views; use entity-specific identifier types and permission-checked API methods.
- [x] Keep filters/tab/order/page/scroll and focus while opening/closing details; support direct `/data/:sid`, refresh, Back/Forward, and missing/private-study responses.
- [x] Label ordinary detail content as broader context when its endpoint is not selection constrained. Do not invent “why this matched.”
- [x] Replace authenticated-image plugin assumptions with the session API or safe same-origin image paths. Revoke object URLs on replacement/unmount/logout; cancel stale requests and clear protected previews.

**Gate:** Browser detail journeys preserve position and focus; unauthorized/missing files are distinct; object URLs/listeners are disposed and private previews do not survive logout.

### Task 12: Migrate and validate active plots

**Depends on:** Tasks 4, 11. **Files:** Migrate `plots/{ScatterPlot,TimecoursePlot}.vue`; create `features/plots/{types,plotly,usePlot}.ts`, `types/plotly-dist-min.d.ts`, plot component/browser tests and deterministic trace fixtures.

- [x] Record current supported traces, uncertainty fields, axes/units, legends, zoom/reset, scale toggles, hover/export interactions, and missing-value behavior before replacing the wrapper.
- [x] Use dynamic import of the Plotly engine only when a plot is requested. Declare only the supported v4 module surface/trace shapes locally, citing the exact package and [function reference](https://plotly.com/javascript/plotlyjs-function-reference/); do not publish declarations as a general Plotly typing replacement or use `any`/blanket assertions.
- [x] Preserve arrays, precision, units, error bars, metadata and subset context. Fix render orchestration without adding client-side scientific recalculation or unit conversion.
- [x] Dispose Plotly instances, observers and events on unmount/replacement, and guard asynchronous import/render completion. Test resize and repeated detail opening.
- [x] Delete confirmed orphan plot components and the unreachable Vega stack. If reachability evidence changes, update the dependency decision before removal.

**Gate:** Typed boundary checks and real-browser plots agree with representative trace fixtures and interactions. Bundle/network evidence proves charts are absent from initial non-plot loading.

### Task 13: Implement applied-selection exports

**Depends on:** Tasks 4, 8, 10–11. **Files:** Replace `search.js` download behavior, `dialogs/DownloadDialog.vue`, and download/format buttons with `features/exports/useSelectionExport.ts` and typed controls. Tests: `tests/{unit,components}/selection-export.spec.ts`, `tests/e2e/exports.spec.ts`.

- [x] Serialize the immutable applied criteria/scope, never current draft controls or visible page. Disable export until selection resolution completes; clearly state that it covers the dataset, not one page.
- [x] Preserve ZIP selection download, cancellation, progress/error/retry states, content disposition, and separately labeled full-study/attachment downloads where the current API supports them.
- [x] Handle 401/403, size limits (413), capacity (503/Retry-After), malformed responses, and cancellation distinctly. Decode error bodies even when requesting binary data; revoke downloaded object URLs.
- [x] Download with the real backend and inspect CSV scientific identities against Task 4 expected selections. Do not compare expanded row counts to nested entity badges or claim snapshot reproducibility.

**Gate:** Draft edits cannot change the export, both scopes produce expected contents, and denied/licence-restricted downloads remain denied.

### Task 14: Complete account, administration, and curation migration

**Depends on:** Tasks 5–6 and shared detail/table patterns. **Files:** Migrate all `components/auth/*`, `navigation/Account.vue`, and account Vuex methods into `features/account`, `features/admin`, `api/{account,admin}.ts`; migrate `Curation.vue` and `InfoNodeTable.vue` into `features/curation`. Port all three existing `.spec.js` files into mounted `.spec.ts` tests.

- [x] Port registration, verification, login/logout, reset/recovery, invitation acceptance, provider login/onboarding/link/unlink/reauthentication, profile/avatar/email management, and provider-reference privacy. Preserve callback parameters and browser-bound flows.
- [x] Preserve personal key create/show-once/rotate/revoke, browser session revoke, MFA enrollment/challenge/recovery, administrator reauthentication, curator requests, assigned studies, and paginated security activity. Clear secrets after display/unmount and reject stale activity from a previous account.
- [x] Split large Account/AdminSettings components into focused typed subcomponents. Preserve role changes, activation constraints, password reset, invitation delivery/retry, study curator/reader assignment, role-request decisions, usage/quotas, and audit pagination. UI role gating supplements backend checks; it does not authorize actions.
- [x] Rework old direct-method unit tests into mounted user-observable tests without dropping password clearing, failed logout, invitation claiming, MFA secret cleanup, and stale-response coverage.
- [x] Migrate vocabulary search/highlighting/annotations under `/curation`; preserve terminology navigation without introducing study editing that was never present.

**Gate:** Controlled browser/API tests cover anonymous, ordinary, assigned curator, reviewer, and administrator capabilities. Real provider credentials/SMTP delivery remain staging checks, not simulated successes. All Task 1 routes now have maintained implementations.

### Task 15: Verify static delivery and deployment compatibility

**Depends on:** Tasks 2–3, 6; final verification after Tasks 9–14. **Files:** Update both frontend Dockerfiles, `frontend/README.md`, `.env.example`, `docs/{deployment,local-upload-testing}.md`; expand Task 3's `tests/deployment/nginx.conf` (test/example configuration) and deployment assertions in `compose.frontend-test.yaml`/Playwright.

- [x] Replace `npm install` with `npm ci`, pin supported Node/npm and container digests, explicitly bootstrap/assert npm 12.1.0, and remove `NODE_OPTIONS=--openssl-legacy-provider`. Keep production static artifact delivery and its documented `/vue` handoff; the current Dockerfile does not itself serve HTTP.
- [x] Provide a concrete static-server/reverse-proxy test fixture for the production artifact. Route `/api`, `/accounts`, `/media`, and other observed backend asset paths to the backend before SPA fallback. Do not silently add a new production proxy/service to the backend-only default Compose stack.
- [x] Test direct entry/refresh at every preserved history route, correct asset MIME/cache behavior, deployment base paths, 404 asset handling, and same-origin cookies/CSRF. API and missing asset requests must never return SPA HTML.
- [x] Document `VITE_API_BASE`, public-only configuration, proxy port/origin agreement, artifact handoff, and rollback to the retained legacy artifact. Verify the real deployment's proxy configuration before release; the repository currently contains no production proxy to assume correct.

**Gate:** Built static assets pass direct-route and same-origin session tests through the fixture; deployment instructions identify the actual artifact/proxy responsibilities and rollback path.

### Task 16: Remove migration remnants and close acceptance gates

**Depends on:** All preceding tasks. **Files:** Entire frontend, workflows, migration ledger, dependency audit, release evidence, docs, and `release-notes/unreleased.md` when implementation is ready.

- [x] Delete old entry points, store/mixins, Vue CLI/Babel/Webpack/PostCSS configuration, obsolete packages, old JS tests, deprecated/orphan components, and temporary migration exclusions. Retain tool-required JavaScript only with a documented reason; none is planned for application/tests.
- [x] Tighten Task 3's `test:source` TypeScript inventory check by removing all temporary migration allowances; check for maintained SFC script language/setup, JS source/test islands, ignored routes, compat packages, and unexplained type suppressions. Review exceptions manually; do not rely on an easily bypassed grep alone.
- [x] Run clean install, `npm ls`, runtime/development audit and deprecation review. Record transitive exceptions and remediation decisions separately from security findings. Recheck versions, but do not auto-upgrade the verified release candidate.
- [x] Run full acceptance journeys with the real isolated backend, both scopes, all seven tabs, plots, downloads, account roles, curation, browser navigation and session changes. Check desktop/narrow layouts, keyboard/touch help, focus, announcements, both themes, and contrast. Use Chromium, Firefox and WebKit for the critical journeys; record any browser-specific blocker.
- [x] Compare initial assets and lazy-chart loading against the baseline on the same environment. Investigate material regressions; record measurements instead of inventing performance targets. Visually inspect representative scientific tables and plots, not just screenshots of the landing page.
- [x] Record exact commands, fixture revision, browser/tool versions, artifacts, failures and resolved exceptions in `frontend/docs/modernization-verification.md`. Run affected backend checks, curator asset validation, and docs build. Preserve honest staging limitations for OAuth/SMTP/proxy checks.
- [ ] Review the completed diff and migration ledger, merge only after required CI, and release the completed frontend artifact together when authorized. No database migration is part of this cutover.

**Gate:** Every specification acceptance row has evidence, no maintained workflow or TypeScript scope is omitted, and required staging/deployment checks have passed before claiming the modernization complete.

## 6. Stage boundaries and dependency order

| Stage | Tasks | Exit evidence and limitation |
| --- | --- | --- |
| Baseline/contracts | 1 and 4 | Scientific and route baselines, dependency decisions, rollback artifact. No new UI yet. |
| Foundation | 2, 3, 5, 6 | Typed shell/session/router and enforced test harness. Remaining features explicitly unavailable on the migration branch; not deployable. |
| Research workflow | 7–13 | Search, counts, navigation, plots and exports work against controlled backend data. Account/admin migration may still be incomplete. |
| Feature completion | 14 | All maintained routes, account/admin behavior and vocabulary browsing are migrated. |
| Release readiness | 15–16 | Static delivery, all acceptance checks, dependency cleanup and rollback evidence complete. |

Task 4 can proceed independently of toolchain work. After shared API/state contracts stabilize, account/admin work can run independently of researcher components; plot work follows detail/fixture contracts. Avoid parallel edits to `package.json`, lockfile, shared stores, router, or workflow aggregation. Integrate one feature boundary at a time and rerun affected checks after integration.

## 7. Verification commands and release checklist

These are intended execution commands; they were **not run as implementation acceptance during planning**. Add the declared scripts/configuration before using the frontend commands. Run the commands separately so an early failure cannot be obscured by later successful commands.

```bash
# Select Node 24.21.0 using the project .nvmrc, then bootstrap npm once.
npm install --global npm@12.1.0
node --version
npm --version
# Assert v24.21.0 and 12.1.0 in the harness before proceeding.
# frontend/
npm ci
npm run test:source
npm run typecheck
npm run lint
npm run test:unit -- --run
npm run build
npx playwright install --with-deps
npm run test:e2e
npm ls --all
npm audit --json
npm audit --omit=dev --json
```

```bash
# Repository root, isolated PostgreSQL only
# Start the existing disposable database for backend contract tests.
docker compose -f compose.test.yaml up -d --wait
export PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test
uv run --project backend pytest backend/tests/api/test_frontend_search_contract.py -q -x
uv run --project backend pytest backend/tests -q -x
uv run --project backend python -m pytest tools/backend_migration -q -x
uv run --project backend ruff check .
uv run --project backend ruff format --check .
uv run --project backend ty check --project backend
uv run --project backend python scripts/check_curator_roster.py
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
uv run --no-project --python 3.14 python scripts/llms_txt.py
```

The Playwright command must start or require the isolated `compose.frontend-test.yaml` stack through its documented harness, seed it deterministically, serve the actual production artifact, and clean up only that test project's resources. Do not make browser tests silently pass against mocks when the real-backend project was requested.

- [x] Exact compatible toolchain and reproducible lockfile verified; no obsolete direct dependencies remain without an explicit decision.
- [x] Every maintained source/test module is TypeScript; every maintained SFC script uses typed setup; no compatibility runtime or unexplained suppression remains.
- [x] Draft/applied state, canonical URLs, navigation, both scopes, counts and error/race states meet the specification.
- [x] Semantic fixture results, scientific formatting, plot context, and applied-selection export parity are verified.
- [ ] Live provider/SMTP delivery still requires staging credentials; local migrated account/admin/curation behavior and role boundaries are verified.
- [x] Accessible keyboard/touch flows and wide/narrow/light/dark visual behavior have been inspected.
- [ ] Actual production-proxy verification and durable deployed-artifact retention remain operator gates. Local artifact/history/CI/bundle checks and recovered baseline evidence pass.

## Planning evidence and limits

This plan is based on repository source/configuration inspection, two independent read-only feature/contract audits, npm/Node metadata queries, and official framework guidance. No frontend dependencies were installed, no application source was migrated, and no future acceptance test is claimed to have passed. Known risks are addressed by explicit tasks: TypeScript 7 tooling incompatibility, Plotly v4 declaration coverage, Vue/Vuetify major API changes, old code's search defects, scientific subset context, expired/permission-bound selection UUIDs, and the absent in-repository production proxy. Task checkboxes remain open.
