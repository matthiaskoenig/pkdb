---
search:
  exclude: true
---

# Folder browser and recent workspaces implementation plan

Goal: implement the [design](../specs/2026-10-01-curation-folder-browser-design.md) for issue #857.

Architecture: the local curation engine lists folders and remembers recent workspaces in `state.json`; the loopback transport exposes two CSRF-protected POST endpoints; the static page renders a folder browser dialog and a recent list in the header menu.

## Task 1: engine recent workspaces and errors

Files: `python/src/pkdb/curation/engine.py`, `python/tests/test_curation_engine.py`.

1. Write failing tests: opening folders orders `recent_workspaces` newest first without duplicates, limited to 10; the list survives an engine restart; `snapshot()` flags missing folders; `forget_workspace` removes one entry; `select_workspace` raises `WorkspaceError` with a clear message for missing paths and files.
2. Add `WorkspaceError`, `RECENT_LIMIT`, loading and saving `recent_workspaces`, `forget_workspace`, and the snapshot field.
3. Run `uv run pytest tests/test_curation_engine.py` in `python/`.

## Task 2: engine directory listing

Files: same as Task 1.

1. Write failing tests for `list_directories`: default path, kinds, hidden folders and files omitted, case-insensitive sorting, `truncated`, `parent` at the root, relative and missing paths rejected.
2. Implement `list_directories` with `os.scandir`.
3. Run the engine tests.

## Task 3: transport endpoints

Files: `python/src/pkdb/curation/server.py`, `python/tests/test_curation_server.py`.

1. Write failing tests: `/local/directories` and `/local/workspace/forget` reach the engine with session and CSRF, are rejected without them, and `WorkspaceError` returns 400 with its message.
2. Add the routes and the error mapping.
3. Run the server tests.

## Task 4: page

Files: `python/src/pkdb/curation/static/index.html`, `app.js`, `style.css`.

1. Replace the workspace dialog content with path field, navigation buttons, breadcrumb, folder list, recent list, and actions.
2. Render the recent list in the header Workspace menu.
3. Discard stale browse responses.

## Task 5: documentation and verification

1. Describe folder browsing and recent workspaces in `docs/local-curation.md`.
2. Run ruff, ty, and the full `python/` test suite.
3. Run `pkdb curate` against `pkdb_data` in Chrome; browse, open, switch through recent entries, remove an entry, and check desktop and 390 px layouts.
4. Build the documentation.
