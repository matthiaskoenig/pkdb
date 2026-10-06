---
search:
  exclude: true
---

# Study format v2, sub-project 3: workbook generation and sync engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Curators and AI agents edit the TSV tables of a study format 2 folder through a generated, gitignored Excel workbook. `pkdb tables open|sync|add` keeps the workbook and the TSV files in step with a line-based 3-way merge, never loses an edit, and never writes partial results.

**Architecture:**
- A new package `pkdb.studyformat.workbook` has three modules:
  - `base`: workbook location, open-workbook detection, the `_base` encoding and the sync state file.
  - `write`: builds the workbook from canonical TSV text with openpyxl.
  - `read`: turns the sheets back into canonical TSV text, reusing `load_table` and the formatter.
- `pkdb.studyformat.merge` is a pure diff3 line merge.
- `pkdb.studyformat.sync` compares base B, workbook W and tables T per table file and decides what to write.
- `pkdb.tables_cli` exposes the engine, and `pkdb upload` calls it.
- The curation app (sub-project 4) will call the same `sync_study` function.

**Tech Stack:**
- Python 3.14, openpyxl 3.1 (already a dependency), `difflib` and `zlib` from the standard library.
- LibreOffice (headless) for round-trip tests in CI.
- pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-05-study-format-v2-design.md`.
- Sections 10.1 (commands `pkdb tables`, `pkdb upload`), 10.2 (workbook), 10.3 (sync engine), 10.4 (formulas) and 16 (testing).
- Section 10.6, the decisions taken while planning this sub-project, is binding for this plan.

## Global Constraints

- **Python client:**
  - Run from `python/`: `uv run --locked pytest -q`, `uv run --locked ruff check .`, `uv run --locked ruff format --check .`, `uv run --locked ty check`.
  - Every commit keeps the suite green.
  - The backend is not touched; run its suite once at the end of the branch.
- **Docs:** `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` without warnings.
- **Dependencies:** no new runtime dependencies. openpyxl is already one. Read workbooks with openpyxl, not fastexcel: calamine does not expose formulas, and 10.3 needs them.
- **Writing:**
  - Never use the em dash character.
  - Markdown paragraphs stay on one source line.
  - No attribution lines in commits.
  - Python 3.14 syntax is fine (for example `except ValueError, OSError:`).
- **Issues:**
  - Every new issue code is registered in `python/src/pkdb/studyformat/issues.py` (`_GROUPS`, and `WARNINGS` for warnings).
  - Issues are built with `make_issue`, whose `file="<table>.tsv"` gives the sheet name and cell.
- **Atomic writes:** every write goes through `pkdb.cache.atomic_text` or the new `atomic_bytes`.
- **pkdb_data is read-only:**
  - `/home/mkoenig/git/pkdb_data` must never be written.
  - Never read or search its whole `studies/` directory, and never run bulk formatters on it.
  - A test that needs a real study copies a single study folder to `tmp_path` first.
- **Workbook name:** the workbook of study folder `<substance>/<name>` is `<name>.xlsx` in that folder (spec 4).
- **Sync state file:** `.<name>.xlsx.pkdb-base` (spec 10.6).

## Review Focus

1. **Two saves while the workbook stays open.** A curator saves, the 1-second watcher syncs, and then the curator changes the same cell again and saves. Both saves reach the TSVs without a conflict, because of the sync state file. The test belongs to Task 5.
2. **Lossless round trip.** TSV to workbook to a LibreOffice re-save to TSV is byte-identical. This includes:
   - numbers with 16 or 17 significant digits;
   - text that a spreadsheet would convert: `1-2`, `007`, `=x`, `TRUE`, `1e3` in a text column;
   - `NR` in `time`;
   - an empty optional table.

   The test belongs to Task 3.
3. **Converted cells.** A cell the spreadsheet converted (a date, a percentage, an error value, or a formula without a cached value) is reported at its sheet and cell, and the sync writes nothing. The tests belong to Tasks 3 and 5.
4. **No lost edits, no partial writes.** A sync never replaces a workbook whose changes are not yet in the TSVs. It writes nothing when any table conflicts or any sheet has an error. If a write fails, the earlier files stay intact. The test belongs to Task 5.
5. **Large workbooks.** A workbook whose stored dimension claims 1,048,576 rows, but which holds 10 rows, reads in under 2 seconds. A 20,000-row study syncs within the budgets of Tasks 3 and 5.

---

### Task 1: Foundations: atomic bytes, ignored files, sheet-safe table names, workbook location and lock detection

**Files:**
- Modify: `python/src/pkdb/cache.py`
  - Add `atomic_bytes`.
  - `atomic_text` becomes a thin wrapper around it.
- Modify: `python/src/pkdb/source_files.py` (`ignored_source`).
- Modify: `python/src/pkdb/studyformat/layout.py` (two new rules).
- Modify: `python/src/pkdb/studyformat/issues.py` (register the codes).
- Create:
  - `python/src/pkdb/studyformat/workbook/__init__.py`
  - `python/src/pkdb/studyformat/workbook/base.py` (location and lock part only; Task 2 extends this module).
- Test:
  - `python/tests/test_cache.py` (or the existing module that tests `atomic_text`)
  - `python/tests/test_source_files.py` (create it if it is missing)
  - `python/tests/studyformat/test_studyformat_layout.py`
  - `python/tests/studyformat/test_workbook_base.py`

**Interfaces (produced):**
- `pkdb.cache.atomic_bytes(path: Path, data: bytes) -> None` behaves exactly like `atomic_text`:
  - It uses the same `_create_temporary` temp file (`.tmp<16 hex>`) and fsyncs it.
  - It keeps the mode of an existing file.
  - It replaces the target with `Path.replace` and fsyncs the directory on POSIX.
  - `atomic_text(path, text)` encodes UTF-8 with LF newlines and calls it, so its behavior does not change.
- `ignored_source(path)` also ignores:
  - the temporary files of `_create_temporary` (`re.fullmatch(r"\.tmp[0-9a-f]{16}", name)`);
  - sync state files (`name.startswith(".") and name.endswith(".pkdb-base")`).

  Without this, the curation watcher and `source_hashes` see transient files.
- Layout issues, both `layout` category errors:
  - `table_name_too_long`: a table file whose name without `.tsv` is longer than 31 characters. Message: "Excel limits sheet names to 31 characters"; the hint suggests a shorter source.
  - `duplicate_table_name`: two table files whose names are equal ignoring case. Report it on the second file in natural order and name the first.
- `pkdb.studyformat.workbook.base`:
  - `SHEET_NAME_LIMIT = 31`.
  - `workbook_path(folder: Path) -> Path`: `folder / f"{folder.name}.xlsx"`.
  - `state_path(workbook: Path) -> Path`: `workbook.with_name(f".{workbook.name}.pkdb-base")`.
  - `open_lock(workbook: Path) -> Path | None`: the lock file that shows the workbook is open, or None. It checks, in the workbook's folder:
    - `.~lock.<file>#` (LibreOffice);
    - `~$<file>` (Excel);
    - `~$<file[2:]>` (Office replaces the first two characters of long names).

    Only regular files count. A directory or a symlink with such a name is ignored.

- [ ] **Step 1: Write the failing tests.**
  - `atomic_bytes`:
    - It writes bytes, keeps the mode of an existing file and leaves no temp file behind.
    - When `Path.replace` raises (monkeypatched), the old content stays and the temp file is removed.
  - `atomic_text` output is unchanged.
  - `ignored_source` ignores `.tmp0123456789abcdef` and `.Example.xlsx.pkdb-base`, but not `.tmp` or `tmp0123456789abcdef`.
  - Layout:
    - `timecourses_Fig1_plasma_concentrations.tsv` (36 characters) is `table_name_too_long`; a name of exactly 31 characters passes.
    - `outputs_TabA.tsv` together with `outputs_Taba.tsv` is `duplicate_table_name`, reported on `outputs_Taba.tsv`.
  - `open_lock`:
    - It returns the path for each of the three lock names.
    - It returns None when no lock exists, and for a directory named like a lock.
- [ ] **Step 2: Run the tests and see them fail.**

  Run: `cd python && uv run --locked pytest -q tests/studyformat/test_workbook_base.py tests/studyformat/test_studyformat_layout.py tests/test_source_files.py`
- [ ] **Step 3: Implement.** Keep `atomic_text`'s docstring accurate, and document that `atomic_bytes` is the primitive.
- [ ] **Step 4: Run the full client suite, ruff and ty.** All green. Add the generated column reference only if the layout rules change `docs/study-format.md`; regenerate it with `pkdb schema docs --output docs/study-format.md` and never edit it by hand.
- [ ] **Step 5: Commit** "Add atomic byte writes, sheet-safe table names and workbook lock detection".

---

### Task 2: Workbook writer (`build_workbook`) with `_lists` and `_base`

**Files:**
- Modify: `python/src/pkdb/studyformat/workbook/base.py` (the `_base` encoding and the sync state file).
- Create: `python/src/pkdb/studyformat/workbook/write.py`.
- Modify: `python/src/pkdb/studyformat/issues.py` (codes).
- Test:
  - `python/tests/studyformat/test_workbook_write.py`
  - `python/tests/studyformat/test_workbook_base.py`
  - snapshot `python/tests/studyformat/data/workbook_template.json`

**Interfaces:**
- Consumes:
  - `TABLES`, `TableSpec`, `Column`, `ColumnType`, `parse_table_file`, `table_file`, `natural_key`, `format_number`, `parse_number`, `read_tsv` and `make_issue`;
  - `vocabulary_terms(vocabulary)` (`pkdb.studyformat.terms`);
  - `Vocabulary.measurements` (`MeasurementRule.deprecated`);
  - `atomic_text`.
- Produces in `pkdb.studyformat.workbook.base`:
  - Constants `LISTS_SHEET = "_lists"`, `BASE_SHEET = "_base"`, `WORKBOOK_FORMAT = 1` and `BASE_CHUNK = 32000`.
  - `@dataclass(frozen=True) WorkbookBase(generation: str, created: datetime, files: Mapping[str, str])`. `generation` is a uuid4 hex, `created` is timezone-aware UTC, and `files` maps a table file name to its canonical text.
  - `base_rows(base: WorkbookBase) -> list[tuple[object, ...]]` and `parse_base(rows: Iterable[tuple[object, ...]]) -> WorkbookBase`.
    - `parse_base` raises `BaseError(code, message)`.
    - `code` is `workbook_base_invalid` (bad marker, bad checksum, undecodable chunk) or `workbook_newer` (format version greater than `WORKBOOK_FORMAT`).
    - Row 1 is `("pkdb workbook", WORKBOOK_FORMAT, generation, created.isoformat())`.
    - Every following row is `(file, sha256 hex of the UTF-8 text, chunk index, chunk)`. The chunks are base64 of zlib-compressed UTF-8, split every `BASE_CHUNK` characters.
  - Sync state file:
    - `read_state(workbook: Path, generation: str) -> dict[str, str | None]` returns the base overrides when the file exists, parses, and names this generation. Otherwise it returns `{}`. None means the table is absent in the base.
    - `write_state(workbook: Path, generation: str, files: Mapping[str, str | None]) -> None` writes JSON `{"format": 1, "generation": ..., "files": {...}}` with `atomic_text`.
    - `remove_state(workbook: Path) -> None`.
- Produces in `pkdb.studyformat.workbook.write`:
  - `@dataclass(frozen=True) WorkbookBuild(data: bytes | None, base: WorkbookBase, issues: list[ValidationIssue])`, where `data` is None when `issues` has an error.
  - The builder:

    ```python
    build_workbook(
        tables: Mapping[str, str],
        vocabulary: Vocabulary,
        *,
        existing: Path | None = None,
        empty_sheets: Iterable[str] = (),
        generation: str | None = None,
        created: datetime | None = None,
    ) -> WorkbookBuild
    ```

    - `tables` holds the canonical TSV text of each table file present.
    - `empty_sheets` names extra per-source sheets (for example `outputs_Tab3`) to add with only the header.
    - `generation` and `created` default to a new uuid4 hex and now (UTC). Tests pass fixed values.
  - `workbook_template() -> dict` describes every sheet a full template has, for the snapshot test: header, column formats, comments, validation targets.
  - `WorkbookError(Exception)` carries `.code` and `.message`.

**Requirements:**
- **Sheets:**
  - `subjects`, `interventions` and `characteristica` always come first, even when their TSV is absent. They get the header only.
  - Then come the `outputs_*`, `timecourses_*` and `scatters_*` sheets of `tables` and `empty_sheets`. Sort them by `(KIND_ORDER[kind], natural_key(source))`, the order of `layout.scan_folder`.
  - Then come the scratch sheets kept from `existing`, in their original order.
  - Then `_lists` (state `hidden`) and `_base` (state `veryHidden`).
  - The first sheet is active.
  - A sheet name longer than 31 characters raises `WorkbookError("table_name_too_long", ...)`. Layout validation prevents it in practice.
- **Header:**
  - Row 1 holds the template columns in template order (`spec.names`) in a bold font.
  - The pane is frozen at `A2`, and the autofilter covers the header range.
  - Each header cell has a comment (author `pkdb`): the column description, a line `Example: <example>` when the column has an example, and `Required` for required columns.
  - Column widths are clamped to 8 to 60 characters, from the longest of the header and the first 200 cell texts.
- **Cell values from canonical text:**
  - **NUMBER, INTEGER and TIME columns:** a number cell when the text parses as a number, has at most 15 significant digits, and satisfies `format_number(float(text)) == text`. Write an `int` when the canonical text has no `.`, `e` or `E`, otherwise a `float`. Anything else is a text cell, for example `NR`, 16 or 17 significant digits, or invalid text.
  - **Every other column type:** text cells.
  - Every text cell has `number_format = "@"`, and its `data_type` is forced to `"s"`, so `=x` is never a formula.
  - Empty text leaves the cell empty.
  - Text columns also get a text column style, so a newly typed cell is text (for example `ws.column_dimensions[letter].number_format = "@"`; verify the openpyxl API).
- **Dropdowns:**
  - Use openpyxl `DataValidation(type="list", allow_blank=True, showErrorMessage=False)` over `<letter>2:<letter>1048576`.
  - Leave `showDropDown` at its default: in openpyxl, True hides the arrow.
  - Columns with `Column.references` (`subjects` or `interventions`, including the scatter axis copies) use `=<sheet>!$<name letter>$2:$<name letter>$1048576`. Here `<sheet>` is `subjects` or `interventions`, and `<name letter>` is the letter of that table's `name` column.
  - Columns with `Column.vocabulary` use the `_lists` column of that vocabulary key.
  - ENUM columns use the `_lists` column `choice:<column name>`.
  - UNIT columns and `choice` get no dropdown, because their values depend on the measurement.
- **`_lists`:**
  - One column per list. Row 1 is the list key, and the values from row 2 are sorted by `natural_key`.
  - The vocabulary lists come from `vocabulary_terms(vocabulary)`.
  - The `measurements` list leaves out rules with `deprecated` set.
  - Only lists that some column uses are written.
- **`_base`:** `base_rows(WorkbookBase(generation, created, tables))`. `empty_sheets` are not in the base, because they have no file.
- **`existing` workbook:**
  - Load it with `openpyxl.load_workbook(existing)`, in full mode, without `data_only`, so formulas stay.
  - Keep the sheets whose names start with `_`, other than `_lists` and `_base`. Remove all others, then add the new sheets.
  - If it cannot be loaded, raise `WorkbookError("workbook_unreadable", ...)`. The caller must never overwrite it then.
- **Errors** are issues, never crashes. Both give `data=None`.
  - `cell_too_long`: a cell text over 32,767 characters, at the TSV file, line and column.
  - `illegal_character`: an openpyxl `IllegalCharacterError`, at the cell.
- **Output:** `data` is the workbook saved to a `BytesIO`. Set `wb.properties.created` and `wb.properties.modified` to `created`.

- [ ] **Step 1: Write the failing tests.** Use `valid_study` and the `sf_vocabulary` fixture; read the canonical texts from the formatted folder.
  - Sheet order, including `outputs_Tab2` before `outputs_Tab10`. An absent `interventions.tsv` still gives an `interventions` sheet with the header only.
  - Header, bold, `A2` freeze, autofilter and comment text.
  - Typed cells:
    - `0.1` is a float cell;
    - `12` is an int cell;
    - `0.30000000000000004` is a text cell with `@`;
    - `NR` in `time` is text;
    - `1-2` and `=x` in `comment` are text with `data_type == "s"`.
  - Data validations:
    - `measurement` points at `_lists`;
    - `subjects` points at `subjects!$<name letter>$2:...`;
    - `interventions` (NAMES) points at the interventions name column;
    - `error_type` points at `choice:error_type`;
    - `unit` has none;
    - every validation has `showErrorMessage` False.
  - `_lists` is hidden and holds no deprecated measurement (`old_measure` from `sf_vocabulary`).
  - `_base` is `veryHidden`, and `parse_base` returns the input texts and generation.
  - A text over 32,000 characters needs two chunks and still round trips.
  - A tampered chunk gives `workbook_base_invalid`; format 2 in row 1 gives `workbook_newer`.
  - Regenerating with `existing` keeps a `_notes` sheet with a value and a formula, and removes an old `outputs_Tab9` sheet.
  - Sync state: `write_state` then `read_state` with the same generation round trips; another generation gives `{}`; a corrupt state file gives `{}`.
  - `cell_too_long` and `illegal_character` (a cell with `chr(0x01)`) return issues and no data.
  - Snapshot:
    - `workbook_template()` equals the committed JSON file.
    - The test prints a regeneration command on mismatch. Document the command in the test module docstring: `uv run --locked python -c "..."` writing the file.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** `base.py` (encoding and state file) and `write.py`.
- [ ] **Step 4: Run the client suite, ruff and ty.** All green.
- [ ] **Step 5: Commit** "Generate the study workbook with dropdowns, comments and its base".

---

### Task 3: Workbook reader and LibreOffice round trip

**Files:**
- Create: `python/src/pkdb/studyformat/workbook/read.py`.
- Modify: `python/src/pkdb/studyformat/formatter.py`.
  - Split `render_table` into `table_rows(table, study_name, order) -> list[tuple[int, tuple[str, ...]]] | None` (the source line and cells of each row, in canonical order; None for an optional table without rows) plus rendering.
  - `render_table` keeps its signature and output.
- Modify: `python/src/pkdb/studyformat/issues.py`.
- Modify: `python/tests/studyformat/conftest.py` (a LibreOffice re-save fixture).
- Modify: `.github/workflows/ci-cd.yml` (install LibreOffice for the Linux client job).
- Test: `python/tests/studyformat/test_workbook_read.py`.

**Interfaces:**
- Consumes:
  - `build_workbook`, `parse_base`, `BASE_SHEET`, `LISTS_SHEET`, `WorkbookBase` (Task 2);
  - `load_table`, `RowLimit`, `parse_table_file`, `subject_order`, `table_rows`, `render_tsv`, `make_issue`, `format_number`.
- Produces in `pkdb.studyformat.workbook.read`:
  - `@dataclass(frozen=True) SheetTable(file: str, text: str, rows: tuple[int, ...])`.
    - `text` is the canonical TSV text.
    - `rows[i]` is the sheet row of canonical line `i + 1`; `rows[0] == 1` for the header.
  - `@dataclass(frozen=True) WorkbookContent`:
    - `tables: dict[str, SheetTable]`: one entry per data sheet with content. An optional table without rows is left out, as if absent.
    - `sheets: tuple[str, ...]`: data sheet names in workbook order.
    - `base: WorkbookBase | None`.
    - `issues: list[ValidationIssue]`.
    - `.ok`: no error issue.
  - `read_workbook(path: Path, study_name: str, *, max_rows: int | None = None) -> WorkbookContent`.

**Requirements:**
- **Reading:**
  - Open the file twice with `openpyxl.load_workbook(path, read_only=True, data_only=False)` and `(..., data_only=True)`. Walk each data sheet's rows from both in lockstep, so memory holds one row of each.
  - Call `reset_dimensions()` on both read-only sheets before iterating, so an inflated stored dimension is ignored.
  - Close both workbooks in `finally`.
  - A file that is not a valid workbook gives an error `workbook_unreadable`.
- **Sheets:**
  - `_lists` and `_base` are special.
  - Other names starting with `_` are scratch sheets and are skipped.
  - A name that `parse_table_file(f"{name}.tsv")` accepts is a data sheet.
  - Anything else is an `unknown_sheet` error. The hint says to rename the sheet to `<kind>_<source>`, or to start it with `_` to keep it as scratch.
  - `subjects` is required: a workbook without it gives `missing_sheet`.
- **Base:**
  - A missing `_base` gives `base=None` and a warning `workbook_base_missing`.
  - A `BaseError` gives an issue with its code: `workbook_newer` is an error, `workbook_base_invalid` a warning, and `base=None`.
- **Cell to text.** For a formula cell, `value` is the cached value from the `data_only` pass.
  - None gives `""`.
  - `str` is the text. A text containing `\t`, `\n` or `\r` is an error `cell_line_break` at the cell; the hint names the character.
  - `bool` gives `TRUE` or `FALSE`.
  - `int` gives `str(value)`, and `float` gives `format_number(value)`.
  - `datetime`, `date` or `time` is an error `cell_date`. Hint: "The spreadsheet converted this cell to a date; format the column as text and enter the value again".
  - A number whose number format contains `%` is an error `cell_percent`. Hint: "20% is stored as 0.2; enter 20".
  - An error value (`data_type == "e"` or a text in `#NULL! #DIV/0! #VALUE! #REF! #NAME? #NUM! #N/A #GETTING_DATA`) is an error `cell_error`.
- **Formulas:**
  - The `data_only=False` pass shows a formula as `data_type == "f"`.
  - A formula whose cached value is None is an error `formula_without_value`. Hint: "save the workbook in Excel or LibreOffice".
  - Otherwise the cached value is used, with a warning `formula_value` per cell. Repeated `formula_value` and `cell_*` issues are capped with `IssueCap` per sheet and code.
- **Table text:**
  - The header is the row-1 texts, with trailing empty header cells dropped.
  - A non-empty value in a column past the last header cell is an error `value_outside_table` at that cell.
  - Fully empty rows are skipped, but each row keeps its sheet row number. Emit an empty line for it, so `Row.line` from `load_table` equals the sheet row.
  - Build the TSV bytes and call `load_table(file, data, spec, source, study=study_name, limit=RowLimit(max_rows))`.
  - Structural issues returned by `load_table` keep their file, line and column, and therefore their sheet and cell. If it returns no table, the sheet is left out of `tables`.
  - Read `subjects` first. `order = subject_order(subjects table)`.
  - Canonical text is `render_tsv(spec.names, [cells for _, cells in table_rows(...)])`, and `rows` is `(1, *[line for line, _ in table_rows(...)])`.
- **Performance:** document the budget in the test and keep it there.
  - A 20,000-row `outputs_Tab1` sheet reads in under 15 s on CI.
  - A workbook whose `<dimension>` claims `A1:Z1048576` but holds 10 rows reads in under 2 s. Build it by saving a workbook and rewriting the dimension in the zip in the test.
- **LibreOffice fixture** in `conftest.py`:
  - `libreoffice_resave(path: Path) -> Path` runs `soffice --headless --calc --convert-to xlsx:"Calc MS Excel 2007 XML" --outdir <tmp> <path>`. Use a fresh `-env:UserInstallation=file://<tmp>/lo-profile`, so parallel runs and user profiles do not interfere, and a 120 s timeout.
  - When `soffice` is missing, the test skips, unless the environment variable `PKDB_REQUIRE_LIBREOFFICE=1` is set; then it fails.
- **CI:** in the Linux client job of `.github/workflows/ci-cd.yml`, before the tests, run:
  - `sudo apt-get update && sudo apt-get install -y --no-install-recommends libreoffice-calc`
  - set `PKDB_REQUIRE_LIBREOFFICE: "1"` for that job only.

  macOS and Windows tag jobs skip these tests.

- [ ] **Step 1: Write the failing tests.**
  - **Round trip:**
    - For `valid_study` plus a fixture table with the edge texts of Review Focus 2, `read_workbook(build_workbook(...))` returns texts byte-identical to the canonical TSV files.
    - The same holds after `libreoffice_resave`.
  - **Unsorted rows:** a sheet with rows S2 then S1 gives canonical order S1, S2, and `rows` maps to sheet rows 3 and 2.
  - **Formulas:**
    - An openpyxl-written `=B2*2` without a cached value gives `formula_without_value` at its cell.
    - After `libreoffice_resave`, the same workbook gives the computed value and a `formula_value` warning.
  - **Converted cells:**
    - a datetime cell gives `cell_date`;
    - a `0.2` cell with format `0%` gives `cell_percent`;
    - a `#DIV/0!` error cell gives `cell_error`;
    - a text with `\n` gives `cell_line_break`.
  - **Sheets:**
    - a sheet `outputs_Tab2 (2)` gives `unknown_sheet`;
    - a `_notes` sheet is ignored;
    - a missing `subjects` sheet gives `missing_sheet`.
  - **Values and header:**
    - a value in column Z past the header gives `value_outside_table`;
    - an unknown header column gives the `load_table` structural issue at sheet cell `<letter>1`.
  - **Base:** a missing `_base` gives a warning and `base=None`.
  - **Performance:** the two budgets.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** the formatter split, `read.py`, the fixture and the CI step.
- [ ] **Step 4: Run the client suite, ruff and ty.** All green, with LibreOffice tests running locally (`soffice` is installed here).
- [ ] **Step 5: Commit** "Read the study workbook back into canonical tables and test the LibreOffice round trip".

---

### Task 4: Three-way line merge (`pkdb.studyformat.merge`)

**Files:**
- Create: `python/src/pkdb/studyformat/merge.py`.
- Test: `python/tests/studyformat/test_merge.py`.

**Interfaces (produced):**
- `@dataclass(frozen=True) Conflict(base: tuple[str, ...], ours: tuple[str, ...], theirs: tuple[str, ...], base_start: int, ours_start: int, theirs_start: int)`. The starts are 0-based line indices.
- `@dataclass(frozen=True) MergeResult(lines: tuple[str, ...] | None, conflicts: tuple[Conflict, ...])`.
  - `lines` is None exactly when there are conflicts and no `prefer` was given.
  - With `prefer`, `lines` holds the resolved merge, and `conflicts` still lists what was resolved.
- `merge_lines(base: Sequence[str], ours: Sequence[str], theirs: Sequence[str], *, prefer: Literal["ours", "theirs"] | None = None) -> MergeResult`.

**Requirements:**
- diff3 semantics, as in `git merge-file`, on whole lines:
  - A region changed on one side only takes that side.
  - A region changed identically on both sides is taken once.
  - Different changes to the same or adjacent base regions conflict. Changes are adjacent when no unchanged base line separates them.
  - With `prefer`, a conflicting region takes that side's lines, and every other region merges normally.
- Algorithm (bzr/Breezy `merge3`, reimplemented):
  - Compute matching blocks with `difflib.SequenceMatcher(None, base, side, autojunk=False).get_matching_blocks()` for both sides.
  - Intersect them into sync regions where base, ours and theirs agree.
  - Walk the gaps between sync regions, and classify each gap as unchanged, ours-only, theirs-only, same-change or conflict.
  - Append a final zero-length sync region at the ends.
- Deterministic. The input lines contain no line terminators; callers split canonical TSV text with `text.splitlines()`.
- **Performance:** two 20,000-line sides with 200 scattered single-line edits each merge in under 2 s.

- [ ] **Step 1: Write the failing tests.** Parametrized tables of small cases with expected results:
  - Identities: `merge(b, x, b) == x`, `merge(b, b, y) == y` and `merge(b, x, x) == x`.
  - Insertions at different places combine, and so do deletions at different places.
  - An edit on one side and a deletion of a distant line on the other combine.
  - The same line edited differently is one conflict with correct starts and contents.
  - Adjacent edits conflict.
  - Both sides append different lines at the end: conflict.
  - Empty base with both sides adding different content: conflict; identical content merges.
  - `prefer="ours"` and `prefer="theirs"` resolve only the conflicting regions.
  - Property test (`random.Random(seed)`, 500 cases on 20-line bases with up to 4 edits per side): with `prefer=None`, a result without conflicts contains every line that both sides kept and that the base had, in base order. When `git` is on PATH, also compare clean results with `git merge-file -p` on the same inputs. Skip that comparison without git.
  - The performance budget.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the client suite, ruff and ty.**
- [ ] **Step 5: Commit** "Add a three-way line merge for study tables".

---

### Task 5: Sync engine (`sync_study`)

**Files:**
- Create: `python/src/pkdb/studyformat/sync.py`.
- Modify:
  - `python/src/pkdb/studyformat/issues.py`;
  - `python/src/pkdb/studyformat/__init__.py` (export `sync_study`, `SyncResult`).
- Test: `python/tests/studyformat/test_sync.py`.

**Interfaces:**
- Consumes:
  - `workbook_path`, `state_path`, `open_lock`, `read_state`, `write_state`, `remove_state` (Tasks 1 and 2);
  - `build_workbook`, `WorkbookError` (Task 2);
  - `read_workbook` (Task 3);
  - `merge_lines` (Task 4);
  - `load_study`, `render_table`, `subject_order`, `FileChange` (formatter), `atomic_text`, `atomic_bytes`.
- Produces in `pkdb.studyformat.sync`:
  - `@dataclass(frozen=True) SyncConflict(file: str, sheet: str, workbook_rows: tuple[tuple[int, str], ...], table_lines: tuple[tuple[int, str], ...], base_lines: tuple[str, ...])`.
    - Rows and lines are 1-based sheet rows and TSV line numbers, with their text.
    - A delete/modify conflict has one side empty.
  - `WorkbookAction = Literal["created", "regenerated", "unchanged", "close_to_update"]`.
  - `@dataclass(frozen=True) SyncResult`:
    - `folder: Path`, `workbook: Path`;
    - `changes: tuple[FileChange, ...]`: TSV writes and deletes, done or planned in check mode;
    - `workbook_action: WorkbookAction`;
    - `lock: Path | None`;
    - `conflicts: tuple[SyncConflict, ...]`;
    - `issues: tuple[ValidationIssue, ...]`;
    - `checked: bool`, true in check mode;
    - `.ok`: no error issue and no unresolved conflict.
  - The sync function:

    ```python
    sync_study(
        folder: Path,
        vocabulary: Vocabulary,
        *,
        keep: Literal["workbook", "tables"] | None = None,
        check: bool = False,
    ) -> SyncResult
    ```

**Algorithm.** Every table text is canonical; "absent" is a missing key.
1. **Tables T:**
   - `study = load_study(folder)`.
   - If any issue is in `load.STRUCTURAL` (for example git conflict markers or an unknown column), return those issues with no action and no writes. T must be loadable to merge.
   - `T = {file: render_table(table, study.name, subject_order(study.table("subjects.tsv")))}` for every loaded table, dropping None results. `study.name` is the name `planned_files` uses, and `read_workbook` gets the same name.
   - T is the canonical form of what is on disk; untouched files are not reformatted.
2. **No workbook:**
   - In check mode, report `workbook_action="created"`.
   - Otherwise call `build_workbook(T, vocabulary)` and `atomic_bytes`, then `remove_state(workbook)`, and return `"created"`.
   - If the lock check finds a lock, the workbook is open somewhere, which is impossible without a file. Ignore it.
3. **Workbook W:**
   - `content = read_workbook(path, folder.name)`.
   - If it has an error, return its issues. Write nothing and never regenerate.
4. **Base B:**
   - `content.base.files`, overlaid by `read_state(path, content.base.generation)`. A None value in the state removes the file from B.
   - If `content.base` is None, B is empty, and every table where W and T differ conflicts unless `keep` is set.
5. **Per file** in the union of W, T and B keys, with `w`, `t` and `b` (None means absent):
   - `w == t`: nothing to do for T.
   - `t == b`: the workbook changed. The new T is `w` (write, or delete when `w` is None).
   - `w == b`: the tables changed. T stays; the workbook needs `t`.
   - Otherwise:
     - If one of `w`/`t` is None and `b` is not None, it is a delete/modify conflict. `keep` picks the side: workbook means `w` (possibly delete), tables means `t`.
     - Otherwise `merge_lines(b or "", w, t, prefer=...)` with ours = workbook, theirs = tables. A clean result is `"\n".join(lines) + "\n"`, re-rendered through `load_table` and `render_table` so it is canonical.
     - Each conflict region becomes a `SyncConflict`, located through `content.tables[file].rows` and the T line numbers, plus an error issue `sync_conflict` at the first workbook row of the region.
   - The `subjects` sheet or table may not be deleted. If `w` is None for `subjects.tsv`, it is a `missing_sheet` error (already reported by the reader).
6. If any error issue or unresolved conflict exists, return without writing anything.
7. **Writes** (skipped in check mode, but still listed):
   - Write every TSV change with `atomic_text`, or `unlink` it.
   - Record every table whose new T now equals `w` in the sync state with `write_state(path, generation, {file: new_t})`. Keep earlier entries of the same generation.
   - This makes the next sync see `w == b`, Review Focus 1.
8. **Workbook:**
   - It needs regeneration when any table's new T differs from `w`.
   - If it does and `open_lock(path)` finds a lock, the action is `close_to_update`, with a warning `workbook_open`. The warning names the lock file and adds: "If the workbook is not open, delete <lock>".
   - Otherwise build from the new T with `existing=path` and `empty_sheets=` the per-source data sheets of `content.sheets` that have no table in the new T, so a sheet added by `pkdb tables add` survives before it has rows. Write with `atomic_bytes` and `remove_state`; the action is `regenerated`.
   - A `PermissionError` on replace (Windows keeps open files locked) also gives `close_to_update`.
   - A `WorkbookError` gives its issue, after the TSV writes. The TSVs are already correct, and the workbook stays untouched.
   - No regeneration needed: `unchanged`.
9. Never call `build_workbook` without `existing` when a workbook exists, so scratch sheets survive.

- [ ] **Step 1: Write the failing tests.** Use `valid_study`, edit cells through openpyxl on the generated workbook (then `libreoffice_resave` when a test needs cached values), and assert both the files and the result.
  - **No workbook:** created. Its `_base` equals T, and the TSVs are unchanged.
  - **In step:** `w == t` is unchanged, with no writes. The mtimes of the TSVs and the workbook are unchanged.
  - **Workbook changed:** the TSV is written in canonical form, the state file records it, and the workbook is `unchanged`; it already holds the content.
  - **Tables changed** (edit a TSV): the workbook is regenerated, the new `_base` equals T, and the state file is removed.
  - **Both changed in different rows:** merged. The TSV holds both edits, and the workbook is regenerated.
  - **Both changed in the same cell:**
    - The result holds a conflict with the sheet row and the TSV line, nothing is written, and the old bytes are unchanged.
    - `keep="workbook"` and `keep="tables"` resolve it, and the other edits still merge.
  - **Workbook open:**
    - With `~$Example.xlsx`, a tables change gives `close_to_update`, and the workbook bytes stay unchanged. Repeat with `.~lock.Example.xlsx#`.
    - A workbook change is still written to the TSVs while the workbook is open.
  - An empty sheet added by `pkdb tables add` survives a regeneration caused by a tables change.
  - **Review Focus 1:** with the workbook open, change a cell and sync, then change the same cell again and sync. Both are written, with no conflict.
  - **State file:** a state file of another generation is ignored; after regeneration, no state file exists.
  - **New sheet:** a copied and renamed sheet `outputs_Tab3` with one row creates `outputs_Tab3.tsv`.
  - **Removed sheet:** a removed `outputs_Tab2` sheet deletes `outputs_Tab2.tsv` when T equals B. A removed sheet with T changed is a delete/modify conflict.
  - **Errors** write nothing:
    - a formula without a cached value;
    - git conflict markers in a TSV;
    - an unknown sheet.
  - **Base:** a missing `_base` with W equal to T is fine; with W and T different, it conflicts unless `keep` is given.
  - **Failed write:** a TSV write that fails (monkeypatch `Path.replace` to raise on the second file) raises or reports. The workbook is not regenerated, and the first file is canonical new content, not partial: atomic per file.
  - **Check mode:** reports the changes and the action without touching any file, compared by bytes and mtimes.
  - **Scratch sheet:** a `_notes` sheet with a value survives regeneration.
  - **Performance:** a 20,000-row study syncs a one-cell workbook change in under 30 s on CI, including regeneration when tables changed.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the client suite, ruff and ty.**
- [ ] **Step 5: Commit** "Sync the study workbook and the TSV tables with a three-way merge".

---

### Task 6: `pkdb tables open|sync|add` and the upload, validate and prepare integration

**Files:**
- Create: `python/src/pkdb/tables_cli.py` (`register`, `run`).
- Modify:
  - `python/src/pkdb/cli.py`: register the `tables` command and dispatch it. Extract the vocabulary selection used by `validate` into a reusable function, and use it in both places with the same behavior.
  - The upload, validate and prepare paths for study format 2 (`python/src/pkdb/preparation.py`, `python/src/pkdb/batch.py` and/or `cli.py`; follow where format 2 folders are dispatched today).
  - `python/src/pkdb/studyformat/issues.py`.
- Test:
  - `python/tests/studyformat/test_tables_cli.py`;
  - extend `python/tests/studyformat/test_studyformat_upload.py` and the validate CLI tests.

**Interfaces:**
- Consumes:
  - `sync_study`, `SyncResult` (Task 5); `build_workbook` (Task 2); `workbook_path`, `open_lock` (Task 1);
  - `preparation.study_folders`, `is_v2_folder`, `format_folder`;
  - `pkdb.curation.launch.open_path(path, reveal=False)`.
- Produces:
  - **`pkdb tables sync PATH [--keep {workbook,tables}] [--check] [--format {human,json}]`** plus the vocabulary options of `validate` (`--vocabulary`, `--endpoint`, `--cache-dir`, `--offline`).
    - It handles every study under PATH (`study_folders`). Format 1 folders are skipped like `pkdb format` does.
    - JSON lines, one per study: `{"path", "ok", "workbook", "workbook_action", "lock", "changes": [{"file","action"}], "conflicts": [{"file","sheet","workbook_rows","table_lines","base_lines"}], "issues": [...]}`.
    - Human output:
      - one line per change and the workbook action;
      - every conflict with sheet, rows and both versions;
      - issues in the existing `_print_human` style.
    - Exit 1 when any study is not ok, or in `--check` mode when anything would change.
  - **`pkdb tables open STUDY [--no-open]`** plus the vocabulary options.
    - It syncs (creating the workbook if needed) and then opens the workbook with `open_path`. A sync that is not ok is reported, but the workbook still opens so the curator can fix it there.
    - Exit 1 when the sync is not ok.
    - `--no-open` exists for scripts and tests.
  - **`pkdb tables add STUDY TABLE`** plus the vocabulary options. TABLE is `<kind>_<source>`, for example `outputs_Tab3`.
    - It is rejected when `parse_table_file(f"{TABLE}.tsv")` is not a per-source kind, when the name is longer than 31 characters, or when the table already exists as a TSV or a sheet.
    - It syncs first and stops if the sync is not ok.
    - If the workbook is open, it errors: "Close the workbook first, or copy a sheet in the spreadsheet application and rename it to TABLE".
    - Otherwise it rebuilds with `build_workbook(T, vocabulary, existing=path, empty_sheets=[TABLE] + existing empty sheets)`, so empty sheets added before are kept: they are data sheets without content in `read_workbook`. It writes atomically and removes the state file.
    - A warning `missing_image` hint is printed when the source is not `Text` and `<name>_<source>.png` is missing.
  - **Git ignore check** (warning `workbook_not_ignored`): when the study is inside a git work tree and `git check-ignore -q <workbook>` exits 1, the CLI prints the lines to add to `.gitignore`: `*.xlsx` and `.*.pkdb-base`. If git is missing, skip silently. Implement `ignored_by_git(path: Path) -> bool | None` in `tables_cli.py` and use it in `sync` and `open`.
  - **Upload:**
    - For a format 2 folder, `pkdb upload` runs `sync_study(folder, vocabulary)` and then `format_folder(folder)` before preparing.
    - A sync that is not ok, or format issues, stop that study with the issues in its result (`stage` `"sync"` or `"format"`) and nothing is uploaded.
    - Batch uploads do this per study in the worker that prepares it.
  - **Validate and prepare:**
    - For a format 2 folder with a workbook, `pkdb validate` and `pkdb prepare` run `sync_study(folder, vocabulary, check=True)`.
    - They add `"workbook": {"action": ..., "changes": [...], "conflicts": n}` to the JSON result.
    - In human mode they print one line "Workbook changes are not in the tables yet; run pkdb tables sync" when the check plans TSV changes or conflicts.
    - They never write.

- [ ] **Step 1: Write the failing tests** with `main([...])` and `capsys`, following `test_studyformat_cli.py`.
  - `tables sync` on a folder of two studies (one format 1, skipped) gives JSON lines with the right fields.
  - `--check` writes nothing and exits 1 when changes are planned.
  - A conflict exits 1 and lists the rows; `--keep tables` resolves it.
  - `tables open --no-open` creates the workbook. Without `--no-open`, `open_path` is called with the workbook path (monkeypatched).
  - `tables add`:
    - It adds an `outputs_Tab3` sheet with the header.
    - A second `add` of the same table errors; so do an open workbook and a bad name (`results_Tab3`, `outputs_Tab3_with_a_very_long_name_x`).
    - After adding a row to the new sheet, `tables sync` creates `outputs_Tab3.tsv`.
  - The git ignore warning appears in a temporary git repository without `.gitignore` and disappears with `*.xlsx` and `.*.pkdb-base` in it. Skip when git is missing.
  - Upload of a format 2 study with an unsynced workbook change uploads the changed value: use the existing upload test client fixtures, and check that the uploaded TSV bytes contain the edit. An upload with a conflict uploads nothing.
  - `validate` reports the workbook line and the JSON field without writing.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the client suite, ruff and ty.**
- [ ] **Step 5: Commit** "Add pkdb tables open, sync and add, and sync format 2 studies before upload".

---

### Task 7: Documentation and release note

**Files:**
- Create: `docs/workbooks.md`, page title "Edit tables in a workbook".
- Modify:
  - `zensical.toml`: navigation entry next to "Study format".
  - `docs/python-client.md`: command list, with `pkdb tables` and the upload change.
  - `docs/study-format.md`: only the hand-written part, if one exists. Otherwise link from the generator's intro in `pkdb.studyformat.export` and regenerate the file with `pkdb schema docs`.
  - `docs/local-curation.md`: one sentence saying that the curation app will use the same sync in a later release. Do not describe unimplemented UI.
  - `release-notes/unreleased.md`: one new entry at the top, without a PR number.
- Test: the docs build.

**Requirements:**
- `docs/workbooks.md` covers, concisely and accurately for the implemented behavior:
  - **Workflow:** `pkdb tables open`, edit, save, `pkdb tables sync`, commit the TSVs.
  - **Sheet layout:** dropdowns, header comments, the text-formatted columns, and scratch sheets starting with `_`.
  - **Adding a table:** `pkdb tables add`, or copy and rename a sheet.
  - **The sync table of spec 10.3** in user terms, plus the sync state file.
  - **Conflicts:** how they are shown, `--keep`, and editing the workbook to resolve them.
  - **Open workbooks and lock files**, including stale locks.
  - **Formulas:** cached values are stored; a formula without one is an error; scratch calculations belong in `_` sheets, because regeneration replaces data-sheet formulas with their values.
  - **Converted cells:** dates, percentages, error values and line breaks.
  - **Numbers:** numbers with more than 15 significant digits appear as text.
  - **Git:** the `.gitignore` lines `*.xlsx` and `.*.pkdb-base`.
  - **Upload:** syncs and formats first; validate and prepare only report.
  - **Compatibility:** Excel and LibreOffice.
- Release note: one paragraph, user-facing.
- Keep `README.md` and `docs/index.md` aligned only if a shared feature list changes there; check and adapt.

- [ ] **Step 1: Write the docs** and run the docs build (no warnings).
- [ ] **Step 2: Run the client suite** (the CLI help texts may be tested), ruff and ty.
- [ ] **Step 3: Commit** "Document editing study tables in a workbook".
