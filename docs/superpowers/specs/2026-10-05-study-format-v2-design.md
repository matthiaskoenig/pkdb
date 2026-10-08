---
search:
  exclude: true
---

# Study format v2: fixed table templates, git-native curation and AI-ready uploads

Date: 2026-10-05. Status: Draft for review. The work is split into six sub-projects (section 17), each with its own implementation plan.

## 1. Objective

Curated studies in `pkdb_data` must be simple to change for human curators and for AI agents, reviewable as readable diffs in GitHub pull requests, free of binary merge conflicts, and validated against one schema that also checks the relationships between tables. Every study moves to the new format, including legacy studies that keep groups, individuals, interventions or outputs inline in `study.json`.

Success criteria:

- Every change to a study is a readable line diff in a GitHub pull request.
- Edits to different rows merge automatically. A conflict on the same row is a text conflict, never a choice between two binary files.
- All tables follow fixed templates. Nothing is silently ignored: an unknown table file or workbook sheet is an error.
- One schema module defines files, tables, columns, types, vocabulary bindings and cross-table references. The same validator runs in the curation app, the CLI, pre-commit, CI and on the server.
- Formatting is deterministic. Upload and CI reject unformatted data, so the database only receives canonical data.
- JSON files are written only by the curation app and `pkdb` commands.
- AI agents can curate a study end to end through the `pkdb` CLI and a documented contract. Every uncertainty is recorded in a standard review format that the curation app shows.
- Every piece of information has a single source of truth. Copies exist only where they are derived and overwritten by tooling.
- All existing studies are migrated, gated by an equivalence check against the current parser.

## 2. Current state

Findings from the repositories on 2026-10-05:

- `pkdb_data` tracks about 1,580 `study.json`, 1,621 xlsx and 8,653 hidden TSV files. `.git` is 7.9 GB with about 9,300 xlsx revisions. There is no `.gitattributes` and no LFS.
- `study.json` is a template mini-language (`col==`, `||`, `subset`, `#` comment rows, comma lists, schedule strings such as `S0T24R3`) that maps arbitrary sheet columns. The meaning of a value is spread over the JSON template, the row-2 sheet headers and the cell values or formulas.
- Three generations coexist: inline entities in JSON (a sample of 489 study files had 724 inline groups, 624 inline interventions and 261 inline outputs), mixed studies, and sheet-driven studies with `TabGroups`, `TabIndividuals` and `TabInterventions`.
- Sheets exist per paper table or figure with two header rows and inconsistent headers (`measurement` vs `measurement_type`, `subject` vs `individual`). Formulas are common (Guo2016 `Fig3` has 189, Kasichayanula2013 `Fig1` has 373), as are comment rows, scratch columns and embedded screenshots. Sheets that `study.json` does not reference are silently ignored (for example Jensen2017 `Tab1`).
- The hidden TSVs are ignored by the parser whenever an xlsx exists, are often stale, and appear in most "resolved merge conflicts" commits. There are two table readers: openpyxl for validation and calamine for the TSV export.
- There is no schema for the source format and no check on studies in pre-commit or CI. Invalid JSON is committed (talinolol/Drozdzik2014, semaglutide/Granhall2019). Copy-paste overwrote identities (albuterol/Hindle1992 with Goldstein1987 content). `studies/study_identifiers.json` is maintained by hand, and 8 studies have two PKDB identifiers.
- The study `date` field holds the release date that is also recorded in `study_identifiers.json` (for example Guo2016: `PKDB01237`, 2026-09-28 in both). The `reference` field holds the PubMed ID.
- The local curation app (`pkdb curate`) never writes `study.json`. The MCP server is read-only.
- GitHub issues in matthiaskoenig/pkdb_data are mostly titled `<substance>/<Study>`, some with prefixes ("Curate ", "Check and curate "). Labels are the substance plus `curate` or `check`, and curators are assignees.

## 3. Decisions

| Topic | Decision |
|---|---|
| Committed form of the data | TSV tables. The xlsx workbook is a generated, gitignored working copy. |
| Editing | Humans edit the workbook in Excel or LibreOffice; the curation app syncs it to the TSVs. AI edits the TSV text and uses the `pkdb` CLI. |
| Table split | Study-wide `subjects`, `interventions` and `characteristica` tables. Per-source files for outputs, timecourses and scatters (`<kind>_<source>.tsv`). |
| Groups and individuals | One `subjects` table. `count` = 1 is an individual, any other count is a group. |
| Characteristica | One `characteristica` table with the same row model as outputs. |
| Interventions | The output row model extended with dosing fields. |
| Formulas | Committed tables hold values only. Derivations happen in postprocessing. |
| `value` | Removed from the source format, the canonical model, the database and the API. For n = 1 the number is the `mean`. |
| Geometric statistics | `gmean`, `gsd` and `gcv` columns. |
| `cv`, `gcv` | Percent in the source, fraction in the canonical model. |
| Timecourse labels | Required and persisted. |
| Count | First-class column on all observation rows. |
| Review information | `review.json` per study in a fixed schema, shown in the curation app. |
| Provenance | Study level in `study.json`; row-level authorship from git history. |
| Identity | `<substance>/<name>` from the folder location. The PKDB identifier is stored in the `release` block of `study.json` once the study is finished. |
| `study_identifiers.json` | Removed after migration; release information lives in each `study.json`. |
| GitHub | Exactly one issue per study titled `<substance>/<name>`, kept in sync by tooling. |
| Migration | One-shot conversion of all studies, gated by an equivalence check. v1 code is deleted afterwards. |
| Schema technology | Pydantic models as the single source; JSON Schema is exported from them. |

## 4. Study folder

```
studies/<substance>/<name>/
  study.json                 metadata, written by the curation app and `pkdb study`
  reference.json             bibliographic snapshot, written by `pkdb reference`
  review.json                review status and items, written by the curation app and `pkdb review`
  subjects.tsv               groups and individuals
  interventions.tsv
  characteristica.tsv
  outputs_<source>.tsv       one file per paper table or figure
  timecourses_<source>.tsv
  scatters_<source>.tsv
  <name>.pdf
  <name>_<source>.png        image of each paper table or figure
  <name>_<source>.tsv        raw extraction of a paper table as printed (optional)
  <name>_<source>.wpd.json   WebPlotDigitizer project of a figure (optional)
  <name>.xlsx                generated working copy, gitignored
```

`study.json`, `reference.json`, `review.json` and `subjects.tsv` are required. The other tables are optional, and an observation file exists only when it has rows. The raw extraction files are specified in section 4 of the [curation app design](2026-10-06-curation-app-design.md); study folder names `outputs`, `timecourses` and `scatters` are reserved.

A file is an error when it is a `.tsv` or `.json` file with a name not listed above, a `.csv`, `.xls` or `.xlsx` file other than the generated workbook, or a hidden TSV from v1. Every other file (PDF, images, documents) is an attachment and is uploaded as today.

## 5. Tables

### 5.1 TSV encoding

- UTF-8 without byte order mark, LF line endings, a final newline.
- Tab separated, no quoting. Cells must not contain tabs or line breaks. Leading and trailing whitespace is removed.
- One header row with exactly the template columns in template order, including columns that are empty in every row.
- An empty cell means missing. `NA` and `nan` are not used. `NR` (not reported) is allowed only in `time` and `time_unit`.
- Numbers are written in the shortest form that converts back to the same binary value. Integers have no decimal point. The formatter never rounds.
- There are no comment rows. Each table has a `comment` column.

### 5.2 Sources and file names

A source names the place in the publication: `Tab` or `Fig` followed by letters, digits, `_` or `-` (`Tab2`, `TabA`, `TabS1`, `Fig3A`), or `Text` for values from the article text. For every source except `Text`, `<name>_<source>.png` must exist.

Observation files are named `<kind>_<source>.tsv` with kind `outputs`, `timecourses` or `scatters`. The file name is the source of truth for the source of its rows. The `study` column (all tables) and the `source` column (per-source files) are owned by the formatter: it overwrites them from the folder name and the file name, so they are readable copies and never edited. In `subjects`, `interventions` and `characteristica` the `source` column is curator data.

### 5.3 Common observation columns

`characteristica`, `interventions`, `outputs` and `timecourses` share one row model.

| Column | Meaning |
|---|---|
| `study` | Study name, filled by the formatter. |
| `source` | Source of the row (5.2). |
| `subjects` | Name of exactly one row in `subjects.tsv`. |
| `measurement` | What is measured (vocabulary; was `measurement_type`). |
| `calculation` | Qualifies the statistic (vocabulary; was `calculation_type`). `unspecified summary` marks a central value without a stated statistic. `geometric mean` is retired in favour of `gmean`. |
| `substance` | Substance (vocabulary). |
| `tissue` | Tissue (vocabulary). |
| `method` | Method (vocabulary). |
| `choice` | Categorical value (vocabulary of the measurement). |
| `time`, `time_unit` | Time point, or `NR`. |
| `count` | Number of subjects the row describes. Empty means the count of the referenced subject. |
| `mean`, `sd`, `se`, `cv` | Arithmetic statistics. For n = 1 the number is `mean`. `cv` is in percent. |
| `gmean`, `gsd`, `gcv` | Geometric statistics. `gsd` is the dimensionless factor, `gcv` is in percent. |
| `median`, `min`, `max` | Order statistics. |
| `unit` | Unit of all statistics in the row except `cv`, `gcv`, `gsd` and `count`. |
| `error_bar`, `error_type` | Digitized end of an error bar on the value axis, in `unit`, and its type (`sd`, `se` or `gsd`). |
| `comment` | Free text. |

### 5.4 Tables and column order

| File | Columns |
|---|---|
| `subjects.tsv` | `study, name, parent, count, source, comment` |
| `characteristica.tsv` | `study, source, subjects, measurement, calculation, substance, tissue, method, choice, time, time_unit, count, mean, sd, se, cv, gmean, gsd, gcv, median, min, max, unit, error_bar, error_type, comment` |
| `interventions.tsv` | `study, source, name, subjects, measurement, calculation, substance, tissue, method, choice, route, form, application, time, time_end, interval, doses, time_unit, count, mean, sd, se, cv, gmean, gsd, gcv, median, min, max, unit, error_bar, error_type, comment` |
| `outputs_<source>.tsv` | `study, source, subjects, interventions, measurement, calculation, substance, tissue, method, choice, time, time_unit, count, mean, sd, se, cv, gmean, gsd, gcv, median, min, max, unit, error_bar, error_type, comment` |
| `timecourses_<source>.tsv` | `study, source, label, subjects, interventions, measurement, calculation, substance, tissue, method, choice, time, time_unit, count, mean, sd, se, cv, gmean, gsd, gcv, median, min, max, unit, error_bar, error_type, comment` |
| `scatters_<source>.tsv` | `study, source, name, subjects, x_interventions, x_measurement, x_substance, x_tissue, x_method, x_time, x_time_unit, x_mean, x_unit, y_interventions, y_measurement, y_substance, y_tissue, y_method, y_time, y_time_unit, y_mean, y_unit, comment` |

### 5.5 Rules

Subjects:

- The root subject `all` is required and has no parent. Every other subject has a `parent`, and the tree has no cycles.
- A subject with `count` = 1 is an individual. Any other count, including an unknown count, makes it a group.
- A child's count does not exceed its parent's count.

Characteristica are the baseline values of a subject (age, weight, sex, creatinine clearance). A `choice` row (for example `sex` = `M`) uses `count` for the number of subjects with that choice, and its numeric statistics are empty.

Interventions:

- `name` is unique and is the reference used by the `interventions` columns.
- Dosing interventions use `route`, `form`, `application`, the schedule columns and the statistics (a fixed dose of 100 mg is `mean` = 100, `unit` = mg). Non-dosing interventions (circadian status, fasting, smoking, body position) use `measurement` and `choice`.
- Schedule: `time` is the first administration, `interval` the dosing interval, `doses` the number of administrations, and `time_end` the end of a continuous administration. An irregular schedule is a `;`-separated list in `time` (`0;12;40`) with `interval` and `doses` empty. `time`, `time_end` and `interval` use `time_unit`.
- `subjects` is optional. It is set when the dose statistics describe a specific subject, such as body-weight-adjusted doses with `sd` or `min` and `max`.

Outputs and timecourses:

- `interventions` is a comma-separated list of intervention names.
- In `timecourses_*`, `label` is required. A series is the set of rows with the same label. All rows of a series share `subjects`, `interventions`, `measurement`, `calculation`, `substance`, `tissue` and `method`. Labels are unique across the study, and a time point appears at most once per series.

Scatters: each row is one point. The axes have their own interventions because a scatter typically plots a baseline value (no intervention) against a PK parameter. `name` labels the scatter dataset and is unique across the study.

Statistics:

- When the effective count is 1, only `mean` (or `choice`) is allowed. `sd`, `se`, `cv`, `gmean`, `gsd`, `gcv`, `median`, `min` and `max` must be empty.
- With `calculation` = `unspecified summary`, only `mean` is allowed.
- `error_bar` requires `error_type`. Types `sd` and `se` require `mean`, and `gsd` requires `gmean`. The reported column of the same type must be empty.
- `min` must not exceed `max`. `median` and `mean` outside `[min, max]` give a warning.
- Negative values are rejected where the vocabulary forbids them.

Row order (natural sort, so `Tab2` sorts before `Tab10`; remaining ties are broken by the full row text):

| File | Sort keys |
|---|---|
| `subjects.tsv` | Depth-first from `all`, children by name |
| `characteristica.tsv` | `subjects` (in subject order), `source`, `measurement`, `substance`, `choice` |
| `interventions.tsv` | `name` |
| `outputs_*` | `subjects`, `interventions`, `measurement`, `calculation`, `substance`, `tissue`, `method`, `choice`, `time` |
| `timecourses_*` | `label`, `time` |
| `scatters_*` | `name`, `subjects` |

## 6. study.json

```json
{
  "format": 2,
  "reference": {"pmid": "27129716"},
  "creator": "changlinh",
  "curators": [{"user": "changlinh", "rating": 1}, {"user": "mkoenig", "rating": 2.5}],
  "collaborators": [],
  "licence": "closed",
  "access": "private",
  "provenance": {"kind": "manual_curation"},
  "issue": 2158,
  "release": {"pkdb_id": "PKDB01237", "date": "2026-09-28"},
  "descriptions": ["Verbatim quote from the paper."],
  "comments": [{"user": "mkoenig", "text": "..."}],
  "notes": {
    "subjects": {"descriptions": [], "comments": []},
    "interventions": {"descriptions": [], "comments": []}
  }
}
```

- `format` is the format version.
- `reference` holds the PubMed ID and/or DOI and is the single source of truth for which publication the study describes. Without a PubMed ID or DOI, the reference is manual and `reference.json` is its only record.
- `creator`, `curators` (user and rating 0 to 5), `collaborators`, `licence`, `access` and `provenance` keep today's meaning. `provenance` uses the existing kinds `manual_curation`, `data_import` and `automatic_curation` (method, version, assets, run id).
- `issue` is the number of the study's GitHub issue (section 12).
- `release` exists only for finished studies: `pkdb_id` is the PKDB identifier and `date` the release date. It replaces the v1 `sid` and `date` fields and the entries of `study_identifiers.json`.
- `descriptions` and `comments` describe the study. `notes` holds the descriptions and comments per table kind (`subjects`, `interventions`, `characteristica`, `outputs`, `timecourses`, `scatters`), which v1 stored in `groupset`, `interventionset` and similar sections.
- The study's identifier `<substance>/<name>` and its name are derived from the folder location and are not stored. Data entities are not allowed in `study.json`.
- The file is written with a fixed key order, 2-space indentation and a final newline.

`reference.json` keeps today's format and is the saved snapshot of the publication's metadata, including manual corrections from the Reference dialog. Its `pmid` and `doi` are checked copies: validation, upload and the curation app compare them with `study.json` and fetch a fresh snapshot on mismatch, as `sync_reference` does today.

## 7. review.json

```json
{
  "status": "in_review",
  "reviewers": ["mkoenig"],
  "items": [
    {
      "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
      "kind": "uncertainty",
      "state": "resolved",
      "target": {"file": "timecourses_Fig2.tsv", "rows": {"label": "caf_plasma_D1"}, "column": "sd"},
      "acknowledges": "sd_se_mismatch",
      "text": "The legend does not say whether the error bars are SD or SE.",
      "author": "mkoenig",
      "agent": "claude-opus-5-5",
      "created": "2026-10-05T10:12:00Z",
      "thread": [{"author": "mkoenig", "created": "2026-10-06T07:58:00Z", "text": "Methods section: SD."}],
      "resolved_by": "mkoenig",
      "resolved": "2026-10-06T08:00:00Z"
    }
  ]
}
```

- `status` is `draft`, `in_review` or `approved`. `reviewers` lists the reviewing users.
- `kind` is `question` (unclear, needs a person), `uncertainty` (low-confidence extraction or digitization) or `issue` (known problem, such as an inconsistency in the paper).
- `state` is `open`, `resolved` or `dismissed`. `resolved_by` and `resolved` are set when the state leaves `open`.
- `target` is optional (missing means the whole study). `file` names a file of the study (a table for `rows` and `column`), `rows` is a column-to-value filter that may match several rows (for example a series by `label`), and `column` names a column. A filter survives re-sorting and edits. A `key` instead of `rows` and `column` names a part of a file without rows, such as a dataset of a WebPlotDigitizer project, so that an acknowledgement covers exactly one warning.
- `author` is the responsible person. `agent` is set when an AI wrote the item.
- `acknowledges` names a validation warning code. The validator then no longer reports that warning for the target, unless the item is `dismissed`.
- `id` is a ULID. Items are sorted by `id`.

Rules:

- A target that no longer matches any row is a warning.
- `approved` requires zero open items. `approved_by` and `approved` record the person who approved and when; they are set exactly when the status is `approved`, and setting it also requires zero validation errors and is refused for agents (section 4.4 of the [curation app design](2026-10-06-curation-app-design.md)).
- `access: public` requires a `release`, and `pkdb release` requires `approved`.

Concurrent additions on two branches can conflict at the end of the item list. This is rare because AI curation and review run one after the other. If it becomes a real problem, items move to one file each (`review/<id>.json`).

## 8. Schema module and generated artifacts

A new package `pkdb.studyformat` in `python/src/pkdb` is the single source of truth. It declares:

- Pydantic row models for `subjects`, the common observation row and its extensions for interventions, outputs, timecourses and scatters, plus the `study.json` and `review.json` models. Each column has a type, a description, an example and whether it is required.
- The file naming rules (section 4 and 5.2) and sort keys (5.5).
- Declarative relationships: `subjects.parent` and every `subjects` column refer to `subjects.name`; every `interventions`, `x_interventions` and `y_interventions` entry refers to `interventions.name`; vocabulary columns refer to their vocabulary kind; `source` refers to an image file; review targets refer to tables, rows and columns.

Generated from the module, never written by hand:

- The workbook template (section 10.2).
- JSON Schema for `study.json`, `review.json` and every row type (`pkdb schema export`), which is the contract for AI agents.
- The column reference page in the documentation.

The validator, the formatter, the reader and the workbook generator all read the relationships and column definitions from this module.

## 9. Validation

One run collects all issues instead of stopping at the first. Layers:

1. Layout: required files, no unknown data files or sheets, images for every source.
2. Format: canonical TSV and JSON form, exact headers, `study` and `source` consistent with folder and file names.
3. Rows: types and enums, required columns, statistics rules (5.5), unit syntax.
4. Relationships: every declared reference resolves; the subject tree; counts; label uniqueness, series consistency and unique time points per series; duplicate rows; warnings for unused interventions and subjects; review targets and states.
5. Vocabulary: values and per-measurement rules (allowed units, choices, required time, negative values), against the vocabulary lock offline or the server online.
6. Postprocessing: derivations, unit normalization and PK derivation through the existing `prepare_study` stages.

Issues reuse `ValidationIssue` (code, severity, message, suggestions). `SourceLocation` points to file, row, column and header. Workbook rows match TSV lines one to one (header on line and row 1), so the same location identifies the TSV line and the workbook cell. Output goes to the terminal, the curation app and `--json`.

The same code runs on workbook save in the curation app, in `pkdb validate`, in the pkdb_data pre-commit hook, in pkdb_data CI and on the server for every upload.

## 10. Tooling

### 10.1 Commands

| Command | Purpose |
|---|---|
| `pkdb format [paths] [--check]` | Write canonical TSV and JSON: headers, column order, row order, numbers, empty cells, `study` and `source` columns, removal of empty observation files. `--check` reports and exits non-zero without writing. |
| `pkdb validate [paths] [--json]` | Run section 9. |
| `pkdb tables open\|sync\|add <study>` | Build and open the workbook, sync it, or add a `<kind>_<source>` table or, with `--raw <source>`, a raw table sheet. |
| `pkdb study show\|patch\|reference` | Show and edit `study.json`: metadata, curators, notes, provenance, reference identifiers. |
| `pkdb review show\|add\|reply\|resolve\|dismiss\|reopen\|status\|acknowledge` | Show and edit `review.json`. |
| `pkdb reference ...` | Resolve and write `reference.json` (exists today). |
| `pkdb new <substance>/<name> --pmid N \| --doi D` | Create a study (section 12). |
| `pkdb move <old> <new>` | Rename or move a study, including its GitHub issue title. |
| `pkdb release <study>...` | Assign PKDB identifiers and release dates (section 12). |
| `pkdb registry` | List released studies with PKDB identifier, location and date. |
| `pkdb issues sync [--adopt] [--dry-run]` | Align GitHub issues with the repository (section 12). |
| `pkdb plot <study> [--source S] [--out DIR]` | Render the raw extraction and mapped rows of a source on the figure image for comparison. |
| `pkdb digitize import <study> <source> <file>` | Store a WebPlotDigitizer project as the raw extraction of a figure. |
| `pkdb check --staged` | Pre-commit entry point: sync state, format check and offline validation for studies with staged files. |
| `pkdb schema export` | Write the JSON Schema files. |
| `pkdb migrate <paths> --report <file>` | Convert v1 studies (section 15). |
| `pkdb upload` | Sync, format, validate and upload. |

The curation app calls the same functions as these commands.

### 10.2 Workbook

- File `<name>.xlsx` in the study folder, gitignored.
- Sheets `subjects`, `interventions`, `characteristica`, then the `outputs_*`, `timecourses_*` and `scatters_*` sheets in natural order. Sheet names equal the TSV file names without `.tsv`.
- One bold, frozen header row with filters. Each header cell has a comment with the column description from the schema.
- Text columns use the text number format so that spreadsheet applications do not convert values to dates.
- Dropdowns (data validation) for references and vocabulary columns read their lists from a hidden `_lists` sheet, which avoids the 255-character limit of inline lists.
- A very hidden `_base` sheet stores the TSV content the workbook was generated from, together with the format version and the generation time. It is the base for the 3-way merge.
- Sheets whose names start with `_` (other than `_lists` and `_base`) are local scratch sheets. They are never synced and are kept when the workbook is regenerated, as far as openpyxl preserves them (values, formulas and basic formatting; charts and images are not guaranteed).
- A new table is added with "Add table" in the curation app or `pkdb tables add`, or by copying a sheet in the spreadsheet application and renaming it. Sync checks the header.

### 10.3 Sync engine

The engine compares the base B (from `_base`), the workbook content W and the TSV files T.

| State | Action |
|---|---|
| No workbook | Generate it from T. |
| W = T | In sync. If B differs (the base could not be written while the workbook was open), update the base when the workbook is closed. |
| W changed, T = B | Write W to the TSVs in canonical form. The base is updated when the workbook is closed (previous row). |
| T changed, W = B | Regenerate the workbook from T. If it is open (lock files `~$<file>` or `.~lock.<file>#`), ask the user to close it. |
| W and T changed | Line-based 3-way merge per file on canonical TSV lines, the same algorithm git uses. A clean merge is written to the TSVs and the workbook is regenerated when closed. On conflicts nothing is written; the conflicting rows are listed with sheet, row and both versions, and the user keeps one side or edits the workbook. |

Rules:

- The engine never overwrites a workbook that has changes not yet in the TSVs.
- All writes are atomic (temporary file and rename).
- A formula cell is stored as its cached value, and an info issue lists those cells. A formula without a cached value is an error, because the workbook was not saved by a spreadsheet application.
- An unknown sheet name is an error.

### 10.4 Formulas

Committed tables hold the values reported in the paper or digitized from figures. Calculations move to postprocessing (section 11.2), where they are done the same way for every study and marked as calculated.

| Formula use in v1 | Handling in v2 |
|---|---|
| SD from a digitized error bar (`ABS(mean_pm - mean)`) | `error_bar` and `error_type`; postprocessing derives the value |
| `se = sd/SQRT(n)`, cv, variance | Postprocessing from `count` |
| Unit rescaling | Record the reported unit; the backend normalizes units |
| Labels built with `&` | Not needed; labels are entered directly |
| Times such as `=1/12` | Use a fitting time unit |
| `AVERAGE` and `STDEV` over individuals | Postprocessing, or not stored |
| One-off rescaling (`=U5/AVERAGE(...)`) | Value plus `comment` |

Formulas remain usable in the workbook as a scratch aid. Only the computed value is stored.

### 10.5 Curation app

`pkdb curate` becomes the writer for `study.json` (metadata forms), `review.json` (review items) and the TSVs (through the sync engine). This replaces the "never edits source files" rule of the 2026-09-24 local curation design.

- The existing 1-second watcher runs sync, format and validate on every change and lists issues with sheet and cell.
- Actions: Open tables, Add table, sync status, conflict resolution, metadata editor, reference dialog (exists today), review items with their target rows and the figure image, "acknowledge" on validation warnings, and the `pkdb plot` comparison.

The design of the app, including the exact commands of `pkdb study`, `pkdb review`, `pkdb digitize` and `pkdb plot`, is the [curation app design](2026-10-06-curation-app-design.md).

### 10.6 Workbook and sync decisions

Decided on 2026-10-06 while planning sub-project 3:

- Saving the workbook twice while it stays open must never conflict with the first sync. Besides the `_base` sheet, the engine keeps a hidden sync state file `.<name>.xlsx.pkdb-base` beside the workbook. It holds the base of every table written from the workbook since the workbook was generated, keyed by the generation identifier stored in `_base`, and overrides `_base` for those tables. The workbook is rewritten only when the tables hold content the workbook lacks (a pull, a merge, a new or removed file), not merely to refresh the base, so formatting and scratch formulas in data sheets survive ordinary syncs. Regeneration starts a new generation and removes the sync state file.
- Dropdowns of the reference columns (`subjects`, `interventions` and the scatter axes) read the live `name` column of the `subjects` and `interventions` sheets, so new rows appear immediately. Vocabulary and choice lists come from the hidden `_lists` sheet and leave out deprecated measurements. Dropdowns suggest values but never block other input; validation stays with `pkdb validate`.
- Numbers with more than 15 significant digits are written as text cells, because LibreOffice saves at most 15 significant digits. Every other number is a number cell, so TSV to workbook to TSV is lossless in Excel and LibreOffice.
- Excel limits sheet names to 31 characters and compares them ignoring case. Layout validation therefore rejects table file names longer than 31 characters before `.tsv` and table file names that differ only in case.
- A cell the spreadsheet application converted is an error at its cell: a date, a percentage (20% is stored as 0.2), an error value such as `#DIV/0!`, a line break or a tab in text, or a value outside the header columns.
- `pkdb tables add` adds an empty sheet with the template header, which is not a file yet: the TSV appears when the sheet has a row and is synced, because the formatter removes tables without rows.
- `pkdb tables sync --keep workbook|tables` resolves the conflicting parts of every conflicting table to one side and still merges the other changes; `--check` reports the planned changes without writing.
- `pkdb upload` syncs and formats a format 2 folder before preparing it and stops on conflicts. `pkdb validate` and `pkdb prepare` never write; they report workbook changes that are not yet in the tables.

## 11. Postprocessing and canonical model

### 11.1 Reading

A single TSV reader reads every cell as text and types it through the schema module. It builds the canonical study directly:

- A subject with `count` = 1 becomes an `Individual` whose group is its `parent`. Any other subject becomes a `Group`.
- `characteristica` rows become the characteristics of their subject.
- `interventions` rows become `Intervention` with the schedule fields and an optional subject.
- `outputs_*` rows become measurements with `output_type` `output`.
- `timecourses_*` rows become measurements with `output_type` `timecourse`, grouped by `label` into timecourses. The label persists.
- Each `scatters_*` row becomes an x and a y measurement labelled `<name>_x` and `<name>_y`, and the scatter dataset pairs them by subject.
- `cv` and `gcv` are divided by 100.

After cutover, the v1 importer is deleted: the mini-language interpreter (`importers/expressions.py` and the template logic of `importers/folder.py`), the workbook reader `importers/workbook.py` and the hidden TSV export `tsv.py`. openpyxl remains only in the workbook generator and sync engine.

### 11.2 Derivations

Derivations extend `domain/statistics.py`. Reported values are never overwritten. Derived values are marked `calculated` with `derived_from`.

- An empty `count` takes the subject's count and is marked as inherited.
- `sd`, `se` and `cv` are derived from each other with `count` and `mean` (exists today).
- `gsd` and `gcv` are derived from each other: gcv = sqrt(exp(ln(gsd)^2) - 1), gsd = exp(sqrt(ln(1 + gcv^2))).
- From `error_bar`: `sd` or `se` = |error_bar - mean|, and `gsd` = max(error_bar / gmean, gmean / error_bar).
- Over-determined values (for example reported `sd` and `se`) are checked against each other, and a mismatch is a warning that a review item can acknowledge.
- Not derived: arithmetic from geometric statistics or the reverse, and mean or SD from median, range or IQR.
- Unit normalization and PK derivation from timecourses remain as today.

### 11.3 Canonical model, database and API

- `Statistics` loses `value` and gains `gmean`, `gsd` and `gcv`. n = 1 and unspecified summaries are stored in `mean`.
- `Intervention.time` becomes a number or a list of numbers. `interval`, `doses` and an optional subject reference are added. Schedule strings are no longer accepted.
- Studies are identified by `<substance>/<name>`. The canonical metadata carries the reference identifiers, the issue number, the release block and the review status and items.
- The processing version goes from 8 to 9.
- Database: an Alembic migration adds the new statistics, moves stored `value` into `mean`, removes `value`, and adds storage for the study identifier, release, issue and review data. Every study is re-uploaded after the data migration (section 15).
- API, coordinated with the ongoing API redesign: responses carry `gmean`, `gsd` and `gcv` and no `value`; the study resource exposes the identifier, PKDB identifier, release date, issue link, review status and review items (read-only). Uploads of non-canonical bundles are rejected.
- Frontend: show the new statistics and the release and review state, and plot timecourses by label. The Python client (polars) and the read-only MCP tools return the new fields.

## 12. Identity, lifecycle, release and GitHub issues

Identity: every study is identified by `<substance>/<name>`, its folder location (for example `albuterol/Guo2016`). Names may repeat across substances.

Lifecycle: `draft` -> `in_review` -> `approved` (review status in `review.json`) -> released (`release` block in `study.json`). Only released studies have a PKDB identifier. A released study that is corrected later keeps its `pkdb_id` and returns to `in_review`.

Release:

- `pkdb release <study>...` requires `approved`, no open review items and a clean validation. It assigns the next free PKDB numbers (the maximum over all studies plus one) and today's date.
- Releases go through a pull request. Branch protection requires release pull requests to be up to date with `develop`, and CI checks that PKDB identifiers are unique, so two releases cannot take the same number.
- `pkdb registry`, the documentation and the API derive the list of released studies from the `release` blocks.

GitHub issues in matthiaskoenig/pkdb_data:

- Every study has exactly one issue titled `<substance>/<name>`. `study.json` stores its number.
- Labels: the substance label (the parent folder name) and the workflow label for the review status: `curate` (draft), `check` (in_review), `approved` (approved). A released study's issue is closed as completed.
- Assignees: the curators and reviewers, translated to GitHub logins through the user roster on the server (imported GitHub references).
- `pkdb new` creates the issue, or adopts an existing issue with the exact title, and stores its number. `pkdb move` renames the folder and the issue together.
- A pkdb_data workflow on pushes to `develop` and nightly runs `pkdb issues sync`. It aligns titles, labels, assignees and open or closed state with the repository. It only changes GitHub and never commits. Users without a GitHub login in the roster produce a warning.
- During migration, `pkdb issues sync --adopt` matches existing issues by exact title or the known prefixes ("Curate ", "Check ", "Check and curate "), renames them to the canonical title, records the number in `study.json`, and closes duplicates with a link to the kept issue. Issues that do not belong to a study are left alone.

### 12.1 Identity in URLs, storage and upload

Decided on 2026-10-05 while planning sub-project 2:

- URLs use two path segments: `/api/v2/studies/{substance}/{name}` (with `/publication` and `/validate` below it) and the web page `/data/{substance}/{name}`. Released studies stay reachable by their PKDB identifier: `/data/PKDB01237` and the single-segment API routes answer with a permanent redirect (308) to the canonical URL, so existing links keep working. Single-segment routes keep serving and accepting format 1 studies until the cutover.
- Study folder names `publication` and `validate` are reserved and rejected by layout validation, because they collide with route segments.
- The database keeps one `sid` column holding `<substance>/<name>` for format 2 studies, plus `pkdb_id` (unique, nullable), `release_date`, `issue`, `review_status` and the review items. Study `name` is the folder name and `date` is the release date.
- Rename on re-upload: an upload of `caffeine/Harder1988` whose `release.pkdb_id` is `PKDB00198` takes over an existing row whose `sid` or `pkdb_id` is `PKDB00198`; its `sid` becomes `caffeine/Harder1988`. Uploads stay idempotent and no data reset is needed.
- Upload transport for format 2: the client sends the exact text of `study.json` and `reference.json` and every other file of the folder; the server writes them into a temporary `<substance>/<name>` folder and runs the same loader, validator and reader as the client, including the format check.

## 13. AI curation workflow

The contract for AI agents is the `pkdb` CLI (every command supports `--json`), the exported JSON Schema, the generated column reference, the vocabulary lock and a `pkdb-curation` agent skill in pkdb_data with an `AGENTS.md` for other agents. The skill describes the workflow and points to `pkdb schema export` instead of repeating the schema. No MCP write tools are needed.

Workflow for a new study:

1. `pkdb new <substance>/<name> --pmid N` creates the folder, `study.json` with provenance `automatic_curation` (model and run id) and the responsible person as creator, `reference.json`, `subjects.tsv` with `all`, `review.json` with status `draft`, and the GitHub issue.
2. The agent reads the PDF and saves the table and figure crops as `<name>_<source>.png`. It transcribes each table as printed into `<name>_<source>.tsv` and digitizes each figure into a WebPlotDigitizer project imported with `pkdb digitize import`, then maps the raw extractions into `subjects`, `characteristica`, `interventions`, `outputs_<Tab>` and `timecourses_<Fig>`. Every command runs with `--agent <model>`.
3. It runs `pkdb format` and `pkdb validate --json` until there are no errors. Each warning is fixed or acknowledged with a review item. `pkdb plot` renders the digitized series on the axes of each figure, and the agent compares the rendering with the image and corrects the data.
4. It records every assumption and every low-confidence value as a review item (`question` or `uncertainty`). Every digitized series gets an `uncertainty` item until a person has checked it. The status becomes `in_review`.
5. It commits as the `pkdb-ai` identity on its own branch and opens one pull request per study that links the study's issue and lists the tables, the review items and the validation summary.
6. A curator reviews in the curation app (review items with target rows, figure and plot comparison), resolves the items, edits through the workbook if needed, and sets `approved`. The pull request is merged, and the study is uploaded and later released.

Corrections of existing studies follow the same loop.

Guardrails: JSON files are written only through `pkdb` commands, and the canonical-form check in pre-commit and CI catches most hand edits. AI never uploads to production; uploads happen after a reviewed merge. Because every study is its own folder, branch and pull request, and there is no shared registry file, many agents can work in parallel without touching shared files.

## 14. pkdb_data repository

- `.gitignore`: `studies/**/*.xlsx`, spreadsheet lock files (`~$*`, `.~lock.*#`).
- `.gitattributes`: `*.tsv text eol=lf`, `*.json text eol=lf`, `*.pdf binary`, `*.png binary`.
- Pre-commit: a local hook runs `pkdb check --staged`. The existing generic hooks keep excluding `studies/`.
- CI (required check on `develop`): `pkdb format --check` and `pkdb validate --offline` with the pinned vocabulary lock on changed studies; repository-wide uniqueness of PKDB identifiers and issue numbers.
- Issue sync workflow (section 12) with `issues: write` permission.
- Documentation: the curation guide is rewritten for the v2 workflow and links to the generated column reference. The upload and backend commands stay documented in `pkdb`.

## 15. Migration and cutover

### 15.1 Converter

`pkdb migrate <paths> --report migration.json` converts from the entities the current parser has already resolved, not from the raw templates. Every resolved entity knows its sheet and row, which gives its source. Inline JSON entities take their source from their `image`, otherwise `Text`.

| v1 | v2 |
|---|---|
| Groups and individuals | `subjects.tsv`; individuals get count 1 and their group as parent |
| Group and individual characteristica | `characteristica.tsv`; individual `value` becomes `mean` |
| Interventions | `interventions.tsv`; `S<start>T<interval>R<n>` becomes `time`, `interval`, `doses` (R is the number of administrations, as in the OSP importer); `0\|12\|40` becomes `0;12;40` |
| Outputs | `outputs_<source>.tsv` |
| Timecourse outputs | `timecourses_<source>.tsv` with their labels |
| Scatter datasets | `scatters_<source>.tsv`, pairing the x and y outputs by subject |
| `value` | `mean` (n = 1 or `unspecified summary`) |
| `calculation_type: geometric mean` | `gmean` |
| `cv` | multiplied by 100 |
| Formula cells | cached values; where an `sd` or `se` cell is `ABS(X - mean)` on the same row, `error_bar` = X and `error_type` is set, and the `sd` or `se` cell is left empty |
| `sid`, `date`, `study_identifiers.json` | `release.pkdb_id` and `release.date` for registered studies |
| `reference` (PMID) | `reference.pmid`; DOI from `reference.json` |
| Section descriptions and comments | `notes` |
| `[user, rating]`, `[user, text]` | `{user, rating}`, `{user, text}` |
| Entry-level comments | `comment` column |
| xlsx and hidden TSVs | removed from the working tree; kept in history under tag `v1-final` |

The report lists for manual decisions: v1 groups with count 1 (they become individuals), `array` outputs, geometric means with `sd` or `cv` (arithmetic or geometric is unclear), every converted dosing schedule for a spot check, sheets with data that `study.json` never referenced, invalid JSON, studies with two PKDB identifiers or a registry path that does not exist, a `date` that differs from the registry date, folders with an xlsx but no `study.json`, non-PNG source images, and GitHub issues that could not be matched.

### 15.2 Equivalence gate

For each study, A is the v1 folder prepared with the current code and B the converted folder prepared with the new code. Both are normalized (subjects by name, measurements by natural key, timecourses by label, scatter pairs by subject) and compared with a relative tolerance of 1e-9 after applying the intended transformations of 15.1.

Each study is classified as identical, intended changes only (each change listed), mismatch (needs a manual fix) or invalid in v1.

### 15.3 Cutover

1. Fix studies that are invalid in v1 through normal pull requests. Merge or pause open curation pull requests.
2. Run the migration on a branch and iterate on manual fixes until no study has a mismatch. Tag `v1-final` on `develop`.
3. Merge the migration as one pull request, reviewed through the report, spot checks and green CI.
4. Run `pkdb issues sync --adopt --dry-run`, review the plan, then run it.
5. Re-upload all studies with processing version 9 to a staging database and compare counts and API output with production.
6. Keep `pkdb migrate` with the v1 reader until no v1 branches remain open, then delete all v1 code.

## 16. Testing

- Schema: unit tests for every row model and relationship rule. Snapshot tests that the JSON Schema, the workbook template and the column reference regenerate byte for byte.
- Formatter: `format(format(x)) == format(x)` on fixtures and the corpus. TSV to workbook to TSV gives identical bytes, tested with a headless LibreOffice save in CI.
- Sync engine: one test per state in 10.3, including conflicts, open workbooks, atomic writes and formula cells with and without cached values.
- Validator: one minimal broken fixture study per issue code. The full migrated corpus validates.
- Derivations: tests against hand-calculated values for sd, se, cv, gsd, gcv and error bars.
- Migration: golden conversions of acetaminophen/Abernethy1982 (mixed), caffeine/Harder1988 (inline), albuterol/Guo2016 (many formulas), a caffeine scatter study and an individual-level study; the full-corpus equivalence gate.
- Backend: the Alembic migration, ingestion of v2 bundles, rejection of non-canonical bundles, and API responses with the new statistics, without `value`, and with release and review data.
- Curation app: end-to-end browser tests of the metadata editor, review items, Open tables and sync status, and the plot comparison.
- Issue sync: tests against a mocked GitHub API, then a dry run on the real repository.
- pkdb_data CI: a branch with deliberately broken studies.

## 17. Sub-projects

| # | Sub-project | Depends on |
|---|---|---|
| 1 | Schema module, v2 reader, formatter and validator (`pkdb format`, `validate`, `schema export`) | none |
| 2 | Postprocessing and backend: statistics, `value` removal, schedules, identity, release and review storage, API, processing version 9 | 1 |
| 3 | Workbook generation and sync engine (`pkdb tables`) | 1 |
| 4 | Curation app: metadata editor, review UI, tables and sync UI, `pkdb plot`, `pkdb study`, `pkdb review` | 2, 3 |
| 5 | Migration converter, equivalence gate, `pkdb release`, `pkdb registry`, `pkdb new`, `pkdb move`, `pkdb issues sync`, cutover | 1, 2 |
| 6 | pkdb_data tooling: pre-commit, CI, `.gitignore` and `.gitattributes`, curation guide, AI skill and `AGENTS.md`, issue sync workflow | 1, 3, 5 |

Sub-project 5 can start once 1 and 2 are done, in parallel with 3 and 4. The cutover (15.3) happens when all six are finished.

## 18. Out of scope

- Shrinking the repository history (rewrite or LFS for PDF and PNG files). Once workbooks are no longer committed, growth slows; this can be decided separately.
- A spreadsheet grid editor in the web frontend.
- MCP write tools. The CLI is the AI interface.
- Row-level provenance columns.
- The API redesign beyond the changes listed in 11.3.
