---
search:
  exclude: true
---

# Curation app for study format 2

Date: 2026-10-06. Status: Draft for review. Sub-project 4 of [Study format v2](2026-10-05-study-format-v2-design.md) (section 17). The screens and decisions were settled in two Lavish review rounds on 2026-10-06; the implementation is split into three parts (section 12), each with its own plan and pull request.

## 1. Objective

A curator opens a format 2 study that a person or an AI agent curated and checks it in one place: every review item next to the rows it points at and the source it came from, every validation issue at its cell, every paper table and figure next to its raw extraction and the rows mapped into the database. The curator edits metadata in forms, edits tables in the workbook while the app keeps workbook and tables in sync, resolves review items, and approves the study. AI agents do the same through the `pkdb` CLI, which calls the same functions.

Success criteria:

- `pkdb curate` is the writer for `study.json` (metadata forms), `review.json` (review items) and the tables (through the sync engine). Every write goes through the same library functions as the CLI, is validated before it is written, is atomic, and is refused when the file changed on disk since it was read.
- For every source the app shows the image, the raw extraction (the paper table as printed, or the digitized figure) and the mapped rows of all tables with that source. Digitized figures are overlaid on the image.
- A review item shows its target rows and, for a digitized series, the figure with that series emphasized.
- A warning is acknowledged with one action and a reason, and acknowledged warnings stay visible.
- Approving a study requires zero open review items, zero validation errors and a person, not an agent, who approves.
- The app is format 2 only and uses the website's components and theme in light and dark mode.
- End-to-end browser tests run against the real local server and cover metadata, review, acknowledgement, sync status and conflicts, sources and the plot comparison, with zero Content Security Policy violations.

## 2. Current state

Findings from the code on 2026-10-06 (develop at `10f2a91a`):

- `python/src/pkdb/curation/` is a stdlib `ThreadingHTTPServer` (`server.py`, 273 lines) over one `CurationEngine` class (`engine.py`, 1,305 lines) with three threads: the 1-second watcher (`scan`, `schedule_changes`), the job worker (`run_job`) and the 30-second connection heartbeat. The browser polls the whole snapshot every 1.5 s. The front end is 335 lines of dense vanilla JavaScript without views for metadata, review or tables.
- The engine never imports `pkdb.studyformat`. For a format 2 folder it reads format 1 keys (`sid`, `groupset`, curators as strings), so identity, curators and counts are empty; it never syncs the workbook, never formats, and uploads without the sync and format step of `pkdb upload`. The Reference dialog fails when the identifiers change, because `study.json` owns them in format 2.
- Acknowledged warnings are removed from the report, so a UI must list them from the review items. Items in state `dismissed` still acknowledge.
- Nothing stores where the axes of a figure image are, and there is no raw transcription of paper tables. There is no `pkdb study`, `pkdb review` or `pkdb plot`, no ULID generator, and no plotting code in the Python package.
- The sync engine merges line based (diff3 on canonical lines), so a grid whose row order must be kept fits its merge; reading, rendering and workbook writing are template driven and need a raw path.
- The website front end (`frontend/`) uses Vue 3.5, Vuetify 4.2 with Font Awesome, vue-router, Pinia, Plotly 4.1, vitest and Playwright, with strict source checks (`<script setup lang="ts">` only, no `any`, no JavaScript sources). It has one Vite entry and no CSP nonce.

## 3. Decisions

| # | Topic | Decision |
|---|---|---|
| D1 | Front end | Vue 3 + Vuetify, built into the Python package. |
| D2 | Figure comparison | Overlay on the figure image when the figure is digitized; a plot beside the image otherwise. |
| D3 | Tables in the app | Read-only viewer with highlighted review targets and issue cells. Editing happens in the workbook. |
| D4 | Layout | Overview page plus a full study page with a section rail. |
| D5 | Author of writes | The PK-DB account (`--user` / `PKDB_USER`, checked against the API key when online). |
| D6 | Format 1 | Not supported. Format 1 folders are counted, not listed; they stay on the released app version until the cutover. |
| R1 | Figure calibration | Comes from the digitization file of the figure (WebPlotDigitizer JSON); no copy in `study.json`. |
| R2 | Drawing | Interactive Plotly in the browser; `pkdb plot` renders the same comparison with matplotlib for agents. |
| R3 | Metadata saving | Explicit Save and Discard with an on-disk change check. Metadata is the first section of the study page. |
| R4 | Front-end source | A second Vite entry in `frontend/`; the build output is gitignored and built by CI before the wheel. |
| R5 | Approval | Zero open items, zero validation errors, approved by a person. |
| R6 | Raw extraction | Every table and figure source keeps its raw extraction beside the mapped rows: `<name>_<source>.tsv` for tables, `<name>_<source>.wpd.json` for figures. |

## 4. Format additions

These additions amend the format 2 design (section 13 lists the changed sections). They are implemented in `pkdb.studyformat` and therefore apply to the CLI, pre-commit, CI, upload and the server alike.

### 4.1 Raw extraction

A source is a paper table (`Tab…`), a figure (`Fig…`) or the text (`Text`). The mapped rows of a source are the rows of the per-source tables `<kind>_<source>.tsv` plus the rows of `subjects`, `interventions` and `characteristica` whose `source` column names it. The raw extraction is what was read off the paper before mapping:

| Source | Raw extraction | Written by |
|---|---|---|
| `Tab…` | `<name>_<source>.tsv`, the table as printed | the curator in the workbook sheet `<name>_<source>`, or an agent as text |
| `Fig…` | `<name>_<source>.wpd.json`, the WebPlotDigitizer project of the image | `pkdb digitize import` |
| `Text` | none | |

Raw extractions are optional for validation, because migrated studies have none. The AI workflow writes them for every table and figure source it extracts (section 13 of the format 2 design).

### 4.2 Table raw extraction

`<name>_<source>.tsv` holds the cells of the paper table in their printed positions: header rows, row labels, units and footnote markers as text, merged cells written once in their top-left position.

- Encoding: UTF-8, LF line endings and a final newline, tab separated, cells quoted and escaped as in the other tables. There is no header line with column names and there are no `study` or `source` columns.
- Canonical form: each cell stripped of surrounding whitespace, rows padded to the widest row, trailing empty cells and fully empty rows removed, row order kept. Cells are text: nothing is parsed as a number, so `1.50`, `007` and `12 ± 3` stay as printed. A file without non-empty cells is removed, like an empty table.
- Workbook: the sheet `<name>_<source>` follows the data sheets of the same source. Every cell is written as a text cell and the used columns plus a margin of 10 columns default to the text format, so typed values stay text. There are no dropdowns, comments, filters or frozen panes. Converted cells (dates, percentages, errors, line breaks) are errors at their cell, as for data sheets.
- Sync: the same three-way, line-based merge as the data tables, with the raw renderer instead of the template renderer, so rows are never re-sorted. `pkdb tables add <study> --raw Tab2` adds the sheet; the file appears once the sheet has a non-empty cell.
- Layout: a file matches when its name is `<name>_<source>.tsv` with the folder name as `<name>` and a `Tab…` source. Its sheet name counts in the 31-character and case-insensitive uniqueness checks. A raw table without a table image is an error (`missing_image`), as for data tables.

### 4.3 Figure raw extraction

`<name>_<source>.wpd.json` is a WebPlotDigitizer 4 project (`version` `[4, x]`) digitized on `<name>_<source>.png` itself, so pixel coordinates refer to that image with the origin at the top-left corner and y pointing down.

- Accepted content: `axesColl` entries of type `XYAxes` with `isLogX`, `isLogY`, `noRotation` and exactly four `calibrationPoints` in the order X1, X2, Y1, Y2 (`px`, `py` in pixels; `dx`, `dy` numbers or numeric strings), `datasetColl` entries with `name`, `axesName` and `data` points (`x`, `y` pixels), and an empty or absent `measurementColl`. Other axes types, date calibration values and measurements are errors (`digitization_unsupported`).
- Calibration: values are transformed with `log10` on log axes. Lines of equal x run parallel to the Y1-to-Y2 vector and lines of equal y parallel to the X1-to-X2 vector, as in WebPlotDigitizer: a pixel `p` is written as `p - X1 = a·(X2 - X1) + b·(Y2 - Y1)`, which gives `x = x1 + a·(x2 - x1)`, and as `p - Y1 = c·(X2 - X1) + d·(Y2 - Y1)`, which gives `y = y1 + d·(y2 - y1)`. `noRotation` forces horizontal and vertical axis vectors. The inverse maps data to pixels for the overlay. Tests check the mapping against the `value` arrays of real WebPlotDigitizer exports.
- Dataset names connect raw and mapped data: a dataset named like a timecourse `label` holds the central values of that series (time on x; `mean`, else `median`, else `gmean` on y), a dataset named `<label>;error_bar` holds the ends of its error bars, and a dataset named like a scatter `name` holds its points (`x_*` on x, `y_*` on y). Names cannot contain `;`, so these names never collide. Digitizing and mapping use the units printed on the axes; conversions happen in postprocessing.
- Canonical form: the loaded JSON with its key order, `autoDetectionData` set to `null`, every point `value` recomputed from the pixels with the calibration above (numbers rendered like table numbers), written by `dump_json`.
- `pkdb digitize import <study> <source> <file>` accepts a bare `wpd.json` or a saved `.tar` project, validates it, and writes the canonical file. When `<name>_<source>.png` is missing and the project contains exactly one PNG image, the import writes it.
- Validation:
  - `digitization_outside_image` (error): a calibration or data pixel lies outside the image.
  - `unknown_dataset` (warning): a dataset name matches no label, `<label>;error_bar` or scatter name of the source.
  - `digitized_mismatch` (warning): a mapped row lies more than 2 pixels from every point of its dataset, or a dataset point has no mapped row. The issue sits at the row and column, so it can be acknowledged.
- Rows of a figure source without a matching dataset are not compared; the app draws them beside the image.

### 4.4 Review approval

`review.json` gains `approved_by` (a user) and `approved` (a time with time zone), written after `reviewers`. Both are set exactly when `status` is `approved`, and `approved_by` must be listed in `reviewers`; the model rejects anything else. Setting a study to approved, in the app or with `pkdb review status approved`:

- requires zero open items (validated, as today) and zero validation errors at that moment (checked by the command, not stored);
- is refused when the command runs for an agent (`--agent` or `PKDB_AGENT`), so a person always approves;
- records the user as `approved_by`, adds them to `reviewers` and stores the time.

Any other status clears both fields. Items in state `dismissed` no longer acknowledge warnings, so dismissing an acknowledgement brings its warning back.

### 4.5 Reserved names and new codes

- Study folder names equal to a per-source kind (`outputs`, `timecourses`, `scatters`) are reserved, because `outputs_Tab2.tsv` would be both a table and a raw extraction.
- New issue codes: `digitization_invalid` (error, the file is not a readable WebPlotDigitizer project), `digitization_unsupported` (error), `digitization_outside_image` (error), `unknown_dataset` (warning), `digitized_mismatch` (warning). Raw table cells use the existing cell and layout codes.

## 5. Library

New modules in `pkdb.studyformat`, used by the CLI and the app. Every write function takes the folder, the user, an optional agent, and the revision the caller read; it validates the complete new document with the Pydantic model, writes canonical text atomically under a per-folder lock, and returns the new revision. A revision is the SHA-256 of the file bytes (`absent` for a missing file). A stale revision raises `RevisionConflict` with the current content.

- `revision.py`: revisions, the per-folder lock and `RevisionConflict`.
- `ulid.py`: monotonic ULIDs (48-bit milliseconds and 80 random bits, Crockford base 32).
- `metadata.py`: `read_metadata(folder)` and `write_metadata(folder, metadata, revision)`; `patch_metadata` applies a JSON merge patch (RFC 7386) and writes; a changed PMID or DOI refreshes `reference.json` through `sync_reference`.
- `review_edit.py`: `add_item`, `reply`, `resolve`, `dismiss`, `reopen`, `set_status` (section 4.4) and `acknowledge(folder, issue, text)`. `acknowledge` builds the target from the issue: the file, the column, and a `rows` filter over the table's sort columns of that row, extended column by column until it matches only that row; issues without a row target the file.
- `raw.py`: loading, rendering and workbook reading and writing of raw tables.
- `digitize.py`: loading and validating WebPlotDigitizer projects, the calibration in both directions, the canonical form, `import_project`, and the comparison behind `digitized_mismatch`.
- `sources.py`: `study_sources(study)` lists each source with its image, raw extraction and mapped rows; `source_view(study, source)` returns them with pixel coordinates for every raw point and every mapped row of a digitized figure, and with data values for hover.
- `plot.py`: `render_source(study, source, path)` draws the image, the raw points and the mapped rows with error bars with matplotlib (overlay for digitized figures, two panels otherwise). matplotlib becomes a direct dependency of the client.
- `pipeline.py`: `sync_and_format(folder, vocabulary)` syncs (one retry when a save arrives during the sync) and formats, stopping on conflicts. `pkdb upload` and the app's watcher both use it; the private copy in `batch.py` goes away.

## 6. CLI

All commands take `--user` (default `PKDB_USER`) and `--agent` (default `PKDB_AGENT`), print human output on a terminal and JSON otherwise (`--format human|json`), and exit non-zero on validation errors and revision conflicts.

| Command | Purpose |
|---|---|
| `pkdb study show <study>` | Print `study.json`, its revision and the derived identity. |
| `pkdb study patch <study> (--json TEXT \| --file F) [--revision R]` | Apply a JSON merge patch to `study.json`. |
| `pkdb study reference <study> [--pmid N] [--doi D]` | Set the identifiers and refresh `reference.json`. |
| `pkdb review show <study> [--state S]` | Print items with their target matches. |
| `pkdb review add <study> --kind K --text T [--file F] [--rows COL=VALUE ...] [--column C] [--acknowledges CODE]` | Add an item; prints its id. |
| `pkdb review reply\|resolve\|dismiss\|reopen <study> <id> [--text T]` | Change an item. |
| `pkdb review status <study> draft\|in_review\|approved` | Change the status (section 4.4). |
| `pkdb review acknowledge <study> <code> --file F --line N [--column C] --text T` | Acknowledge one warning. |
| `pkdb digitize import <study> <source> <file>` | Write `<name>_<source>.wpd.json` (section 4.3). |
| `pkdb plot <study> [--source S] [--out DIR]` | Render `<name>_<source>.plot.png` per source into DIR (default a new temporary folder), never into the study folder. |
| `pkdb tables add <study> --raw <source>` | Add a raw table sheet (extends section 10.1 of the format 2 design). |

## 7. Curation engine and local API

### 7.1 Structure

The engine becomes format 2 only and is split by responsibility. The format 1 paths are deleted: the `metadata.py` summary of format 1 sections, `sid`-based identity and duplicate checks, hidden `.<name>_*.tsv` markers, `sync_tsvs`, and the manual issue-to-folder mapping (the issue number is in `study.json`).

| Module | Responsibility |
|---|---|
| `engine.py` | Facade: state file, threads, snapshot. |
| `workspace.py` | Workspace selection, folder browser, the 1-second scan, study rows, file resolution. |
| `jobs.py` | Queue, worker, the pipeline of section 7.2, upload outcome handling (`resume`, `retry_unknown`). |
| `connection.py` | Configuration, heartbeat, vocabulary, identity. |
| `issues.py` | GitHub issue state, labels and assignees for display, by the issue number in `study.json`. |
| `studies.py` | Study detail, tables, sources and images for the API; write actions that call the library. |
| `server.py` | HTTP, sessions, CSRF, CSP nonce, static assets and avatars. |

A study is addressed by its identity `<substance>/<name>` instead of a hash.

### 7.2 Watcher pipeline

The watcher keeps today's behavior (1-second scan, 1 s of quiet, one queued job per study, the initial scan validates every study). A job runs:

1. `sync_and_format`. A conflict ends the job with status `conflict` and the conflicting rows; nothing else runs.
2. Validation (`validate_folder`), or `prepare_folder` when the job uploads.
3. Upload when "On save" is Upload, with today's outcome handling.

The study row carries review status, open item count, error and warning counts, sync status (`in_sync`, `workbook_open`, `syncing`, `conflict`, `no_workbook`), release, issue, curators and the last upload. A write made in the app changes file signatures, so the watcher validates afterwards without special cases.

### 7.3 HTTP API

All `/local/` routes keep today's session cookie, CSRF header, Host and Origin checks and JSON-only bodies. GET responses carry an `ETag`; the browser polls with `If-None-Match` and receives `304` when nothing changed.

| Method and path | Purpose |
|---|---|
| `GET /local/state` | Overview: workspace, connection, user, study rows, jobs. |
| `GET /local/studies/{substance}/{name}` | Study page: metadata and revision, review and revision, problems, acknowledged warnings, sync status and conflicts, sources, files, jobs. |
| `GET /local/studies/{substance}/{name}/tables/{file}` | Header and rows with TSV line numbers, or the grid of a raw table. |
| `GET /local/studies/{substance}/{name}/sources/{source}` | `source_view` (section 5). |
| `GET /local/studies/{substance}/{name}/files/{file}` | A registered image of the study (`png`, `jpg`, `jpeg`, `webp`), for `<img>` and the plot. |
| `POST /local/studies/metadata` | Write `study.json` (`study`, `revision`, `metadata`). |
| `POST /local/studies/review` | `add`, `reply`, `resolve`, `dismiss`, `reopen`, `status`, `acknowledge`. |
| `POST /local/studies/tables` | `open` the workbook, `sync`, `resolve` with `keep`, `add` a data or raw sheet. |
| existing | Session, workspace, folder browser, settings, mode, jobs, pause, resume, retry, reference, files open, history, reports. |

A stale revision returns `409` with the current document; validation errors return `422` with the issues; everything else keeps today's error mapping. The body limit rises from 64 KiB to 1 MiB.

### 7.4 Identity

The user is the authenticated PK-DB account when an API key is configured and the server is reachable, otherwise the configured user (`--user`, `PKDB_USER` or the saved setting). Writes are refused without a user. The app shows the user in the header; the CLI uses the same resolution.

### 7.5 Security

- Every response of `index.html` gets a fresh nonce. The CSP becomes `style-src 'self' 'nonce-…'` with `script-src 'self'` unchanged; the nonce reaches the Vite-generated tags (`html.cspNonce` placeholder replaced by the server), Vuetify (`theme.cspNonce`) and the style element Plotly reuses (`plotly.js-style-global`, created by the app with the nonce before Plotly loads). `'unsafe-inline'` is never allowed; the end-to-end tests fail on any `securitypolicyviolation` event.
- File, table, source and image routes serve only files registered in the study, reject symlinks and paths outside the study folder, and apply the row limits of upload.
- Avatars move from the build output to the tracked `python/src/pkdb/curation/avatars/` (written by `scripts/update_client_curators.py`) and are served at `/avatars/`.

## 8. Front end

### 8.1 Source, build and packaging

- Source in `frontend/src/curation-app/` with the entry `frontend/curation-app.html` and its own `vite.curation.config.ts`: relative base, `build.outDir` `../python/src/pkdb/curation/static` with `emptyOutDir`, `assetsInlineLimit: 0`, and `html.cspNonce`. It shares `plugins/vuetify.ts` (extended with an optional nonce), Font Awesome, lint, type checks and source checks with the website.
- `npm run build:curation` builds; `npm run dev:curation` serves with Vite and proxies `/local` and `/avatars` to a running `pkdb curate --no-browser` (`PKDB_CURATION_URL`).
- `python/src/pkdb/curation/static/` is gitignored. The wheel includes it as a hatch artifact, and a hatch build hook fails the build when `index.html` is missing. CI builds the assets before `uv build` and the wheel install test. A source checkout without assets makes `pkdb curate` exit with the instruction to run `npm run build:curation`.
- The vanilla front end, `tools/curation_docs/smoke.mjs` and its fixtures are removed.

### 8.2 Screens

Routes use hash history: `#/` and `#/studies/{substance}/{name}/{section}`.

- **Header:** logo, workspace (folder browser, recent workspaces), file watching (pause), connection and user, settings, light and dark theme.
- **Overview:** search, substance filter and status chips (all, needs attention, draft, in review, approved); a table with study and reference title, review status and AI provenance, open items, errors and warnings, sync status, release, issue, curators, On save and last upload; batch Validate, Upload and On save for selected rows; a footer that counts format 1 folders. "Needs attention" means errors, a sync conflict, or open items while in review.
- **Study page:** a header with identity, review status, release, issue with its label, provenance, a summary line, and the actions Open tables, Validate, Upload and a menu (Open folder, Open PDF, Add table, Copy path). The rail lists Metadata, Review, Problems, Sources, Tables and Activity with counts. The page opens on Review when items are open, on Problems when there are errors, otherwise on Metadata.
- **Metadata:** cards for reference (PMID, DOI, match state of `reference.json`, and the Reference dialog for corrections), people (creator, curators with ratings in half steps, collaborators from the roster), access and provenance (provenance fields per kind), issue and release (read only), descriptions, comments, and notes per table kind. A sticky bar shows unsaved changes with Save and Discard; leaving with unsaved changes asks first; a stale revision blocks Save and offers Reload, which keeps the user's edits on top of the reloaded document and marks fields that changed on disk.
- **Review:** state and kind filters, New item, item cards (kind, state, target, acknowledged code, agent and thread markers), and the selected item with its thread, Reply, Resolve, Dismiss or Reopen. Below it the target: the matching rows, and for a digitized series the figure overlay with the other series faded. Setting the status explains why approval is refused.
- **Problems:** severity filter, issues with code, message, file, line, column and workbook cell, Show in table, Open tables, and Acknowledge for warnings (reason required). Acknowledged warnings are listed from the review items with a link to the item.
- **Sources:** one tab per source. Table sources show the image, the raw table grid and the mapped rows grouped by table. Figure sources show the overlay of raw points and mapped rows on the image (hover shows the TSV line and values; clicking a mapped point selects its row), a plot beside the image when there is no digitization, the mapped rows, and the issues of the source.
- **Tables:** the sync status first (in sync with the last sync summary, workbook open, syncing, or the conflict panel with base, workbook and tables for the conflicting rows and Keep workbook, Keep tables, Open workbook), then one tab per table and raw table with a read-only grid. Rows targeted by open review items are amber, cells with issues are outlined, empty columns can be hidden, and Add table adds a data or raw sheet.
- **Activity:** jobs of the study (syncs, validations, uploads, app writes), newest first.
- **Dialogs:** workspace, settings, upload review and the unknown-outcome retry carry over from today's app.

### 8.3 Structure

`main.ts`, `App.vue`, the router, an API client (CSRF header, typed responses, `409` and `422` handling), a polling composable with ETags, Pinia stores for the overview and the open study, views per page and section, and components such as `TableGrid` (row virtualization above 500 rows), `SourceOverlay` (Plotly in pixel space with the image as layout image, error bars as line segments), `ReviewItem`, `AcknowledgeDialog`, `AddTableDialog` and `ConflictPanel`.

## 9. Error handling

| Situation | Behavior |
|---|---|
| File changed on disk before a write | `409`; the metadata form offers Reload; review actions report the conflict and reload the items. Nothing is retried silently. |
| Invalid document | `422` with the issues at their fields; nothing is written. |
| Sync conflict | Job status `conflict`; the Tables section shows the panel; format, validation and upload wait. |
| Workbook open during add or regeneration | Refused with "close the workbook first"; syncs wait for the next save. |
| Missing image or raw extraction | The section shows a placeholder naming the expected file. |
| WebPlotDigitizer file invalid | The figure shows the plot beside the image and the issue. |
| Missing user | Writes refused with a link to settings. |
| Missing front-end assets | `pkdb curate` exits with the build instruction. |
| Server unreachable | Header shows the connection state; uploads pause as today; local writes continue. |

## 10. Testing

- Library: unit tests for revisions and conflicts, ULIDs (order and format), metadata patches, every review action and the approval rules, acknowledgement targets (unique row filters), raw table read, render, workbook round trip with text cells, and merge without re-sorting; WebPlotDigitizer loading, both calibration directions against real export `value` arrays (linear, log, rotated), canonical form idempotence, import of `.json` and `.tar`, and one broken fixture per new issue code; `source_view` pixel coordinates.
- Plot: `pkdb plot` writes PNGs, and a test checks that its pixel positions match `source_view`.
- CLI: one test per command in human and JSON output, including conflicts and agent refusal of approval.
- Engine and server: format 2 fixture workspaces for the pipeline (sync, conflict, format, validate, upload with a mocked client), ETags, every new route including path and symlink rejection, the CSP nonce per response, and the body limit.
- End to end: Playwright in `frontend/tests/curation-e2e/` with its own config. A global setup creates a workspace with fixture studies (images, raw tables, a WebPlotDigitizer file, a workbook), starts the real `pkdb curate --offline` with a recording opener (`PKDB_OPEN_COMMAND`), and reads the launch URL. Specs cover overview filters, metadata edit, save and on-disk conflict, review add, reply, resolve and the approval refusal, acknowledge and its listing, sync status after a workbook save (edited with openpyxl) and conflict resolution, sources with raw table and overlay hover, light and dark screenshots, axe accessibility checks, and zero CSP violations. CI runs them in the client job with Node and Python.
- Front-end unit tests (vitest) for the API client, the polling composable and the grid.

## 11. Documentation

- `docs/local-curation.md` is rewritten for format 2 with new screenshots rendered by a rewritten `tools/curation_docs/render.mjs`.
- `pkdb schema docs` documents raw tables, WebPlotDigitizer projects with the dataset naming rule, and the review approval fields in `docs/study-format.md`; the JSON Schema export includes them.
- The CLI reference documents `pkdb study`, `pkdb review`, `pkdb digitize` and `pkdb plot`.

## 12. Implementation parts

| Part | Content | Depends on |
|---|---|---|
| A | Sections 4 to 6: format additions, library, CLI, `pkdb plot`, schema docs. | merged sub-projects 1 to 3 |
| B | Section 7: engine split and format 2 pipeline, local API, identity, security, avatars. | A |
| C | Sections 8, 10 (end to end) and 11: front end, packaging, CI, documentation. | B |

Each part is one plan and one pull request against `develop`.

## 13. Changes to the format 2 design

Applied to [the format 2 design](2026-10-05-study-format-v2-design.md) together with this spec: section 4 lists the raw extraction files, section 7 the approval fields and the dismissed rule, section 10.1 the new commands, section 10.5 points here, and section 13 adds raw extraction and `--agent` to the AI workflow.

## 14. Out of scope

- Editing tables or digitizing figures in the app. Tables are edited in the workbook; figures are digitized in WebPlotDigitizer.
- Creating, renaming or labelling GitHub issues (sub-project 5) and the curation guide and agent skill in pkdb_data (sub-project 6).
- Format 1 folders.
- Multi-user or remote use of the local app.
