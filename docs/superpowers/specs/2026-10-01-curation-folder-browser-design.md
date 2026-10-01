---
search:
  exclude: true
---

# Folder browser and recent workspaces for local curation

Date: 2026-10-01. Status: Approved. Issue: [#857](https://github.com/matthiaskoenig/pkdb/issues/857). The [implementation plan](../plans/2026-10-01-curation-folder-browser.md) records the task breakdown and verification.

## 1. Objective

Curators currently type an absolute folder path into the **Choose workspace** dialog of `pkdb curate`. They must be able to choose the workspace by browsing the folder tree instead, and switch between recently used workspaces with one click.

Success criteria:

- A curator opens a `pkdb_data` checkout, a substance folder, or a single study folder without typing a path.
- Folders that are a repository or a study are recognizable while browsing.
- The last workspaces are remembered across restarts and available from the header **Workspace** menu and from the dialog.
- Missing recent folders are shown as unavailable and can be removed from the list.
- Errors such as a missing or unreadable folder are explained in the notice bar instead of a generic failure message.

## 2. Constraints

The browser cannot provide absolute file-system paths to a web page. `showDirectoryPicker()` returns handles without paths, and `<input webkitdirectory>` uploads file contents. Native operating-system dialogs started from Python (tkinter, zenity, AppleScript) are unavailable on headless machines, in many Python builds, and inside containers. The local service already runs on loopback with a session cookie and CSRF token, so it lists folders and the page renders them.

Listing folder names is a read-only operation limited to the authenticated local user, who can already read these folders in a terminal. It exposes no file contents.

## 3. Design

### 3.1 Engine (`pkdb.curation.engine`)

- `WorkspaceError(ValueError)` carries a curator-facing message. `select_workspace` raises it for missing paths, files, a state directory inside the workspace, and an active job.
- `recent_workspaces` is a list of absolute path strings, newest first, at most `RECENT_LIMIT = 10`, without duplicates. It is loaded from and saved to `state.json`. Every successful `select_workspace` call moves the opened folder to the front, including the startup selection.
- `snapshot()` adds `recent_workspaces: [{"path": str, "exists": bool}]`. Existence checks run outside the engine lock.
- `forget_workspace(path)` removes one entry and saves state. Forgetting the current workspace only removes it from the list.
- `list_directories(path=None)` returns `{"path", "parent", "home", "kind", "entries", "truncated"}`:
  - `path` defaults to the current workspace, or to the home folder when the workspace no longer exists. `~` is expanded. Relative paths are rejected.
  - `entries` are child folders `{"name", "path", "kind"}`, sorted case-insensitively. Hidden folders (name starts with `.`) and files are omitted. Symbolic links to folders are listed, as `select_workspace` resolves them.
  - `kind` is `repository` when the folder has a `studies/` subfolder, `study` when it has `study.json`, else `folder`. Unreadable children are `folder`.
  - At most `DIRECTORY_LIMIT = 2000` entries are returned. `truncated` reports whether more exist.
  - `parent` is `None` at the file-system root.
  - Missing, non-folder, and unreadable paths raise `WorkspaceError`.

### 3.2 Transport (`pkdb.curation.server`)

- `POST /local/directories {"path"?: str}` calls `list_directories`. It is a POST so the CSRF token and same-origin checks apply.
- `POST /local/workspace/forget {"path": str}` calls `forget_workspace`.
- `WorkspaceError` maps to HTTP 400 with its message, like `ReferenceError`.

### 3.3 Page (`static/index.html`, `app.js`, `style.css`)

- The **Choose workspace** dialog contains:
  - The existing path field. Pressing Enter or **Go** browses to the typed path.
  - **Up** and **Home** buttons and a clickable breadcrumb for the shown folder.
  - A scrollable folder list. Clicking a folder browses into it. Repository and study folders carry badges.
  - A recent workspace list.
  - **Open this folder**, which opens the shown folder as the workspace.
- The header **Workspace** menu shows the recent list below the current workspace. Clicking an entry switches the workspace directly. The current workspace is marked, unavailable entries are disabled, and every entry has a remove button.
- Switching workspace clears study selection and detail, as today.

## 4. Error handling

- Engine errors with curator-facing text use `WorkspaceError`; the page shows them in the notice bar and the dialog stays open.
- Switching while a job runs reports "Wait for the current job before changing workspace".
- A stale browse response (the user navigated again before it arrived) is discarded.

## 5. Testing

- Engine unit tests: recent order, duplicate handling, limit, persistence across restart, forget, missing entries flagged, directory listing kinds, hidden folders, sorting, truncation, root parent, error messages.
- Transport tests: both endpoints require session and CSRF, pass arguments to the engine, and map `WorkspaceError` to 400 with its message.
- End-to-end: run `pkdb curate` against the real `pkdb_data` checkout in Chrome, browse to a substance folder, open it, switch back through the recent list, and check the layout at desktop and phone width.
- Documentation: `docs/local-curation.md` describes browsing and recent workspaces.

## 6. Out of scope

Native operating-system dialogs, showing files inside the browser, creating or renaming folders, and pinning favorites.
