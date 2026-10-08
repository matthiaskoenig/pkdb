---
search:
  exclude: true
---

# Curation app, part C: front end, packaging and documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the vanilla `pkdb curate` page with a Vue 3 + Vuetify app built from a second Vite entry in `frontend/`, packaged into the Python wheel, tested end to end against the real local server, and documented with new screenshots.

**Architecture:**
- Source in `frontend/src/curation-app/`, entry `frontend/curation-app.html`, config `frontend/vite.curation.config.ts`; the build writes `python/src/pkdb/curation/static/` (gitignored), which the wheel includes as a hatch artifact.
- A fetch-based API client (`api.ts`) handles the launch token handshake, the CSRF header, ETags (`If-None-Match`, 304) and the error bodies of the part B API; Pinia setup stores hold the overview snapshot and the open study; views poll with a composable.
- Hash routing (`#/`, `#/studies/{substance}/{name}/{section}`); the study page has a section rail (Metadata, Review, Problems, Sources, Tables, Activity).
- Strict CSP: the server replaces `__PKDB_NONCE__` in `index.html`; Vite puts it on generated tags (`html.cspNonce`), Vuetify reads it (`theme.cspNonce`), Plotly reuses a pre-created nonced style element.
- Playwright end-to-end tests start the real `pkdb curate --offline` on a fixture workspace with a recording opener.

**Tech Stack:** Vue 3.5, Vuetify 4.2 (Font Awesome icons, the website theme), vue-router 5 (hash history), Pinia 4, Plotly 4.1 (`plotly.js-dist-min`), Vite 8, TypeScript 6, vitest 5 with `@vue/test-utils`, Playwright 1.63 with `@axe-core/playwright`, hatchling build hooks, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-06-curation-app-design.md`, sections 8 (front end), 9 (error handling), 10 (end-to-end and front-end unit tests) and 11 (documentation). Parts A and B are merged; the local API they provide is binding (routes and shapes are summarized in each task's Interfaces).

## Global Constraints

- **Frontend rules** (`frontend/scripts/check-source.ts`, eslint, `vue-tsc`): only `<script setup lang="ts">` in `.vue` files, no JavaScript files in `src/` or `tests/`, no `any`, no `@ts-ignore`/`@ts-nocheck`; components import Vuetify components explicitly from `vuetify/components` as the website does; dependencies stay pinned exactly; no new runtime dependency.
- **Run from `frontend/`:** `npm run test:source`, `npm run typecheck`, `npm run lint`, `npm run test:unit`, `npm run build`, `npm run build:curation`; every commit keeps them green. Python (`python/`): `uv run --locked pytest -q`, ruff, ty. Docs: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean`.
- **Writing:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines in commits or docs; user-facing text in plain, short English sentences.
- **CSP (spec 7.5):** never `'unsafe-inline'`, no inline `<script>`, no literal `style="..."` attributes in templates or generated HTML (Vue `:style` bindings are allowed, they use the CSSOM); the nonce placeholder is exactly `__PKDB_NONCE__`.
- **Routing:** hash history only (the server has no SPA fallback).
- **API:** all requests are same-origin to `/local/...`; POSTs send JSON with `X-CSRF-Token`; never send the API key except in the settings dialog's write-only field.
- **Theme:** reuse `frontend/src/plugins/vuetify.ts` (light and dark website theme, Font Awesome); the theme follows the system and a header toggle overrides it (persisted in `localStorage` key `pkdb.curation.theme`, read in try/catch).
- **pkdb_data is read-only:** never write `/home/mkoenig/git/pkdb_data`; fixtures live in the repository.
- **Accessibility:** every interactive element has an accessible name; axe (`wcag2a`, `wcag2aa`, `wcag21aa`) reports no violations on each screen.

## Review Focus

1. **Session expiry and server restarts.** After `pkdb curate` restarts, the page shows "The local server stopped" or "Open the launch URL printed in your terminal" (401) instead of failing silently, and recovers when the server is back. Test in Task 2.
2. **A study.json changed on disk while the metadata form has unsaved edits.** Save answers 409; Reload keeps the user's edits on top of the reloaded document and marks fields that changed on disk; nothing is lost. Test in Task 6.
3. **Large tables.** A timecourse table with 5,000 rows renders without freezing (row virtualization above 500 rows) and highlights stay correct while scrolling. Test in Task 10.
4. **CSP with real Vuetify and Plotly.** No `securitypolicyviolation` event on any screen, in light and dark mode, including the figure overlay. Test in Task 12.
5. **Narrow windows.** At 390 x 844 every screen is usable without horizontal page scroll (tables scroll inside their container, the rail becomes a menu). Test in Task 12.

---

### Task 1: Second Vite entry, packaging and removal of the vanilla page

**Files:**
- Create: `frontend/curation-app.html`, `frontend/vite.curation.config.ts`, `frontend/src/curation-app/main.ts`, `frontend/src/curation-app/App.vue` (shell with header placeholder and an empty overview route), `frontend/src/curation-app/router.ts`, `frontend/src/curation-app/csp.ts`, `python/hatch_build.py`
- Modify: `frontend/src/plugins/vuetify.ts` (`makeVuetify(options?: { cspNonce?: string })`), `frontend/package.json` (scripts `build:curation`, `dev:curation`), `frontend/tsconfig.json` (include the new config if needed), `python/pyproject.toml` (hatch artifacts and build hook), `.gitignore` (`python/src/pkdb/curation/static/`), `python/src/pkdb/curation/launch.py` (missing assets), `.github/workflows/ci-cd.yml` (client job builds the assets before `uv build`; the wheel check asserts `pkdb/curation/static/index.html`)
- Delete: `python/src/pkdb/curation/static/{index.html,app.js,style.css}` (`git rm`), `tools/curation_docs/smoke.mjs`; move `pkdb_logo.png` to `frontend/src/curation-app/assets/pkdb_logo.png` (imported by the app, so Vite fingerprints it)
- Test: `frontend/tests/unit/curation-csp.spec.ts`, `python/tests/test_curation_server.py` (missing assets), `python/tests/test_hatch_build.py`

**Interfaces:**
- Produces: `npm run build:curation` (`vite build --config vite.curation.config.ts`) writes `python/src/pkdb/curation/static/index.html` and hashed assets under `assets/`; `npm run dev:curation` serves the app with a proxy of `/local` and `/avatars` to `PKDB_CURATION_URL` (an origin such as `http://127.0.0.1:43117`), rewriting `Origin` and `Host` to the target; `cspNonce(): string | undefined` in `csp.ts` reads `document.querySelector('meta[property="csp-nonce"]')?.nonce`.
- `makeVuetify(options = {})` passes `theme: { ..., cspNonce: options.cspNonce }`; the website keeps calling `makeVuetify()` unchanged.

- [ ] **Step 1: Write the failing tests**

`frontend/tests/unit/curation-csp.spec.ts`:

```ts
import { describe, expect, it } from "vitest";
import { cspNonce } from "../../src/curation-app/csp";

describe("cspNonce", () => {
  it("reads the nonce of the csp-nonce meta tag", () => {
    const meta = document.createElement("meta");
    meta.setAttribute("property", "csp-nonce");
    meta.nonce = "abc123";
    document.head.append(meta);
    expect(cspNonce()).toBe("abc123");
    meta.remove();
  });

  it("is undefined without the meta tag", () => {
    expect(cspNonce()).toBeUndefined();
  });
});
```

`python/tests/test_curation_server.py`: `launch.run` exits with code 1 and prints "The curation app is not built. Run npm ci and npm run build:curation in frontend/." when `ASSETS / "index.html"` is missing (monkeypatch `server.ASSETS` to an empty folder; the engine must not start, so check it before constructing the engine).

`python/tests/test_hatch_build.py`: import `hatch_build` from `python/` (add the folder to `sys.path` in the test), instantiate the hook class with a fake root, and assert that `initialize("standard", {})` raises `RuntimeError` mentioning `npm run build:curation` for the `wheel` and `sdist` targets when `src/pkdb/curation/static/index.html` is missing, and does nothing for the `editable` version or when the file exists. Build the hook object the way hatchling does (read `hatchling.builders.hooks.plugin.interface.BuildHookInterface.__init__`) or test a small pure function `check_assets(root: Path, target: str, version: str) -> None` that the hook calls.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run tests/unit/curation-csp.spec.ts` and `cd python && uv run --locked pytest -q tests/test_curation_server.py tests/test_hatch_build.py`
Expected: FAIL (modules missing).

- [ ] **Step 3: Implement the entry and the build**

`frontend/curation-app.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Local curation · PK-DB</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/curation-app/main.ts"></script>
  </body>
</html>
```

`frontend/vite.curation.config.ts`:

```ts
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig, type ProxyOptions } from "vite";

const target = process.env.PKDB_CURATION_URL ?? "http://127.0.0.1:43117";

function local(): ProxyOptions {
  return {
    target,
    changeOrigin: true,
    configure(proxy) {
      // The local server accepts requests only from its own origin.
      proxy.on("proxyReq", (request) => request.setHeader("Origin", target));
    },
  };
}

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  base: "/",
  html: { cspNonce: "__PKDB_NONCE__" },
  build: {
    outDir: "../python/src/pkdb/curation/static",
    emptyOutDir: true,
    assetsInlineLimit: 0,
    sourcemap: false,
    rollupOptions: { input: fileURLToPath(new URL("./curation-app.html", import.meta.url)) },
  },
  server: { port: 8090, strictPort: true, proxy: { "/local": local(), "/avatars": local() } },
});
```

The built file is `static/curation-app.html`; rename it to `index.html` after the build (a tiny Vite plugin in the config with `generateBundle`/`writeBundle` that renames the HTML asset, or set the HTML file name through `build.rollupOptions` so the output is `index.html`; check that the output folder holds `index.html` and `assets/`). `assetsInlineLimit: 0` keeps fonts and images out of `data:` URLs (`font-src` falls back to `'self'`).

`frontend/src/curation-app/csp.ts`:

```ts
/** The nonce the local server put into index.html, for styles created at runtime. */
export function cspNonce(): string | undefined {
  const meta = document.querySelector<HTMLMetaElement>('meta[property="csp-nonce"]');
  return meta?.nonce || undefined;
}
```

`main.ts` creates the app with `createPinia()`, the router and `makeVuetify({ cspNonce: cspNonce() })`, imports `../styles/app.css` only if it contains nothing website-specific (otherwise a small `curation-app/styles.css`), and mounts `#app`. `App.vue` is a `v-app` shell with an app bar (logo, "Local curation") and `<router-view>`; the real header comes in Task 3. `router.ts` uses `createWebHashHistory()` with routes `/` (overview placeholder component) and `/studies/:substance/:name/:section?` (placeholder), lazily imported.

`python/hatch_build.py` defines `CustomBuildHook(BuildHookInterface)` with `PLUGIN_NAME = "custom"`, whose `initialize(version, build_data)` calls `check_assets(Path(self.root), self.target_name, version)`; `check_assets` raises `RuntimeError("The curation app assets are missing in src/pkdb/curation/static. Run npm ci and npm run build:curation in frontend/ before building the package.")` for targets `wheel` and `sdist` with `version == "standard"` when `src/pkdb/curation/static/index.html` is missing. `pyproject.toml`:

```toml
[tool.hatch.build]
artifacts = ["src/pkdb/curation/static/**"]

[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
```

Make sure the sdist includes `hatch_build.py` and the built assets (check with `uv build --project python --out-dir <tmp>` after `npm run build:curation`, then `tar tzf`/`unzip -l`).

`launch.run` checks `ASSETS / "index.html"` before creating the engine and returns 1 with the message above (printed to stderr).

- [ ] **Step 4: CI**

In `.github/workflows/ci-cd.yml` `client` job, before `uv build`: `actions/setup-node` with Node 24.21.0 and the npm cache of `frontend/package-lock.json`, `npm install --global npm@12.1.0`, `npm ci` and `npm run build:curation` in `frontend/` (all OS of the matrix). Extend "Verify isolated public wheel and CLI" with `python -c "import importlib.resources as r; assert (r.files('pkdb.curation') / 'static' / 'index.html').is_file()"`. The frontend workflow already lints and type-checks `src/curation-app/` because it lies under `src/`.

- [ ] **Step 5: Verify and commit**

Run the frontend checks, `npm run build:curation`, the Python suite, `git status` (no built file tracked), and a manual start: `uv run --project python pkdb curate <a tmp workspace> --offline --no-browser`, open the launch URL in a headless browser (`npx -y chrome-devtools-axi`) and check the shell renders with no console CSP errors.

```bash
git add -A frontend python/hatch_build.py python/pyproject.toml python/src/pkdb/curation .gitignore .github/workflows/ci-cd.yml python/tests tools/curation_docs
git commit -m "Build the curation app from a second Vite entry into the Python package"
```

---

### Task 2: API client, session and polling

**Files:**
- Create: `frontend/src/curation-app/api/types.ts`, `frontend/src/curation-app/api/client.ts`, `frontend/src/curation-app/api/session.ts`, `frontend/src/curation-app/composables/usePolling.ts`, `frontend/src/curation-app/stores/overview.ts`, `frontend/src/curation-app/stores/study.ts`
- Test: `frontend/tests/unit/curation-api.spec.ts`, `frontend/tests/unit/curation-polling.spec.ts`, `frontend/tests/unit/curation-stores.spec.ts`

**Interfaces:**
- Consumes (local API, part B): `POST /local/session {token}` gives `{csrf_token}` and the session cookie; `GET /local/state` (snapshot with `csrf_token`), `GET /local/studies/{substance}/{name}`, `.../tables/{file}`, `.../sources/{source}`, `GET /local/curators`, `GET /local/reports/{id}` all send `ETag` and answer `304` to a matching `If-None-Match`; errors are JSON `{error, ...}`: 401 (no session), 403 (`no_user`, `user_mismatch`, origin), 404, 409 (`{error, file, revision, content}` for stale revisions, `{error}` for an ambiguous identity), 413, 415, 422 (`{error, issues, code?}`), 500.
- Produces:
  - `types.ts`: TypeScript interfaces for every response shape: `Snapshot`, `StudyRow`, `Job`, `StudyDetail`, `DocumentState<T>` (`{revision: string | null, value: T | null, issues: ValidationIssue[]}`), `StudyMetadata`, `Review`, `ReviewItem`, `ValidationIssue`, `SyncState`, `ConflictData`, `SourceSummary`, `SourceView`, `OverlayPoint`, `TableResponse` (`{file, kind: "table", header, rows: {line, cells}[]} | {file, kind: "raw", rows}`), `Profile`, `Directories`, `TablesResult`, `MetadataWrite`, `ReviewWrite`. Copy the field lists from the part B code (`python/src/pkdb/curation/engine.py` `snapshot`, `studies.py` `study_detail`/`study_table`/`study_source`, `metadata.py` `profile`, `python/src/pkdb/studyformat/models.py`, `python/src/pkdb/schemas/review.py`, `python/src/pkdb/schemas/validation.py`), optional fields as `?:`.
  - `client.ts`:
    - `class ApiError extends Error { status: number; body: Record<string, unknown> }` with helpers `isRevisionConflict(error)`, `isValidationError(error)` (422), `isNoUser(error)` (403 `no_user` or `user_mismatch`).
    - `getJson<T>(path, { etag?, signal? }): Promise<{ status: 200, etag: string | null, data: T } | { status: 304, etag: string }>`.
    - `postJson<T>(path, body): Promise<T>`; sends `Content-Type: application/json`, `X-CSRF-Token: csrfToken()`, `credentials: "same-origin"`; updates the CSRF token from any response field `csrf_token`.
    - `setCsrfToken(token)`, `csrfToken()`.
    - `ServerStopped` (a `TypeError` from `fetch`) and `SessionMissing` (401) errors that the shell turns into banners.
    - Responses are validated structurally (an object with the expected top-level keys) with small helpers like the website's `isRecord`, then typed; never `any`.
  - `session.ts`: `bootstrap(location: Location, history: History): Promise<void>` reads `#token=...` from the hash, clears it with `history.replaceState` before posting, posts it to `/local/session`, and stores the CSRF token; without a token it relies on the existing cookie (the first `GET /local/state` then tells 401 or OK).
  - `usePolling(load: (etag) => Promise<...>, intervalMs = 1500)`: polls while the page is visible (`document.visibilityState`), keeps the last ETag and data, exposes `data`, `error`, `refresh()`, stops on unmount.
  - Stores (Pinia setup stores): `useOverviewStore()` (`snapshot`, `error`, `start()`, `stop()`, `refresh()`, actions that POST the existing routes: `selectWorkspace(path)`, `forgetWorkspace(path)`, `listDirectories(path?)`, `configure(settings)`, `setMode(ids, mode)`, `enqueue(ids, action)`, `cancelJobs(ids)`, `clearHistory()`, `retry(id)`, `pause(paused)`, `resume(ids?)`, `openFile(studyId, file?, reveal?)`, `refreshAssignments()`); `useStudyStore()` (`identity`, `detail`, `open(substance, name)`, `close()`, `refresh()`, `table(file)`, `source(source)` with per-route ETag caches, `curators()` cached once, writes `saveMetadata(revision, metadata)`, `reviewAction(revision, action, payload)`, `tablesAction(action, payload)` that return the API result and refresh the detail).

- [ ] **Step 1: Write the failing tests**

`curation-api.spec.ts` (mock `globalThis.fetch` with `vi.fn` returning `Response` objects):
- `getJson` sends `If-None-Match` when given an ETag and returns `{status: 304, etag}` on 304;
- `postJson` sends the CSRF header, the JSON body and same-origin credentials; a 409 body becomes an `ApiError` with `isRevisionConflict` true and `body.content`; a 422 body exposes `issues`; a 403 `no_user` is `isNoUser`; a rejected fetch (`TypeError`) becomes `ServerStopped`; a 401 becomes `SessionMissing`;
- `bootstrap` clears the hash before the POST (assert the order with a call log) and stores the CSRF token from the response.

`curation-polling.spec.ts` (fake timers): polls every 1500 ms, sends the previous ETag, keeps the data on 304, pauses while the document is hidden, stops after unmount (mount a tiny test component that uses the composable).

`curation-stores.spec.ts`: `useStudyStore().open("caffeine", "Example")` loads `/local/studies/caffeine/Example`, percent-encodes each segment (an identity with a space or `%`), and refreshes the detail after `saveMetadata`; `useOverviewStore().enqueue(["caffeine/Example"], "validate")` posts `{ids, action}`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run tests/unit/curation-api.spec.ts tests/unit/curation-polling.spec.ts tests/unit/curation-stores.spec.ts`
Expected: FAIL (modules missing).

- [ ] **Step 3: Implement**

`client.ts` core:

```ts
let token = "";

export function setCsrfToken(value: string): void {
  token = value;
}

export function csrfToken(): string {
  return token;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: Record<string, unknown>,
  ) {
    super(typeof body.message === "string" ? body.message : typeof body.error === "string" ? body.error : `Request failed (${status})`);
  }
}

export class ServerStopped extends Error {}
export class SessionMissing extends Error {}

async function send(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(path, { ...init, credentials: "same-origin" });
  } catch (error) {
    if (error instanceof TypeError) throw new ServerStopped("The local server stopped. Start pkdb curate again.");
    throw error;
  }
}

async function failure(response: Response): Promise<never> {
  const body = await response.json().catch(() => ({}));
  const record = isRecord(body) ? body : {};
  if (response.status === 401) throw new SessionMissing(typeof record.error === "string" ? record.error : "Open the launch URL printed in your terminal");
  throw new ApiError(response.status, record);
}
```

Complete `getJson` and `postJson` around these helpers (update `token` from a `csrf_token` field of any successful JSON response). Encode identities with `encodeURIComponent` per segment in one helper `studyPath(identity, ...parts)`.

- [ ] **Step 4: Run the tests**

Run: the three spec files, then `npm run test:source && npm run typecheck && npm run lint && npm run test:unit`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/curation-app frontend/tests/unit
git commit -m "Add the curation app API client, session handshake and polling stores"
```

---

### Task 3: Header, workspace, connection and settings

**Files:**
- Create: `frontend/src/curation-app/components/AppHeader.vue`, `WorkspaceDialog.vue`, `SettingsDialog.vue`, `ConnectionMenu.vue`, `StatusBanner.vue`
- Modify: `frontend/src/curation-app/App.vue`
- Test: `frontend/tests/components/curation-header.spec.ts`, `curation-workspace-dialog.spec.ts`, `curation-settings-dialog.spec.ts`

**Interfaces:**
- Consumes: `useOverviewStore()` (snapshot fields `workspace`, `recent_workspaces`, `paused`, `connection`, `connection_error`, `checked_at`, `endpoint`, `account`, `user`, `author {user, reason}`, `vocabulary.status`, `client_version`, `server_version`, `update_required`, `offline`), actions `selectWorkspace`, `forgetWorkspace`, `listDirectories`, `configure`, `pause`, `resume`; `ServerStopped`/`SessionMissing` from the store error.
- Produces: the header of every page (spec 8.2): logo, "Local curation", workspace menu (path, Choose workspace, recent workspaces with remove), file watching (Active/Paused badge, Pause/Resume), connection menu (state badge, error, last check, endpoint, account, vocabulary, versions with the `pkdb update` hint), the effective author (`author.user`, or `author.reason` as a warning with a link that opens the settings), settings button, theme toggle. `StatusBanner` shows the server-stopped and session-missing states and recovers when the next poll succeeds.

- [ ] **Step 1: Write the failing tests**

Component tests (mount with the global Vuetify plugin from `tests/setup.ts` and a Pinia store whose actions are spies):
- `curation-header.spec.ts`: renders the workspace path, the connection state text for each `connection` value ("Connected", "Offline", "Connecting", "Not configured", "Rejected API key" for `unauthorized`, "Update pkdb" for `incompatible`, "Error"), the author `curator`, and for `author.reason` the warning text and a button "Set user" that opens the settings dialog; Pause calls `pause(true)`; the theme toggle switches the Vuetify theme and writes `localStorage` (and survives a throwing `localStorage`).
- `curation-workspace-dialog.spec.ts`: opening lists the folders of `listDirectories()` with their kind ("repository", "study", "folder"), Up and Home navigate, Open calls `selectWorkspace(path)`, a recent workspace that no longer exists is shown as unavailable and can be removed (`forgetWorkspace`), a `WorkspaceError` message (400 body `error`) is shown inline.
- `curation-settings-dialog.spec.ts`: submits only changed fields of endpoint, user and offline, and the API key only when typed; the key field is cleared after submit and on close; a 400 error is shown inline.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run tests/components/curation-header.spec.ts tests/components/curation-workspace-dialog.spec.ts tests/components/curation-settings-dialog.spec.ts`
Expected: FAIL.

- [ ] **Step 3: Implement**

Use `v-app-bar`, `v-menu`, `v-list`, `v-chip`, `v-dialog`, `v-text-field`, `v-switch`, `v-btn` with Font Awesome icons (`fas fa-folder-open`, `fas fa-eye`, `fas fa-plug`, `fas fa-gear`, `fas fa-circle-half-stroke`). Map states to Vuetify colors (`success`, `warning`, `error`, `info`). The header collapses into a menu below 960 px width.

- [ ] **Step 4: Run the tests, the frontend checks; commit**

```bash
git add frontend/src/curation-app frontend/tests/components
git commit -m "Add the curation app header with workspace, connection and settings"
```

---

### Task 4: Overview page

**Files:**
- Create: `frontend/src/curation-app/views/OverviewPage.vue`, `frontend/src/curation-app/components/StudyTable.vue`, `UploadDialog.vue`, `RetryDialog.vue`, `frontend/src/curation-app/overview.ts` (pure filtering and labels)
- Test: `frontend/tests/unit/curation-overview.spec.ts`, `frontend/tests/components/curation-overview-page.spec.ts`

**Interfaces:**
- Consumes: `snapshot.studies: StudyRow[]` (`id`, `path`, `substance`, `duplicate`, `mode`, `status`, `summary {title, review_status, open_items, curators, release, issue, ai}`, `counts {errors, warnings}`, `sync {status, changes, conflicts}`, `issue {number, state, labels, url}`, `last_upload {at, url}`, `message`), `snapshot.format1_folders`, `snapshot.jobs`, `snapshot.can_upload`; store actions `setMode`, `enqueue`, `retry`; `GET /local/curators` (profiles for avatars).
- Produces: `filterStudies(rows, { search, substance, chip }): StudyRow[]` and `needsAttention(row): boolean` (errors, a sync conflict, or open items while in review) in `overview.ts`; the overview route `#/`.

- [ ] **Step 1: Write the failing tests**

`curation-overview.spec.ts` (pure): search matches identity and title case-insensitively; substance filter; chips `all`, `attention`, `draft`, `in_review`, `approved`; `needsAttention` true for `counts.errors > 0`, `sync.status === "conflict"`, `summary.open_items > 0 && summary.review_status === "in_review"`, false otherwise.

`curation-overview-page.spec.ts`: renders one row per study with identity, title, review status chip ("Draft", "In review", "Approved"), "AI" marker for `summary.ai`, open items, "2 errors"/"1 warning"/"valid", sync status label ("In sync", "Workbook open", "Changed", "Conflict", "Syncing", "No workbook", "Unknown"), release id or "-", issue link `#2158` to `issue.url`, curator avatars with names as accessible labels, On save mode and last upload; clicking a row navigates to `#/studies/caffeine/Example` (a duplicate row shows "Duplicate identity" and is not clickable for upload); selecting rows enables Validate (posts `enqueue(ids, "validate")`), Upload (opens the upload dialog listing the studies; confirm posts `enqueue(ids, "upload")`; disabled without `can_upload` with a tooltip), On save select plus Apply (`setMode`); the footer reads "1,412 study format 1 folders are not listed. Convert them with pkdb migrate; until then they stay on the released app version." for `format1_folders = 1412` and is hidden for 0; a row with an unknown upload outcome (`status === "unknown"`) offers "Review uncertain upload", which opens the retry dialog whose confirm checkbox must be checked before `retry(id)`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: the two spec files. Expected: FAIL.

- [ ] **Step 3: Implement**

`v-table` (or `VDataTable` if registered; the website uses `v-table`) with sortable headers built by hand, `v-text-field` search, `v-select` substance, `v-chip-group` filters, a batch toolbar. The table scrolls horizontally inside its container on narrow screens.

- [ ] **Step 4: Run the tests and checks; commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the overview page of the curation app"
```

---

### Task 5: Study page shell, header and rail

**Files:**
- Create: `frontend/src/curation-app/views/StudyPage.vue`, `frontend/src/curation-app/components/StudyHeader.vue`, `SectionRail.vue`, `AddTableDialog.vue`, `frontend/src/curation-app/study.ts` (default section and rail counts)
- Modify: `frontend/src/curation-app/router.ts`
- Test: `frontend/tests/unit/curation-study.spec.ts`, `frontend/tests/components/curation-study-page.spec.ts`

**Interfaces:**
- Consumes: `useStudyStore()` (`open`, `detail: StudyDetail`, `reviewAction("status")`, `tablesAction("open"|"add")`), `useOverviewStore()` (`enqueue`, `openFile`, snapshot row for `last_upload`/`mode`), detail fields `id`, `summary`, `issue`, `review.value.status`, `counts`, `sync`, `reference`, `mode`, `problems`, `review.value.items`, `sources`, `files`.
- Produces: route `#/studies/:substance/:name/:section?` with sections `metadata`, `review`, `problems`, `sources`, `tables`, `activity`; `defaultSection(detail)` (review when items are open, problems when there are errors, otherwise metadata); `railCounts(detail)` (`review` open items, `problems` errors plus warnings, `sources` count, `tables` count of table and raw files); `StudyHeader` (identity, review status select, release chip, issue chip with label, provenance chip "AI curated · <method>", summary line with title, PMID, On save mode, sync status and counts, actions Open tables, Validate, Upload and a menu with Open folder, Open PDF, Add table, Copy path); the section components of Tasks 6 to 11 plug into `StudyPage` by name.

- [ ] **Step 1: Write the failing tests**

- `curation-study.spec.ts`: `defaultSection` and `railCounts` for representative details.
- `curation-study-page.spec.ts`:
  - opening `#/studies/caffeine/Example` without a section redirects to the default section;
  - the rail lists the six sections with counts and marks the active one; below 600 px it becomes a select;
  - the header shows `caffeine/Harder1988`, "PKDB00198 · released 2026-09-28", "#2158 · check", "AI curated · claude-opus-5-5";
  - changing the review status to Approved posts `reviewAction(revision, "status", {status: "approved"})`; a 422 `approval_refused` shows its message ("Approved needs zero open review items and zero validation errors ...") in an alert and resets the select;
  - Open tables posts `tablesAction("open")` and shows its issues (for example a workbook that could not be created) in an alert;
  - Validate posts `enqueue([id], "validate")`; Upload requires `can_upload`;
  - Open folder and Open PDF call `openFile(id)` and `openFile(id, "<name>.pdf")`; Copy path writes the folder path to `navigator.clipboard`;
  - Add table opens a dialog (kind outputs, timecourses or scatters, or raw table; source such as `Tab3`, `Fig2`; preview of the sheet and file name; the image expected) that posts `tablesAction("add", {table: "outputs_Tab3"})` or `{raw: "Tab3"}` and shows the API issues;
  - a duplicate identity (409 from the detail) shows "This identity belongs to two folders" with both paths from the message; a 404 shows "This study is not in the workspace" with a link back.

- [ ] **Step 2: Run the tests to verify they fail**

Run: the two spec files. Expected: FAIL.

- [ ] **Step 3: Implement**

`StudyPage` opens the study on route entry, polls the detail with `usePolling` (detail ETag), and renders the section component; the header and rail stay visible while sections load. Sections not built yet render a placeholder that later tasks replace.

- [ ] **Step 4: Run the tests and checks; commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the study page with header, actions and section rail"
```

---

### Task 6: Metadata section

**Files:**
- Create: `frontend/src/curation-app/sections/MetadataSection.vue`, `frontend/src/curation-app/components/ReferenceDialog.vue`, `PeopleFields.vue`, `NotesFields.vue`, `frontend/src/curation-app/metadata.ts` (form model, diff and three-way merge)
- Test: `frontend/tests/unit/curation-metadata.spec.ts`, `frontend/tests/components/curation-metadata-section.spec.ts`, `curation-reference-dialog.spec.ts`

**Interfaces:**
- Consumes: `detail.metadata: DocumentState<StudyMetadata>`, `detail.reference`, `detail.reference_match`, `detail.people`, `GET /local/curators` (roster for creator, curators and collaborators), `saveMetadata(revision, metadata)` (`POST /local/studies/metadata`: 200 `{revision, reference, reference_error}`, 409 `{error, file, revision, content}`, 422 `{error, issues}`, 403), and the reference routes `POST /local/reference/read|search|preview|save` with `{id: "<substance>/<name>", ...}` (behavior of the vanilla dialog described in the part B digest: read, search a citation, preview with only changed fields as `input`, save with the preview token; editing invalidates the token).
- Produces: `toForm(value)`, `fromForm(form): StudyMetadata` (drops empty optional values like the canonical writer), `changedFields(base, current): string[]`, `mergeOnReload(base, mine, theirs): { merged, conflicts: string[] }` (keeps the user's edits on top of the reloaded document; a field edited on both sides keeps mine and is listed in `conflicts`).

- [ ] **Step 1: Write the failing tests**

`curation-metadata.spec.ts`: `fromForm(toForm(value))` round-trips a full `study.json` value; empty descriptions and notes are dropped; `mergeOnReload` keeps a local licence edit while taking a disk-side curator change, and lists a field changed on both sides in `conflicts`.

`curation-metadata-section.spec.ts`:
- cards for reference (PMID, DOI, match state "reference.json matches" or "reference.json does not match study.json" or "No identifiers", and "Correct title, authors, journal..." opening the Reference dialog), people (creator autocomplete from the roster with avatars, curator rows with a 0 to 5 rating in half steps, add and remove, collaborators combobox), access and provenance (licence and access radios, public disabled without a release with the hint "Public needs a release (pkdb release)", provenance kind select with method, version and run id for automatic curation), issue and release read only with "Set by pkdb release", descriptions and comments lists, notes per table kind;
- editing shows a sticky bar "Unsaved changes in study.json" with Discard and Save, and marks the Metadata rail entry;
- Save posts the full metadata with the revision; success hides the bar; `reference_error` shows "study.json saved; reference.json could not be refreshed: ...";
- 422 shows each issue at its field (by `issue.field`) and keeps the form;
- 409 shows "study.json changed on disk after you opened this form" with Reload; Reload applies `mergeOnReload` with the 409 `content`, keeps the user's edits, highlights fields changed on disk, and Save then uses the new revision;
- 403 `no_user` shows "Set your PK-DB user in Connection settings" with a button that opens the settings;
- navigating away with unsaved changes asks for confirmation (router guard and `beforeunload`);
- an invalid `study.json` (`value: null` with issues) shows the issues and offers "Start a new study.json from these fields" only when the revision is not null (a symlinked or unregistered file has `revision: null` and is read only).

`curation-reference-dialog.spec.ts`: search fills candidates, preview sends only changed fields, Save is disabled until a preview exists and after any further edit.

- [ ] **Step 2: Run the tests to verify they fail**

Run: the three spec files. Expected: FAIL.

- [ ] **Step 3: Implement**

Use `v-form`, `v-text-field`, `v-autocomplete` (roster items with `v-avatar`), a rating component built from buttons if `VRating` is not registered (register it in the curation app's Vuetify instance only if needed: extend the component list passed by `makeVuetify` through its options, not the website's list), `v-radio-group`, `v-expansion-panels`, `v-alert`. The save bar is `position: sticky` through a CSS class.

- [ ] **Step 4: Run the tests and checks; commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the metadata section with checked saves and the reference dialog"
```

---

### Task 7: Review section

**Files:**
- Create: `frontend/src/curation-app/sections/ReviewSection.vue`, `frontend/src/curation-app/components/ReviewItemCard.vue`, `ReviewItemDetail.vue`, `NewItemDialog.vue`, `TargetView.vue`, `frontend/src/curation-app/review.ts` (filters, target text)
- Test: `frontend/tests/unit/curation-review.spec.ts`, `frontend/tests/components/curation-review-section.spec.ts`

**Interfaces:**
- Consumes: `detail.review: DocumentState<Review>` (items with `id`, `kind`, `state`, `target {file, rows, column}`, `acknowledges`, `text`, `author`, `agent`, `created`, `thread`, `resolved_by`, `resolved`), `reviewAction(revision, action, payload)` for `add` (`kind`, `text`, `target?`, `acknowledges?`), `reply` (`item`, `text`), `resolve`/`dismiss`/`reopen` (`item`, `text?`); `table(file)` for target rows; `source(source)` for the overlay of a digitized series (a target file `timecourses_<Fig>.tsv` with `rows.label` maps to source `<Fig>` and series `label`); `people` profiles for avatars.
- Produces: `filterItems(items, state, kind)`, `targetText(target)` ("timecourses_Fig1.tsv · label = caf_plasma_D150 · column error_type", "whole study"), `seriesOfTarget(target): { source, series } | null`.

- [ ] **Step 1: Write the failing tests**

`curation-review.spec.ts`: filters by state and kind; `targetText` for file only, rows, column, none; `seriesOfTarget` for a timecourse label target and null otherwise.

`curation-review-section.spec.ts`: state chips Open/Resolved/Dismissed/All with counts; kind filter; item cards show kind, state, target, acknowledged code, an agent marker with the agent name as accessible label, a thread marker; selecting an item shows its text, author with avatar, "written by <agent>", created time, thread entries, a reply box (open items only) and Reply/Resolve/Dismiss or Reopen; Resolve posts `{item, text?}` with the review revision; a dismissed acknowledgement can be reopened; New item opens a dialog (kind, text, optional target: file select from `detail.files`, row filter pairs from the table header, column select) that posts `add`; the target view lists the matching rows (fetch `table(file)`, filter by `rows`) and, for a digitized series, renders `SourceOverlay` (Task 9) with that series emphasized; a 409 reloads the detail and shows "review.json changed on disk; the items were reloaded. Repeat your action."; a 403 shows the user hint.

Use a stub for `SourceOverlay` in this component test (Task 9 builds it); if Task 9 is not merged yet, create a minimal `SourceOverlay.vue` that renders its props as text and is replaced in Task 9.

- [ ] **Step 2: Run the tests to verify they fail**

Run: the two spec files. Expected: FAIL.

- [ ] **Step 3: Implement, run the tests and checks, commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the review section with items, threads, targets and new items"
```

---

### Task 8: Problems section

**Files:**
- Create: `frontend/src/curation-app/sections/ProblemsSection.vue`, `frontend/src/curation-app/components/AcknowledgeDialog.vue`, `frontend/src/curation-app/problems.ts`
- Test: `frontend/tests/unit/curation-problems.spec.ts`, `frontend/tests/components/curation-problems-section.spec.ts`

**Interfaces:**
- Consumes: `detail.problems: ValidationIssue[]` (`code`, `severity`, `message`, `source {file, sheet, row, column, cell, header}`, `suggestions`), `detail.acknowledged` (`id`, `code`, `target`, `text`, `author`, `resolved`), `reviewAction(revision, "acknowledge", {code, file, line?, column?, text})` (422 when several locations match, with the message naming them), `openFile(id, file)`, `tablesAction("open")`.
- Produces: `groupByFile(issues)`, `location(issue)` ("timecourses_Fig1.tsv · line 6 · mean · sheet cell timecourses_Fig1!O6"), the Problems route section.

- [ ] **Step 1: Write the failing tests**

Pure tests for grouping and location text. Component tests: severity filter chips with counts (All, Errors, Warnings); issues grouped by file with code, message, location and suggestions ("Did you mean: ..."); "Show in table" navigates to `#/studies/<id>/tables?file=<file>&line=<row>&column=<header>`; "Open tables" posts `tablesAction("open")`; Acknowledge exists only for warnings, opens a dialog with the code, location, message and a required reason, and posts `{code, file, line, column, text}`; the acknowledged list ("Acknowledged warnings (n)") shows each with a link to its review item (`#/studies/<id>/review?item=<id>`); a study beyond the upload limits shows the limit issue at the top.

- [ ] **Step 2: Run, implement, run the tests and checks, commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the problems section with acknowledgements"
```

---

### Task 9: Sources section and the figure overlay

**Files:**
- Create: `frontend/src/curation-app/sections/SourcesSection.vue`, `frontend/src/curation-app/components/SourceOverlay.vue`, `RawGrid.vue`, `MappedRows.vue`, `frontend/src/curation-app/plotly.ts` (nonce-aware loader), `frontend/src/curation-app/overlay.ts` (traces in pixel space)
- Test: `frontend/tests/unit/curation-overlay.spec.ts`, `frontend/tests/components/curation-sources-section.spec.ts`

**Interfaces:**
- Consumes: `detail.sources: SourceSummary[]` (`source`, `image`, `raw`, `raw_kind`, `tables`), `source(source): SourceView` (`image_url`, `image_size [w, h]`, `raw_grid`, `digitization`, `mapped: {file, kind, header, rows: [line, cells][]}[]`, `overlay: {series, role, px, py, x, y, file, line, error_px}[]`, `unmatched`), `loadPlotly()` pattern of `frontend/src/features/plots/plotly.ts`, `plotColors` of `frontend/src/features/plots/theme.ts`.
- Produces:
  - `overlayTraces(view, highlight?: string | null): { traces, layout }`: axes in pixel space `x [0, w]`, `y [h, 0]` hidden, the image as a layout image (`xref: "x"`, `yref: "y"`, `x: 0`, `y: 0`, `sizex: w`, `sizey: h`, `sizing: "stretch"`, `layer: "below"`), one trace per series and role (raw: small dots; mapped: `x-thin-open` markers), error bars as line segments from `(px, py)` to `error_px` in the series color, series colored from a fixed palette by base series name (strip `;error_bar`), other series faded (opacity 0.2) when `highlight` is set, `hovertemplate` "<file> line <line><br><series><br>x <x> · y <y>" with `customdata`, no mode bar (`displayModeBar: false`), fixed axes;
  - `loadNoncedPlotly()`: before the first import, creates `<style id="plotly.js-style-global" nonce="...">` in `document.head` when absent, using `cspNonce()`, so Plotly reuses it instead of creating an un-nonced element;
  - `SourceOverlay.vue` props `{ view: SourceView; highlight?: string | null }`, emits `select-row` with `{file, line}` when a mapped point is clicked; renders a host `div` with `role="img"` and an accessible name, a legend (series names with colors), and an accessible data table in a `<details>`.

- [ ] **Step 1: Write the failing tests**

`curation-overlay.spec.ts`: for a view with a 100 x 100 image, two series and error bar points, `overlayTraces` returns the layout image with the right size and axes ranges, mapped markers at the given pixels, error bar segments ending at `error_px`, the same color for `drug_plasma` and `drug_plasma;error_bar`, opacity 0.2 for non-highlighted series, and `customdata` lines; `loadNoncedPlotly` creates the nonced style element once (mock the dynamic import as the website tests do).

`curation-sources-section.spec.ts` (mock `source()`): one tab per source; a table source shows the image (`<img>` with `alt` "<source> of <identity>"), the raw grid (`RawGrid`, text cells as printed) and the mapped rows grouped by table with TSV line numbers; a figure source with a digitization renders `SourceOverlay` (stubbed) with the view and lists `unmatched` series ("Not digitized: caf_plasma_D75"); without a digitization it shows the image beside a data plot of the mapped rows (reuse `ScientificPlot` only if its input fits; otherwise build a small data plot in `SourceOverlay` with `mode: "plot"`), and placeholders name missing files ("No raw extraction: add <name>_<source>.tsv", "No image: add <name>_<source>.png"); a click on a mapped point navigates to the Tables section at that file and line.

- [ ] **Step 2: Run, implement, run the tests and checks, commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the sources section with raw extractions and the figure overlay"
```

---

### Task 10: Tables section and the table grid

**Files:**
- Create: `frontend/src/curation-app/sections/TablesSection.vue`, `frontend/src/curation-app/components/TableGrid.vue`, `ConflictPanel.vue`, `frontend/src/curation-app/grid.ts`
- Test: `frontend/tests/unit/curation-grid.spec.ts`, `frontend/tests/components/curation-table-grid.spec.ts`, `curation-tables-section.spec.ts`

**Interfaces:**
- Consumes: `detail.sync {status, changes, conflicts}`, `detail.conflicts: ConflictData[]` (`file`, `sheet`, `workbook_rows {row, text}[]`, `table_lines {line, text}[]`, `base_lines`, `kept`), `detail.files`, `detail.review` (open item targets), `detail.problems` (issue cells), `table(file): TableResponse`, `tablesAction("open"|"sync"|"resolve"|"add", payload)` (200 with `{ok, workbook_action, changes, conflicts, issues}`; a failed sync is `ok: false` with issues, not an HTTP error).
- Produces:
  - `TableGrid.vue` props `{ table: TableResponse; highlightLines?: Set<number>; markColumn?: string | null; issueCells?: Map<number, Set<string>>; focus?: { line: number; column?: string } | null; hideEmpty?: boolean }`; renders a header and rows with TSV line numbers, amber rows for `highlightLines`, outlined cells for issues (with the issue message as the cell's accessible description), a marked column; above 500 rows it virtualizes rows (`VVirtualScroll` or a small windowing component with a fixed row height) and scrolls to `focus`;
  - `visibleColumns(table, hideEmpty)`, `targetLines(table, items)` (open review items' `rows` filters on this file), `issueCells(issues, file)` in `grid.ts`;
  - `ConflictPanel.vue`: per conflicting file, base, workbook and tables rows side by side (cells split by tab under the table header when known), buttons Keep workbook and Keep tables (post `resolve` with `keep`) and Open workbook.

- [ ] **Step 1: Write the failing tests**

`curation-grid.spec.ts`: `visibleColumns` hides columns empty in every row; `targetLines` matches rows by filter; `issueCells` maps `(row, header)`.

`curation-table-grid.spec.ts`: renders lines and cells; amber rows and outlined issue cells; a 5,000-row table renders fewer than 100 row elements and scrolling (set `scrollTop` and dispatch `scroll`) renders the rows of that window with correct line numbers; `focus` scrolls the line into view and marks the cell.

`curation-tables-section.spec.ts`: the sync status alert for each status ("In sync", "Workbook open: close it to sync", "Syncing", "Changed: the next sync writes N files", "Conflict in <file>", "No workbook yet: Open tables creates it", "Not checked yet"); the conflict panel posts `resolve` with `keep: "workbook"` and shows the result issues; tabs per table and raw table (counts); "Hide empty columns" toggle; the route query `file`, `line`, `column` (from Problems) selects the tab and focuses the cell; Add table opens the dialog of Task 5.

- [ ] **Step 2: Run, implement, run the tests and checks, commit**

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the tables section with sync status, conflicts and a virtualized grid"
```

---

### Task 11: Activity section

**Files:**
- Create: `frontend/src/curation-app/sections/ActivitySection.vue`
- Test: `frontend/tests/components/curation-activity-section.spec.ts`

**Interfaces:**
- Consumes: `detail.jobs: Job[]` (newest first; `action` `validate`, `validate_remote`, `upload`, `write`; `status`; `stage`; `message`; `created_at`; `persistence`; `report_id`; `upload {url}`), `GET /local/reports/{id}` (download as JSON), `cancelJobs([id])`, `clearHistory()`.
- Produces: the Activity section: one entry per job with an icon per action, the message, time, status chip, persistence ("created", "replaced", "unknown outcome"), a link to the uploaded study page, "Download report" (fetch the report and save it as `pkdb-report-<id>.json` through a Blob link), Cancel for queued jobs; "Clear finished history".

- [ ] **Step 1: Write the failing test, run, implement, run, commit**

The component test covers each action and status label, the report download (mock `getJson` and `URL.createObjectURL`), cancel and clear.

```bash
git add frontend/src/curation-app frontend/tests
git commit -m "Add the activity section of the study page"
```

---

### Task 12: End-to-end tests against the real local server

**Files:**
- Create: `tools/curation_testing/fixture/caffeine/Harder1988/...` (a committed format 2 study: `study.json`, `review.json` with open, resolved and dismissed items including an acknowledgement and an agent item, `reference.json`, `subjects.tsv`, `interventions.tsv`, `characteristica.tsv`, `outputs_Tab2.tsv`, `timecourses_Fig1.tsv` with two series and one misplaced point, `Harder1988_Tab2.tsv` raw table, `Harder1988_Fig1.png` (900 x 600), `Harder1988_Fig1.wpd.json`, `Harder1988_Tab2.png`, `Harder1988.pdf` placeholder), a second study `caffeine/Newton1981` (draft, with one deliberate error), and one format 1 folder `caffeine/Legacy1990`
- Create: `tools/curation_testing/workspace.py` (copies the fixture to a target folder and creates the workbook of Harder1988 with `sync_study` and the bundled vocabulary), `tools/curation_testing/record_open.py` (appends its argument to the file named by `PKDB_OPEN_LOG`)
- Create: `frontend/playwright.curation.config.ts`, `frontend/tests/curation-e2e/global-setup.ts`, `global-teardown.ts`, `fixtures.ts`, specs `overview.spec.ts`, `metadata.spec.ts`, `review.spec.ts`, `problems.spec.ts`, `tables.spec.ts`, `sources.spec.ts`, `screens.spec.ts`
- Modify: `frontend/package.json` (script `test:curation-e2e`), `.github/workflows/ci-cd.yml` (client job, Linux 3.14 only: `npx playwright install --with-deps chromium` and `npm run test:curation-e2e`, uploading `frontend/playwright-report` on failure), `frontend/eslint.config.ts` and `tsconfig.json` only if the new files need it
- Test: the specs

**Interfaces:**
- Consumes: the built app (`npm run build:curation`), `pkdb curate <workspace> --offline --no-browser --port 0 --state-dir <dir>` printing `PK-DB curation: http://127.0.0.1:<port>/#token=...`, `PKDB_OPEN_COMMAND`, `PKDB_USER=curator`.
- Produces: `npm run test:curation-e2e` (`playwright test --config playwright.curation.config.ts`, chromium, one worker); a fixture `test.extend` that gives each spec a fresh workspace and server (start per test file through a worker-scoped fixture so files do not share state), the launch URL, the workspace path and the open log.

- [ ] **Step 1: Fixture data**

The fixture validates with the bundled vocabulary (`uv run --project python pkdb validate tools/curation_testing/fixture/caffeine/Harder1988 --offline`) with zero errors and only the deliberate warnings (one `digitized_mismatch` from the misplaced point, one `unused_intervention`); Newton1981 has exactly one deliberate error. Use real vocabulary terms (substance `caffeine`, tissue `plasma`, measurement `concentration`, species `homo sapiens`). Check `pkdb format --check` passes for both.

- [ ] **Step 2: Write the specs**

Each spec opens the launch URL, waits for the overview, collects `securitypolicyviolation` events through `page.addInitScript` (push into `window.__cspViolations`) and console errors, and asserts both are empty at the end. Cover spec section 10:

- `overview.spec.ts`: two rows, the footer "1 study format 1 folder is not listed ...", the search and chips, Needs attention lists Newton1981, Validate queues a job and the status changes, the header shows the user `curator`;
- `metadata.spec.ts`: edit the licence and a description, Save, the file on disk changes (read it with `fs`); edit again, change `study.json` on disk meanwhile (append a description with Node `fs` in canonical JSON), Save gives the conflict message, Reload keeps the edit and shows the disk change, Save succeeds;
- `review.spec.ts`: reply and resolve an open item, the thread shows the reply; add an item with a row target; set Approved is refused with the message while items are open;
- `problems.spec.ts`: acknowledge the `unused_intervention` warning with a reason; it moves to "Acknowledged warnings" and a review item exists; Show in table focuses the cell;
- `tables.spec.ts`: sync status "In sync"; Open tables records the workbook path in the open log; edit the workbook on disk with a Python helper (`uv run --project python python tools/curation_testing/edit_workbook.py <workbook> <sheet> <cell> <value>`, created in this task) and the tables update within the next polls; create a conflict (edit the same row in the workbook and the TSV) and resolve it with Keep workbook;
- `sources.spec.ts`: the Fig1 tab renders the overlay (the Plotly host has data), hovering a mapped point shows "timecourses_Fig1.tsv line 6", clicking it opens the Tables section at that line; the Tab2 tab shows the image, the raw grid and the mapped rows;
- `screens.spec.ts`: for overview and each study section, in light and dark theme: axe (`wcag2a`, `wcag2aa`, `wcag21aa`) has no violations, no horizontal page scroll at 390 x 844, and full-page screenshots are attached to the report.

- [ ] **Step 3: Run**

Run: `cd frontend && npm run build:curation && npm run test:curation-e2e`
Expected: all specs pass with zero CSP violations. Fix product code (not tests) when a spec finds a defect; record each fix in the report.

- [ ] **Step 4: CI and commit**

Wire the CI step, run the frontend checks and the Python suite once.

```bash
git add tools/curation_testing frontend .github/workflows/ci-cd.yml
git commit -m "Test the curation app end to end against the real local server"
```

---

### Task 13: Documentation and screenshots

**Files:**
- Modify: `docs/local-curation.md` (rewrite for the new app), `tools/curation_docs/README.md`
- Rewrite: `tools/curation_docs/render.mjs` (Playwright screenshots of the new UI against a running `pkdb curate` on the Task 12 fixture workspace)
- Replace: `docs/images/curation/*.png` (overview, study review, sources overlay, tables conflict, metadata; light theme, 1440 x 900)
- Test: docs build

**Interfaces:**
- Consumes: Tasks 1 to 12.

- [ ] **Step 1: Rewrite the page**

`docs/local-curation.md` (paragraphs on one line, no em dash) covers: starting `pkdb curate` (workspace, launch URL, offline, user and API key, `PKDB_USER`), the overview (columns, filters, needs attention, batch actions, format 1 folders), the study page sections (Metadata with Save and conflicts, Review with targets and approval rules, Problems with acknowledgements, Sources with raw extractions and the overlay, Tables with sync status and conflicts, Activity), what happens on save (sync, format, validate, upload), working with the workbook (Open tables, Add table, conflicts), WebPlotDigitizer projects (`pkdb digitize import`), AI-curated studies (agent items, `pkdb review`), the local API for developers (short), building from source (`npm ci && npm run build:curation`, `npm run dev:curation` with `PKDB_CURATION_URL`), and troubleshooting (server stopped, launch URL, missing assets). Replace the statement that the app needs no Node installation with: the published package contains the built app; a source checkout needs Node once.

- [ ] **Step 2: Screenshots**

`render.mjs` reads `PKDB_CURATION_URL` (loopback only), drives the new UI by roles and labels, and writes the five images. Run it against the fixture workspace, look at each image (Read the PNGs) and fix visible defects in the app before committing them.

- [ ] **Step 3: Verify and commit**

Run the docs build without warnings and the frontend and Python checks.

```bash
git add docs tools/curation_docs
git commit -m "Document the curation app with new screenshots"
```
