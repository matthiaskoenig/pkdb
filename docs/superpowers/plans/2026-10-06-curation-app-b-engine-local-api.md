---
search:
  exclude: true
---

# Curation app, part B: format 2 engine and local API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pkdb curate` becomes a format 2 only engine that syncs, formats, validates and uploads study folders through the shared pipeline, and serves a local JSON API for study details, tables, sources, images and checked writes of `study.json`, `review.json` and the workbook, ready for the Vue front end of part C.

**Architecture:**
- `python/src/pkdb/curation/engine.py` (1,305 lines) is split by responsibility into mixins that share the engine state: `workspace.py` (workspace, scan, rows, files), `jobs.py` (queue, worker, pipeline, upload outcomes), `connection.py` (settings, heartbeat, vocabulary, identity), `issues.py` (GitHub issues by number) and `studies.py` (study detail, tables, sources, images, writes). `engine.py` keeps the constructor, the state file, the snapshot and `close`.
- Rows are format 2 studies addressed by their identity `<substance>/<name>`; format 1 folders are counted, never touched.
- Jobs run `pkdb.studyformat.pipeline.sync_and_format` under the folder lock, then validate or prepare and upload as today.
- `server.py` gains `/local/studies/...` routes with ETags, 409 and 422 error mapping, a per-response CSP nonce for `index.html`, `/avatars/`, and a 1 MiB body limit.

**Tech Stack:** Python 3.14 standard library HTTP server, Pydantic 2, the part A library (`pkdb.studyformat.{metadata,review_edit,revision,sources,pipeline,sync,validation,load}`, `pkdb.identity`), pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-06-curation-app-design.md`, section 7 (engine and local API) with the error handling of section 9 and the engine and server tests of section 10. Part A (merged in #872) provides the library functions this plan calls.

## Global Constraints

- **Python client:** run from `python/`: `uv run --locked pytest -q`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`. Every commit keeps the suite green. The backend is not touched.
- **Docs:** `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` without warnings.
- **Writing:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines in commits or docs; Python 3.14 syntax is fine.
- **pkdb_data is read-only:** never write `/home/mkoenig/git/pkdb_data`, never scan or search its whole `studies/` directory in tests; tests build workspaces under `tmp_path`.
- **Format 2 only (spec D6):** the engine never syncs, formats, validates or uploads a format 1 folder; it only counts them.
- **Identity:** a study is addressed by `<substance>/<name>` (parent folder name and folder name), in rows, jobs, modes and routes (spec 7.1).
- **Writes:** every write goes through the part A functions (`write_metadata`, the `review_edit` actions, `sync_study`, `add_table`), which validate, write atomically under `pkdb.studyformat.revision.folder_lock` and raise `RevisionConflict` on stale revisions. `folder_lock` is not reentrant: never take it twice on one call path.
- **HTTP errors (spec 7.3, 9):** stale revision `409` with the current document; invalid document `422` with the issues; missing user `403` with `"error": "no_user"`; unknown study or file `404`; ambiguous identity `409`; everything else keeps today's mapping. Body limit 1 MiB.
- **Security (spec 7.5):** `/local/` routes keep the session cookie, CSRF header, Host and Origin checks and JSON-only bodies; file, table, source and image routes serve only files registered in the study, reject symlinks and paths outside the study folder; `index.html` gets a fresh nonce per response with `style-src 'self' 'nonce-…'`; `'unsafe-inline'` never appears.
- **Nonce placeholder:** the literal `__PKDB_NONCE__` in `index.html` is replaced by the response nonce (part C configures Vite's `html.cspNonce` with it).

## Review Focus

1. **A workspace with format 1 folders (pkdb_data today).** Opening it lists no format 1 study, never writes into those folders (no sync, no format, no reference file), and reports their number. Test in Task 2.
2. **Two folders with the same identity** (a copied study in a second subtree). Both rows are shown and marked, uploads and writes for that identity are refused with a clear message, and the routes answer `409`. Test in Task 2 and Task 5.
3. **A write while the watcher job formats the same folder.** The job holds the folder lock while it syncs and formats, so an app write of `study.json` is never overwritten by the formatter; a write with the revision read before the job formatted the file gets `409`. Test in Task 3 and Task 6.
4. **Crafted paths on the read routes.** `..`, `%2F` inside a segment, absolute names, a symlinked image and files that are not registered in the study answer `404` without reading outside the study folder. Test in Task 5.
5. **Polling with ETags.** A repeated `GET` with `If-None-Match` answers `304` without a body; the ETag changes after a write, a job or a file change. Test in Task 5.

---

### Task 1: Split the engine into modules

**Files:**
- Create: `python/src/pkdb/curation/workspace.py`, `python/src/pkdb/curation/jobs.py`, `python/src/pkdb/curation/connection.py`, `python/src/pkdb/curation/issues.py`
- Modify: `python/src/pkdb/curation/engine.py` (keeps `__init__`, `_save`, `snapshot`, `close`, re-exports)
- Modify: `python/tests/test_curation_engine.py` (monkeypatch targets only)

**Interfaces:**
- Produces: `class CurationEngine(WorkspaceMixin, JobsMixin, ConnectionMixin, IssuesMixin)` in `engine.py` with unchanged public methods and behavior. `pkdb.curation.engine` still exports `CurationEngine`, `WorkspaceError`, `folder_kind`, `now`, `fingerprint` (other modules import `WorkspaceError` from it: `server.py`, `cli.py`).
- Mixin modules hold the methods; module-level helpers move with their users:
  - `workspace.py`: `WorkspaceError`, `folder_kind`, `RECENT_LIMIT`, `DIRECTORY_LIMIT`, class `WorkspaceMixin` with `select_workspace`, `forget_workspace`, `_folder`, `list_directories`, `_row`, `scan`, `_watch`, `schedule_changes`, `resolve_file`, `reference_action`.
  - `jobs.py`: `now`, `fingerprint`, class `JobsMixin` with `_enqueue_one`, `enqueue`, `_selected`, `set_mode`, `_cancel_pending`, `set_paused`, `report`, `_worker`, `_server_validate`, `run_job`, `_safe`, `resume`, `cancel_jobs`, `clear_history`, `retry_unknown`. It imports `prepare`, `source_hashes`, `Client`, `bundled_vocabulary` at module level (tests patch them here).
  - `connection.py`: `HEARTBEAT_SECONDS`, `INCOMPATIBLE`, `CONNECTION_FAILED`, `_connection_problem`, class `ConnectionMixin` with `_connection_status`, `_context`, `configure`, `_connect`, `connect`, `_vocabulary`. It imports `Client` at module level.
  - `issues.py`: class `IssuesMixin` with `refresh_assignments`, `map_assignment` and a method `_issue_rows()` holding the issue-to-study matching that `snapshot` does today (`engine.py:224-244`).
- The mixins document at the top of each module which engine attributes they read and write (`self.lock`, `self.studies`, `self.jobs`, `self.queue`, ...); all attributes stay initialized in `CurationEngine.__init__`.

- [ ] **Step 1: Move the code**

Move each method verbatim into its mixin; keep imports minimal per module; no behavior change. `CurationEngine` keeps `__init__` (attribute setup, thread start), `_save`, `snapshot` (calls `self._issue_rows()`) and `close`. Avoid circular imports: mixin modules never import `engine.py`; `engine.py` imports the mixins.

- [ ] **Step 2: Update test patch targets**

In `python/tests/test_curation_engine.py`, replace `monkeypatch.setattr(module, "prepare", ...)` by patching `pkdb.curation.jobs`, and `module.Client` by `pkdb.curation.jobs.Client` and `pkdb.curation.connection.Client` (patch both where a test exercises both paths), `module.bundled_vocabulary` by `pkdb.curation.jobs.bundled_vocabulary`. Keep `from pkdb.curation import engine as module` for `CurationEngine`. Do not change any assertion.

- [ ] **Step 3: Verify**

Run: `cd python && uv run --locked pytest -q tests/test_curation_engine.py tests/test_curation_server.py tests/test_curation_metadata.py tests/test_curation_github.py` then the full suite, ruff and ty.
Expected: PASS with the same test count as before the split (`git stash` the change once to count if needed). `wc -l python/src/pkdb/curation/*.py` shows no module above 600 lines.

- [ ] **Step 4: Commit**

```bash
git add python/src/pkdb/curation python/tests/test_curation_engine.py
git commit -m "Split the curation engine into workspace, jobs, connection and issues modules"
```

---

### Task 2: Format 2 study rows

**Files:**
- Create: `python/src/pkdb/curation/studies.py` (row summary now; detail and writes in Tasks 5 and 6)
- Modify: `python/src/pkdb/curation/workspace.py` (`_row`, `scan`, `schedule_changes`), `python/src/pkdb/curation/jobs.py` (`_enqueue_one`, `enqueue`, `_selected`, `retry_unknown`), `python/src/pkdb/curation/engine.py` (`snapshot`)
- Modify: `python/src/pkdb/curation/metadata.py` (remove the format 1 `study_summary` and `SECTIONS`; keep `profile`, `reference_summary`)
- Move: the fixtures `sf_vocabulary`, `make_study`, `tsv`, `valid_files`, `valid_study` from `python/tests/studyformat/conftest.py` to `python/tests/conftest.py` (unchanged code; remove them from the old file), so curation tests can use them
- Modify: `python/tests/test_curation_engine.py`, `python/tests/test_curation_metadata.py`
- Test: `python/tests/test_curation_rows.py` (new)

**Interfaces:**
- Produces in `pkdb.curation.studies`: `study_summary(folder: Path) -> dict` with keys `title` (from `reference.json` `title` or None), `review_status` (`draft`, `in_review`, `approved` or None when `review.json` is invalid), `open_items` (int), `curators` (list of user names), `creator`, `release` (`{"pkdb_id", "date"}` or None), `issue` (int or None), `provenance` (`kind` and, for `automatic_curation`, `method`), `ai` (bool: provenance kind `automatic_curation`). Files that do not parse give None or empty values, never exceptions.
- Row changes: internal key is the folder path relative to the workspace (`row["path"]`); `row["id"]` is the identity `f"{folder.parent.name}/{folder.name}"`; `row["duplicate"]` is True when another row has the same identity; `row["summary"]` holds `study_summary(folder)`. Removed keys: `sid`, `duplicate_sid`, `identity_changed`, `metadata` (format 1 summary), the `generated_from` marker of files.
- `JobsMixin._selected(ids)` resolves identities; an identity of two rows raises `ValueError("<id> is the identity of two folders: <path>, <path>; rename one")`; jobs and modes store the identity as `study_id`.
- `snapshot()` adds `"format1_folders": int` (folders with a `study.json` that are not format 2).

- [ ] **Step 1: Write the failing tests**

Create `python/tests/test_curation_rows.py`:

```python
import json

import pytest

from pkdb.curation import engine as module
from pkdb.studyformat.jsonio import dump_json


@pytest.fixture
def workspace(tmp_path, make_study, valid_files):
    folder = make_study(valid_files)  # tmp_path/caffeine/Example
    legacy = tmp_path / "caffeine" / "Legacy1990"
    legacy.mkdir()
    (legacy / "study.json").write_text(json.dumps({"sid": "Legacy1990", "name": "Legacy1990"}))
    (legacy / "Legacy1990.xlsx").write_bytes(b"not a workbook")
    engine = module.CurationEngine(tmp_path, state_dir=tmp_path.parent / "state", offline=True, start=False)
    yield engine, folder, legacy
    engine.close()


def test_rows_are_format_2_studies_by_identity(workspace):
    engine, folder, legacy = workspace
    snapshot = engine.snapshot()
    assert [row["id"] for row in snapshot["studies"]] == ["caffeine/Example"]
    assert snapshot["format1_folders"] == 1
    row = snapshot["studies"][0]
    assert row["path"] == "caffeine/Example" and row["duplicate"] is False
    assert row["summary"]["review_status"] == "draft"
    assert row["summary"]["curators"] == ["curator"]
    assert row["summary"]["title"] == "Example study"
    assert "sid" not in row and "metadata" not in row


def test_format_1_folders_are_never_touched(workspace):
    engine, folder, legacy = workspace
    before = {path.name: path.read_bytes() for path in legacy.iterdir()}
    engine.scan()
    for item in engine.studies.values():
        item["_changed_at"] -= 2
    engine.schedule_changes()
    assert all(job["study_id"] != "caffeine/Legacy1990" for job in engine.jobs)
    assert {path.name: path.read_bytes() for path in legacy.iterdir()} == before


def test_duplicate_identity_is_marked_and_refused(workspace, tmp_path, valid_files):
    engine, folder, legacy = workspace
    copy = tmp_path / "copies" / "caffeine" / "Example"
    copy.mkdir(parents=True)
    for file, content in valid_files.items():
        (copy / file).write_bytes(content if isinstance(content, bytes) else content.encode())
    engine.scan()
    rows = [row for row in engine.snapshot()["studies"] if row["id"] == "caffeine/Example"]
    assert len(rows) == 2 and all(row["duplicate"] for row in rows)
    with pytest.raises(ValueError, match="identity of two folders"):
        engine.enqueue(["caffeine/Example"], "validate")


def test_summary_of_unreadable_files(workspace):
    engine, folder, legacy = workspace
    (folder / "review.json").write_text("{broken")
    (folder / "study.json").write_text(dump_json({"format": 2}))
    engine.scan()
    summary = engine.snapshot()["studies"][0]["summary"]
    assert summary["review_status"] is None and summary["curators"] == []
```

`make_study` creates `tmp_path/<substance>/<name>`; the engine's state directory must lie outside the workspace (`select_workspace` refuses otherwise), hence `tmp_path.parent / "state"`. If that directory is shared between parallel tests, use `tmp_path_factory.mktemp("state")` instead.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/test_curation_rows.py`
Expected: FAIL (fixtures not found until moved, then rows with hashed ids and format 1 rows).

- [ ] **Step 3: Implement**

- Move the fixtures to `python/tests/conftest.py`; the studyformat tests keep using them unchanged.
- `studies.study_summary(folder)`: read `study.json` with `load_json` and validate with `StudyMetadata`; on failure read the raw dict leniently for `creator`, `curators` (user names), `issue`, `release`; read `review.json` with `Review` (None status on failure); read `reference.json` `title`. Never raise.
- `workspace.scan`: a folder with `study.json` is a row only when `pkdb.studyformat.is_v2_folder(folder)`; count the others in `self.format1_folders` (an int attribute initialized in `__init__`). The row dict key is the relative path; `_row` sets `id` to the identity. `scan` sets `row["summary"] = study_summary(folder)` when the signature changes and recomputes `duplicate` for all rows after the loop (replacing the `duplicate_sid` counter). Remove the `sid` identity-change logic and the hidden-TSV `generated_from` marker.
- `schedule_changes`, `_enqueue_one`, `enqueue`, `retry_unknown`: replace `duplicate_sid` checks by `duplicate` with the message "Rename one of the folders with identity <id> before uploading"; `schedule_changes` never queues a duplicate.
- `_selected(ids)`: map each identity to its rows; unknown identity raises `ValueError("Study is not in this workspace")`; two rows raise the message in the interfaces.
- Modes and jobs: `self.modes[context][identity]`; `row["mode"]` reads by identity. Jobs from a state file written by the format 1 app keep their old hashed `study_id` and simply match no row.
- `metadata.py`: delete `SECTIONS`, `_people`, `_text`, `study_summary`, keep `profile`, `_curators`, `_author`, `reference_summary` (and update `test_curation_metadata.py` accordingly).
- Rewrite the `workspace` fixture of `test_curation_engine.py` to a format 2 study built with `make_study(valid_files)` (state directory outside the workspace) and adapt the tests that relied on format 1 behavior: delete `test_validation_exports_workbook_tables_and_marks_them_generated` and the format 1 parts of `test_scan_summarizes_study_and_reference_metadata` (replace with a summary assertion), change ids from hashes to `"caffeine/Example"`.

- [ ] **Step 4: Run the tests**

Run: `cd python && uv run --locked pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/curation python/tests
git commit -m "List format 2 studies by identity in the curation engine and leave format 1 folders untouched"
```

---

### Task 3: Format 2 job pipeline and sync status

**Files:**
- Modify: `python/src/pkdb/curation/jobs.py` (`run_job`), `python/src/pkdb/curation/workspace.py` (`scan`: sync status)
- Test: `python/tests/test_curation_pipeline.py` (new)

**Interfaces:**
- Consumes: `pkdb.studyformat.pipeline.sync_and_format(folder, vocabulary, *, max_rows=None, on_stage=None) -> PipelineResult(syncs, formatted, stopped)` with `stopped in {"sync", "saved_again", "format", None}`, `PipelineResult.ok`, `.changes`, `.issues`; `pkdb.studyformat.revision.folder_lock`; `pkdb.studyformat.sync.workbook_check(folder, vocabulary) -> dict | None` (`action`, `changes`, `conflicts`, `ok`).
- Produces: job status `"conflict"` (a sync conflict or an unresolved save during the sync stopped the job before validation); the job report holds `"conflicts"` (the `SyncConflict` data as in `tables_cli._entry`) and `"pipeline_issues"`; `row["sync"] = {"status": "no_workbook"|"in_sync"|"changed"|"conflict"|"workbook_open"|"syncing"|"unknown", "changes": int, "conflicts": int}`; `row["counts"] = {"errors": int, "warnings": int}` from the last report.
- The engine vocabulary for local work: `self._local_vocabulary()` in `JobsMixin` returns the cached vocabulary of the endpoint or the bundled one (the logic `run_job` has today for offline jobs), used by the pipeline, `workbook_check` and later by the write routes.

- [ ] **Step 1: Write the failing tests**

```python
import json

import openpyxl
import pytest

from pkdb.curation import engine as module
from pkdb.curation import jobs
from pkdb.studyformat.sync import sync_study
from pkdb.studyformat.workbook.base import workbook_path


@pytest.fixture
def workspace(tmp_path_factory, make_study, valid_files):
    folder = make_study(valid_files)
    engine = module.CurationEngine(folder.parent.parent, state_dir=tmp_path_factory.mktemp("state"), offline=True, start=False)
    yield engine, folder
    engine.close()


def run_next(engine):
    identifier = next(iter(engine.queue))
    job = engine.queue.pop(identifier)
    engine.active = identifier
    job["status"] = "running"
    try:
        engine.run_job(job)
    finally:
        engine.active = None
    return job


def settle(engine):
    for item in engine.studies.values():
        item["_changed_at"] -= 2
    engine.schedule_changes()


def test_validation_formats_first(workspace):
    engine, folder = workspace
    table = folder / "timecourses_Fig1.tsv"
    table.write_text(table.read_text() + "\n\n")  # not canonical
    settle(engine)
    job = run_next(engine)
    assert job["status"] == "succeeded", job["message"]
    assert not table.read_text().endswith("\n\n")
    row = engine.snapshot()["studies"][0]
    assert row["counts"] == {"errors": 0, "warnings": 0}
    assert row["sync"]["status"] == "no_workbook"


def test_conflict_stops_before_validation(workspace, sf_vocabulary, monkeypatch):
    engine, folder = workspace
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    assert sync_study(folder, sf_vocabulary).ok
    path = workbook_path(folder)
    book = openpyxl.load_workbook(path)
    sheet = book["timecourses_Fig1"]
    header = [cell.value for cell in sheet[1]]
    sheet.cell(3, header.index("mean") + 1).value = 5
    book.save(path)
    table = folder / "timecourses_Fig1.tsv"
    lines = table.read_text().splitlines()
    cells = lines[2].split("\t")
    cells[header.index("mean")] = "7"
    lines[2] = "\t".join(cells)
    table.write_text("\n".join(lines) + "\n")
    engine.scan()
    assert engine.snapshot()["studies"][0]["sync"]["status"] == "conflict"
    settle(engine)
    called = []
    monkeypatch.setattr(jobs, "prepare", lambda *a, **k: called.append(1))
    job = run_next(engine)
    assert job["status"] == "conflict" and not called
    report = engine.report(job["report_id"])
    assert report["conflicts"] and report["conflicts"][0]["file"] == "timecourses_Fig1.tsv"


def test_pipeline_runs_under_the_folder_lock(workspace, monkeypatch):
    engine, folder = workspace
    held = []

    class Lock:
        def __init__(self, path):
            held.append(("enter", path))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            held.append(("exit", None))

    real = jobs.sync_and_format

    def pipeline(path, vocabulary, **kwargs):
        assert held and held[-1][0] == "enter"
        return real(path, vocabulary, **kwargs)

    monkeypatch.setattr(jobs, "folder_lock", Lock)
    monkeypatch.setattr(jobs, "sync_and_format", pipeline)
    settle(engine)
    assert run_next(engine)["status"] == "succeeded"
    assert held[0] == ("enter", folder)
```

The conflict test edits the third line (the second data row) of the table and the same row in the workbook to different values; reuse the exact cell and column approach of `python/tests/studyformat/test_pipeline.py` if it differs.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/test_curation_pipeline.py`
Expected: FAIL (no `sync_and_format` in `jobs`, no `sync` and `counts` in rows).

- [ ] **Step 3: Implement**

In `run_job`, replace the format 1 step

```python
            tables = sync_tsvs(row["_folder"])
```

by the pipeline under the folder lock, and drop the `WorkbookError` import and handling:

```python
            vocabulary = self._local_vocabulary()
            with folder_lock(row["_folder"]):
                pipeline = sync_and_format(row["_folder"], vocabulary)
            if not pipeline.ok and pipeline.stopped in {"sync", "saved_again"}:
                outcome["conflicts"] = conflict_entries(pipeline)
                outcome["pipeline_issues"] = [i.model_dump(mode="json") for i in pipeline.issues]
                job.update(status="conflict", message="Resolve the conflict between the workbook and the tables")
                row.update(status="conflict", stale=True)
                return  # the finally block writes the report
            if not pipeline.ok:
                # stopped == "format": its issues are reported like validation problems.
                raise StudyValidationError(ValidationReport(issues=list(pipeline.issues)))
            tables = describe(pipeline.changes)
```

Details:
- `conflict_entries(pipeline)` lives in `jobs.py` and turns the `SyncConflict`s of the last sync into the dicts `tables_cli._entry` produces (`file`, `sheet`, `workbook_rows`, `table_lines`, `base_lines`, `kept`); move that dict building into a shared helper `pkdb.studyformat.sync.conflict_data(conflict) -> dict` and use it in both places.
- A format stop reports its issues like a validation failure (job `failed`, row `invalid`, issues in the report): the `StudyValidationError(ValidationReport(...))` raised above goes through the existing `except StudyValidationError` branch and the same `finally` path.
- `tables` (the files the pipeline wrote) replaces the old `sync_tsvs` result in `outcome["tables_updated"]`; the rescan logic after a repair stays (the pipeline changes the fingerprint).
- The vocabulary used for validation and upload stays as today (`self._vocabulary(client)` online); `_local_vocabulary()` is the offline/cached choice of today's code, reused for the pipeline.
- `scan`: when the signature changes, set `row["sync"]` from `workbook_check(folder, self._local_vocabulary())` (None gives `no_workbook`; `conflicts > 0` gives `conflict`; `action == "close_to_update"` gives `workbook_open`; `ok is None` gives `unknown`; changes give `changed`; else `in_sync`); catch `OSError` and `ValueError` as `unknown`. While a job of the row is in the sync stage, `row["sync"]["status"]` is `syncing` (set in `run_job` around the pipeline call).
- The `finally` block of `run_job` sets `row["counts"]` by counting the report issues by severity (use `error_count`/`warning_count` of the report when present).

- [ ] **Step 4: Run the tests**

Run: `cd python && uv run --locked pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/curation python/src/pkdb/studyformat/sync.py python/src/pkdb/tables_cli.py python/tests/test_curation_pipeline.py
git commit -m "Sync and format format 2 studies before validating them in the curation engine"
```

---

### Task 4: GitHub issues by number

**Files:**
- Modify: `python/src/pkdb/curation/issues.py`, `python/src/pkdb/curation/engine.py` (`snapshot`, `_save`, `__init__`), `python/src/pkdb/curation/server.py` (remove `/local/assignments/map`)
- Test: `python/tests/test_curation_github.py`, `python/tests/test_curation_server.py`, `python/tests/test_curation_engine.py` (remove `test_assignment_mapping_overrides_ambiguous_title`)

**Interfaces:**
- Produces: `row["issue"] = {"number", "state", "labels", "assignees", "url"}` from the cached GitHub issue whose number is `row["summary"]["issue"]`, or `{"number": n, "state": None, ...}` when the issue is not in the cache, or None without an issue number. The snapshot's `github` block keeps `users`, `status`, `limited`, `refreshed_at`, `error`, `user`, `repository`, `issues` (without `study_ids`). `self.mappings`, `map_assignment` and the route are removed; old state files with `mappings` load without error.

- [ ] **Step 1: Write the failing tests**

Add to `python/tests/test_curation_rows.py` (Task 2 fixture):

```python
def test_issue_comes_from_the_number_in_study_json(workspace):
    engine, folder, legacy = workspace
    metadata = json.loads((folder / "study.json").read_text())
    (folder / "study.json").write_text(dump_json({**metadata, "issue": 2158}))
    engine.github.data = {
        **engine.github.data,
        "issues": [
            {
                "number": 2158,
                "title": "Curate caffeine/Example",
                "html_url": "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
                "state": "open",
                "assignees": ["mkoenig"],
                "labels": ["caffeine", "check"],
            }
        ],
    }
    engine.scan()
    assert engine.snapshot()["studies"][0]["issue"] == {
        "number": 2158,
        "state": "open",
        "labels": ["caffeine", "check"],
        "assignees": ["mkoenig"],
        "url": "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
    }
    engine.github.data = {**engine.github.data, "issues": []}
    assert engine.snapshot()["studies"][0]["issue"]["state"] is None
```

In `test_curation_server.py`, `POST /local/assignments/map` answers 404.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/test_curation_github.py tests/test_curation_server.py`
Expected: FAIL.

- [ ] **Step 3: Implement**

`IssuesMixin._issue_for(number) -> dict | None` looks the number up in `self.github.data["issues"]`; `snapshot` fills `row["issue"]` per row; delete the title matching, `self.mappings` (keep tolerating the key in old state files), `map_assignment`, and the `/local/assignments/map` route.

- [ ] **Step 4: Run the tests**

Run: `cd python && uv run --locked pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/curation python/tests
git commit -m "Link studies to their GitHub issue by the number in study.json"
```

---

### Task 5: Read API for study pages

**Files:**
- Modify: `python/src/pkdb/curation/studies.py` (class `StudiesMixin`), `python/src/pkdb/curation/engine.py` (add the mixin), `python/src/pkdb/curation/server.py` (routes, ETags)
- Test: `python/tests/test_curation_api.py` (new; a real loopback server over a real engine and a format 2 workspace)

**Interfaces:**
- Consumes: `pkdb.studyformat.load.load_study`, `pkdb.studyformat.sources.study_sources/source_view`, `pkdb.studyformat.metadata.read_metadata` (`MetadataError` with `issues`), `pkdb.studyformat.review_edit.read_review` (`ReviewError` with `issues`), `pkdb.studyformat.raw.raw_grid`.
- Produces in `StudiesMixin`:
  - `study_folder(identity: str) -> Path` (raises `LookupError` for an unknown identity and `AmbiguousStudy(ValueError)` for a duplicate)
  - `study_version(identity) -> str`: a cheap key of row fingerprint, status, mode, report id, sync status and the ids and statuses of the study's jobs; the detail ETag is derived from it
  - `study_detail(identity) -> dict` with keys `id`, `path`, `status`, `mode`, `sync`, `counts`, `summary`, `issue`, `metadata` (`{"revision", "value", "issues"}`: `value` is the `study.json` model dump or None when invalid, `issues` the problems), `review` (same shape for `review.json`), `problems` (last report issues), `acknowledged` (items with `acknowledges` that are not dismissed: `id`, `code`, `target`, `text`, `author`, `resolved_by`, `resolved`), `sources` (`study_sources` as dicts), `files` (registered file names), `jobs` (the study's jobs, newest first), `report_id`
  - `study_table(identity, file) -> dict`: a data table `{"file", "kind": "table", "header": [...], "rows": [{"line", "cells"}]}`, a raw table `{"file", "kind": "raw", "rows": [{"line", "cells"}]}`; `LookupError` for any other name
  - `study_source(identity, source) -> dict`: `dataclasses.asdict(source_view(...))` plus `image_url` (`/local/studies/<substance>/<name>/files/<image>` or None)
  - `study_image(identity, file) -> tuple[bytes, str]`: content and media type for registered `png`, `jpg`, `jpeg`, `webp` files only
- Server routes (GET, cookie required): `/local/studies/{substance}/{name}`, `.../tables/{file}`, `.../sources/{source}`, `.../files/{file}`. Every JSON GET under `/local/` sends `ETag`; `If-None-Match` equal to it gives `304` with the ETag and no body. `/local/state` hashes its JSON; the detail uses `study_version`; tables and sources hash their JSON.
- Path parsing: split the URL path on `/` before percent-decoding each segment; reject empty segments, `.` and `..`, and decoded segments containing `/`, `\` or NUL (404).

- [ ] **Step 1: Write the failing tests**

Create `python/tests/test_curation_api.py` with a fixture that builds a format 2 study (`make_study(valid_files)`, plus `Example_Tab2.tsv` raw table, a real PNG `Example_Fig1.png` and `Example_Fig1.wpd.json` from `python/tests/studyformat/digitize_fixtures.py`; import it by adding that directory to `sys.path` in the test module or move the helpers to `python/tests/digitize_fixtures.py` and update their two importers), a real `CurationEngine(..., offline=True, start=False)`, a `create_server(engine)` thread and the `request`/`authenticate` helpers of `test_curation_server.py` (move those two helpers into `python/tests/curation_http.py` and import them in both test modules).

Tests (each asserting status codes and key content):

```python
def test_study_detail(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, data = request(server, "GET", "/local/studies/caffeine/Example", headers=headers)
    assert status == 200
    detail = json.loads(data)
    assert detail["id"] == "caffeine/Example"
    assert detail["metadata"]["value"]["licence"] == "open" and detail["metadata"]["revision"]
    assert detail["review"]["value"]["status"] == "draft"
    assert {s["source"] for s in detail["sources"]} >= {"Fig1", "Tab2"}
    etag = response_headers["ETag"]
    again = request(server, "GET", "/local/studies/caffeine/Example", headers={**headers, "If-None-Match": etag})
    assert again[0] == 304 and again[2] == b""
    (folder / "study.json").write_text((folder / "study.json").read_text().replace('"open"', '"closed"'))
    engine.scan()
    changed = request(server, "GET", "/local/studies/caffeine/Example", headers={**headers, "If-None-Match": etag})
    assert changed[0] == 200 and changed[1]["ETag"] != etag


def test_tables_sources_and_images(api):
    server, engine, folder = api
    headers = authenticate(server)
    table = json.loads(request(server, "GET", "/local/studies/caffeine/Example/tables/timecourses_Fig1.tsv", headers=headers)[2])
    assert table["kind"] == "table" and table["rows"][0]["line"] == 2
    raw = json.loads(request(server, "GET", "/local/studies/caffeine/Example/tables/Example_Tab2.tsv", headers=headers)[2])
    assert raw["kind"] == "raw"
    source = json.loads(request(server, "GET", "/local/studies/caffeine/Example/sources/Fig1", headers=headers)[2])
    assert source["image_url"] == "/local/studies/caffeine/Example/files/Example_Fig1.png"
    assert source["overlay"]
    status, image_headers, data = request(server, "GET", source["image_url"], headers=headers)
    assert status == 200 and image_headers["Content-Type"] == "image/png" and data.startswith(b"\x89PNG")


@pytest.mark.parametrize(
    "path",
    [
        "/local/studies/caffeine/Example/files/..%2Fstudy.json",
        "/local/studies/caffeine/Example/files/study.json",
        "/local/studies/caffeine/Example/files/%2Fetc%2Fpasswd",
        "/local/studies/caffeine/../Example",
        "/local/studies/caffeine/Example/tables/Example.pdf",
        "/local/studies/caffeine/Missing",
        "/local/studies/caffeine/Example/sources/Fig9",
    ],
)
def test_crafted_paths_are_not_found(api, path):
    server, engine, folder = api
    assert request(server, "GET", path, headers=authenticate(server))[0] == 404


def test_symlinked_image_is_refused(api, tmp_path):
    server, engine, folder = api
    outside = tmp_path / "outside.png"
    outside.write_bytes((folder / "Example_Fig1.png").read_bytes())
    (folder / "Example_Fig3.png").symlink_to(outside)
    engine.scan()
    assert request(server, "GET", "/local/studies/caffeine/Example/files/Example_Fig3.png", headers=authenticate(server))[0] == 404


def test_duplicate_identity_answers_409(api, valid_files):
    server, engine, folder = api
    copy = engine.root / "copies" / "caffeine" / "Example"
    copy.mkdir(parents=True)
    for file, content in valid_files.items():
        (copy / file).write_bytes(content if isinstance(content, bytes) else content.encode())
    engine.scan()
    status, _, data = request(server, "GET", "/local/studies/caffeine/Example", headers=authenticate(server))
    assert status == 409 and "identity of two folders" in json.loads(data)["error"]


def test_state_etag(api):
    server, engine, folder = api
    headers = authenticate(server)
    status, response_headers, _ = request(server, "GET", "/local/state", headers=headers)
    assert request(server, "GET", "/local/state", headers={**headers, "If-None-Match": response_headers["ETag"]})[0] == 304
```

`authenticate` consumes the bootstrap token once per server; call it once per test (a fresh server per test from the fixture) or keep the headers on the fixture. A symlink inside the study is a layout error, so the file is not registered and the route answers 404 either way; the test pins that the route never follows it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/test_curation_api.py`
Expected: FAIL (404 for every new route).

- [ ] **Step 3: Implement**

- `StudiesMixin` reads under `self.lock` only what it needs from the row (folder, fingerprint, report id, problems), then loads files outside the lock.
- `study_image` checks: the file name is in `load_study(folder).layout.files` (registered, no symlink, top level only), the suffix is one of `.png`, `.jpg`, `.jpeg`, `.webp`, `(folder / name).resolve()` is inside `folder.resolve()`, then reads the bytes.
- In `server.do_GET`, route `/local/studies/` paths with the parser described in the interfaces; map `LookupError` to 404, `AmbiguousStudy` to 409 (`{"error": "<message>"}`), `ValueError` from parsing to 404. Add `_reply(..., etag=...)` support and the 304 path. Image responses carry their media type and no ETag.

- [ ] **Step 4: Run the tests**

Run: `cd python && uv run --locked pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb/curation python/tests
git commit -m "Serve study details, tables, sources and images from the local curation API"
```

---

### Task 6: Write API and author identity

**Files:**
- Modify: `python/src/pkdb/curation/studies.py` (writes), `python/src/pkdb/curation/connection.py` (`author`), `python/src/pkdb/curation/server.py` (routes, error mapping, `MAX_BODY`), `python/src/pkdb/studyformat/review_edit.py` (`matching_warnings`), `python/src/pkdb/study_cli.py` (use it)
- Test: `python/tests/test_curation_api.py`, `python/tests/studyformat/test_review_edit.py`

**Interfaces:**
- Consumes: `write_metadata(folder, metadata, revision, *, resolver=None, refresh_reference=False) -> MetadataWrite(revision, reference, reference_error)`; `review_edit.add_item/reply/resolve/dismiss/reopen/set_status/acknowledge` (all take `folder, author, ...` and a `revision`, return the new revision or `(item, revision)`); `RevisionConflict(file, expected, current, content)`; `MetadataError.issues`, `ReviewError.issues`, `ApprovalRefused`; `pkdb.identity.Author`, `IdentityError`; `sync_study(folder, vocabulary, *, keep=None)`, `add_table(folder, vocabulary, table)`; `pkdb.curation.launch.open_path`.
- Produces:
  - `ConnectionMixin.author(agent: str | None = None) -> Author`: the authenticated account (`self.account`) when an API key is configured and the last connection check succeeded, otherwise the configured user (`self.user`); `IdentityError("Set your PK-DB user in Connection settings")` when neither exists.
  - `review_edit.matching_warnings(issues, code, file, line=None, column=None) -> list[ValidationIssue]` and `review_edit.warning_locations(issues) -> set[tuple[int | None, str | None]]`, moved out of `study_cli._review_acknowledge` (the CLI uses them).
  - `StudiesMixin.write_metadata(identity, revision, metadata: dict) -> dict` (`{"revision", "reference", "reference_error"}`), `review_action(identity, payload: dict) -> dict` (`{"revision"}` plus `"item"` for add and acknowledge), `tables_action(identity, payload: dict) -> dict` (`open`, `sync`, `resolve` with `keep`, `add` with `table` or `raw`; returns the sync or add result like `tables_cli._entry`). Each write rescans the study afterwards.
  - Routes (POST, JSON, CSRF): `/local/studies/metadata` `{study, revision, metadata}`; `/local/studies/review` `{study, revision, action, ...}` with `add` (`kind`, `text`, optional `target` `{file, rows, column}`, `acknowledges`), `reply` (`item`, `text`), `resolve`/`dismiss`/`reopen` (`item`, optional `text`), `status` (`status`), `acknowledge` (`code`, `file`, optional `line`, `column`, and `text`); `/local/studies/tables` `{study, action, ...}`.
  - Error mapping in `do_POST`: `RevisionConflict` 409 `{"error", "file", "revision": current, "content"}`; `MetadataError`, `ReviewError` (including `ApprovalRefused`, with `"code": "approval_refused"`) 422 `{"error", "issues"}`; `IdentityError` 403 `{"error": "no_user", "message"}`; `AmbiguousStudy` 409. `MAX_BODY = 1024 * 1024`.

- [ ] **Step 1: Write the failing tests**

Add to `test_curation_api.py` (with `engine.user = "curator"` set in the fixture):

```python
def test_metadata_write_and_conflict(api):
    server, engine, folder = api
    headers = authenticate(server)
    detail = json.loads(request(server, "GET", "/local/studies/caffeine/Example", headers=headers)[2])
    metadata = {**detail["metadata"]["value"], "licence": "closed"}
    body = {"study": "caffeine/Example", "revision": detail["metadata"]["revision"], "metadata": metadata}
    status, _, data = request(server, "POST", "/local/studies/metadata", body, headers)
    assert status == 200 and json.loads((folder / "study.json").read_text())["licence"] == "closed"
    stale = request(server, "POST", "/local/studies/metadata", body, headers)
    assert stale[0] == 409 and json.loads(stale[2])["file"] == "study.json"
    invalid = {**body, "revision": json.loads(data)["revision"], "metadata": {**metadata, "licence": "maybe"}}
    rejected = request(server, "POST", "/local/studies/metadata", invalid, headers)
    assert rejected[0] == 422 and json.loads(rejected[2])["issues"]


def test_review_actions_and_approval_refusal(api):
    server, engine, folder = api
    headers = authenticate(server)
    revision = json.loads(request(server, "GET", "/local/studies/caffeine/Example", headers=headers)[2])["review"]["revision"]
    status, _, data = request(server, "POST", "/local/studies/review", {"study": "caffeine/Example", "revision": revision, "action": "add", "kind": "question", "text": "Why?"}, headers)
    assert status == 200
    item, revision = json.loads(data)["item"], json.loads(data)["revision"]
    refused = request(server, "POST", "/local/studies/review", {"study": "caffeine/Example", "revision": revision, "action": "status", "status": "approved"}, headers)
    assert refused[0] == 422 and json.loads(refused[2])["code"] == "approval_refused"
    done = request(server, "POST", "/local/studies/review", {"study": "caffeine/Example", "revision": revision, "action": "resolve", "item": item["id"]}, headers)
    assert done[0] == 200


def test_writes_need_a_user(api):
    server, engine, folder = api
    engine.user = ""
    headers = authenticate(server)
    response = request(server, "POST", "/local/studies/review", {"study": "caffeine/Example", "revision": None, "action": "add", "kind": "question", "text": "?"}, headers)
    assert response[0] == 403 and json.loads(response[2])["error"] == "no_user"


def test_write_after_the_job_formatted_the_file_conflicts(api):
    server, engine, folder = api
    headers = authenticate(server)
    revision = json.loads(request(server, "GET", "/local/studies/caffeine/Example", headers=headers)[2])["metadata"]["revision"]
    (folder / "study.json").write_text((folder / "study.json").read_text() + "\n")  # an external edit
    from pkdb.studyformat.formatter import format_folder
    format_folder(folder)  # what the watcher job does
    response = request(server, "POST", "/local/studies/metadata", {"study": "caffeine/Example", "revision": revision, "metadata": {"format": 2, "creator": "curator", "licence": "open", "access": "private"}}, headers)
    assert response[0] == 409


def test_tables_open_uses_the_opener(api, monkeypatch):
    server, engine, folder = api
    opened = []
    monkeypatch.setattr("pkdb.curation.studies.open_path", lambda path, **kw: opened.append(path))
    headers = authenticate(server)
    status, _, data = request(server, "POST", "/local/studies/tables", {"study": "caffeine/Example", "action": "open"}, headers)
    assert status == 200 and opened == [folder / "Example.xlsx"]
```

Add to `test_review_edit.py` a unit test of `matching_warnings` and `warning_locations` (code/file/line/column filters, one location for two file-level warnings). The existing CLI acknowledge tests must keep passing.

If the external edit plus format does not change the revision (the formatter restores the same bytes), make the external edit a real change instead (for example a new description) so the test pins "revision read before the job wrote".

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/test_curation_api.py tests/studyformat/test_review_edit.py`
Expected: FAIL.

- [ ] **Step 3: Implement**

- `author()` in `ConnectionMixin`; `StudiesMixin` calls it in every review write (metadata writes need no author field, but refuse with `IdentityError` without a user, as spec 7.4 says writes are refused without a user).
- `write_metadata`: validate the payload with `StudyMetadata.model_validate` and map `ValidationError` to `MetadataError(validation_issues(error, "study.json", "invalid_study_json"))`; resolver `ReferenceResolver(offline=self.offline)`.
- `review_action`: dispatch on `action`; `status approved` passes `vocabulary=self._local_vocabulary()`; `acknowledge` validates the folder with `validate_folder(folder, self._local_vocabulary())`, selects with `matching_warnings`, and requires exactly one location (otherwise `ReviewError` naming the locations, as the CLI does).
- `tables_action`: `open` runs `sync_study` under `folder_lock` and opens the workbook with `open_path` (imported into `studies.py` at module level so tests can patch it); `sync`/`resolve` run `sync_study(folder, vocabulary, keep=...)` under `folder_lock`; `add` calls `add_table` with `table` or `f"{folder.name}_{raw}"`. Return `ok`, `workbook_action`, `changes`, `conflicts` (via `conflict_data`), `issues`.
- `server.do_POST`: add the routes and the error mapping before the generic handlers; raise `MAX_BODY`, and update `test_payload_limits_paths_and_errors` in `test_curation_server.py`: a body of 512 KiB is accepted (reaches the action), one above 1 MiB answers 413.

- [ ] **Step 4: Run the tests**

Run: `cd python && uv run --locked pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/src/pkdb python/tests
git commit -m "Write study.json, review.json and the workbook through the local curation API"
```

---

### Task 7: CSP nonce, avatars and a recording opener

**Files:**
- Modify: `python/src/pkdb/curation/server.py` (index nonce, `/avatars/`), `python/src/pkdb/curation/launch.py` (`PKDB_OPEN_COMMAND`), `scripts/update_client_curators.py` (`TARGET_AVATARS`), `python/src/pkdb/curation/static/app.js` (avatar URLs, if it references `static/avatars` or `avatars/`)
- Move: `python/src/pkdb/curation/static/avatars/` to `python/src/pkdb/curation/avatars/` (`git mv`)
- Test: `python/tests/test_curation_server.py`

**Interfaces:**
- Produces: `GET /` and `/index.html` read `index.html`, replace every `__PKDB_NONCE__` with a fresh `secrets.token_urlsafe(16)` and send `Content-Security-Policy` with `style-src 'self' 'nonce-<nonce>'` (all other directives unchanged); every other response keeps `style-src 'self'`. `GET /avatars/<file>` serves files of `python/src/pkdb/curation/avatars/` (no auth, path-contained, images only). `launch.open_path(path, reveal=False)`: when `PKDB_OPEN_COMMAND` is set, runs `shlex.split(command) + [str(path)]` instead of the platform opener (same timeout and `check=True`).

- [ ] **Step 1: Write the failing tests**

In `test_curation_server.py`: the `local_server` fixture writes `index.html` containing `<style nonce="__PKDB_NONCE__"></style>`; two GETs of `/` return different nonces, each equal in the body and in the CSP header (`'nonce-<value>'` in `style-src`), and `'unsafe-inline'` appears in no header; `GET /static/app.js` keeps `style-src 'self'` without a nonce. Update `test_bundled_curator_avatars_are_served_as_images` to `/avatars/<file>`. A `launch` test sets `PKDB_OPEN_COMMAND` to a small recording script (written to `tmp_path`, `chmod +x`) or to `sys.executable` with `-c` code, calls `open_path(file)`, and asserts the recorded argument; an unset variable keeps the platform behavior (existing test).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/test_curation_server.py`
Expected: FAIL.

- [ ] **Step 3: Implement**

Build the CSP string in one function `_csp(nonce: str | None) -> str` used by `_reply`; pass the nonce only for the index document. Move the avatars with `git mv`, point `AVATARS = Path(__file__).parent / "avatars"`, serve `/avatars/` before the static fallback, update `scripts/update_client_curators.py` and the vanilla `app.js` paths so the current UI keeps showing avatars until part C replaces it, and check the wheel still contains the avatars (`python/pyproject.toml` packages `src/pkdb`, which includes the new folder; verify with `uv build --project python --out-dir /tmp/pkdb-wheel-check` and `unzip -l`, then remove the build output).

- [ ] **Step 4: Run the tests**

Run: `cd python && uv run --locked pytest -q` and `uv run --locked python ../scripts/update_client_curators.py --check` (from `python/`; the CI runs it so).
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A python/src/pkdb/curation scripts/update_client_curators.py python/tests/test_curation_server.py
git commit -m "Give index.html a style nonce, serve avatars from their own folder and allow a recording opener"
```

---

### Task 8: Documentation of the format 2 engine

**Files:**
- Modify: `docs/local-curation.md`
- Test: docs build

**Interfaces:**
- Consumes: Tasks 1 to 7. Part C rewrites the page with the new front end; this task removes statements that part B makes wrong.

- [ ] **Step 1: Update the page**

In `docs/local-curation.md` (paragraphs on one source line):
- State that the app lists study format 2 folders by `<substance>/<name>`, counts format 1 folders without touching them, and that format 1 curation stays on the released app version until the migration.
- Replace the format 1 hidden-TSV and "the app never edits study sources" statements: each save syncs the workbook with the tables, formats and validates (and uploads when On save is Upload); a sync conflict stops the job until it is resolved with `pkdb tables sync --keep workbook|tables` or in the workbook.
- Replace the issue mapping text: the GitHub issue comes from the `issue` number in `study.json`.
- Add a short "Local API" paragraph naming the routes of spec 7.3 for developers of the front end (no request examples needed).

- [ ] **Step 2: Verify**

Run: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` from the repository root and `cd python && uv run --locked pytest -q`.
Expected: no warnings, PASS.

- [ ] **Step 3: Commit**

```bash
git add docs/local-curation.md
git commit -m "Document the format 2 curation engine and its local API"
```
