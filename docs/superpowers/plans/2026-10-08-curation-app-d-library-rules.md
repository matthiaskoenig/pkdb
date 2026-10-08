---
search:
  exclude: true
---

# Curation app, part D: library rules from the server and exact acknowledgements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The curation app stops re-implementing rules of the `pkdb.studyformat` library, because the local server sends what the library knows, and an acknowledgement of a warning covers exactly that warning.

**Architecture:**
- Every TypeScript copy of a library rule in `frontend/src/curation-app/` is replaced by data of the local server: the table files with their kinds in workbook order and the kind and removing side of each sync conflict (`study_detail`), a preview route for a new table and one for a draft review target, the matched lines and the digitized series of every review target (`study_detail.targets`), error bar ends as part of their series (`study_source`), suggestion kinds and a field-free message on issues, and the review item of each write job. The front end keeps only labels of enumerated values.
- One mechanism ties both sides: **contract fixtures**. A Python test (`python/tests/test_curation_contract.py`) builds real answers of the engine and the library on a copy of the e2e fixture workspace and compares them with JSON files in `frontend/tests/fixtures/curation-contract/`; `frontend/tests/unit/curation-contract.spec.ts` reads the same files and asserts what the app does with them. A change on either side fails a test on that side.
- A warning without a row of a data table carries a stable `key` in its `SourceLocation` (the dataset name of a WebPlotDigitizer project, the review item id in `review.json`). `pkdb review acknowledge`, the local server and the app store it as the new `key` of the `ReviewTarget`, which then matches exactly that warning. A target of a file alone keeps its old meaning (every warning of the code in the file), so existing `review.json` files are unchanged and keep their meaning; the app labels such acknowledgements with their scope. A new acknowledgement of a warning that has neither a row nor a key is refused instead of silently widened.

**Tech Stack:** Python 3.14 (Pydantic 2, pytest, ruff, ty), the `pkdb curate` local server (`http.server`), Vue 3.5 with Vuetify 4.2, Pinia, TypeScript 6, vitest 5 with `@vue/test-utils`, Playwright 1.63.

**Spec:** `docs/superpowers/specs/2026-10-06-curation-app-design.md` (sections 5, 7.3 and 8) and `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (section 7, `review.json`, and section 9, issues). The requirements come from the final review of part C, Important 3 and Important 4 (`final-review.md` of the part C session); the part C fix already added the scope sentence to the Acknowledge dialog, which this plan removes again because new acknowledgements are exact.

## Global Constraints

- **Python:** 3.14; run from `python/`: `uv run --locked pytest -q`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`. Run the backend suite when a schema that `backend/` uses changes (`SourceLocation`, `ReviewTarget`, `ValidationIssue` messages): from the repository root, `docker compose -f compose.test.yaml up -d --wait`, `export PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test`, `uv run --project backend pytest backend/tests -q -x`.
- **Frontend rules** (`frontend/scripts/check-source.ts`, eslint, `vue-tsc`): only `<script setup lang="ts">` in `.vue` files, no JavaScript files in `src/` or `tests/`, no `any`, no `@ts-ignore`/`@ts-nocheck`; components import Vuetify components explicitly from `vuetify/components`; no literal `style="..."` attributes (Vue `:style` bindings are allowed); dependencies stay pinned exactly; no new runtime dependency.
- **Gates, from `frontend/`, every commit keeps them green:** `npm run test:source`, `npm run typecheck`, `npm run lint`, `npm run test:unit -- --run`, `npm run build`, `npm run build:curation`, `npm run test:curation-e2e`. Docs, when a Markdown file changes: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` from the repository root.
- **Writing:** never use the em dash character; Markdown paragraphs on one source line; no attribution lines in commits, docs or code; user-facing text in plain, short English sentences.
- **Generated files:** never hand-edit `docs/study-format.md` (regenerate it with `pkdb schema docs`), any `CHANGELOG.md`, or the contract fixtures in `frontend/tests/fixtures/curation-contract/` (regenerate them with `PKDB_UPDATE_CONTRACT=1`).
- **pkdb_data is read-only and never used:** fixtures live in the repository (`tools/curation_testing/fixture`, `python/tests`).
- **API:** all requests are same-origin to `/local/...`; POSTs send JSON with `X-CSRF-Token`. The two new preview routes are POSTs that read, like `/local/reference/preview`: they need the session and the CSRF header, but no user, and they record no activity.
- **Compatibility:** a `review.json` written before this plan loads and keeps its meaning; `ReviewTarget` and `SourceLocation` without a `key` serialize exactly as before (no `"key": null` anywhere, also not in the backend database or API); jobs saved in `state.json` by part C keep their item links and texts. Nothing else of the local API stays backward compatible: the page and the server ship in one package.
- **One mechanism for cross-language checks:** contract fixtures (Task 1). Component tests that render a server answer which a fixture holds take it from the fixture.

## Review Focus

1. **A `review.json` written before this plan with a file-wide acknowledgement** (target `{file}` only, as `target_for_issue` wrote for `unknown_dataset`): it must keep hiding every warning of its code in that file, now and later, and the Problems section must say so in the acknowledged list. Tests in Task 6 (library matching, contract fixture, component test).
2. **Two warnings of one code in one file without rows** (two `unknown_dataset` datasets in one `.wpd.json`): acknowledging one leaves the other listed after the next validation, and a dataset added later raises a new warning. Tests in Task 6 (library, local API, Playwright).
3. **Fast typing in Add table and New review item**, where the preview answers arrive out of order or late: the dialog shows only the answer for the current input, never a stale one, and Add waits for it. Tests in Task 2 (`usePreview`) and Task 3 (New item dialog).
4. **A study beyond the upload limits:** the study detail has empty `tables` and `targets`, the target preview answers `413` with the limit, and the sections show their limit message instead of failing. Tests in Task 1 and Task 3 (local API).
5. **The state of `pkdb curate` saved by part C:** write jobs without `item` still link their review item in the Activity, and a job saved as canceled with the message `Queued` reads "Canceled before starting". Test in Task 5 (engine restart).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `python/tests/curation_contract.py` (create) | `check_contract(name, value)`: compares an answer with its fixture or rewrites it with `PKDB_UPDATE_CONTRACT=1`. |
| `python/tests/test_curation_contract.py` (create) | One test per fixture, built with the real engine on a copy of `tools/curation_testing/fixture`. |
| `frontend/tests/fixtures/curation-contract/*.json` (generated) | `tables`, `table-preview`, `targets`, `source-fig1`, `messages`, `acknowledgements`. |
| `frontend/tests/unit/curation-contract.spec.ts` (create) | The front-end side of every fixture. |
| `python/src/pkdb/studyformat/tables.py` | `RAW_KIND`. |
| `python/src/pkdb/studyformat/layout.py` | `workbook_tables(layout)`. |
| `python/src/pkdb/studyformat/sync.py` | `SyncConflict.removed`, `conflict_data` kind and removed, `NEW_TABLE_KINDS`, `new_table_name`, `TablePreview`, `preview_table`, `_name_refusal`. |
| `python/src/pkdb/studyformat/targets.py` (create) | `DigitizedSeries`, `TargetMatch`, `match_target(study, target)`. |
| `python/src/pkdb/studyformat/digitize.py` | `SERIES_COLUMNS`, `dataset_series(name)`, keys of `unknown_dataset` and file-level `digitized_mismatch`. |
| `python/src/pkdb/studyformat/sources.py`, `plot.py` | `OverlayPoint.series` is the series, `OverlayPoint.error_bar_end` marks error bar ends. |
| `python/src/pkdb/studyformat/issues.py`, `terms.py`, `load.py` | Suggestion kinds, `make_issue(key=..., suggestion=...)`, `context.detail` of document issues. |
| `python/src/pkdb/schemas/source.py`, `schemas/review.py` | `SourceLocation.key`, `ReviewTarget.key`, both omitted when unset. |
| `python/src/pkdb/studyformat/relations.py` | Key of `review_target_unmatched`; a key on a table target is `unknown_review_target`. |
| `python/src/pkdb/studyformat/review_edit.py`, `validation.py` | `NoExactTarget`, exact `target_for_issue`, `key` in `matching_warnings` and `warning_locations`, `Acknowledgement.key`, `acknowledgement_scope`. |
| `python/src/pkdb/study_cli.py` | `--key` of `pkdb review add` and `pkdb review acknowledge`. |
| `python/src/pkdb/curation/studies.py`, `server.py`, `jobs.py`, `engine.py`, `state.py` | Detail fields, preview routes, add by kind and source, job `item` and `parts`, legacy job migration, acknowledgement `key` and `scope`. |
| `frontend/src/curation-app/api/types.ts` | The new fields and guards. |
| `frontend/src/curation-app/composables/usePreview.ts` (create) | One preview request at a time, only the answer for the current input. |
| `frontend/src/curation-app/{study,tables,tableKinds,review,grid,overlay,problems,activity,metadata}.ts` | The rule copies go away; small helpers over server data stay. |
| Components and sections | `AddTableDialog`, `NewItemDialog`, `TargetView`, `ConflictPanel`, `AcknowledgeDialog`, `TablesSection`, `SourcesSection`, `ProblemsSection`, `ReviewSection`, `ActivitySection`. |
| `frontend/tests/curation-e2e/acknowledge.spec.ts` (create) | Acknowledges one of two datasets end to end. |
| Docs | `docs/installation.md`, `docs/local-curation.md`, `docs/python-client.md`, `python/src/pkdb/studyformat/export.py` (then `docs/study-format.md` regenerated), the two specs, `release-notes/unreleased.md`. |

Rule copies that stay on purpose, with the reason (say so in the PR description):
- Labels of enumerated values (`TABLE_KIND_LABELS`, `NEW_TABLE_KINDS`, `STAGE_LABELS`, job status labels): they are UI text; the contract fixture lists every table kind and new-table kind of the library, so a new value fails a test.
- `LIMIT_CODES` (`row_limit`, `file_limit`) and `sync_conflict` in `withoutConflicts`: issue codes are API values, not rules.
- `location()` says "row" for an issue of `<study>.xlsx`: the format allows exactly one spreadsheet file per study.
- `IMPLIED_COLUMNS` in `sources.ts` and `columnLetters`: display choices and the spreadsheet column convention.

---

### Task 1: Contract fixtures and the table files of a study

**Files:**
- Create: `python/tests/curation_contract.py`, `python/tests/test_curation_contract.py`, `frontend/tests/unit/curation-contract.spec.ts`, `frontend/tests/fixtures/curation-contract/tables.json` (generated)
- Modify: `python/src/pkdb/studyformat/tables.py`, `python/src/pkdb/studyformat/layout.py`, `python/src/pkdb/studyformat/sync.py:85-120,301-330`, `python/src/pkdb/curation/studies.py:374-430`
- Modify: `frontend/src/curation-app/api/types.ts`, `frontend/src/curation-app/study.ts:55-93`, `frontend/src/curation-app/tables.ts:1-30,150-225`, `frontend/src/curation-app/components/ConflictPanel.vue`, `frontend/src/curation-app/sections/TablesSection.vue:92-94`
- Test: `python/tests/studyformat/test_studyformat_layout.py`, `python/tests/studyformat/test_sync.py:553-578,702-730`, `python/tests/test_curation_api.py:53-78,143-161`, `frontend/tests/unit/curation-fixtures.ts`, `frontend/tests/unit/curation-study.spec.ts`, `frontend/tests/unit/curation-tables.spec.ts`
- Docs: `docs/installation.md`, `docs/local-curation.md` (Local API)

**Interfaces:**
- Consumes: `scan_folder(folder) -> Layout` (`layout.tables` sorted by `KIND_ORDER` and natural source, `layout.raw_tables` by natural source), `sync_study(folder, vocabulary, check=True) -> SyncResult`, `CurationEngine(root, state_dir=..., offline=True, start=False)`.
- Produces (Python): `RAW_KIND = "raw"` in `tables.py`; `workbook_tables(layout: Layout) -> list[tuple[str, str]]`; `SyncConflict.removed: Side | None = None` (the side that removed the whole table); `conflict_data(conflict)` adds `"kind": str` (a table kind or `"raw"`) and `"removed": "workbook" | "tables" | None`; `study_detail(identity)["tables"]: list[{"file": str, "kind": str}]`, empty beyond the upload limits.
- Produces (tests): `check_contract(name: str, value: object) -> None` in `python/tests/curation_contract.py`; the fixtures `workspace` (a copy of the fixture workspace) and `engine_on(workspace, saved=None) -> CurationEngine` in `test_curation_contract.py`; `contract<T>(value: unknown): T` in `curation-contract.spec.ts`.
- Produces (TypeScript): `type TableFileKind = TableKind | "raw"`, `interface TableEntry { file: string; kind: TableFileKind }`, `StudyDetail.tables: TableEntry[]`, `ConflictData.kind: TableFileKind`, `ConflictData.removed: "workbook" | "tables" | null`; `tableFiles(detail: Pick<StudyDetail, "tables">): string[]`, `isRawTable(detail: Pick<StudyDetail, "tables">, file: string): boolean`, `dataTableFiles(detail: Pick<StudyDetail, "tables">): Set<string>` (until Task 6 removes it); `conflictView(conflict, header)` keeps its signature.

- [ ] **Step 1: Write the failing Python tests**

`python/tests/studyformat/test_studyformat_layout.py` (add `workbook_tables` to the layout import and `from pkdb.studyformat.sync import _sheet_order`):

```python
def test_workbook_tables_follow_the_sheets_of_the_workbook(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "outputs_Tab10.tsv": valid_files["outputs_Tab2.tsv"],
            "Example_Tab2.tsv": "cmax\t2.5\n",
        }
    )
    tables = workbook_tables(scan_folder(folder))
    assert tables == [
        ("subjects.tsv", "subjects"),
        ("interventions.tsv", "interventions"),
        ("characteristica.tsv", "characteristica"),
        ("outputs_Tab2.tsv", "outputs"),
        ("outputs_Tab10.tsv", "outputs"),
        ("timecourses_Fig1.tsv", "timecourses"),
        ("scatters_Fig2.tsv", "scatters"),
        ("Example_Tab2.tsv", "raw"),
    ]
    # The order is the sheet order of the sync.
    files = [file for file, _ in tables]
    assert files == sorted(files, key=lambda file: _sheet_order(file, "Example"))
```

`python/tests/studyformat/test_sync.py`: import `conflict_data` from `pkdb.studyformat.sync`. In `test_a_removed_sheet_whose_table_changed_conflicts` add `removed="workbook"` to the expected `SyncConflict(...)` and, after it:

```python
    data = conflict_data(result.conflicts[0])
    assert (data["kind"], data["removed"]) == ("outputs", "workbook")
```

In `test_a_table_deleted_while_its_sheet_changed_conflicts` (line 702) add `removed="tables"` to the expected `SyncConflict(...)`. The region conflicts (lines 279, 357, 862) keep the default `removed=None`.

`python/tests/test_curation_api.py`, in `test_study_detail`:

```python
    assert detail["tables"] == [
        {"file": "subjects.tsv", "kind": "subjects"},
        {"file": "interventions.tsv", "kind": "interventions"},
        {"file": "characteristica.tsv", "kind": "characteristica"},
        {"file": "outputs_Tab2.tsv", "kind": "outputs"},
        {"file": "timecourses_Fig1.tsv", "kind": "timecourses"},
        {"file": "scatters_Fig2.tsv", "kind": "scatters"},
        {"file": "Example_Tab2.tsv", "kind": "raw"},
    ]
```

and in `test_upload_limits_bound_the_read_routes` extend the existing assertion to `assert detail["sources"] == [] and detail["files"] == [] and detail["tables"] == []`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_studyformat_layout.py tests/studyformat/test_sync.py tests/test_curation_api.py -k "workbook_tables or removed_sheet_whose or deleted_while or study_detail or upload_limits"`
Expected: FAIL (`ImportError: cannot import name 'workbook_tables'`, `TypeError` on `removed=`, `KeyError: 'tables'`).

- [ ] **Step 3: Implement the library and the detail field**

`tables.py`, after `JSON_FILES`:

```python
# The kind of a raw table, the paper table as printed, beside the table kinds.
RAW_KIND = "raw"
```

`layout.py` (import `RAW_KIND`):

```python
def workbook_tables(layout: Layout) -> list[tuple[str, str]]:
    """The table files and raw tables of a study with their kinds, in the order of the workbook sheets.

    The data tables come by kind and source, then the raw tables with the kind `raw`.
    """
    return [
        *((table.name, table.spec.kind) for table in layout.tables),
        *((raw.name, RAW_KIND) for raw in layout.raw_tables),
    ]
```

`sync.py`: extend the docstring of `SyncConflict` with "`removed` is the side that removed the whole table, which the other side then lists from its header, or None for rows that both sides changed." and add the last field `removed: Side | None = None`. In `_removal_conflict` pass `removed="workbook" if workbook is None else "tables"` to the `SyncConflict(...)` it builds. In `conflict_data`:

```python
def _conflict_kind(file: str) -> str:
    """The table kind of a conflicting file, or `raw`: conflicts are about table files and raw tables."""
    parsed = parse_table_file(file)
    return RAW_KIND if parsed is None else parsed[0].kind
```

and add `"kind": _conflict_kind(conflict.file)` and `"removed": conflict.removed` to the returned dict.

`curation/studies.py`, `study_detail`: import `workbook_tables`; set `tables = []` in the `except StudyValidationError` branch and `tables = [{"file": file, "kind": kind} for file, kind in workbook_tables(layout)]` in the `else` branch; return `"tables": tables` after `"files": files`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd python && uv run --locked pytest -q tests/studyformat tests/test_curation_api.py`
Expected: PASS.

- [ ] **Step 5: Add the contract helper and the first contract test**

`python/tests/curation_contract.py`:

```python
"""Contract fixtures: real answers of the local curation API that the front-end tests read.

Each fixture is a JSON file in frontend/tests/fixtures/curation-contract/. A Python test builds
the answer with the real engine and library and compares it with the file, and
frontend/tests/unit/curation-contract.spec.ts reads the same file. A change on one side fails a
test on that side: regenerate the files with PKDB_UPDATE_CONTRACT=1 and let the front-end tests
judge the new answers. Never edit the files by hand.
"""

import json
import math
import os
from pathlib import Path

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "tests"
    / "fixtures"
    / "curation-contract"
)
UPDATE = "PKDB_UPDATE_CONTRACT"
REGENERATE = f"{UPDATE}=1 uv run --locked pytest -q tests/test_curation_contract.py"


def _normalized(value):
    """JSON values with floats rounded to 6 significant digits, so that platforms agree."""
    if isinstance(value, float):
        return float(f"{value:.6g}") if math.isfinite(value) else value
    if isinstance(value, dict):
        return {key: _normalized(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    return value


def check_contract(name: str, value: object) -> None:
    """Compare `value` with the fixture `name`, or write it when PKDB_UPDATE_CONTRACT is set."""
    path = FIXTURES / f"{name}.json"
    data = _normalized(json.loads(json.dumps(value)))
    if os.environ.get(UPDATE):
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
        return
    assert path.is_file(), f"{path} is missing; run {REGENERATE}"
    assert json.loads(path.read_text(encoding="utf-8")) == data, (
        f"{path.name} differs from the answer of the local API; run {REGENERATE} "
        "and run the front-end unit tests against the new fixture"
    )
```

`python/tests/test_curation_contract.py`:

```python
"""Contract fixtures of the local curation API for the front-end tests; see curation_contract.py."""

import json
import shutil
from pathlib import Path

import openpyxl
import pytest
from curation_contract import check_contract

from pkdb.cache import bundled_vocabulary
from pkdb.curation.engine import CurationEngine
from pkdb.studyformat.sync import conflict_data, sync_study
from pkdb.studyformat.tables import TABLES

FIXTURE = Path(__file__).resolve().parents[2] / "tools" / "curation_testing" / "fixture"
DEMO = "caffeine/Demo2020"


@pytest.fixture
def workspace(tmp_path):
    """A copy of the fixture workspace of the end-to-end tests."""
    root = tmp_path / "workspace"
    shutil.copytree(FIXTURE, root)
    return root


@pytest.fixture
def engine_on(tmp_path):
    """Start engines of pkdb curate offline and without threads, writing as curator."""
    started = []

    def start(workspace: Path, saved: dict | None = None) -> CurationEngine:
        state = tmp_path / f"state{len(started)}"
        state.mkdir()
        if saved is not None:
            (state / "state.json").write_text(json.dumps(saved), encoding="utf-8")
        engine = CurationEngine(workspace, state_dir=state, offline=True, start=False)
        engine.user = "curator"
        started.append(engine)
        return engine

    yield start
    for engine in started:
        engine.close()


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is not in {path.name}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")


def test_tables_contract(workspace, engine_on):
    """The table files of Demo2020 and the conflicts of changed rows, a removed sheet and a removed raw sheet."""
    tables = engine_on(workspace).study_detail(DEMO)["tables"]
    folder = workspace / DEMO
    vocabulary = bundled_vocabulary()
    assert sync_study(folder, vocabulary).ok
    workbook = openpyxl.load_workbook(folder / "Demo2020.xlsx")
    del workbook["outputs_Tab2"]
    del workbook["Demo2020_Tab2"]
    workbook["subjects"]["D2"] = 14
    workbook.save(folder / "Demo2020.xlsx")
    _replace(folder / "subjects.tsv", "Demo2020\tall\t\t12\t", "Demo2020\tall\t\t13\t")
    _replace(folder / "outputs_Tab2.tsv", "\t17.6\t", "\t17.8\t")
    _replace(folder / "Demo2020_Tab2.tsv", "17.6 ± 4.2", "17.8 ± 4.2")
    conflicts = [
        conflict_data(conflict)
        for conflict in sync_study(folder, vocabulary, check=True).conflicts
    ]
    assert [(c["file"], c["kind"], c["removed"]) for c in conflicts] == [
        ("subjects.tsv", "subjects", None),
        ("outputs_Tab2.tsv", "outputs", "workbook"),
        ("Demo2020_Tab2.tsv", "raw", "workbook"),
    ]
    check_contract(
        "tables",
        {"tables": tables, "table_kinds": list(TABLES), "conflicts": conflicts},
    )
```

Run: `cd python && PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py && uv run --locked pytest -q tests/test_curation_contract.py`
Expected: the first run writes `frontend/tests/fixtures/curation-contract/tables.json`, the second passes. Read the file: six tables in workbook order, three conflicts with `kind` and `removed`.

- [ ] **Step 6: Use the table list in the front end**

`api/types.ts`:

```ts
/** The kind of a table file: a table kind, or `raw` for the raw table of a paper table. */
export type TableFileKind = TableKind | "raw";

/** A table file of the study with its kind; the study detail lists them in the order of the workbook sheets. */
export interface TableEntry {
  file: string;
  kind: TableFileKind;
}
```

Add `tables: TableEntry[];` to `StudyDetail` (doc comment: "The table files and raw tables in the order of the workbook sheets; empty beyond the upload limits.") and `"tables"` to `isStudyDetail`. Add to `ConflictData`: `kind: TableFileKind;` and `/** The side that removed the whole table, which the other side lists from its header; null for rows that both sides changed. */ removed: "workbook" | "tables" | null;`.

`study.ts`: delete `DATA_TABLE` and `SOURCE_TABLE` and the import of `DATA_TABLE_KINDS` (`SOURCE`, `RAW_SOURCE` and `SOURCE_TABLE_KINDS` stay for `newTable` until Task 2). Replace the three functions:

```ts
/** The table files of a study, data tables and raw tables, in the order of the workbook sheets, as the server lists them. */
export function tableFiles(detail: Pick<StudyDetail, "tables">): string[] {
  return detail.tables.map((table) => table.file);
}

/** Whether a table file of the study is a raw table, the paper table as printed. */
export function isRawTable(detail: Pick<StudyDetail, "tables">, file: string): boolean {
  return detail.tables.some((table) => table.file === file && table.kind === "raw");
}

/** The data tables of a study, which the library loads as tables: the table files without the raw tables. */
export function dataTableFiles(detail: Pick<StudyDetail, "tables">): Set<string> {
  return new Set(detail.tables.filter((table) => table.kind !== "raw").map((table) => table.file));
}
```

`railCounts` uses `tables: detail.tables.length`.

`tables.ts`: delete `rank` and `tableOrder` and the imports of `isRawTable`, `DATA_TABLE_KINDS` and `SOURCE_TABLE_KINDS`. In `conflictView` replace the detection of a removal and the notes (update the doc comment: the server says which side removed the whole table):

```ts
  // A side that removed the whole table leaves the other side listing it from its header, line
  // 1 and row 1; a raw table has no header.
  const removal = conflict.removed !== null && conflict.kind !== "raw";
  const first = removal ? (conflict.table_lines[0] ?? conflict.workbook_rows[0]) : undefined;
  const columns = header ?? (first ? split(first.text) : null);
```

keep the slicing of `base`, `workbook` and `tables` by `removal`, and compute the note as:

```ts
  let note: string | null = null;
  if (conflict.removed === "workbook")
    note = "The sheet has no rows in the workbook, but the table changed since the last sync.";
  else if (conflict.removed === "tables") note = `${conflict.file} was deleted, but its sheet changed since the last sync.`;
  else if (!workbook.length) note = "The workbook removed these rows, and the tables changed them.";
  else if (!tables.length) note = "The tables removed these lines, and the workbook changed them.";
  else if (!base.length) note = "Both sides added these rows.";
```

`ConflictPanel.vue`: drop the `isRawTable` import; build the files from the first unresolved conflict of each file (`new Map(unresolved.value.map((conflict) => [conflict.file, conflict]))`) and let `header(conflict: ConflictData)` return null when `conflict.kind === "raw" || !study.detail?.files.includes(conflict.file)`.

`TablesSection.vue`: `const files = computed(() => (detail.value ? tableFiles(detail.value) : []));` and `const raw = computed(() => new Set((detail.value?.tables ?? []).filter((table) => table.kind === "raw").map((table) => table.file)));`; drop the `tableOrder` and `isRawTable` imports. `SourcesSection`, `ProblemsSection`, `TargetView`, `NewItemDialog` and `AcknowledgeDialog` keep calling `tableFiles(detail)` and `dataTableFiles(detail)`, which now read `detail.tables`.

- [ ] **Step 7: Update the front-end tests and add the contract spec**

`tests/unit/curation-fixtures.ts`: `studyDetail()` gets

```ts
    tables: [
      { file: "subjects.tsv", kind: "subjects" },
      { file: "interventions.tsv", kind: "interventions" },
      { file: "characteristica.tsv", kind: "characteristica" },
      { file: "outputs_Tab2.tsv", kind: "outputs" },
      { file: "timecourses_Fig1.tsv", kind: "timecourses" },
      { file: "Example_Tab2.tsv", kind: "raw" },
    ],
```

and the conflict constants get their fields: `REGION_CONFLICT` `kind: "outputs", removed: null`, `ROWS_REMOVED_CONFLICT` `kind: "subjects", removed: null`, `FILE_DELETED_CONFLICT` `kind: "scatters", removed: "tables"`. Find every test detail whose `files` lists other table files (`rg -n "files:" frontend/tests`) and give it the matching `tables` in sheet order. In `curation-study.spec.ts` replace the `tableFiles` and `isRawTable` tests by tests over `tables` (order kept, raw found, a file that is no table not raw); in `curation-tables.spec.ts` delete the `tableOrder` tests and pass conflicts with `kind` and `removed` to `conflictView`.

`frontend/tests/unit/curation-contract.spec.ts` (later tasks add a `describe` block each and put their imports with these at the top of the file):

```ts
/**
 * The front-end side of the contract fixtures: real answers of the local API, written by
 * python/tests/test_curation_contract.py. Regenerate them there with PKDB_UPDATE_CONTRACT=1.
 */
import { describe, expect, it } from "vitest";
import type { ConflictData, TableEntry } from "../../src/curation-app/api/types";
import { isRawTable, railCounts, tableFiles } from "../../src/curation-app/study";
import { TABLE_KINDS } from "../../src/curation-app/tableKinds";
import { conflictView } from "../../src/curation-app/tables";
import tablesFixture from "../fixtures/curation-contract/tables.json";
import { studyDetail, SUBJECTS_COLUMNS } from "./curation-fixtures";

/** A fixture as the type of the app; the fixture is a real answer of the server. */
function contract<T>(value: unknown): T {
  return value as T;
}

describe("tables contract", () => {
  const tables = contract<TableEntry[]>(tablesFixture.tables);
  const conflicts = contract<ConflictData[]>(tablesFixture.conflicts);
  const conflict = (kind: string) => conflicts.find((entry) => entry.kind === kind)!;

  it("lists the tables of a study in the order of the workbook sheets", () => {
    expect(tableFiles({ tables })).toEqual([
      "subjects.tsv",
      "interventions.tsv",
      "characteristica.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Demo2020_Tab2.tsv",
    ]);
    expect(isRawTable({ tables }, "Demo2020_Tab2.tsv")).toBe(true);
    expect(isRawTable({ tables }, "outputs_Tab2.tsv")).toBe(false);
    expect(railCounts(studyDetail({ tables })).tables).toBe(6);
  });

  it("has the notes of every table kind of the library", () => {
    expect([...TABLE_KINDS]).toEqual(tablesFixture.table_kinds);
  });

  it("compares the rows that both sides changed", () => {
    const view = conflictView(conflict("subjects"), SUBJECTS_COLUMNS);
    expect(view.changed).toEqual(["count"]);
    expect([...view.labels.values()]).toEqual(["Last sync", "Workbook row 2", "Tables line 2"]);
    expect(view.note).toBeNull();
  });

  it("lists a table whose sheet was removed from its header", () => {
    const view = conflictView(conflict("outputs"), null);
    expect(view.note).toBe("The sheet has no rows in the workbook, but the table changed since the last sync.");
    expect(view.table.kind).toBe("table");
    expect(view.table.kind === "table" && view.table.header.slice(0, 3)).toEqual(["study", "source", "subjects"]);
  });

  it("keeps the first line of a raw table, which has no header", () => {
    const view = conflictView(conflict("raw"), null);
    expect(view.table.kind).toBe("raw");
    expect(view.table.rows[0]?.cells[0]).toBe("Parameter");
    expect(view.note).toBe("The sheet has no rows in the workbook, but the table changed since the last sync.");
  });
});
```

Run: `cd frontend && npx vitest run tests/unit/curation-contract.spec.ts tests/unit/curation-study.spec.ts tests/unit/curation-tables.spec.ts`
Expected: PASS.

- [ ] **Step 8: Document the fixtures and the detail field**

`docs/installation.md`, after the block of frontend checks, one paragraph: "The unit tests of the curation app read contract fixtures in `frontend/tests/fixtures/curation-contract/`. `python/tests/test_curation_contract.py` writes them from real answers of the local server on the fixture workspace and fails when an answer changes. Regenerate them from `python/` with `PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py`, review the diff, and run the frontend unit tests against them. Never edit them by hand."

`docs/local-curation.md`, Local API, the `GET /local/studies/{substance}/{name}` item: "the study page with metadata, review, problems, acknowledged warnings, sync status and conflicts, sources, files, the table files with their kinds in the order of the workbook sheets, and jobs."

- [ ] **Step 9: Run every gate**

Run: `cd python && uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Run: `cd frontend && npm run test:source && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && npm run build:curation && npm run test:curation-e2e`
Run: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean`
Expected: all pass; `git status` shows only the files of this task.

- [ ] **Step 10: Commit**

```bash
git add python/src/pkdb/studyformat/tables.py python/src/pkdb/studyformat/layout.py python/src/pkdb/studyformat/sync.py python/src/pkdb/curation/studies.py python/tests frontend/src/curation-app frontend/tests docs/installation.md docs/local-curation.md
git commit -m "Send the table files of a study and the kind of each sync conflict from the local server"
```

---

### Task 2: Preview a new table on the server

**Files:**
- Create: `frontend/src/curation-app/composables/usePreview.ts`, `frontend/tests/unit/curation-preview.spec.ts`, `frontend/tests/fixtures/curation-contract/table-preview.json` (generated)
- Modify: `python/src/pkdb/studyformat/sync.py:857-920`, `python/src/pkdb/curation/studies.py:686-735`, `python/src/pkdb/curation/server.py:375-395`
- Modify: `frontend/src/curation-app/api/types.ts`, `frontend/src/curation-app/stores/study.ts`, `frontend/src/curation-app/tableKinds.ts`, `frontend/src/curation-app/study.ts:56-60,228-291`, `frontend/src/curation-app/components/AddTableDialog.vue`
- Test: `python/tests/studyformat/test_sync.py`, `python/tests/test_curation_api.py:668,872-935,1106,1194`, `python/tests/test_curation_contract.py`, `frontend/tests/unit/curation-contract.spec.ts`, `frontend/tests/unit/curation-study.spec.ts:201-240`, `frontend/tests/components/curation-study-page.spec.ts:588-690`
- Docs: `docs/local-curation.md` (Local API)

**Interfaces:**
- Consumes: `RAW_KIND` (Task 1), `_table_name_issue(table, study)`, `_same_name(name, names)`, `add_table(folder, vocabulary, table)`, `image_file(study, source)`, `SOURCE_PATTERN`, `TEXT_SOURCE`, `RAW_SOURCE` (`studyformat/raw.py`).
- Produces (Python): `NEW_TABLE_KINDS: tuple[str, ...] = ("outputs", "timecourses", "scatters", "raw")`; `new_table_name(study: str, kind: str, source: str) -> str`; `TablePreview(table: str, file: str, image: str | None, image_found: bool, issues: tuple[ValidationIssue, ...])`; `preview_table(folder: Path, kind: str, source: str) -> TablePreview`; engine method `table_preview(identity: str, payload: dict) -> dict`; route `POST /local/studies/tables/preview` with `{study, kind, source}`; the tables action `add` takes `{kind, source}` instead of `table` or `raw`.
- Produces (TypeScript): `interface TablePreview { table: string; file: string; image: string | null; image_found: boolean; issues: ValidationIssue[] }`, `isTablePreview`; `type NewTableKind = "outputs" | "timecourses" | "scatters" | "raw"` and `NEW_TABLE_KINDS: readonly { value: NewTableKind; label: string }[]` in `tableKinds.ts`; store `previewTable(kind: NewTableKind, source: string): Promise<TablePreview>`; `usePreview<I, O>(input: () => I | null, load: (value: I) => Promise<O>): Preview<O>` with `Preview<O> = { data: ShallowRef<O | null>; loading: Ref<boolean>; error: Ref<string | null> }`.

- [ ] **Step 1: Write the failing Python tests**

`python/tests/studyformat/test_sync.py` (import `NEW_TABLE_KINDS`, `TablePreview`, `preview_table` from `pkdb.studyformat.sync`):

```python
def test_new_table_kinds_are_the_tables_split_by_source_and_raw():
    assert NEW_TABLE_KINDS == ("outputs", "timecourses", "scatters", "raw")


def test_preview_table_names_the_sheet_file_and_image(valid_study):
    assert preview_table(valid_study, "outputs", " Tab3 ") == TablePreview(
        table="outputs_Tab3",
        file="outputs_Tab3.tsv",
        image="Example_Tab3.png",
        image_found=False,
        issues=(),
    )
    raw = preview_table(valid_study, "raw", "Tab2")
    assert (raw.table, raw.file, raw.image, raw.image_found, raw.issues) == (
        "Example_Tab2",
        "Example_Tab2.tsv",
        "Example_Tab2.png",
        True,
        (),
    )
    text = preview_table(valid_study, "outputs", "Text")
    assert (text.image, text.image_found, text.issues) == (None, False, ())


@pytest.mark.parametrize(
    ("kind", "source", "code", "message"),
    [
        ("raw", "Fig2", "invalid_table_name", "A raw table needs a paper table source such as Tab3"),
        ("outputs", "Tab 3", "invalid_table_name", "Use a source such as Tab3, Fig2A or Text"),
        ("subjects", "Tab3", "invalid_table_name", "Choose the kind outputs, timecourses, scatters or raw"),
        ("timecourses", "Fig1", "table_exists", "timecourses_Fig1.tsv already exists"),
        ("outputs", "Tab" + "1" * 30, "table_name_too_long", None),
    ],
)
def test_preview_table_refuses_what_add_table_refuses(valid_study, kind, source, code, message):
    [issue] = preview_table(valid_study, kind, source).issues
    assert issue.code == code
    if message is not None:
        assert issue.message == message
```

`python/tests/test_curation_api.py`, new test:

```python
def test_table_preview_and_add_by_kind_and_source(api, sf_vocabulary, monkeypatch):
    server, engine, folder = api
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    headers = authenticate(server)
    preview = "/local/studies/tables/preview"
    body = {"study": "caffeine/Example", "kind": "outputs", "source": "Tab3"}
    status, _, data = request(server, "POST", preview, body, headers)
    assert status == 200
    assert json.loads(data) == {
        "table": "outputs_Tab3",
        "file": "outputs_Tab3.tsv",
        "image": "Example_Tab3.png",
        "image_found": False,
        "issues": [],
    }
    status, _, data = request(server, "POST", preview, {**body, "kind": "raw", "source": "Fig1"}, headers)
    assert [issue["message"] for issue in json.loads(data)["issues"]] == [
        "A raw table needs a paper table source such as Tab3"
    ]
    # A preview writes nothing and needs no user.
    engine.user = ""
    assert request(server, "POST", preview, body, headers)[0] == 200
    assert not (folder / "outputs_Tab3.tsv").exists()
```

In `test_tables_sync_resolve_and_add` replace `tables(action="add", raw="Tab3")` by `tables(action="add", kind="raw", source="Tab3")`, `table="outputs_Tab3"` by `kind="outputs", source="Tab3"`, `table="nonsense"` by `kind="outputs", source="nonsense"` (still `invalid_table_name`), keep `tables(action="add")[0] == 400`, and replace the `table=..., raw=...` case by `tables(action="add", kind="outputs")[0] == 400` (no source). At lines 668, 1106 and 1194 replace `{"action": "add", "raw": "Tab3"}` by `{"action": "add", "kind": "raw", "source": "Tab3"}`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_sync.py tests/test_curation_api.py -k "new_table_kinds or preview_table or table_preview or tables_sync_resolve_and_add"`
Expected: FAIL (`ImportError`, 404 for the preview route, 400 for the add by kind).

- [ ] **Step 3: Implement the preview in the library**

`sync.py` (import `RAW_KIND`, `SOURCE_PATTERN` from `tables.py` and `RAW_SOURCE` from `raw.py`):

```python
# The kinds of a new table: the tables split by source, and the raw table of a paper table.
NEW_TABLE_KINDS = (
    *(kind for kind, spec in TABLES.items() if spec.per_source),
    RAW_KIND,
)


def new_table_name(study: str, kind: str, source: str) -> str:
    """The sheet of a new table: `<kind>_<source>`, or `<study>_<source>` for a raw table."""
    return f"{study}_{source}" if kind == RAW_KIND else f"{kind}_{source}"


@dataclass(frozen=True)
class TablePreview:
    """A new table before it is added: its sheet, file and image, and why it cannot be added.

    `image` is the image of its source, None for the text of the paper. `issues` hold the
    refusal of the name, and are empty when `add_table` would sync and add the sheet.
    """

    table: str
    file: str
    image: str | None
    image_found: bool
    issues: tuple[ValidationIssue, ...] = ()


def _name_refusal(folder: Path, table: str) -> ValidationIssue | None:
    """Why `add_table` refuses a name before it syncs: not a new table name, or an existing file."""
    if (issue := _table_name_issue(table, folder.name)) is not None:
        return issue
    try:
        names = [entry.name for entry in folder.iterdir()]
    except OSError:
        # The sync reports a folder it cannot read.
        names = []
    if (existing := _same_name(f"{table}.tsv", names)) is not None:
        return make_issue("table_exists", f"{existing} already exists", file=existing)
    return None


def preview_table(folder: Path, kind: str, source: str) -> TablePreview:
    """What `add_table` would add for a kind of NEW_TABLE_KINDS and a source, or why it refuses.

    The source of a raw table must be a paper table, and any other source one such as Tab3,
    Fig2A or Text; then the checks of `add_table` before its sync apply.
    """
    folder = Path(folder).resolve()
    source = source.strip()
    table = new_table_name(folder.name, kind, source)
    if kind not in NEW_TABLE_KINDS:
        *kinds, last = NEW_TABLE_KINDS
        issue = make_issue(
            "invalid_table_name", f"Choose the kind {', '.join(kinds)} or {last}"
        )
    elif kind == RAW_KIND and not RAW_SOURCE.fullmatch(source):
        issue = make_issue(
            "invalid_table_name", "A raw table needs a paper table source such as Tab3"
        )
    elif not SOURCE_PATTERN.fullmatch(source):
        issue = make_issue(
            "invalid_table_name", "Use a source such as Tab3, Fig2A or Text"
        )
    else:
        issue = _name_refusal(folder, table)
    image = None if source == TEXT_SOURCE else image_file(folder.name, source)
    return TablePreview(
        table=table,
        file=f"{table}.tsv",
        image=image,
        image_found=image is not None and (folder / image).is_file(),
        issues=() if issue is None else (issue,),
    )
```

In `add_table` replace the name check and the `names`/`_same_name` block by `if (issue := _name_refusal(folder, table)) is not None: return AddTableResult(table, None, (issue,))`.

- [ ] **Step 4: Serve the preview and add by kind and source**

`curation/studies.py` (import `RAW_KIND`, `AddTableResult`, `preview_table`):

```python
    def table_preview(self, identity: str, payload: dict) -> dict:
        """What Add table would add for `kind` and `source`, and why it would refuse; writes nothing."""
        preview = preview_table(
            self.study_folder(identity), _text(payload, "kind"), _text(payload, "source")
        )
        return {
            "table": preview.table,
            "file": preview.file,
            "image": preview.image,
            "image_found": preview.image_found,
            "issues": _issues(list(preview.issues)),
        }
```

In `tables_action`, the `add` branch:

```python
        if action == "add":
            kind = _text(payload, "kind")
            preview = preview_table(folder, kind, _text(payload, "source"))
            added = (
                AddTableResult(preview.table, None, preview.issues)
                if preview.issues
                else self._under_folder_lock(
                    folder,
                    lambda vocabulary: add_table(folder, vocabulary, preview.table),
                )
            )
```

keep the rest of the branch, with `noun = "raw table" if kind == RAW_KIND else "table"` in the activity message (`Added {noun} {added.table}` and `Could not add {noun} {preview.table}`).

`curation/server.py`, `_action`: add `"/local/studies/tables/preview"` to the set of study paths and, before the final `return engine.tables_action(study, body)`, `if path == "/local/studies/tables/preview": return engine.table_preview(study, body)`.

- [ ] **Step 5: Run the Python tests to verify they pass**

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_sync.py tests/test_curation_api.py tests/test_curation_pipeline.py`
Expected: PASS.

- [ ] **Step 6: Write the failing `usePreview` test**

`frontend/tests/unit/curation-preview.spec.ts`:

```ts
import { describe, expect, it } from "vitest";
import { flushPromises } from "@vue/test-utils";
import { nextTick, ref } from "vue";
import { usePreview } from "../../src/curation-app/composables/usePreview";

/** A request that the test answers when it wants. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (error: unknown) => void } {
  let resolve: (value: T) => void = () => undefined;
  let reject: (error: unknown) => void = () => undefined;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function recorder() {
  const asked: string[] = [];
  const answers = new Map<string, ReturnType<typeof deferred<string>>>();
  const load = (value: string) => {
    asked.push(value);
    const answer = deferred<string>();
    answers.set(value, answer);
    return answer.promise;
  };
  return { asked, answers, load };
}

describe("usePreview", () => {
  it("asks for one input at a time and keeps only the answer for the current input", async () => {
    const input = ref<string | null>("Tab");
    const { asked, answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    expect(asked).toEqual(["Tab"]);
    expect(preview.loading.value).toBe(true);
    input.value = "Tab3";
    await nextTick();
    input.value = "Tab31";
    await nextTick();
    expect(asked).toEqual(["Tab"]);
    answers.get("Tab")?.resolve("old");
    await flushPromises();
    // The answer of an older input never shows; the newest input is asked for next.
    expect(preview.data.value).toBeNull();
    expect(asked).toEqual(["Tab", "Tab31"]);
    answers.get("Tab31")?.resolve("new");
    await flushPromises();
    expect(preview.data.value).toBe("new");
    expect(preview.loading.value).toBe(false);
  });

  it("clears without input and keeps the message of a failure", async () => {
    const input = ref<string | null>("Tab3");
    const { answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    answers.get("Tab3")?.reject(new Error("The local server stopped."));
    await flushPromises();
    expect(preview.error.value).toBe("The local server stopped.");
    input.value = null;
    await nextTick();
    expect([preview.data.value, preview.error.value, preview.loading.value]).toEqual([null, null, false]);
  });
});
```

Run: `cd frontend && npx vitest run tests/unit/curation-preview.spec.ts`
Expected: FAIL (module not found).

- [ ] **Step 7: Implement `usePreview`**

`frontend/src/curation-app/composables/usePreview.ts`:

```ts
import { ref, shallowRef, watch, type Ref, type ShallowRef } from "vue";
import { messageOf } from "../study";

/** The preview of the local server for the current input of a dialog. */
export interface Preview<O> {
  /** The answer for the current input; null without input, while it loads, or after a failure. */
  data: ShallowRef<O | null>;
  /** Whether the answer for the current input is still to come. */
  loading: Ref<boolean>;
  /** Why the preview of the current input failed, or null. */
  error: Ref<string | null>;
}

/**
 * A preview of the local server for the input of a dialog, such as a new table or the rows that
 * a draft review target matches. It asks again whenever the input changes, with one request at a
 * time: an input that changes during a request is asked for when that request ends, and only the
 * answer for the current input is kept. A null input clears the preview.
 */
export function usePreview<I, O>(input: () => I | null, load: (value: I) => Promise<O>): Preview<O> {
  const data = shallowRef<O | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  let wanted: I | null = null;
  let version = 0;
  let running = false;

  async function drain(): Promise<void> {
    running = true;
    while (wanted !== null) {
      const asked = version;
      const value: I = wanted;
      let answer: O | null = null;
      let failure: string | null = null;
      try {
        answer = await load(value);
      } catch (caught) {
        failure = messageOf(caught);
      }
      // The input changed meanwhile: ask for the newest one, if any.
      if (asked !== version) continue;
      data.value = answer;
      error.value = failure;
      wanted = null;
    }
    running = false;
    loading.value = false;
  }

  watch(
    () => {
      const value = input();
      return value === null ? null : JSON.stringify(value);
    },
    () => {
      version += 1;
      wanted = input();
      data.value = null;
      error.value = null;
      loading.value = wanted !== null;
      if (!running && wanted !== null) void drain();
    },
    { immediate: true },
  );
  return { data, loading, error };
}
```

Run: `cd frontend && npx vitest run tests/unit/curation-preview.spec.ts`
Expected: PASS.

- [ ] **Step 8: Use the server preview in Add table**

`api/types.ts`: the `TablePreview` interface of the Interfaces block and `export const isTablePreview = hasKeys<TablePreview>("table", "file", "image", "image_found", "issues");`.

`tableKinds.ts`: delete `DATA_TABLE_KINDS`, `SOURCE_TABLE_KINDS` and `SourceTableKind`; keep `TABLE_KINDS` as `["subjects", "interventions", "characteristica", "outputs", "timecourses", "scatters"] as const satisfies readonly TableKind[]` with its labels, and add:

```ts
/** The kinds of a new table, as the local server adds them (`NEW_TABLE_KINDS` of the library). */
export type NewTableKind = "outputs" | "timecourses" | "scatters" | "raw";

export const NEW_TABLE_KINDS: readonly { value: NewTableKind; label: string }[] = [
  { value: "outputs", label: TABLE_KIND_LABELS.outputs },
  { value: "timecourses", label: TABLE_KIND_LABELS.timecourses },
  { value: "scatters", label: TABLE_KIND_LABELS.scatters },
  { value: "raw", label: "Raw table" },
];
```

`study.ts`: delete `SOURCE`, `RAW_SOURCE`, `SHEET_NAME_LIMIT`, `NewTableKind`, `NEW_TABLE_KINDS`, `NewTable`, `newTable` and the `tableKinds` import.

`stores/study.ts`:

```ts
  /** What Add table would add for `kind` and `source`, and why the server would refuse it; writes nothing. */
  function previewTable(kind: NewTableKind, source: string): Promise<TablePreview> {
    return postJson("/local/studies/tables/preview", { study: opened(), kind, source }, isTablePreview);
  }
```

and return it from the store.

`AddTableDialog.vue`: import `NEW_TABLE_KINDS` and `NewTableKind` from `../tableKinds`; replace `table` by

```ts
const preview = usePreview(
  () => (study.detail && source.value.trim() ? { kind: kind.value, source: source.value.trim() } : null),
  (value) => study.previewTable(value.kind, value.source),
);
/** The new table as the server previews it for the current kind and source. */
const table = computed(() => preview.data.value);
/** Why the table cannot be added: the refusal of the server, or a failed preview. */
const problem = computed(() => table.value?.issues[0]?.message ?? preview.error.value);
const canAdd = computed(() => table.value !== null && table.value.issues.length === 0 && !busy.value);
```

`add()` returns unless `canAdd`, posts `study.tablesAction("add", { kind: kind.value, source: source.value.trim() })`, emits `result.table ?? chosen.table`, and names `${chosen.table} was not added.` on failure. The template binds `:error-messages="problem"`, shows the preview when `table && !table.issues.length` with `table.table`, `table.file`, `table.image` and `table.image_found`, and disables Add with `!canAdd`.

- [ ] **Step 9: Contract and component tests**

`python/tests/test_curation_contract.py` (import `NEW_TABLE_KINDS`):

```python
TABLE_PREVIEWS = [
    {"kind": "outputs", "source": "Tab3"},
    {"kind": "timecourses", "source": "Text"},
    {"kind": "raw", "source": "Tab2"},
    {"kind": "raw", "source": "Fig2"},
    {"kind": "outputs", "source": "Tab 3"},
    {"kind": "outputs", "source": "Tab2"},
]


def test_table_preview_contract(workspace, engine_on):
    engine = engine_on(workspace)
    previews = [
        {"request": request, "response": engine.table_preview(DEMO, request)}
        for request in TABLE_PREVIEWS
    ]
    assert [len(entry["response"]["issues"]) for entry in previews] == [0, 0, 1, 1, 1, 1]
    check_contract("table-preview", {"kinds": list(NEW_TABLE_KINDS), "previews": previews})
```

Run: `cd python && PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py && uv run --locked pytest -q tests/test_curation_contract.py`

`curation-contract.spec.ts`:

```ts
import type { TablePreview } from "../../src/curation-app/api/types";
import { isTablePreview } from "../../src/curation-app/api/types";
import { NEW_TABLE_KINDS } from "../../src/curation-app/tableKinds";
import tablePreviewFixture from "../fixtures/curation-contract/table-preview.json";

describe("table preview contract", () => {
  it("offers every kind of a new table that the library adds", () => {
    expect(NEW_TABLE_KINDS.map((kind) => kind.value)).toEqual(tablePreviewFixture.kinds);
  });

  it("accepts every preview answer", () => {
    for (const { response } of tablePreviewFixture.previews) expect(isTablePreview(contract<TablePreview>(response))).toBe(true);
  });
});
```

`curation-study.spec.ts`: delete the `newTable` tests. `curation-study-page.spec.ts`: the add-table tests answer `"POST /local/studies/tables/preview"` with a `Handler` that returns a `TablePreview` for the posted kind and source (for Harder1988: `outputs`/`Tab3` with `Harder1988_Tab3.png` found, `raw`/`Tab4` with `Harder1988_Tab4.png` missing), and expect the posted add bodies `{ study: "caffeine/Harder1988", action: "add", kind: "outputs", source: "Tab3" }` and `{ ..., kind: "raw", source: "Tab4" }`. The refusal test answers from the contract fixture (`tablePreviewFixture.previews.find((entry) => entry.request.kind === body?.kind && entry.request.source === body?.source)?.response`) and expects the dialog to contain the fixture messages of `Tab 3` and `Tab2`, with Add disabled.

- [ ] **Step 10: Document the route**

`docs/local-curation.md`, Local API, after the item of the write routes: "- `POST /local/studies/tables/preview` reads without writing: what Add table would add for a kind and a source, with the sheet, the file, the image and why it would refuse. The `add` action of `POST /local/studies/tables` takes the same `kind` and `source`."

- [ ] **Step 11: Run every gate**

Run: `cd python && uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Run: `cd frontend && npm run test:source && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && npm run build:curation && npm run test:curation-e2e`
Run: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean`
Expected: all pass.

- [ ] **Step 12: Commit**

```bash
git add python/src/pkdb/studyformat/sync.py python/src/pkdb/curation/studies.py python/src/pkdb/curation/server.py python/tests frontend/src/curation-app frontend/tests docs/local-curation.md
git commit -m "Preview a new table on the local server instead of copying the naming rules"
```

---

### Task 3: Review targets matched by the server

**Files:**
- Create: `python/src/pkdb/studyformat/targets.py`, `python/tests/studyformat/test_targets.py`, `frontend/tests/fixtures/curation-contract/targets.json` (generated)
- Modify: `python/src/pkdb/studyformat/digitize.py:359-430`, `python/src/pkdb/curation/studies.py:374-430,557-580`, `python/src/pkdb/curation/server.py:310-345,375-395`
- Modify: `frontend/src/curation-app/api/types.ts`, `frontend/src/curation-app/stores/study.ts`, `frontend/src/curation-app/grid.ts:34-75`, `frontend/src/curation-app/review.ts:99-120`, `frontend/src/curation-app/components/TargetView.vue`, `frontend/src/curation-app/components/NewItemDialog.vue`, `frontend/src/curation-app/sections/TablesSection.vue:142-149`, `frontend/src/curation-app/sections/ReviewSection.vue:337`
- Test: `python/tests/test_curation_api.py`, `python/tests/test_curation_contract.py`, `frontend/tests/unit/curation-contract.spec.ts`, `frontend/tests/unit/curation-review.spec.ts:81-137`, `frontend/tests/unit/curation-grid.spec.ts:63-98`, `frontend/tests/components/curation-review-section.spec.ts`, `frontend/tests/components/curation-tables-section.spec.ts`
- Docs: `docs/local-curation.md` (Local API)

**Interfaces:**
- Consumes: `LoadedStudy.table(file)`, `LoadedTable.matching_lines(filters)`, `LoadedStudy.digitization(source)`, `source_kind(source)` (`sources.py`), `usePreview` (Task 2), `_bounded(folder)` in `studies.py`.
- Produces (Python): `SERIES_COLUMNS = {"timecourses": "label", "scatters": "name"}` in `digitize.py`; `DigitizedSeries(source: str, series: str)`, `TargetMatch(lines: tuple[int, ...] | None, series: DigitizedSeries | None)`, `match_target(study: LoadedStudy, target: ReviewTarget | None) -> TargetMatch` in `targets.py`; `study_detail(identity)["targets"]: dict[item_id, {"lines": list[int] | None, "series": {"source", "series"} | None}]` for every review item with a target file, empty beyond the upload limits; engine method `target_preview(identity: str, payload: dict) -> dict`; route `POST /local/studies/review/preview` with `{study, target}`; a POST that is beyond the upload limits answers `413`.
- Produces (TypeScript): `interface DigitizedSeries { source: string; series: string }`, `interface TargetMatch { lines: number[] | null; series: DigitizedSeries | null }`, `StudyDetail.targets: Record<string, TargetMatch>`, `isTargetMatch`; store `previewTarget(target: ReviewTarget): Promise<TargetMatch>`; in `grid.ts`: `targetMatch(targets, item): TargetMatch`, `targetLines(file: string, items: readonly ReviewItem[], targets: Readonly<Record<string, TargetMatch>>): Set<number>`, `itemsWithoutRows(file, items, targets): { whole: number; unmatched: number }`; in `review.ts`: `rowsAt(rows: readonly TableRow[], lines: readonly number[]): TableRow[]`; `TargetView` takes the prop `item: ReviewItem`.

- [ ] **Step 1: Write the failing library test**

`python/tests/studyformat/test_targets.py`:

```python
import json

from digitize_fixtures import GOOD, png, project

from pkdb.schemas.review import ReviewTarget
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.targets import DigitizedSeries, TargetMatch, match_target


def digitized(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
        }
    )
    assert format_folder(folder).ok
    return load_study(folder)


def test_a_row_filter_matches_the_lines_of_its_rows(valid_study):
    study = load_study(valid_study)
    table = study.table("timecourses_Fig1.tsv")
    assert table is not None
    expected = tuple(row.line for row in table.rows if row.cells["time"] == "1")
    target = ReviewTarget(file="timecourses_Fig1.tsv", rows={"label": "drug_plasma", "time": "1"})
    assert match_target(study, target).lines == expected
    nothing = ReviewTarget(file="timecourses_Fig1.tsv", rows={"label": "drug_feces"})
    assert match_target(study, nothing).lines == ()


def test_a_target_without_rows_or_of_another_file_has_no_lines(valid_study):
    study = load_study(valid_study)
    for target in (
        None,
        ReviewTarget(),
        ReviewTarget(file="timecourses_Fig1.tsv", column="mean"),
        ReviewTarget(file="study.json"),
    ):
        assert match_target(study, target) == TargetMatch(None, None)


def test_a_series_of_a_digitized_figure_is_named(make_study, valid_files):
    study = digitized(make_study, valid_files)
    series = ReviewTarget(file="timecourses_Fig1.tsv", rows={"label": "drug_plasma", "time": "1"})
    assert match_target(study, series).series == DigitizedSeries("Fig1", "drug_plasma")
    # Fig2 has no WebPlotDigitizer project, and a paper table no digitization at all.
    scatter = ReviewTarget(file="scatters_Fig2.tsv", rows={"name": "age_vs_cmax"})
    assert match_target(study, scatter).series is None
    table = ReviewTarget(file="outputs_Tab2.tsv", rows={"measurement": "cmax"})
    assert match_target(study, table).series is None
```

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_targets.py`
Expected: FAIL (`ModuleNotFoundError: pkdb.studyformat.targets`).

- [ ] **Step 2: Implement `match_target`**

`digitize.py`, before `mapped_points`:

```python
# The column that names the series of a timecourse or scatter row, as its dataset is named.
SERIES_COLUMNS = {"timecourses": "label", "scatters": "name"}
```

and in `mapped_points` read the label with `row.cells.get(SERIES_COLUMNS["timecourses"], "")` and the name with `row.cells.get(SERIES_COLUMNS["scatters"], "")`.

`python/src/pkdb/studyformat/targets.py`:

```python
"""What a review target selects in a loaded study: the lines of its rows and its digitized series."""

from dataclasses import dataclass

from pkdb.schemas.review import ReviewTarget
from pkdb.studyformat.digitize import SERIES_COLUMNS
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import source_kind


@dataclass(frozen=True)
class DigitizedSeries:
    """A series of a figure with a WebPlotDigitizer project: the figure and the series name."""

    source: str
    series: str


@dataclass(frozen=True)
class TargetMatch:
    """What a review target selects.

    `lines` are the TSV lines of the rows that its row filter matches in a data table, in file
    order; None for a target without a row filter or of a file that is no data table. `series` is
    the series that its filter names in a timecourse or scatter table of a figure with a
    WebPlotDigitizer project, else None.
    """

    lines: tuple[int, ...] | None
    series: DigitizedSeries | None


def match_target(study: LoadedStudy, target: ReviewTarget | None) -> TargetMatch:
    """The rows and the digitized series of a review target, as `pkdb review show` counts them."""
    if target is None or target.file is None:
        return TargetMatch(None, None)
    table = study.table(target.file)
    if table is None:
        return TargetMatch(None, None)
    lines = tuple(sorted(table.matching_lines(target.rows))) if target.rows else None
    column = SERIES_COLUMNS.get(table.kind)
    name = target.rows.get(column) if column else None
    series = None
    if (
        name
        and table.source is not None
        and source_kind(table.source) == "figure"
        and study.digitization(table.source) is not None
    ):
        series = DigitizedSeries(table.source, name)
    return TargetMatch(lines, series)
```

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_targets.py tests/studyformat/test_digitize.py tests/studyformat/test_digitize_checks.py`
Expected: PASS.

- [ ] **Step 3: Write the failing API tests**

`python/tests/test_curation_api.py`:

```python
def test_detail_and_preview_match_review_targets(api):
    server, engine, folder = api
    created = "2026-10-01T10:00:00Z"
    item = new_ulid()
    review = {
        "status": "draft",
        "items": [
            {
                "id": item,
                "kind": "question",
                "target": {"file": "timecourses_Fig1.tsv", "rows": {"label": "drug_plasma"}},
                "text": "Which dose?",
                "author": "curator",
                "created": created,
            }
        ],
    }
    (folder / "review.json").write_text(json.dumps(review))
    # The TSV line of each time point of the formatted table.
    lines = (folder / "timecourses_Fig1.tsv").read_text().splitlines()
    time = lines[0].split("\t").index("time")
    at = {row.split("\t")[time]: number for number, row in enumerate(lines[1:], start=2)}
    headers = authenticate(server)
    detail = _detail(server, headers)
    assert detail["targets"] == {
        item: {
            "lines": sorted(at.values()),
            "series": {"source": "Fig1", "series": "drug_plasma"},
        }
    }
    preview = "/local/studies/review/preview"
    body = {"study": "caffeine/Example", "target": {"file": "timecourses_Fig1.tsv", "rows": {"time": "1"}}}
    status, _, data = request(server, "POST", preview, body, headers)
    assert status == 200
    assert json.loads(data) == {"lines": [at["1"]], "series": None}
    status, _, data = request(server, "POST", preview, {**body, "target": {"rows": {"time": "1"}}}, headers)
    assert status == 422
    assert json.loads(data)["issues"][0]["code"] == "invalid_review_json"
```

In `test_upload_limits_bound_the_read_routes` add `detail["targets"] == {}` to the detail assertion and, after the loop:

```python
    body = {"study": "caffeine/Example", "target": {"file": "timecourses_Fig1.tsv", "rows": {"time": "1"}}}
    status, _, data = request(server, "POST", "/local/studies/review/preview", body, headers)
    assert status == 413 and "more than" in json.loads(data)["error"]
```

Run: `cd python && uv run --locked pytest -q tests/test_curation_api.py -k "match_review_targets or upload_limits"`
Expected: FAIL (`KeyError: 'targets'`, 404).

- [ ] **Step 4: Serve the matches and the preview**

`curation/studies.py` (import `match_target`): in `study_detail` set `targets = {}` beyond the limits, and in the `else` branch

```python
            targets = {
                item.id: dataclasses.asdict(match_target(study, item.target))
                for item in (study.review.items if study.review else ())
                if item.target is not None and item.target.file is not None
            }
```

and return `"targets": targets`. Add:

```python
    def target_preview(self, identity: str, payload: dict) -> dict:
        """The rows and the digitized series of a draft review target; writes nothing."""
        try:
            target = ReviewTarget.model_validate(payload.get("target"))
        except ValidationError as error:
            raise _review_error(
                validation_issues(error, REVIEW_JSON, review_edit.CODE)
            ) from None
        study = _bounded(self.study_folder(identity))
        return dataclasses.asdict(match_target(study, target))
```

`curation/server.py`: add `"/local/studies/review/preview"` to the study paths of `_action` with `if path == "/local/studies/review/preview": return engine.target_preview(study, body)`; in `do_POST` add, after the `AmbiguousStudy` clause and before `except ValueError, TypeError, OSError`:

```python
        except StudyValidationError as error:
            # The study is beyond the upload limits.
            self._reply(413, {"error": str(error)})
```

Run: `cd python && uv run --locked pytest -q tests/test_curation_api.py tests/test_curation_server.py`
Expected: PASS.

- [ ] **Step 5: Use the matches in the front end**

`api/types.ts`: the `DigitizedSeries` and `TargetMatch` interfaces of the Interfaces block, `targets: Record<string, TargetMatch>;` in `StudyDetail` (doc comment: "What the target of each review item with a file selects, by item id, as the library matches it; empty beyond the upload limits."), `"targets"` in `isStudyDetail`, and `export const isTargetMatch = hasKeys<TargetMatch>("lines", "series");`.

`stores/study.ts`:

```ts
  /** The rows and the digitized series that a draft review target selects; writes nothing. */
  function previewTarget(target: ReviewTarget): Promise<TargetMatch> {
    return postJson("/local/studies/review/preview", { study: opened(), target }, isTargetMatch);
  }
```

`review.ts`: delete `FIGURE_TABLE`, `SERIES_COLUMNS`, `seriesOfTarget` and `matchingRows`; add

```ts
/** The rows at `lines`, in their order in the table. */
export function rowsAt(rows: readonly TableRow[], lines: readonly number[]): TableRow[] {
  const wanted = new Set(lines);
  return rows.filter((row) => wanted.has(row.line));
}
```

`grid.ts`: delete `rowFilters`, the `matchingRows` import, and the old `targetLines` and `itemsWithoutRows`; add

```ts
const NOTHING: TargetMatch = { lines: null, series: null };

/** What the target of `item` selects, as the local server matched it; nothing for an item without a file. */
export function targetMatch(targets: Readonly<Record<string, TargetMatch>>, item: ReviewItem): TargetMatch {
  return targets[item.id] ?? NOTHING;
}

function openItemsOf(file: string, items: readonly ReviewItem[]): ReviewItem[] {
  return items.filter((item) => item.state === "open" && item.target?.file === file);
}

/** The lines of the rows of `file` that the row filters of its open review items match. */
export function targetLines(
  file: string,
  items: readonly ReviewItem[],
  targets: Readonly<Record<string, TargetMatch>>,
): Set<number> {
  return new Set(openItemsOf(file, items).flatMap((item) => targetMatch(targets, item).lines ?? []));
}

/**
 * The open review items about `file` that color no row: those without a row filter, such as all
 * items about a raw table, and those whose row filter matches no row.
 */
export function itemsWithoutRows(
  file: string,
  items: readonly ReviewItem[],
  targets: Readonly<Record<string, TargetMatch>>,
): { whole: number; unmatched: number } {
  let whole = 0;
  let unmatched = 0;
  for (const item of openItemsOf(file, items)) {
    const lines = targetMatch(targets, item).lines;
    if (lines === null) whole += 1;
    else if (lines.length === 0) unmatched += 1;
  }
  return { whole, unmatched };
}
```

`TablesSection.vue`: `targetLines(table.value.file, items, detail.value?.targets ?? {})` and `itemsWithoutRows(table.value.file, items, detail.value?.targets ?? {})`, with `items = detail.value?.review.value?.items ?? []`.

`ReviewSection.vue`: `<TargetView v-if="selected" :item="selected" />`.

`TargetView.vue`: `defineProps<{ item: ReviewItem }>()`; `target = computed(() => props.item.target)`; `match = computed(() => (study.detail ? targetMatch(study.detail.targets, props.item) : { lines: null, series: null }))`; `filtered = computed(() => match.value.lines !== null)`; `series = computed(() => match.value.series)`; in `rows` use `const matched = match.value.lines === null ? loaded.rows : rowsAt(loaded.rows, match.value.lines);` and keep the columns of `Object.keys(target.value?.rows ?? {})` and the item column.

`NewItemDialog.vue`: drop `matchingRows`; add

```ts
/** The draft target with its row filters, which the local server matches; null without filters. */
const draft = computed<ReviewTarget | null>(() =>
  file.value !== null && table.value !== null && Object.keys(rows.value).length
    ? { file: file.value, rows: rows.value }
    : null,
);
const preview = usePreview(() => draft.value, (target) => study.previewTarget(target));
const matches = computed(() => {
  const loaded = table.value;
  const lines = preview.data.value?.lines;
  if (!loaded || lines == null) return null;
  return { matched: lines.length, text: matchText(lines.length, loaded.rows.length) };
});
```

and let `canAdd` also require `!preview.loading.value`.

- [ ] **Step 6: Contract test and front-end tests**

`python/tests/test_curation_contract.py`:

```python
TARGET_DRAFTS = [
    {"file": "timecourses_Fig1.tsv", "rows": {"label": "caf_plasma_100mg", "time": "4"}},
    {"file": "timecourses_Fig1.tsv", "rows": {"label": "caf_plasma_200mg"}},
    {"file": "outputs_Tab2.tsv", "rows": {"measurement": "auc_inf", "comment": ""}},
    {"file": "outputs_Tab2.tsv", "rows": {"measurement": "AUC"}},
    {"file": "Demo2020_Tab2.tsv"},
]


def test_targets_contract(workspace, engine_on):
    engine = engine_on(workspace)
    detail = engine.study_detail(DEMO)
    previews = [
        {"request": draft, "response": engine.target_preview(DEMO, {"target": draft})}
        for draft in TARGET_DRAFTS
    ]
    check_contract(
        "targets",
        {
            "items": [
                {"id": item["id"], "state": item["state"], "target": item.get("target")}
                for item in detail["review"]["value"]["items"]
            ],
            "targets": detail["targets"],
            "previews": previews,
        },
    )
```

Run: `cd python && PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py && uv run --locked pytest -q tests/test_curation_contract.py`

`curation-contract.spec.ts`:

```ts
import type { ReviewItem, TargetMatch } from "../../src/curation-app/api/types";
import { itemsWithoutRows, targetLines, targetMatch } from "../../src/curation-app/grid";
import { matchText } from "../../src/curation-app/review";
import targetsFixture from "../fixtures/curation-contract/targets.json";
import { reviewItem } from "./curation-fixtures";

describe("targets contract", () => {
  const items = targetsFixture.items.map((entry) => reviewItem(contract<Partial<ReviewItem>>(entry)));
  const targets = contract<Record<string, TargetMatch>>(targetsFixture.targets);
  const about = (file: string) => items.find((item) => item.target?.file === file)!;

  it("colors the rows of open items only", () => {
    expect([...targetLines("interventions.tsv", items, targets)]).toEqual(targets[about("interventions.tsv").id]?.lines);
    // The item about subjects.tsv is resolved and the one about timecourses_Fig1.tsv dismissed.
    expect(targetLines("subjects.tsv", items, targets).size).toBe(0);
    expect(targetLines("timecourses_Fig1.tsv", items, targets).size).toBe(0);
    expect(itemsWithoutRows("outputs_Tab2.tsv", items, targets)).toEqual({ whole: 0, unmatched: 0 });
  });

  it("names the digitized series of a figure target", () => {
    expect(targetMatch(targets, about("timecourses_Fig1.tsv")).series).toEqual({ source: "Fig1", series: "caf_plasma_100mg" });
  });

  it("counts the rows of a draft target as the server matched them", () => {
    const [point, , , none, raw] = targetsFixture.previews.map((entry) => contract<TargetMatch>(entry.response));
    expect(matchText(point?.lines?.length ?? -1, 18)).toBe("Matches 1 of 18 rows.");
    expect(none?.lines).toEqual([]);
    expect(raw?.lines).toBeNull();
  });
});
```

Update `curation-review.spec.ts` (delete the `seriesOfTarget` and `matchingRows` tests, test `rowsAt`), `curation-grid.spec.ts` (the new signatures with a `targets` map), `curation-tables-section.spec.ts` and `curation-review-section.spec.ts` (details with `targets`; `mountSection` serves `"POST /local/studies/review/preview"` with a `Handler` that answers `{ lines: [], series: null }` for the value `caf_plasma_D75`, so that "Matches none of 3 rows." stays). Add the component test of Review Focus 3 to the `describe` of `curation-review-section.spec.ts` that holds "warns about a row filter that matches no row":

```ts
  it("shows only the count of the current row filter when an older answer comes late", async () => {
    let answerFirst: (response: Response) => void = () => undefined;
    const preview: Handler = (body) => {
      const target = body?.target as { rows?: Record<string, string> } | undefined;
      if (target?.rows?.label === "caf_plasma_D150")
        return new Promise<Response>((resolve) => (answerFirst = resolve));
      return json({ lines: [3], series: null });
    };
    const wrapper = await mountSection(withReview(), { "POST /local/studies/review/preview": preview });
    await click("New item");
    await labeled(wrapper, VSelect, "File").setValue("timecourses_Fig1.tsv");
    await flushPromises();
    await click("Add row filter");
    await labeled(wrapper, VSelect, "Column 1").setValue("label");
    await labeled(wrapper, VCombobox, "Value 1").setValue("caf_plasma_D150");
    await flushPromises();
    await labeled(wrapper, VCombobox, "Value 1").setValue("caf_plasma_D75");
    await flushPromises();
    answerFirst(json({ lines: [2, 3], series: null }));
    await flushPromises();
    expect(dialog().get(".new-item-matches").text()).toBe("Matches 1 of 3 rows.");
  });
```

- [ ] **Step 7: Document the route**

`docs/local-curation.md`, Local API: extend the item of Task 2 to "`POST /local/studies/tables/preview` and `POST /local/studies/review/preview` read without writing: what Add table would add for a kind and a source, and which rows and digitized series a draft review target selects. ..." and add to the study page item that the detail holds "the rows and the digitized series of each review target".

- [ ] **Step 8: Run every gate**

Run: `cd python && uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Run: `cd frontend && npm run test:source && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && npm run build:curation && npm run test:curation-e2e`
Run: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean`
Expected: all pass; `review.spec.ts` still sees "Matches 1 of 18 rows.".

- [ ] **Step 9: Commit**

```bash
git add python/src/pkdb/studyformat/targets.py python/src/pkdb/studyformat/digitize.py python/src/pkdb/curation/studies.py python/src/pkdb/curation/server.py python/tests frontend/src/curation-app frontend/tests docs/local-curation.md
git commit -m "Match review targets and their digitized series on the local server"
```

---

### Task 4: Error bar ends as part of their series

**Files:**
- Create: `frontend/tests/fixtures/curation-contract/source-fig1.json` (generated)
- Modify: `python/src/pkdb/studyformat/digitize.py:353`, `python/src/pkdb/studyformat/sources.py:75-95,268-300,385-400`, `python/src/pkdb/studyformat/plot.py:13,57-105`
- Modify: `frontend/src/curation-app/api/types.ts:552-566`, `frontend/src/curation-app/overlay.ts`
- Test: `python/tests/studyformat/test_sources.py`, `python/tests/studyformat/test_plot.py:71-94`, `python/tests/test_curation_contract.py`, `frontend/tests/unit/curation-contract.spec.ts`, `frontend/tests/unit/curation-overlay.spec.ts`, `frontend/tests/components/curation-source-overlay.spec.ts`, `frontend/tests/components/curation-sources-section.spec.ts`

**Interfaces:**
- Consumes: `ERROR_BAR_SUFFIX` (stays in `digitize.py`, the only place that knows it, with `_error_bars` of `sources.py` for the mapped rows).
- Produces (Python): `dataset_series(name: str) -> tuple[str, bool]` in `digitize.py`; `OverlayPoint.series` is the series of the point (a timecourse `label` or scatter `name`, never with `;error_bar`); `OverlayPoint.error_bar_end: bool = False` (last field) is true for a digitized end of an error bar; `PlotResult.colors` lists each drawn series once.
- Produces (TypeScript): `OverlayPoint.error_bar_end: boolean`; the overlay trace of digitized error bar ends has the meta `raw-bar <series>`; `DataRow.kind` gains `"Digitized error bar"`; `ERROR_BAR_SUFFIX` and `baseSeries` are gone.

- [ ] **Step 1: Write the failing Python tests**

`python/tests/studyformat/test_sources.py`:

```python
def test_error_bar_ends_belong_to_their_series(make_study, valid_files, tsv):
    wpd = project(GOOD)
    wpd["datasetColl"].append(
        {"name": "drug_plasma;error_bar", "axesName": "XY", "data": [{"x": 10, "y": 50}]}
    )
    folder = with_error_bars(
        make_study,
        valid_files,
        tsv,
        **{"Example_Fig1.png": png(100, 100), "Example_Fig1.wpd.json": json.dumps(wpd)},
    )
    view = source_view(load_study(folder), "Fig1")
    raw = [(p.series, p.error_bar_end) for p in view.overlay if p.role == "raw"]
    assert raw == [("drug_plasma", False)] * 3 + [("drug_plasma", True)]
    assert not any(p.error_bar_end for p in view.overlay if p.role == "mapped")
    assert [s.name for s in view.series] == ["drug_plasma", "drug_urine"]
```

`python/tests/studyformat/test_plot.py`, in `test_error_bar_dataset_shares_the_series_color_and_legend_entry`, replace `assert colors["drug_plasma;error_bar"] == colors["drug_plasma"]` by `assert list(colors) == ["drug_plasma"]`.

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_sources.py tests/studyformat/test_plot.py`
Expected: FAIL (`AttributeError: 'OverlayPoint' object has no attribute 'error_bar_end'`, the colors still list the error bar dataset).

- [ ] **Step 2: Implement the series of a dataset**

`digitize.py`, after `ERROR_BAR_SUFFIX`:

```python
def dataset_series(name: str) -> tuple[str, bool]:
    """The series of a dataset of a project, and whether the dataset holds the ends of its error bars."""
    return name.removesuffix(ERROR_BAR_SUFFIX), name.endswith(ERROR_BAR_SUFFIX)
```

`sources.py`: document the new field in the `OverlayPoint` docstring ("`series` is the timecourse label or scatter name of the point; `error_bar_end` marks a digitized end of an error bar, from the dataset `<series>;error_bar`.") and add `error_bar_end: bool = False` as its last field. In `_overlay`, for the raw points: `series, bar = dataset_series(dataset.name)` and build `OverlayPoint(series, "raw", px, py, x, y, digitization.file, None, None, _value_text(x), _value_text(y), bar)`. In `_series` use `*(p.series for p in overlay)`.

`plot.py`: drop the `ERROR_BAR_SUFFIX` import; `drawn = {p.series for p in view.overlay}`; draw a raw point with `bar = point.error_bar_end` and `color=base[point.series]`; mapped points and their error bars use `base[point.series]`; return `tuple(sorted((name, base[name]) for name in drawn))` as the colors.

Run: `cd python && uv run --locked pytest -q tests/studyformat`
Expected: PASS.

- [ ] **Step 3: Update the overlay of the app**

`api/types.ts`: add to `OverlayPoint` `/** A digitized end of an error bar, of the dataset `<series>;error_bar`. */ error_bar_end: boolean;` and say in the doc of `series` that it is the series of the point.

`overlay.ts`: delete `ERROR_BAR_SUFFIX` and `baseSeries`. `colorOf` and `opacities` use the series as it is. In `overlayTraces`, the error bar segments loop over all `series`; the markers loop over the groups `[["raw", false, "raw"], ["raw", true, "raw-bar"], ["mapped", false, "mapped"]] as const`, select the points by `point.role` and `point.error_bar_end`, and use the meta `` `${prefix} ${name}` ``; the hover text of a bar end names `` `${point.series} (error bar)` `` through `customdata`. `legendEntries` uses `unique(view.overlay.map((point) => point.series))`. `dataRows` gives a raw bar end the kind `"Digitized error bar"`; extend the `DataRow.kind` union.

Update `curation-overlay.spec.ts`: the point builder gets `error_bar_end: false`; the digitized error bar point is `point({ series: "drug_plasma", error_bar_end: true, role: "raw", px: 20, py: 40, x: 1, y: 6 })`; expect the meta `raw-bar drug_plasma` where `raw drug_plasma;error_bar` was; delete the `baseSeries` test; the data row of the bar end is `{ series: "drug_plasma", kind: "Digitized error bar", ... }`. Give the overlay points of `curation-source-overlay.spec.ts` and `curation-sources-section.spec.ts` the field `error_bar_end: false`.

- [ ] **Step 4: Contract test**

`python/tests/test_curation_contract.py`:

```python
def test_source_contract(workspace, engine_on):
    view = engine_on(workspace).study_source(DEMO, "Fig1")
    assert {(p["series"], p["error_bar_end"]) for p in view["overlay"] if p["role"] == "raw"} == {
        ("caf_plasma_100mg", False),
        ("caf_plasma_100mg", True),
        ("caf_plasma_200mg", False),
        ("caf_plasma_200mg", True),
    }
    check_contract("source-fig1", view)
```

Run: `cd python && PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py && uv run --locked pytest -q tests/test_curation_contract.py`

`curation-contract.spec.ts`:

```ts
import type { SourceView } from "../../src/curation-app/api/types";
import { legendEntries, overlayTraces } from "../../src/curation-app/overlay";
import sourceFixture from "../fixtures/curation-contract/source-fig1.json";

describe("source view contract", () => {
  const view = contract<SourceView>(sourceFixture);

  it("draws the digitized error bar ends in the color of their series", () => {
    const { traces } = overlayTraces(view);
    const trace = (meta: string) => traces.find((entry) => entry.meta === meta);
    for (const series of ["caf_plasma_100mg", "caf_plasma_200mg"]) {
      expect(trace(`raw ${series}`)).toBeDefined();
      expect(trace(`mapped ${series}`)).toBeDefined();
      expect(trace(`raw-bar ${series}`)?.marker?.color).toBe(trace(`raw ${series}`)?.marker?.color);
    }
  });

  it("lists each series once in the legend", () => {
    expect(legendEntries(view, "overlay", false).map((entry) => entry.series)).toEqual(["caf_plasma_100mg", "caf_plasma_200mg"]);
  });
});
```

- [ ] **Step 5: Run every gate**

Run: `cd python && uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Run: `cd frontend && npm run test:source && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && npm run build:curation && npm run test:curation-e2e`
Expected: all pass; `sources.spec.ts` still shows the row of a mapped point.

- [ ] **Step 6: Commit**

```bash
git add python/src/pkdb/studyformat/digitize.py python/src/pkdb/studyformat/sources.py python/src/pkdb/studyformat/plot.py python/tests frontend/src/curation-app frontend/tests
git commit -m "Send digitized error bar ends as part of their series"
```

---

### Task 5: Structured suggestions, field messages and write jobs

**Files:**
- Create: `frontend/tests/fixtures/curation-contract/messages.json` (generated)
- Modify: `python/src/pkdb/studyformat/issues.py:170-260`, `python/src/pkdb/studyformat/terms.py:239-249`, `python/src/pkdb/studyformat/load.py:413-458`, `python/src/pkdb/curation/studies.py:299-314,374-430,557-576`, `python/src/pkdb/curation/jobs.py:240-257,800-812`, `python/src/pkdb/curation/state.py:79-81`, `python/src/pkdb/curation/engine.py:97-115`
- Modify: `frontend/src/curation-app/api/types.ts`, `frontend/src/curation-app/problems.ts:100-130`, `frontend/src/curation-app/activity.ts:80-135`, `frontend/src/curation-app/metadata.ts:466-471`, `frontend/src/curation-app/sections/ActivitySection.vue:62`
- Test: `python/tests/studyformat/test_studyformat_terms.py`, `python/tests/studyformat/test_metadata_edit.py`, `python/tests/test_curation_api.py:1058-1140`, `python/tests/test_curation_engine.py:561-578`, `python/tests/test_curation_contract.py`, `frontend/tests/unit/curation-contract.spec.ts`, `frontend/tests/unit/curation-problems.spec.ts:120-150`, `frontend/tests/unit/curation-activity.spec.ts`, `frontend/tests/unit/curation-metadata.spec.ts:245-255`, `frontend/tests/components/curation-problems-section.spec.ts:45-60`

**Interfaces:**
- Consumes: `make_issue`, `validation_issues`, `_review_message(payload, result)`, `_record_write(identity, message, status)`.
- Produces (Python): suggestion kinds in `issues.py`: `FIX = "fix"` (a hint, with optional candidates), `CANDIDATES = "did_you_mean"` (candidates alone, message `DID_YOU_MEAN`), `VOCABULARY = "check_vocabulary"` (spelling suggestions of an unknown term with their caveat, as the domain layer already names them); `make_issue(..., suggestion: str | None = None)`; document issues from `validation_issues` carry `context={"detail": <message without the field>}`, and messages lose pydantic's `Value error, ` prefix; `_review_message(payload, result) -> tuple[str, str | None]` (message and item id); `_record_write(identity, message, status="succeeded", item=None)` stores `"item"`; `job_parts(job: dict) -> list[dict] | None`; detail jobs with an item carry `"parts": [{"text": str} | {"item": str}]`; `CANCELED_BEFORE_START = "Canceled before starting"` in `jobs.py`.
- Produces (TypeScript): `type JobMessagePart = { text: string } | { item: string }`; `Job.item?: string`, `Job.parts?: JobMessagePart[]`; `messageParts(job: Job, items: readonly ReviewItem[]): MessagePart[]`; `suggestionView` decides by `suggestion.kind`; `issueMessage(issue)` reads `issue.context.detail`; `DID_YOU_MEAN`, `SPELLING_HINT`, `REVIEW_ITEM` and `QUEUED_MESSAGE` are gone.

- [ ] **Step 1: Write the failing Python tests**

`python/tests/studyformat/test_studyformat_terms.py` (import `format_folder`, `validate_folder`, and `CANDIDATES`, `FIX`, `VOCABULARY`, `make_issue` from `pkdb.studyformat.issues`):

```python
def test_suggestions_name_their_kind():
    choices = make_issue("unknown_reference", "No row.", candidates=["all"])
    assert [(s.kind, s.candidates) for s in choices.suggestions] == [(CANDIDATES, ["all"])]
    hint = make_issue("unit_dimension", "No unit.", hint="Units of cmax.", candidates=["mg/l"])
    assert hint.suggestions[0].kind == FIX
    term = make_issue("unknown_tissue", "Unknown.", hint="Caveat.", candidates=["plasma"], suggestion=VOCABULARY)
    assert term.suggestions[0].kind == VOCABULARY


def test_an_unknown_term_suggests_spellings_of_the_vocabulary(make_study, valid_files, sf_vocabulary):
    outputs = valid_files["outputs_Tab2.tsv"].replace("plasma", "plasm")
    folder = make_study({**valid_files, "outputs_Tab2.tsv": outputs})
    assert format_folder(folder).ok
    [issue] = [i for i in validate_folder(folder, sf_vocabulary).issues if i.code == "unknown_tissue"]
    assert issue.suggestions[0].kind == VOCABULARY
```

`python/tests/studyformat/test_metadata_edit.py`:

```python
def test_issues_of_a_document_carry_their_message_without_the_field(valid_study):
    patch = {"creator": "Jane Doe", "reference": {"pmid": None}}
    with pytest.raises(MetadataError) as error:
        patch_metadata(valid_study, patch, None)
    found = {issue.field: (issue.message, issue.context) for issue in error.value.issues}
    assert found["creator"] == (
        "creator: A user name has no spaces.",
        {"detail": "A user name has no spaces."},
    )
    plain = "Give a pmid or a doi, or remove reference for a manual reference"
    assert found["reference"] == (f"reference: {plain}", {"detail": plain})
```

`python/tests/test_curation_api.py`, at the end of `test_app_writes_are_listed_in_the_activity` (after Task 2 its tables body is `{"action": "add", "kind": "raw", "source": "Tab3"}`):

```python
    by_message = {job["message"]: job for job in writes}
    assert by_message[f"Added review item {item}"]["item"] == item
    assert by_message[f"Added review item {item}"]["parts"] == [
        {"text": "Added "},
        {"item": item},
    ]
    assert by_message[f"Resolved review item {item}"]["parts"] == [
        {"text": "Resolved "},
        {"item": item},
    ]
    assert "item" not in by_message["Saved study.json"]
    assert "parts" not in by_message["Saved study.json"]
```

`python/tests/test_curation_engine.py`:

```python
def test_saved_jobs_of_part_c_keep_their_links_and_texts(workspace):
    engine, _ = workspace
    engine.jobs.extend(
        [
            job_entry("write", action="write", message="Added review item 01M2FC4AG038NKRKAYDXR834N3"),
            job_entry("queued", "canceled", message="Queued"),
        ]
    )
    engine.close()
    restarted = module.CurationEngine(engine.root, state_dir=engine.state_dir, offline=True, start=False)
    try:
        jobs = {job["id"]: job for job in restarted.study_detail("caffeine/Example")["jobs"]}
        assert jobs["write"]["parts"] == [
            {"text": "Added "},
            {"item": "01M2FC4AG038NKRKAYDXR834N3"},
        ]
        assert jobs["queued"]["message"] == "Canceled before starting"
    finally:
        restarted.close()
```

Run: `cd python && uv run --locked pytest -q tests/studyformat/test_studyformat_terms.py tests/studyformat/test_metadata_edit.py tests/test_curation_api.py tests/test_curation_engine.py -k "kind or without_the_field or activity or part_c"`
Expected: FAIL.

- [ ] **Step 2: Implement suggestion kinds and field messages**

`issues.py`, after `DID_YOU_MEAN`:

```python
# The kinds of the suggestion of an issue: a hint with optional candidates, such as lines to add;
# candidates alone, after DID_YOU_MEAN; and the spelling suggestions of an unknown vocabulary term,
# whose hint is a caveat, as the domain layer names them.
FIX = "fix"
CANDIDATES = "did_you_mean"
VOCABULARY = "check_vocabulary"
```

`make_issue` takes `suggestion: str | None = None` (document it: the kind of the suggestion, by default `FIX` with a hint and `CANDIDATES` without) and builds `Suggestion(kind=suggestion or (FIX if hint else CANDIDATES), ...)`. `terms.py:247`: pass `suggestion=VOCABULARY`.

`load.py`: `_plain_message` returns `detail["msg"].removeprefix("Value error, ")` at its end; `validation_issues` computes `plain = _plain_message(detail, file)` and passes `context={"detail": plain}` to `make_issue` with the message `f"{path or file}: {plain}"`.

- [ ] **Step 3: Implement the item of write jobs and the legacy migrations**

`curation/studies.py` (add `import re`):

```python
# How a write job names its review item, and how jobs saved before `item` existed name it.
_LEGACY_ITEM = re.compile(r"review item (\S+)")


def _item_reference(item: str) -> str:
    return f"review item {item}"


def _review_message(payload: dict, result: dict) -> tuple[str, str | None]:
    """A review action as the activity of the study lists it, and the review item it names."""
    item = result["item"]["id"] if "item" in result else payload.get("item")
    reference = _item_reference(item) if item else ""
    match payload["action"]:
        case "add":
            message = f"Added {reference}"
        case "reply":
            message = f"Replied to {reference}"
        case "status":
            return f"Set the review status to {payload['status']}", None
        case "acknowledge":
            message = f"Acknowledged warning {payload['code']} with {reference}"
        case action:
            done = {"resolve": "Resolved", "dismiss": "Dismissed", "reopen": "Reopened"}
            message = f"{done[action]} {reference}"
    return message, item


def job_parts(job: dict) -> list[dict] | None:
    """The text of a write job split around the review item it names, for a link in the activity.

    Jobs saved before writes recorded `item` name the item only in their message.
    """
    message = job.get("message", "")
    item = job.get("item")
    if item is None and job.get("action") == "write":
        found = _LEGACY_ITEM.search(message)
        item = found.group(1) if found else None
    if item is None:
        return None
    before, reference, after = message.partition(_item_reference(item))
    if not reference:
        return None
    return [
        *([{"text": before}] if before else []),
        {"item": item},
        *([{"text": after}] if after else []),
    ]
```

`review_action` records `message, item = _review_message(payload, result)` with `self._record_write(identity, message, item=item)`. `study_detail` adds parts after the detail copy: `for job in detail["jobs"]: if (parts := job_parts(job)) is not None: job["parts"] = parts`.

`jobs.py`: `CANCELED_BEFORE_START = "Canceled before starting"`, used in `cancel_jobs`; `_record_write(self, identity, message, status="succeeded", item=None)` adds `**({"item": item} if item else {})` to the job. `state.py`: the protocol of `_record_write` gains `item: str | None = None`.

`engine.py` (import `CANCELED_BEFORE_START` from `pkdb.curation.jobs`), in the loop over saved jobs:

```python
            elif job.get("status") == "canceled" and job.get("message") == "Queued":
                # Saved by earlier versions, which kept the message of a queued job when canceling it.
                job["message"] = CANCELED_BEFORE_START
```

Run: `cd python && uv run --locked pytest -q`
Expected: PASS. Run the backend suite of the Global Constraints, because validation messages of `study.json` change in server reports: `uv run --project backend pytest backend/tests -q -x`. Expected: PASS (update any backend assertion that names `Value error, `).

- [ ] **Step 4: Use the structured data in the front end**

`api/types.ts`: `export type JobMessagePart = { text: string } | { item: string };` and on `Job`: `/** The review item that a write of the app named. */ item?: string;` and `/** The message split around the review item it names, from the server. */ parts?: JobMessagePart[];`.

`problems.ts`: delete `DID_YOU_MEAN` and `SPELLING_HINT`;

```ts
export function suggestionView(suggestion: Suggestion): SuggestionView {
  const candidates = (suggestion.candidates ?? []).map(candidateText);
  if (suggestion.kind === "did_you_mean") return { lead: "Did you mean:", candidates, note: null };
  if (suggestion.kind === "check_vocabulary" && candidates.length)
    return { lead: "Did you mean:", candidates, note: suggestion.message };
  return { lead: suggestion.message, candidates, note: null };
}
```

`activity.ts`: delete `QUEUED_MESSAGE` (and its branch in `jobText`) and `REVIEW_ITEM`;

```ts
/**
 * The text of a job with readable references to the review items that it names: the kind of the
 * item and the start of its text, instead of its id. An item that no longer exists is "a review
 * item". The server splits the message around the item.
 */
export function messageParts(job: Job, items: readonly ReviewItem[]): MessagePart[] {
  if (!job.parts) return [{ text: jobText(job) }];
  const parts: MessagePart[] = [];
  let text = "";
  for (const part of job.parts) {
    if ("text" in part) {
      text += part.text;
      continue;
    }
    const item = items.find((candidate) => candidate.id === part.item);
    if (!item) {
      text += "a review item";
      continue;
    }
    parts.push({ text: `${text}the ` });
    parts.push({ text: `${KIND_LABELS[item.kind].toLowerCase()} “${quote(item.text)}”`, item: item.id });
    text = "";
  }
  if (text) parts.push({ text });
  return parts;
}
```

`ActivitySection.vue`: `parts: messageParts(job, detail.value?.review.value?.items ?? [])`.

`metadata.ts`:

```ts
/** The message of an issue without its field, as the library gives it in `context.detail`. */
export function issueMessage(issue: ValidationIssue): string {
  const detail = issue.context?.detail;
  return typeof detail === "string" ? detail : issue.message;
}
```

Update `curation-problems.spec.ts` (kinds instead of messages), `curation-problems-section.spec.ts` (suggestions with `kind: "did_you_mean"`), `curation-activity.spec.ts` (jobs with `parts`; delete the test of the `Queued` branch, which the engine test now covers) and `curation-metadata.spec.ts` (issues with `context.detail`).

- [ ] **Step 5: Contract test**

`python/tests/test_curation_contract.py` (import `pkdb.studyformat.review_edit as review_edit`, `MetadataError`, `make_issue`, `validate_folder`):

```python
ITEM = "01M3A00000000000000000000Z"
QUESTION = "Is the 4 h point read from the figure?"


def test_messages_contract(workspace, engine_on, monkeypatch):
    folder = workspace / DEMO
    vocabulary = bundled_vocabulary()
    _replace(folder / "timecourses_Fig1.tsv", "\tFig1\tcaf_plasma_100mg\tall\t", "\tFig1\tcaf_plasma_100mg\tal\t")
    term = next(
        issue
        for issue in validate_folder(workspace / "caffeine/Draft2021", vocabulary).issues
        if issue.code == "unknown_substance"
    )
    name = next(
        issue for issue in validate_folder(folder, vocabulary).issues if issue.code == "unknown_reference"
    )
    hint = make_issue(
        "unit_dimension",
        "mg cannot be converted to a unit of concentration",
        file="outputs_Tab2.tsv",
        line=2,
        header="unit",
        hint="Units of concentration; amounts of a substance convert with its molar mass.",
        candidates=["mg/l", "g/l"],
    )
    saved = {
        "jobs": [
            {
                "id": "legacy-write",
                "study_id": DEMO,
                "study_name": "Demo2020",
                "action": "write",
                "status": "succeeded",
                "created_at": "2026-10-01T10:00:00+00:00",
                "message": "Added review item 01M2FC4AG038NKRKAYDXR834N3",
                "automatic": False,
                "report_id": None,
            },
            {
                "id": "legacy-canceled",
                "study_id": DEMO,
                "study_name": "Demo2020",
                "action": "validate",
                "status": "canceled",
                "created_at": "2026-10-01T09:00:00+00:00",
                "message": "Queued",
                "automatic": True,
                "report_id": None,
            },
        ]
    }
    engine = engine_on(workspace, saved)
    monkeypatch.setattr(review_edit, "new_ulid", lambda: ITEM)
    detail = engine.study_detail(DEMO)
    engine.review_action(
        DEMO,
        {"action": "add", "revision": detail["review"]["revision"], "kind": "question", "text": QUESTION},
    )
    metadata = {**detail["metadata"]["value"], "creator": "demo curator", "reference": {}}
    with pytest.raises(MetadataError) as refused:
        engine.write_metadata(DEMO, detail["metadata"]["revision"], metadata)
    detail = engine.study_detail(DEMO)
    check_contract(
        "messages",
        {
            "suggestions": [issue.suggestions[0].model_dump(mode="json") for issue in (term, name, hint)],
            "items": [
                {"id": item["id"], "kind": item["kind"], "text": item["text"]}
                for item in detail["review"]["value"]["items"]
            ],
            "jobs": [
                {key: job[key] for key in ("action", "status", "message", "item", "parts") if key in job}
                for job in detail["jobs"]
            ],
            "metadata_issues": [issue.model_dump(mode="json") for issue in refused.value.issues],
        },
    )
```

Run: `cd python && PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py && uv run --locked pytest -q tests/test_curation_contract.py`

`curation-contract.spec.ts`:

```ts
import type { Job, Suggestion, ValidationIssue } from "../../src/curation-app/api/types";
import { jobText, messageParts } from "../../src/curation-app/activity";
import { issueMessage } from "../../src/curation-app/metadata";
import { suggestionView } from "../../src/curation-app/problems";
import messagesFixture from "../fixtures/curation-contract/messages.json";

describe("messages contract", () => {
  const ITEM = "01M3A00000000000000000000Z";
  const QUESTION = "Is the 4 h point read from the figure?";

  it("shows each kind of suggestion", () => {
    const [term, name, hint] = contract<Suggestion[]>(messagesFixture.suggestions);
    expect(suggestionView(term!)).toEqual({ lead: "Did you mean:", candidates: expect.any(Array), note: term!.message });
    expect(suggestionView(name!)).toEqual({ lead: "Did you mean:", candidates: ["all"], note: null });
    expect(suggestionView(hint!).lead).toBe(hint!.message);
  });

  it("links the review item of a change in the app, also in a job saved by part C", () => {
    const items = messagesFixture.items.map((entry) => reviewItem(contract<Partial<ReviewItem>>(entry)));
    const jobs = contract<Job[]>(messagesFixture.jobs);
    const added = jobs.find((job) => job.item === ITEM)!;
    expect(messageParts(added, items)).toEqual([{ text: "Added the " }, { text: `question “${QUESTION}”`, item: ITEM }]);
    const legacy = jobs.find((job) => job.message.endsWith("01M2FC4AG038NKRKAYDXR834N3"))!;
    expect(messageParts(legacy, items)[1]?.item).toBe("01M2FC4AG038NKRKAYDXR834N3");
    expect(jobText(jobs.find((job) => job.status === "canceled")!)).toBe("Canceled before starting");
  });

  it("shows the message of a field without the field", () => {
    for (const issue of contract<ValidationIssue[]>(messagesFixture.metadata_issues)) {
      const text = issueMessage(issue);
      expect(text).not.toBe("");
      expect(text.startsWith(`${issue.field}:`)).toBe(false);
      expect(text.startsWith("Value error")).toBe(false);
    }
  });
});
```

- [ ] **Step 6: Run every gate**

Run: `cd python && uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Run: `cd frontend && npm run test:source && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && npm run build:curation && npm run test:curation-e2e`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add python/src/pkdb/studyformat/issues.py python/src/pkdb/studyformat/terms.py python/src/pkdb/studyformat/load.py python/src/pkdb/curation python/tests frontend/src/curation-app frontend/tests
git commit -m "Send suggestion kinds, field messages and the review item of each write from the local server"
```

---

### Task 6: Exact acknowledgements

**Files:**
- Create: `frontend/tests/curation-e2e/acknowledge.spec.ts`, `frontend/tests/fixtures/curation-contract/acknowledgements.json` (generated)
- Modify: `python/src/pkdb/schemas/source.py:16-90`, `python/src/pkdb/schemas/review.py:24-41`, `python/src/pkdb/studyformat/issues.py:198-260`, `python/src/pkdb/studyformat/digitize.py:490-540`, `python/src/pkdb/studyformat/relations.py:500-540`, `python/src/pkdb/studyformat/review_edit.py:51-56,328-408`, `python/src/pkdb/studyformat/validation.py:116-168`, `python/src/pkdb/study_cli.py:100-145,460-475,486-610`, `python/src/pkdb/curation/studies.py:209-224,280-284,637-673`, `python/src/pkdb/studyformat/export.py:142-144`
- Modify: `frontend/src/curation-app/api/types.ts`, `frontend/src/curation-app/problems.ts:84-200,225-230`, `frontend/src/curation-app/review.ts:90-97`, `frontend/src/curation-app/study.ts` (delete `dataTableFiles`), `frontend/src/curation-app/components/AcknowledgeDialog.vue`, `frontend/src/curation-app/sections/ProblemsSection.vue:181-192,362-385`
- Test: `python/tests/studyformat/test_studyformat_models.py`, `python/tests/studyformat/test_review_edit.py:300-400`, `python/tests/studyformat/test_digitize_checks.py`, `python/tests/studyformat/test_studyformat_relations.py:441`, `python/tests/studyformat/test_study_cli.py:265-288`, `python/tests/test_curation_api.py:795-850`, `python/tests/test_curation_contract.py`, `frontend/tests/unit/curation-contract.spec.ts`, `frontend/tests/unit/curation-problems.spec.ts`, `frontend/tests/components/curation-problems-section.spec.ts`
- Docs: `docs/local-curation.md:134`, `docs/python-client.md:203,209`, `docs/study-format.md` (regenerated), `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (section 7), `docs/superpowers/specs/2026-10-06-curation-app-design.md` (sections 5 and 7.3), `release-notes/unreleased.md`

**Interfaces:**
- Consumes: `ReviewItem`, `Review`, `acknowledged()`, `acknowledgements(study)`, `target_for_issue`, `_acknowledge`, `_acknowledged`, the contract helpers (Task 1).
- Produces (Python): `SourceLocation.key: str | None = None` and `ReviewTarget.key: str | None = None` (min length 1), both omitted from dumps when None; `make_issue(..., key: str | None = None)`; keys on `unknown_dataset` and file-level `digitized_mismatch` (the dataset name) and on `review_target_unmatched` (the item id); `NoExactTarget(ReviewError)` with `code = "no_exact_target"`; `target_for_issue(study, issue) -> ReviewTarget` (never None, raises `NoExactTarget`); `matching_warnings(issues, code, file, line=ANY, column=ANY, key=ANY)`; `warning_locations(issues) -> set[tuple[int | None, str | None, str | None]]`; `Acknowledgement.key: str | None = None`; `AcknowledgementScope = Literal["study", "file", "column", "rows", "key"]` and `acknowledgement_scope(target: ReviewTarget | None) -> AcknowledgementScope`; the `acknowledge` action takes `key` (null matches only warnings without one, left out matches any); `study_detail["acknowledged"][*]["scope"]`; `pkdb review acknowledge --key` and `pkdb review add --key`.
- Produces (TypeScript): `SourceLocation.key?: string`, `ReviewTarget.key?: string`, `AcknowledgedWarning.scope: "study" | "file" | "column" | "rows" | "key"`; `Acknowledgement.key: string | null`; `scopeText(entry: AcknowledgedWarning): string | null` in `problems.ts`; `fileWideScope` and `dataTableFiles` are gone.

- [ ] **Step 1: Write the failing schema and library tests**

`python/tests/studyformat/test_studyformat_models.py` (import `ReviewTarget` and `make_issue`):

```python
def test_a_key_needs_a_file_and_excludes_rows_and_column():
    with pytest.raises(ValidationError, match="key requires file"):
        ReviewTarget(key="legend")
    with pytest.raises(ValidationError, match="key excludes rows and column"):
        ReviewTarget(file="Example_Fig1.wpd.json", key="legend", column="x")
    # A target without a key serializes as before.
    assert ReviewTarget(file="a.tsv").model_dump(mode="json") == {"file": "a.tsv", "rows": {}, "column": None}
    keyed = ReviewTarget(file="Example_Fig1.wpd.json", key="legend")
    assert keyed.model_dump(mode="json")["key"] == "legend"


def test_a_source_without_a_key_serializes_as_before():
    plain = make_issue("unknown_dataset", "A.", file="Example_Fig1.wpd.json").source
    keyed = make_issue("unknown_dataset", "A.", file="Example_Fig1.wpd.json", key="legend").source
    assert plain is not None and keyed is not None
    assert "key" not in plain.model_dump(mode="json")
    assert keyed.model_dump(mode="json")["key"] == "legend"
    assert "key" not in keyed.legacy_dict()
```

`python/tests/studyformat/test_review_edit.py`: import `json`, `format_folder`, `GOOD`, `png`, `project` (from `digitize_fixtures`), `NoExactTarget`, `acknowledgement_scope`. Delete `test_a_warning_off_a_data_table_row_is_acknowledged_in_its_whole_file` and add:

```python
def two_datasets(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(project(GOOD, extra=("legend", "axis labels"))),
        }
    )
    assert format_folder(folder).ok
    return folder


def test_a_warning_of_a_whole_file_is_acknowledged_by_its_key(valid_study):
    issue = make_issue("unknown_dataset", "A.", file="Example_Fig1.wpd.json", key="legend")
    target = target_for_issue(load_study(valid_study), issue)
    assert target == ReviewTarget(file="Example_Fig1.wpd.json", key="legend")


@pytest.mark.parametrize(
    "location",
    [
        {"file": "Example_Fig1.wpd.json"},
        {"file": "Example.xlsx", "line": 4},
        {"file": "Example_Tab2.tsv", "line": 3},
        {"file": "timecourses_Fig1.tsv", "line": 1, "header": "mean"},
    ],
)
def test_a_warning_without_a_row_or_a_key_is_not_acknowledged_alone(valid_study, location):
    issue = make_issue("unknown_dataset", "A.", **location)
    with pytest.raises(NoExactTarget, match="cannot be acknowledged alone"):
        target_for_issue(load_study(valid_study), issue)


def test_a_key_covers_its_warning_and_a_file_target_every_one():
    figure = "Example_Fig1.wpd.json"
    legend, labels = (
        make_issue("unknown_dataset", f"{name}.", file=figure, key=name)
        for name in ("legend", "axis labels")
    )
    exact = {"unknown_dataset": [Acknowledgement(file=figure, key="legend")]}
    assert acknowledged(legend, exact) and not acknowledged(labels, exact)
    # A target of the file alone, as review.json files written before keys hold it.
    whole = {"unknown_dataset": [Acknowledgement(file=figure)]}
    assert acknowledged(legend, whole) and acknowledged(labels, whole)


def test_acknowledging_one_dataset_keeps_the_warning_of_another(make_study, valid_files, sf_vocabulary):
    folder = two_datasets(make_study, valid_files)
    legend = next(
        issue
        for issue in validate_folder(folder, sf_vocabulary).issues
        if issue.code == "unknown_dataset" and issue.source and issue.source.key == "legend"
    )
    item, _ = acknowledge(folder, PERSON, legend, "The legend is no series.", now=NOW)
    assert item.target == ReviewTarget(file="Example_Fig1.wpd.json", key="legend")
    keys = [
        issue.source.key
        for issue in validate_folder(folder, sf_vocabulary).issues
        if issue.code == "unknown_dataset" and issue.source
    ]
    assert keys == ["axis labels"]


@pytest.mark.parametrize(
    ("target", "scope"),
    [
        (None, "study"),
        (ReviewTarget(), "study"),
        (ReviewTarget(file="Example_Fig1.wpd.json"), "file"),
        (ReviewTarget(file="timecourses_Fig1.tsv", column="mean"), "column"),
        (ReviewTarget(file="timecourses_Fig1.tsv", rows={"time": "1"}), "rows"),
        (ReviewTarget(file="Example_Fig1.wpd.json", key="legend"), "key"),
    ],
)
def test_the_scope_of_an_acknowledgement(target, scope):
    assert acknowledgement_scope(target) == scope
```

Update `test_matching_warnings_and_their_locations`: the two project warnings get the keys `"legend"` and `"axis labels"`, `warning_locations(matches) == {(3, "mean", None), (3, "sd", None), (4, "mean", None)}` and `warning_locations(file_level) == {(None, None, "legend"), (None, None, "axis labels")}`; add `matching_warnings(issues, "unknown_dataset", "Example_Fig1.wpd.json", key="legend") == [project[0]]`.

`python/tests/studyformat/test_digitize_checks.py`:

```python
def test_file_level_digitization_warnings_carry_their_dataset_as_key(make_study, valid_files, sf_vocabulary):
    folder = study_with(make_study, valid_files, project([*GOOD, (30, 50)], extra=("legend",)))
    keys = {
        (issue.code, issue.source.key)
        for issue in validate_folder(folder, sf_vocabulary).issues
        if issue.source and issue.source.file == "Example_Fig1.wpd.json"
        and issue.code in {"unknown_dataset", "digitized_mismatch"}
    }
    assert keys == {("unknown_dataset", "legend"), ("digitized_mismatch", "drug_plasma")}
```

`python/tests/studyformat/test_studyformat_relations.py`, in the test at line 441 that reports `review_target_unmatched`: assert `issue.source.key == <the item id>`; add a test that a target `{"file": "timecourses_Fig1.tsv", "key": "x"}` in `review.json` is `unknown_review_target` with the message "Review item <id> targets the key x of timecourses_Fig1.tsv; a key names a part of a file without rows".

`python/tests/studyformat/test_study_cli.py`, rewrite `test_review_acknowledge_file_warnings_that_share_a_code`: without `--key` the command exits 1 and stderr says `2 warnings [unknown_dataset] match in Example_Fig1.wpd.json; narrow them with --key (axis labels, legend)`; with `--key legend` it exits 0, the item target is `ReviewTarget(file="Example_Fig1.wpd.json", key="legend")`, and the next validation still reports `unknown_dataset` for `axis labels`.

Run: `cd python && uv run --locked pytest -q tests/studyformat`
Expected: FAIL.

- [ ] **Step 2: Implement the keys and the exact targets**

`schemas/source.py`: add `key: str | None = None` after `header` (doc comment: "A name that identifies the place of an issue in a file without rows: the dataset of a WebPlotDigitizer project or the review item of `review.json`."); the serializer pops `"key"` like `cell` and `header` when None; `legacy_dict` excludes `{"cell", "header", "key"}`.

`schemas/review.py` (import `model_serializer` from `pydantic`):

```python
class ReviewTarget(Model):
    """What a review item refers to: a file, optionally narrowed to rows and a column, or to a key.

    `rows` and `column` narrow a table. `key` names a part of a file without rows: the dataset of
    a WebPlotDigitizer project, or a review item of review.json. Each requires `file`, and `key`
    excludes `rows` and `column`.
    """

    file: str | None = None
    rows: dict[str, str] = Field(default_factory=dict)
    column: str | None = None
    key: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def file_required(self):
        if (self.rows or self.column) and self.file is None:
            raise ValueError("rows and column require file")
        if self.key is not None:
            if self.file is None:
                raise ValueError("key requires file")
            if self.rows or self.column:
                raise ValueError("key excludes rows and column")
        return self

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        # A target without a key serializes as before keys existed, also in the backend.
        result = handler(self)
        if result.get("key") is None:
            result.pop("key", None)
        return result
```

`issues.py`: `make_issue(..., key: str | None = None)` passes `key=key` to `SourceLocation`; document it.

`digitize.py`: `key=dataset.name` on `unknown_dataset` and on the file-level `digitized_mismatch`.

`relations.py`, `_review_rules`: `key=item.id` on `review_target_unmatched`; after `table` is known to be loaded and before the unknown columns check:

```python
        if target.key is not None:
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets the key {target.key} of {target.file}; "
                "a key names a part of a file without rows",
                file=REVIEW_JSON,
                key=item.id,
            )
            continue
```

`validation.py` (import `Literal` from `typing` and `ReviewTarget` from `pkdb.schemas.review`): `Acknowledgement` gains `key: str | None = None` (docstring: a key reaches exactly the warning with that key; a file without rows, column and key reaches every warning of the code in the file); `acknowledgements` passes `target.key`; in `acknowledged`, after the file comparison:

```python
        if target.key is not None:
            if source.key == target.key:
                return True
            continue
```

and add:

```python
AcknowledgementScope = Literal["study", "file", "column", "rows", "key"]


def acknowledgement_scope(target: ReviewTarget | None) -> AcknowledgementScope:
    """What an acknowledgement with this target covers, as `acknowledged` matches it.

    `study`: every warning of the code; `file`: every warning of the code in the file, also later
    ones; `column`: every warning of the code in that column of the file; `rows`: the warnings at
    the rows that the filter matches, in the column when it names one; `key`: the warning that
    has the key.
    """
    if target is None or target.file is None:
        return "study"
    if target.key is not None:
        return "key"
    if target.rows:
        return "rows"
    return "column" if target.column else "file"
```

`review_edit.py`:

```python
class NoExactTarget(ReviewError):
    """A warning without a row of a data table and without a key; a target of its file would cover every warning of its code."""

    code = "no_exact_target"
```

`target_for_issue` returns `ReviewTarget` and raises instead of returning the target of the file:

```python
    source = issue.source
    if source is None:
        raise NoExactTarget(
            f"The warning [{issue.code}] has no file, so it cannot be acknowledged alone"
        )
    table = study.table(source.file)
    row = None
    if table is not None and source.row is not None:
        row = next((row for row in table.rows if row.line == source.row), None)
    if table is None or row is None:
        if source.key is not None:
            return ReviewTarget(file=source.file, key=source.key)
        raise NoExactTarget(
            f"The warning [{issue.code}] in {source.file} has no row of a data table and no "
            "key, so it cannot be acknowledged alone. To acknowledge every "
            f"[{issue.code}] warning of {source.file}, add a review item with "
            f"--acknowledges {issue.code} --file {source.file}"
        )
```

(the rest of the function is unchanged; update its docstring). `matching_warnings` gains `key: str | None | Wildcard = ANY` with `and (key is ANY or issue.source.key == key)`; `warning_locations` returns `(source.row, source.header, source.key)`.

`study_cli.py`: `pkdb review add --key KEY` ("Name a part of the file without rows, such as a dataset of a WebPlotDigitizer project"), included in `ReviewTarget(file=args.file, rows=rows, column=args.column, key=args.key)` and in the condition that builds a target; the `ValueError` becomes `ReviewError("--rows, --column and --key require --file, and --key excludes --rows and --column")`. `pkdb review acknowledge --key`, passed as `ANY if args.key is None else args.key`; `_narrowing` handles the third element (`--key (axis labels, legend)`); `_target_text` appends `f" key {target['key']}"`.

- [ ] **Step 3: Run the library tests to verify they pass**

Run: `cd python && uv run --locked pytest -q tests/studyformat`
Expected: PASS.

- [ ] **Step 4: Write the failing API test and serve the key and the scope**

`python/tests/test_curation_api.py` (import `format_folder` is there; import `GOOD`, `project`):

```python
def test_acknowledge_one_dataset_by_its_key(api, sf_vocabulary, monkeypatch):
    server, engine, folder = api
    monkeypatch.setattr(engine, "_local_vocabulary", lambda: sf_vocabulary)
    (folder / "Example_Fig1.wpd.json").write_text(json.dumps(project(GOOD, extra=("legend", "axis labels"))))
    assert format_folder(folder).ok
    headers = authenticate(server)
    body = {
        "study": "caffeine/Example",
        "revision": _detail(server, headers)["review"]["revision"],
        "action": "acknowledge",
        "code": "unknown_dataset",
        "file": "Example_Fig1.wpd.json",
        "line": None,
        "column": None,
        "text": "Not data.",
    }
    status, _, data = request(server, "POST", "/local/studies/review", body, headers)
    assert status == 422
    assert json.loads(data)["error"] == (
        "2 warnings [unknown_dataset] match in Example_Fig1.wpd.json at key axis labels, "
        "key legend; give the line, column and key of one"
    )
    status, _, data = request(server, "POST", "/local/studies/review", {**body, "key": "legend"}, headers)
    assert status == 200
    target = json.loads(data)["item"]["target"]
    assert (target["file"], target["key"], "column" in target) == ("Example_Fig1.wpd.json", "legend", False)
    [entry] = _detail(server, headers)["acknowledged"]
    assert entry["scope"] == "key"
```

In `test_acknowledged_warnings_are_listed_until_dismissed` add `"scope": "rows"` to the expected entry, and in `test_acknowledge_one_warning` change the expected error to end with `give the line, column and key of one`.

`curation/studies.py`: `_located(line, column, key)` adds `f"key {key}"`; `_acknowledge` passes `_optional_text(payload, "key") if "key" in payload else ANY` and sorts the locations by `(at[0] or 0, at[1] or "", at[2] or "")`, with the message `...; give the line, column and key of one`; its docstring says that `key` works like `line` and `column`. `_acknowledged` adds:

```python
            "scope": acknowledgement_scope(
                ReviewTarget.model_validate(item["target"]) if item.get("target") else None
            ),
```

Run: `cd python && uv run --locked pytest -q`
Expected: PASS. Then the backend suite of the Global Constraints (`SourceLocation` and `ReviewTarget` are shared): `uv run --project backend pytest backend/tests -q -x`. Expected: PASS without changes, because unset keys are not serialized.

- [ ] **Step 5: Exact acknowledgements in the app**

`api/types.ts`: `key?: string` on `SourceLocation` and `ReviewTarget`; `scope: "study" | "file" | "column" | "rows" | "key";` on `AcknowledgedWarning`.

`problems.ts`: delete `fileWideScope` and its doc; `Acknowledgement` gains `key: string | null`; `acknowledgement(issue)` returns `{ code, file, line: source.row ?? null, column: source.header ?? null, key: source.key ?? null }`; `locationKey` adds `source?.key ?? null` to its array; `location()` appends `source.key` after the header when set; add:

```ts
/** What an acknowledgement covers beyond its own warning, or null when it covers just that one. */
export function scopeText(entry: AcknowledgedWarning): string | null {
  const file = entry.target?.file;
  switch (entry.scope) {
    case "study":
      return `Covers every ${entry.code} warning of the study, also later ones.`;
    case "file":
      return `Covers every ${entry.code} warning in ${file}, also later ones.`;
    case "column":
      return `Covers every ${entry.code} warning in column ${entry.target?.column} of ${file}, also later ones.`;
    default:
      return null;
  }
}
```

`review.ts`, `targetText`: add `target.key ?? ""` as the last part, so a keyed target reads `Demo2020_Fig1.wpd.json · legend`.

`study.ts`: delete `dataTableFiles`.

`AcknowledgeDialog.vue`: delete `covered`, `LISTED`, `coveredLines`, the scope alert and its styles, and the imports of `fileWideScope`, `dataTableFiles` and `plural`.

`ProblemsSection.vue`: `acknowledgedWarning(issue)` marks `locationKey(issue)` when the report still lists it and announces `` `Warning ${issue.code} acknowledged.` ``; drop the `dataTableFiles` and `fileWideScope` imports. In the acknowledged list, after the target line: `<p v-if="scopeText(entry)" class="problem-fact acknowledged-scope">{{ scopeText(entry) }}</p>`.

Update `curation-problems.spec.ts` (delete the `fileWideScope` and `dataTableFiles` tests; test `acknowledgement` with a key, `locationKey` of two keys, `scopeText` of each scope) and `curation-problems-section.spec.ts` (delete the scope alert tests; the payload of a keyed warning has its `key`; only the acknowledged warning is marked; an acknowledged entry with `scope: "file"` shows "Covers every digitized_mismatch warning in timecourses_Fig1.tsv, also later ones." and one with `scope: "rows"` shows no scope).

- [ ] **Step 6: Contract test**

`python/tests/test_curation_contract.py` (import `format_folder`):

```python
ACKNOWLEDGED = "01M3B00000000000000000000Z"
LEGACY = "01M2S000000000000000000000"


def test_acknowledgements_contract(workspace, engine_on, monkeypatch):
    folder = workspace / DEMO
    path = folder / "Demo2020_Fig1.wpd.json"
    wpd = json.loads(path.read_text(encoding="utf-8"))
    axes = wpd["datasetColl"][0]["axesName"]
    wpd["datasetColl"] += [{"name": name, "axesName": axes, "data": []} for name in ("legend", "axis_labels")]
    path.write_text(json.dumps(wpd), encoding="utf-8")
    review = json.loads((folder / "review.json").read_text(encoding="utf-8"))
    created = "2026-09-18T09:00:00+02:00"
    review["items"].append(
        {
            "id": LEGACY,
            "kind": "issue",
            "state": "resolved",
            "target": {"file": "timecourses_Fig1.tsv"},
            "acknowledges": "digitized_mismatch",
            "text": "Written before acknowledgements were exact.",
            "author": "curator",
            "created": created,
            "resolved_by": "curator",
            "resolved": created,
        }
    )
    (folder / "review.json").write_text(json.dumps(review), encoding="utf-8")
    assert format_folder(folder).ok
    vocabulary = bundled_vocabulary()
    warnings = [i for i in validate_folder(folder, vocabulary).issues if i.code == "unknown_dataset"]
    payloads = [
        {"code": "unknown_dataset", "file": "Demo2020_Fig1.wpd.json", "line": None, "column": None, "key": key}
        for key in ("legend", "axis_labels")
    ]
    engine = engine_on(workspace)
    monkeypatch.setattr(review_edit, "new_ulid", lambda: ACKNOWLEDGED)
    revision = engine.study_detail(DEMO)["review"]["revision"]
    engine.review_action(
        DEMO,
        {"action": "acknowledge", "revision": revision, "text": "The legend is no series.", **payloads[0]},
    )
    remaining = [i.source.key for i in validate_folder(folder, vocabulary).issues if i.code == "unknown_dataset" and i.source]
    assert remaining == ["axis_labels"]
    acknowledged = [
        {key: value for key, value in entry.items() if key != "resolved"}
        for entry in engine.study_detail(DEMO)["acknowledged"]
    ]
    check_contract(
        "acknowledgements",
        {
            "warnings": [issue.model_dump(mode="json") for issue in warnings],
            "payloads": payloads,
            "acknowledged": acknowledged,
        },
    )
```

Run: `cd python && PKDB_UPDATE_CONTRACT=1 uv run --locked pytest -q tests/test_curation_contract.py && uv run --locked pytest -q tests/test_curation_contract.py`

`curation-contract.spec.ts`:

```ts
import type { AcknowledgedWarning } from "../../src/curation-app/api/types";
import { acknowledgement, locationKey, scopeText } from "../../src/curation-app/problems";
import { targetText } from "../../src/curation-app/review";
import acknowledgementsFixture from "../fixtures/curation-contract/acknowledgements.json";

describe("acknowledgements contract", () => {
  const warnings = contract<ValidationIssue[]>(acknowledgementsFixture.warnings);
  const entries = contract<AcknowledgedWarning[]>(acknowledgementsFixture.acknowledged);

  it("acknowledges each dataset of a WebPlotDigitizer project by its key", () => {
    expect(warnings.map(acknowledgement)).toEqual(acknowledgementsFixture.payloads);
    expect(new Set(warnings.map(locationKey)).size).toBe(warnings.length);
  });

  it("says which acknowledgements cover a whole file", () => {
    const legacy = entries.find((entry) => entry.scope === "file")!;
    expect(scopeText(legacy)).toBe("Covers every digitized_mismatch warning in timecourses_Fig1.tsv, also later ones.");
    const exact = entries.find((entry) => entry.scope === "key")!;
    expect(scopeText(exact)).toBeNull();
    expect(targetText(exact.target)).toBe("Demo2020_Fig1.wpd.json · legend");
  });
});
```

- [ ] **Step 7: End-to-end test**

`frontend/tests/curation-e2e/acknowledge.spec.ts` (its own spec file, so it gets its own server and workspace):

```ts
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "./fixtures.ts";

const PROJECT = "caffeine/Demo2020/Demo2020_Fig1.wpd.json";
const REASON = "The legend of the figure is no series.";

interface Project {
  datasetColl: { name: string; axesName: string; data: unknown[] }[];
}

interface ReviewJson {
  items: { acknowledges?: string; target?: object; text: string }[];
}

test("acknowledges one dataset of a WebPlotDigitizer project and keeps the warning of another", async ({ app, page }) => {
  const path = join(app.server.workspace, PROJECT);
  const project = JSON.parse(readFileSync(path, "utf8")) as Project;
  const axes = project.datasetColl[0]?.axesName ?? "XY";
  project.datasetColl.push({ name: "legend", axesName: axes, data: [] }, { name: "axis_labels", axesName: axes, data: [] });
  writeFileSync(path, JSON.stringify(project));
  await app.open("#/studies/caffeine/Demo2020/problems");
  const figure = page.getByRole("region", { name: "Demo2020_Fig1.wpd.json", exact: true });
  const legend = figure.getByRole("listitem").filter({ hasText: "'legend'" });
  const labels = figure.getByRole("listitem").filter({ hasText: "'axis_labels'" });
  await expect(legend).toBeVisible();
  await expect(labels).toBeVisible();

  await legend.getByRole("button", { name: "Acknowledge" }).click();
  const dialog = page.getByRole("dialog", { name: "Acknowledge warning" });
  await expect(dialog).not.toContainText("Covers every");
  await dialog.getByRole("textbox", { name: "Reason" }).fill(REASON);
  await dialog.getByRole("button", { name: "Acknowledge" }).click();
  await expect(dialog).toBeHidden();

  // The next validation leaves out only the acknowledged dataset.
  const acknowledged = page.getByRole("region", { name: "Acknowledged warnings (1)" });
  await expect(acknowledged).toContainText("Demo2020_Fig1.wpd.json · legend");
  await expect(acknowledged).not.toContainText("Covers every");
  await expect(legend).toHaveCount(0);
  await expect(labels).toBeVisible();
  const review = JSON.parse(
    readFileSync(join(app.server.workspace, "caffeine/Demo2020/review.json"), "utf8"),
  ) as ReviewJson;
  expect(review.items.filter((item) => item.acknowledges === "unknown_dataset")).toEqual([
    expect.objectContaining({ text: REASON, target: { file: "Demo2020_Fig1.wpd.json", key: "legend" } }),
  ]);
});
```

Run: `cd frontend && npm run build:curation && npx playwright test --config playwright.curation.config.ts tests/curation-e2e/acknowledge.spec.ts`
Expected: PASS. Before the implementation (or with `key` dropped from `acknowledgement()`), the server answers 422 with two matching locations, which proves the test exercises the fix.

- [ ] **Step 8: Documentation**

`python/src/pkdb/studyformat/export.py`, the Review paragraph, after "A dismissed item no longer acknowledges a warning.": "A review item targets the whole study, a file, the rows of a table with given values (`rows`) and a `column`, or a part of a file without rows that a `key` names: the dataset of a WebPlotDigitizer project or a review item of `review.json`. `acknowledges` names a warning code, and `pkdb review acknowledge` targets exactly one warning, at its row and column or by its key. A target of a file alone acknowledges every warning of the code in that file, also later ones." Regenerate: `cd python && uv run --locked pkdb schema docs --output ../docs/study-format.md`.

`docs/local-curation.md:134`, replace the Acknowledge paragraph: "**Acknowledge** marks a warning as expected; errors cannot be acknowledged. It asks for a reason and writes a resolved review item that acknowledges exactly this warning: a warning at a row of a data table at its row and column, and a warning of a whole file by its key, such as the dataset of a WebPlotDigitizer project or the review item of `review.json`. Other warnings with the same code, also later ones, stay listed. The warning leaves the list after the next validation. The acknowledged warnings are listed below the problems with their reason and a link to their review item. An acknowledgement that names only a file, as the app wrote before acknowledgements were exact, covers every warning of its code in that file, also later ones, and the list says so. Dismissing the review item brings its warnings back."

`docs/python-client.md:203`: "Add an item, optionally for `--file`, `--rows COL=VALUE ...`, `--column`, `--key` or a warning `--acknowledges CODE`". `:209`: "`pkdb review acknowledge FOLDER CODE --file FILE --text TEXT` | Acknowledge one validation warning with a resolved item, told apart by `--line`, `--column` and `--key`; a warning of a whole file, such as `unknown_dataset` of a `.wpd.json` file, has the dataset name as its key".

`docs/superpowers/specs/2026-10-05-study-format-v2-design.md`, section 7, the `target` bullet: add "A `key` instead of `rows` and `column` names a part of a file without rows, such as a dataset of a WebPlotDigitizer project, so that an acknowledgement covers exactly one warning." `docs/superpowers/specs/2026-10-06-curation-app-design.md`, section 5: replace "issues without a row target the file" by "issues without a row target their key (a dataset name, a review item id), and an issue with neither is refused"; section 7.3: add the rows `POST /local/studies/tables/preview` (preview a new table) and `POST /local/studies/review/preview` (rows and digitized series of a draft target).

- [ ] **Step 9: Run every gate**

Run: `cd python && uv run --locked pytest -q && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked ty check`
Run (repository root, test database up): `uv run --project backend pytest backend/tests -q -x`
Run: `cd frontend && npm run test:source && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && npm run build:curation && npm run test:curation-e2e`
Run: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean`
Run: `rg -n "ERROR_BAR_SUFFIX|seriesOfTarget|matchingRows|tableOrder|fileWideScope|DID_YOU_MEAN|SPELLING_HINT|REVIEW_ITEM|QUEUED_MESSAGE|newTable\b" frontend/src`
Expected: all pass, and the last command finds nothing.

- [ ] **Step 10: Commit**

```bash
git add python/src/pkdb python/tests frontend/src/curation-app frontend/tests docs/local-curation.md docs/python-client.md docs/study-format.md docs/superpowers/specs
git commit -m "Acknowledge exactly one warning with a key for warnings without a row"
```

- [ ] **Step 11: Release note, once the pull request exists**

Add at the top of `release-notes/unreleased.md` one paragraph, with the number that `gh-axi pr create` printed in place of `NUMBER`: "- The local curation app takes the rules of the study format from the local server instead of its own copies (#NUMBER): the table files of a study with their kinds in workbook order, a preview of a new table and of the rows that a draft review target matches, the matched rows and the digitized series of each review target, digitized error bar ends as part of their series, suggestion kinds, and the review item of each change in the activity. Acknowledging a warning now covers exactly that warning: a warning without a row, such as `unknown_dataset` of a `.wpd.json` file or `review_target_unmatched`, is acknowledged by its key, the dataset name or the review item id, which `review.json` stores as the new `key` of a target, and `pkdb review acknowledge` and `pkdb review add` take `--key`. Acknowledgements of a whole file in existing `review.json` files keep their meaning, and the app says that they cover every warning of their code in that file. Validation messages of `study.json` lose pydantic's `Value error,` prefix, and `pkdb plot` lists the color of each series once." Commit it with the message "Add the release note of part D of the curation app".

---

## Self-Review

**1. Spec coverage.**
- Important 4, the table list with kinds and order and the add-table checks (`study.ts`, `tables.ts`, `tableKinds.ts`): Tasks 1 and 2.
- The series naming of digitized figures (`seriesOfTarget`) and row filter matching (`matchingRows`, `targetLines`, `itemsWithoutRows`): Task 3.
- The `;error_bar` pairing (`ERROR_BAR_SUFFIX`, `baseSeries`): Task 4.
- Server messages matched by text: the spelling hint and "Did you mean" (Task 5, suggestion kinds), review item ids in job messages (Task 5, `item` and `parts`, with saved jobs handled on the server), the `Queued` message of saved jobs (Task 5), the field prefix and "Value error" of document issues (Task 5, `context.detail`).
- Others found: `fileWideScope` (Task 6), the removal heuristic and the raw check of `conflictView` and `ConflictPanel` (Task 1), `dataTableFiles` (Task 1, removed in Task 6). Deliberately kept rule copies are listed under File Structure with their reasons.
- One contract mechanism for all of them: Task 1 introduces it, and every task adds a fixture and its front-end side.
- Important 3: keys in the issue source (Task 6, `SourceLocation.key` with the producers `unknown_dataset`, file-level `digitized_mismatch`, `review_target_unmatched`); the review.json schema (`ReviewTarget.key`) and `pkdb schema docs` (regenerated); `pkdb review acknowledge` and `add` (`--key`); the server route (`key` in the payload, `scope` in the detail); the app dialog (the scope sentence disappears; legacy scopes are shown in the acknowledged list); the docs (`local-curation.md`, `python-client.md`, the export paragraph, both specs).
- Old acknowledgements keep their meaning with no migration: a target without `key` matches as before, and `acknowledgement_scope` tells the app to say so. A new acknowledgement of a warning with neither a row nor a key is refused (`NoExactTarget`) instead of silently widened. Workbook warnings never reach `validate_folder`, so they stay as unacknowledgeable as before.

**2. Placeholder scan.** No "TBD", "similar to", or untested code step. The release note uses `NUMBER`, which the step defines as the number that `gh-axi pr create` prints; it cannot be known earlier.

**3. Type consistency.** `tableFiles`, `isRawTable`, `dataTableFiles` (Task 1) take `Pick<StudyDetail, "tables">` everywhere. `usePreview` (Task 2) is reused in Task 3 with the same signature. Engine methods are `table_preview` and `target_preview` (the library has `preview_table` and `match_target`), used in the server and the contract tests under the same names. `TargetMatch` and `DigitizedSeries` are the same in Python and TypeScript. `OverlayPoint.error_bar_end` and the meta `raw-bar <series>` match between Task 4 code and tests. `job_parts`, `JobMessagePart` and `messageParts(job, items)` match in Task 5. `Acknowledgement.key`, `warning_locations` triples, `acknowledgement_scope` and `scopeText` match in Task 6.

**4. Review Focus.** Each of the five items has a test in its owning task: legacy file targets (Task 6 library, contract and component tests), two keyed warnings in one file (Task 6 library, API and Playwright tests), stale preview answers (Task 2 `usePreview` and Task 3 New item test), beyond the upload limits (Task 1 and Task 3 API tests), saved state of part C (Task 5 engine test).
