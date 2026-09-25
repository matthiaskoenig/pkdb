---
search:
  exclude: true
---

# Local study curation interface

Date: 2026-09-24. Status: Design baseline implemented with the boundaries and verification recorded in the [implementation plan](../plans/2026-09-24-local-curation-interface.md). Issue: [#826](https://github.com/matthiaskoenig/pkdb/issues/826).

See the [illustrated curation guide](../../local-curation.md) for user-facing workflows and labeled design-preview screenshots.

## Product direction

`pkdb curate` opens a local browser application around the Python package. A curator can find assigned work, select local study folders, validate source files, open a problem at its source, and upload a reviewed selection to an explicitly selected PK-DB server. The normal loop is **choose study → open problem → edit and save in the default application → automatically validate → optionally upload**. Manual validation and upload remain available.

The application never edits source files. All editing happens outside the app in the computer’s default applications. It provides study selection, validation, diagnostics, file opening, and uploads. Git commits/pushes and managing GitHub issues are outside its initial scope. MCP remains read-only and is not used for uploads.

## Evidence from the current repositories

- `pkdb_data/docs/curation_guide.md` directs curators to coordinate assignments in the [pkdb_data issue tracker](https://github.com/matthiaskoenig/pkdb_data/issues). Sample issues use titles such as `Gd-EOB-DTPA/Stern2000` and `lenvatinib/Shumaker2020`, GitHub assignees, and labels such as `curate` and `check`. Do not require one particular label: the guide also calls the label `curation`.
- Local `study.json` records creator and curator attribution. Curators may be strings or `[username, score]` pairs. Those entries are attribution, not necessarily current work assignments or upload authorization.
- GitHub and PK-DB usernames can differ: `matthiaskoenig` versus `mkoenig`. A publicly editable GitHub profile field is not a verified identity binding.
- The package already has `study_folders`, immutable source snapshots, `prepare`, `Client.upload`, endpoint-specific vocabulary caching, structured progress events, and detailed validation reports with file/sheet/row/cell locations. Reuse these rather than parsing terminal output or duplicating scientific validation.
- The hosted frontend's current curation page is principally a vocabulary browser. It does not have local filesystem access. Reuse appropriate UI components but make the new app a separate local entry point.
- `/api/v1/me/studies` currently requires a browser session. A local application using a personal API key cannot assume that endpoint or the account profile endpoint will work unchanged.

## Launch and first run

```bash
# From a pkdb_data checkout:
pkdb curate

# From anywhere:
pkdb curate /path/to/pkdb_data --github-user matthiaskoenig

# Work on one substance or study:
pkdb curate /path/to/pkdb_data/studies/apixaban

# Choose the upload target explicitly:
pkdb curate /path/to/pkdb_data --endpoint https://alpha.pk-db.com

# Local inspection and validation without network requests:
pkdb curate /path/to/pkdb_data --offline
```

The command starts a loopback-only service, opens the default browser, and prints the local URL and shutdown instructions. `--no-browser` supports manually opening the URL; `--port` is optional and the default selects a free port. No Docker, database, Node installation, or frontend build is needed on the curator's machine. Bundle built UI assets in the Python distribution. Support the same Python and operating-system matrix as the package.

Recommend including the small local web runtime in the normal package so that installing `pkdb` makes the advertised command work. An optional `pkdb[curation]` extra is an alternative if dependency size proves significant; never install dependencies implicitly when the command runs.

Resolve the workspace from an explicit argument, then a previously selected workspace, then an enclosing checkout containing `studies/`. If none exists, present a local directory chooser or path field. Accept a repository root, studies root, substance folder, or individual study folder. Show the resolved scope before scanning. The root's name need not literally be `pkdb_data`.

Remember workspace, endpoint, GitHub repository, selected user, filters, and per-study save-action settings in local app configuration outside the source checkout. Do not automatically clone, pull, modify, or commit the repository.

## Identity and assignments

### Recommended default: GitHub assignments

“Assigned studies” lists issues assigned to the selected GitHub user in the configured data repository, initially `matthiaskoenig/pkdb_data`. Provide a searchable user selector populated from the repository’s available GitHub users, showing avatar, GitHub login, and display name when available. Users should not need to know or type an exact handle. Selecting a user updates the assignment list and shows whose queue is being viewed; it does not sign in as that user or change the authenticated PK-DB account.

Populate the selector from users available for repository assignment and retain users appearing on existing issue assignments. Deduplicate by GitHub user ID, exclude bots, and load all pages. If access only permits discovering users from visible issues, label that limited list rather than presenting it as complete. Cache the user list for offline use, show its refresh status, and preserve the last selection. Do not silently switch users when refreshing or when an account disappears from the available list. The optional `--github-user` argument preselects a matching user; an unresolved handle is shown as unresolved rather than creating a fabricated user option.

Show the selected GitHub identity visibly; it is not a PK-DB login. Read public assignments without authentication where available; optional GitHub authentication improves access and request budgets but is separate from the PK-DB API key. The application must not require the GitHub CLI.

Read issues only. Follow pagination, exclude pull requests, support open/closed filters, cache results with a last-refreshed timestamp, and respect conditional requests and server retry guidance. Network or authentication failure leaves cached assignments visible with their age. Local browsing and validation continue independently. Refreshing does not reassign, comment on, or close an issue.

### Match issues to local studies

Match an explicit persisted issue-to-folder mapping first, then an exact normalized `substance/study-folder` title against the selected workspace. A unique study SID can be supported where explicitly present. Do not silently accept fuzzy title or author/year matches. Ambiguous or unmatched assignments stay visible with **Locate folder**, candidate suggestions, and an explanation.

An assignment without a local folder is “Not available locally,” not missing work to hide. It may be outside the selected scope or not yet curated. Show **Open GitHub issue** and **Choose folder**. Creating a study skeleton can follow in a later phase.

Store manual mappings outside study source files using repository identity, issue number, and relative path. Detect moved folders or changed SIDs and request remapping rather than accidentally associating a different study. Multiple issues can relate to one study and one issue can be manually associated with several folders.

### Keep three concepts separate

| Information | Source | What it means |
| --- | --- | --- |
| Assigned work | GitHub issue assignees | Who is expected to work on the issue |
| Contributor attribution | `study.json` creator/curators | Who contributed to the scientific curation |
| Upload permission | Authenticated PK-DB server | Whether this account/key may create or replace the study now |

Provide “All local studies” and “Contributed by…” views in addition to “Assigned studies.” Normalize supported curator forms through the existing source schema. Never turn a selected GitHub user or local attribution into remote privileges. Keep GitHub handle and authenticated PK-DB username visible separately.

## Interface

### Workspace view

Use a compact header for workspace, target server, PK-DB account, connectivity, vocabulary status, and active save-action mode. A folder tree/filter sidebar selects the working scope. The main table contains selection, study name/SID, substance, GitHub issue/assignment, local validation status, last upload result, and local-change indicator. Search supports study name, SID, and relative path. Invalid metadata remains visible as an actionable row.

Default to “Assigned studies” after choosing a GitHub user, otherwise “All local studies.” Folder selection and checkboxes support batch validation/upload. State exactly how many studies are selected and whether hidden filtered rows remain selected. The proposed default is selection limited to visible results unless the user explicitly selects the whole scope.

Keep local validation and remote publication status separate. “Valid” means the recorded inputs passed validation; it does not mean uploaded, permitted, current on the server, or scientifically reviewed.

### Study workspace

Show a study heading with SID, relative folder, reference, assignment links, and attribution. Provide **Validate**, **Upload**, **Open folder**, and **Open study files** actions, plus an **On save: Validate / Upload / Off** selector and a visible pause control. Use three tabs:

1. **Overview:** source files, reference metadata, validation freshness, server publication information when authorized, and last successful upload.
2. **Problems:** grouped diagnostics with filters by severity, file, and issue code; total/discovered counts and completeness.
3. **Activity:** recent local validation/upload jobs, timestamps, target endpoint, versions, source fingerprint, and downloadable JSON reports.

Keep the problems panel usable beside a file preview or metadata panel on wide screens; stack panels on smaller screens. Do not crowd the primary workflow with raw JSON, stack traces, or internal service names.

### Problem presentation

Each problem answers: **what happened, where, what value was found, what was expected, and what the curator can do next**. A representative row is:

> Unknown measurement “AA-induced aggregation” · `outputs.xlsx` · `Tab3!C10` · Choose a supported measurement or request a vocabulary addition.

This is illustrative UI text; real content and suggestions must come from the diagnostic report. Group repeated issues without hiding individual locations. Never invent an exact cell, correction, or scientific equivalence when the backend did not provide one. A truncated or incomplete report must visibly say that more problems may remain.

Provide **Open file**, **Reveal in folder**, **Copy location**, and **Show related locations**. JSON diagnostics show their logical path; spreadsheet diagnostics show the workbook, sheet, and physical row/cell. Offer a JSON report download for reproducibility, not as the primary interface.

## Opening files for external editing

An explicit **Open file** action asks the local companion service to open the file with the operating system’s default application for its type: workbooks in the default spreadsheet program, JSON/text in the default editor, PDFs in the default PDF viewer, and images in the default image viewer. There is no app-specific editor selection, embedded editor, or source-file save action. The curator changes file associations through the operating system if desired.

Keep the diagnostic location visible and provide **Copy location** for the sheet/cell or JSON path; opening a file does not promise navigation to that position. If no default application is available or launching fails, show a useful error and offer **Reveal in folder** and **Copy path**. Opening a file never marks its problems as resolved. Revalidation after an external save determines the new result.

Use opaque registered file IDs, resolve paths beneath the chosen workspace, and recheck containment when opening. Diagnostic file strings are not executable commands or trusted arbitrary paths. Invoke executables with argument arrays, never a shell command assembled from report content. Any in-app preview is read-only and safely rendered; opening the original always uses the operating system’s default application. Do not automatically rewrite study files or add new source fields.

## File watching and actions on save

Observe source files in the selected workspace and associate each change with its study. Immediately mark the affected study’s previous results “Changed since validation.” The default action is **Validate on save**. Curators can choose **Upload on save** or **Off** for individual studies or apply a mode to an explicitly selected set. Show the affected study count when applying a mode to a folder or batch; changing a search filter, GitHub user, or table selection does not silently expand the upload-on-save scope.

| Mode | After a saved source change settles |
| --- | --- |
| Validate on save (default) | Prepare and validate the changed study; refresh problems and status automatically |
| Upload on save | Synchronize vocabulary, prepare and validate the changed study, then upload that exact valid snapshot to the selected server |
| Off | Track freshness and show changed status; wait for a manual action |

Selecting **Upload on save** authorizes subsequent save-triggered uploads for the shown studies, endpoint, and authenticated account. Show that context continuously; do not ask again for every save. The operation uses normal server permissions and may replace existing studies. Remember the setting for that same workspace/endpoint/account context, but do not transfer it to another target or identity. Offline mode cannot upload and visibly suspends that action. Initial scans, browser reconnects, opening files, changing filters, and assignment refreshes never trigger uploads.

### Recognizing a completed save

Handle in-place edits, atomic file replacements, renames, creations, and deletions, including spreadsheet applications that emit several filesystem events for one save. Debounce events per study, initially with a one-second quiet period, and verify that source inputs are stable while taking an immutable snapshot. If files are still changing, temporarily locked, or unreadable, show “Waiting for save to finish” and retry reading after they settle. Once a stable saved file is invalid, report its validation errors normally rather than waiting indefinitely.

Ignore known transient editor/OS files for triggering and scientific input discovery without hiding genuine source inputs. A shared ignore policy must keep watched inputs and preparation consistent; do not let the app validate different scientific contents from the CLI. File removal or a changed `study.json` must produce useful errors or rediscovery, not silently remove a failing study from the queue. Detect duplicate SIDs and changed study identities and suspend automatic uploads for those studies until resolved.

Use a source fingerprint to deduplicate repeated events and avoid validating or uploading unchanged content twice. Watcher overflow or missed-event recovery must reconcile the file inventory. Keep **Refresh files** and a polling fallback for filesystems where native watching is unreliable. Recovery after restart can mark results stale and validate, but must not silently upload accumulated changes made while the application was stopped.

### Scheduling and feedback

Queue validation in background workers and serialize uploads. Keep at most one active operation and one latest pending source revision per study; coalesce rapid saves instead of accumulating an upload for every intermediate edit. Different studies retain independent diagnostic state. Show **Changed**, **Waiting for save**, **Queued**, **Validating**, **Uploading**, and the final result, including whether the action was automatic or manual.

If a newer save arrives during validation, do not promote the older result to current readiness or upload it; validate the latest settled snapshot next. Recheck freshness immediately before transfer. If files change after an upload has begun, finish tracking the in-flight snapshot and clearly mark the newer local revision as pending. After a confirmed outcome, process the newest settled revision. Never imply that an older upload includes newer edits.

Validation errors block upload and update the problems panel. A subsequent external save automatically revalidates and uploads when the new snapshot passes. Warnings remain visible and follow the normal validator’s blocking rules. Vocabulary changes alone may trigger revalidation but do not initiate a new upload without a pending save-triggered operation.

Authentication, permission, compatibility, or connectivity failures visibly pause the affected automatic work and provide **Resume** once resolved. An uncertain write outcome blocks further uploads for that study until reconciled; new saves must not bypass that block. Do not automatically retry ambiguous writes. A pause control stops new automatic jobs and pending uploads; it cannot undo an already-sent request. If changes occur while paused, **Resume** shows and processes the latest pending revision for the selected mode.

The service watches while the local app process is running, even if a browser tab is closed; state this in the UI and terminal. Stopping `pkdb curate` stops watching. Opening the UI again reconnects to existing jobs rather than starting duplicate work.

## Vocabulary and compatibility

Default connected mode automatically checks server capabilities when connecting, before validation/upload, and on explicit refresh. If the endpoint's vocabulary hash differs, fetch the matching snapshot, verify its hash/schema, save it atomically in the endpoint-specific cache, and use it for subsequent preparation. Show a short “Vocabulary updated; revalidating…” message and the resulting status.

Every validation result is tied to a source fingerprint, vocabulary hash, and processing version. A vocabulary update invalidates earlier results for upload readiness. Never reuse a prepared result validated against another endpoint's rules. Keep each running job's snapshot immutable and serialize cache replacement safely.

If rules change after preparation and before upload, refresh and reprepare once when the server explicitly confirms the rejected request did not save data. Show the new diagnostics; never loop indefinitely. Stop and ask for a package upgrade when the processing version is incompatible. Do not run `pip`, change the environment, silently change scientific labels, or overwrite an explicitly pinned vocabulary file.

Offline mode makes no GitHub or PK-DB requests and validates with an explicitly selected/cached/bundled snapshot whose source and age are visible. Call the result “Locally valid” and explain that server compatibility remains unchecked. An unavailable server must not silently turn an intended server-compatible check into a successful offline check.

## Validation and uploads

### Validation

Validation uses shared Python preparation and validation code in background workers so scans and large workbooks do not block the interface. Support local validation without credentials and optional server validation using existing REST endpoints. Distinguish local success from successful server validation. Each operation produces a versioned report using the existing upload-feedback contract.

### Upload

Show the target endpoint and authenticated identity at the upload action. Preview the selected studies and known create/replace status before sending; unknown or inaccessible remote state is labeled as such rather than inferred to be “new.” For a manual single-study upload, the explicit Upload action is sufficient authorization once the target and replacement status are visible; a manual batch uses one review screen, not repeated confirmation dialogs. Upload-on-save uses the standing authorization established by its mode selector and the same validation, permission, and persistence contracts.

Queue uploads sequentially initially. Recheck source freshness and vocabulary compatibility, prepare an immutable snapshot, and call the existing REST upload implementation. Preserve atomic per-study replacement. Display stage progress from structured events, bytes when measurable, per-study outcomes, and a batch summary. Show indeterminate progress while the server processes a request; do not invent percentage completion.

Continue past independent study validation errors by default; allow “Stop on first failure.” Pause the batch on systemic failures such as invalid credentials, incompatible processing versions, or unavailable storage/server. An uncertain write outcome pauses the queue and requires reconciliation. Canceling a batch stops queued work; canceling an active request cannot promise server rollback. Never automatically replay an upload after a timeout, disconnect, or local restart.

Use the existing authorized publication-state endpoint to reconcile a possible save where possible. Compare the canonical publication digest produced by the same preparation logic, not a raw folder hash. Keep source freshness and publication identity as distinct concepts. If evidence cannot establish whether the write completed, retain “Outcome unknown,” show the request ID, and offer server inspection plus an explicit retry.

## Architecture and contracts

Recommend a bundled Vue UI sharing visual/report components with the existing frontend, served by a small local Python application. The local service calls package APIs directly rather than spawning and scraping `pkdb` subprocesses. It must not depend on the `pkdb-server` distribution, PostgreSQL, or backend administration credentials.

The local service owns filesystem access, credentials, vocabulary cache, job execution, reports, and GitHub reads. The browser receives safe profile summaries, registered relative file references, job state, and diagnostics. Use a bounded worker pool for validation and one upload worker. Keep versioned local job records in an application state directory, with configurable retention and explicit history clearing. On restart, interrupted writes become unknown and other interrupted jobs remain resumable only by an explicit user action.

Proposed local API responsibilities, subject to implementation refinement:

| Route family | Responsibility |
| --- | --- |
| `/local/workspace` | Select root, scan, inspect files and freshness, configure watched studies and save actions |
| `/local/assignments` | Read/cache GitHub assignments and maintain local mappings |
| `/local/connection` | Configure endpoint and inspect authenticated capabilities |
| `/local/jobs` | Start validation/upload, inspect results, cancel queued work |
| `/local/events` | Reconnectable job updates with sequence numbers |
| `/local/files/{id}/open` | Explicitly open a registered source file |
| `/local/reports/{id}` | Retrieve a bounded rendered report or download JSON |

These are local application routes, not additions to the hosted scientific API or MCP. Event messages carry job ID, monotonic sequence, study ID, stage, measured counters, and report/result references. Reconnecting clients fetch a current snapshot and then subscribe; event loss must not lose the final result.

A minimal hosted addition may be needed: a read-only, API-key-compatible `/api/v2/curation-context` returning the authenticated PK-DB username, key scopes, account curation capability, and paginated authorized study assignments. Specify and test its visibility before implementation; do not reuse session-only account administration routes or expose other users' private profiles. The server remains authoritative on every upload, even if a prior permission preview allowed it. GitHub integration must not be added to server authorization.

### Local access boundary

Bind only to loopback. Protect local APIs with a randomly generated launch session, validate Host/Origin, require CSRF protection for state-changing calls, and do not enable wildcard CORS. A one-time browser bootstrap can exchange a URL-fragment token for a local session and then remove it from the address bar. Remote websites must not be able to trigger file opens, select arbitrary roots, or upload using locally held credentials.

Use `PKDB_API_KEY` by default. If credentials can be entered through the UI, send them only to the local service, keep them in memory unless the user explicitly enables OS credential storage, and never put them in localStorage, URLs, logs, or reports. GitHub credentials are separate. Workspace changes and endpoint changes cancel or isolate queued jobs; jobs retain the endpoint selected at creation and never silently switch targets.

## Scope and delivery sequence

1. **Local loop:** one-command launch, workspace selection, all-local-study discovery, validation, actionable reports, safe file opening, file watching, and automatic validation on save.
2. **Assigned work:** read-only GitHub assignments, searchable GitHub user selection, exact/manual folder mapping, independent PK-DB identity/permission display, and offline cached assignments. This is part of the first complete #826 release, not an optional afterthought.
3. **Connected curation:** automatic vocabulary synchronization, server validation, manual and save-triggered single/batch uploads, measured progress, cancellation and uncertain-outcome handling.
4. **Packaging and acceptance:** bundled assets, clean-install cross-platform tests, isolated API integration, accessibility/browser tests, and user documentation.

Later candidates: read-only scientific plots/previews, source diffs, GitHub issue updates with explicit user intent, and Git workflow integration. Source editing remains external; embedded editors and automatic scientific corrections are excluded.

## Acceptance scenarios

- A clean supported installation launches the UI with `pkdb curate` without Docker or Node and without altering source studies.
- A curator can search and select from available GitHub users without manually entering a handle, including from the cached list offline. Changing the selected user changes the assignment queue but not authentication or permissions.
- GitHub user `matthiaskoenig` and PK-DB user `mkoenig` can coexist visibly; assignment filtering works without equating those identities or granting permissions.
- Assigned issues with exact local folders appear; unmatched, ambiguous, outside-scope, malformed, and missing-SID studies remain discoverable with useful actions.
- A changed source file or vocabulary invalidates earlier readiness. Validating against server A does not authorize reuse against server B.
- File links open approved local sources in the OS-default applications on Linux, macOS, and Windows. No app-specific editor configuration is required. Missing associations or launch failures show a useful fallback, and diagnostic locations remain available to copy.
- Source editing happens entirely outside the app. Saving in the default editor automatically validates the affected study by default and refreshes its diagnostics without a browser reload.
- Upload-on-save sends a settled, validated snapshot to the displayed endpoint without repeated confirmations. Invalid saves never upload; correcting and saving the file triggers validation and upload again.
- Atomic saves, multiple file events, locked workbooks, rapid consecutive saves, file deletions, and watcher recovery do not cause duplicate uploads, stale success indicators, or silently lost diagnostics.
- A save during validation supersedes the earlier pending result; a save during transfer remains a separate pending revision. An unknown upload outcome blocks later automatic writes for that study.
- Changing the selected GitHub user, endpoint, workspace, or visible filter never broadens existing automatic upload authorization. Restarting or reconnecting never uploads a backlog implicitly.
- Off/pause controls stop new automatic operations; manual actions still work, and source fingerprints consistently determine freshness across CLI and local UI.
- Offline mode performs no network requests, retains cached assignment provenance, and clearly labels server compatibility as unchecked.
- A mixed batch produces separate created/replaced/rejected/canceled/unknown outcomes and preserves all source files. Timeout and restart never automatically duplicate writes.
- Assignment refresh and browser reconnect do not lose selection, job results, or error locations. Large reports remain navigable and show omitted counts.
- Private studies and upload permissions are enforced by the server regardless of issue assignees or local attribution. Local API cross-origin attempts cannot invoke privileged actions.
- Use the real `pkdb_data/studies/apixaban` corpus for acceptance, capturing fresh observed results against an isolated server. Do not freeze historical pass/fail counts as scientific truth or modify sources to make the test pass.

## Confirmed interaction requirements

- All source editing happens outside the app.
- Select the curator from available GitHub users through a searchable selector.
- Open source files using the default applications configured on the computer.
- Observe external file saves and validate automatically by default; allow selecting validation, upload, or no automatic action on save. Upload-on-save always validates first.

## Decisions to confirm

- Adopt GitHub issues as the primary assignment source, with local attribution and remote grants displayed separately? This is the recommendation based on the current curation guide and issue structure.
- Include the UI runtime in the standard package or offer a `curation` extra? Prefer the standard install for the one-command experience, subject to a packaging-size check.
- Should the first release include read-only plot previews, or focus on the validation/edit/upload loop? Prefer the latter while reusing existing hosted study views after upload.
