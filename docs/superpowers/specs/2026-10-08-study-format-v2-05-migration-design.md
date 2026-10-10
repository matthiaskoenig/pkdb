---
search:
  exclude: true
---

# Study format 2 migration, GitHub issues and study lifecycle

Date: 2026-10-08. Status: Draft for review. Sub-project 5 of [Study format v2](2026-10-05-study-format-v2-design.md) (section 17), which specifies the converter (15.1), the equivalence gate (15.2), the cutover (15.3), identity, release and GitHub issues (12) and the commands (10.1). This document records the decisions taken while planning it on 2026-10-08 and how the parts fit the code. Where it is silent, the main spec applies.

## 1. Parts

The sub-project is split into three parts, each with its own plan and pull request:

| Part | Content | Depends on |
|---|---|---|
| A | `pkdb migrate`: converter, equivalence gate, report, move of folders without `study.json`, cutover runbook | sub-projects 1 and 2 |
| B | GitHub issue client, `GET /api/v2/curators`, `pkdb issues sync [--adopt]` | sub-project 2 |
| C | `pkdb new`, `pkdb move`, `pkdb release`, `pkdb registry`, server takeover by issue number | B |

Part A comes first because the cutover needs iterations on the corpus and manual fixes in pkdb_data, which take the longest. The cutover itself runs after sub-project 6 by the runbook of part A (section 7).

## 2. Corpus facts

Found in pkdb_data on 2026-10-08 (branch `merge-final`):

- 1760 folders `studies/<substance>/<name>/` in 63 substance folders. 1581 have a `study.json`, 20 of which are invalid JSON. 179 have none: 149 hold only PDF or PNG files, 24 hold an xlsx, 2 are empty.
- 1512 study folders have a `reference.json`.
- `studies/study_identifiers.json` maps 1233 PKDB identifiers to `[<substance>/<name>, <date>]`. 1210 `study.json` files hold a `PKDB` sid.
- 8646 hidden TSV files; 32 of their sheet names do not match the source pattern of the main spec 5.2 (for example `Fig1.2`, `Tab`).
- No folder is format 2 yet.

Code facts that the design relies on:

- `preparation.prepare()` runs the v1 importer (`importers/folder.load_folder`, `parse_bundle`) and `domain/validation.prepare_study`. Every resolved entity keeps a `SourceLocation`: workbook rows have the file, sheet and physical row; hidden TSV rows have the file `.<name>_<sheet>.tsv` and no sheet; inline JSON entities have `file="study.json"` and a path, and their `image` resolves to a file name. Schedules are already parsed into time, interval and doses, and v1 `value` already becomes `mean`.
- The v1 workbook reader opens workbooks with cached values only (`data_only=True`).
- The format 2 writers exist: table specs (`studyformat/tables.py`), `render_tsv`, `format_folder`, `StudyMetadata` and `canonical_study_json`, `canonical_review_json`, the reference resolver (`references.sync_reference`) and the revision-checked writers.
- The only GitHub code is the read-only assignee lookup `curation/github.py`. GitHub logins of users are stored on the server (`User.github`) but listed only by an administrator route.
- The server already takes over a stored study by `release.pkdb_id` and by publication and source (`services/ingestion.py`), and enforces unique `pkdb_id`.

## 3. Part A: converter

A new package `python/src/pkdb/migration/` converts one v1 folder at a time. It reads the entities that the v1 importer resolved; it never interprets the template mini-language a second time.

Conversion of one study:

1. Load v1: `load_folder` and `parse_bundle` give the resolved `CanonicalStudy` with the `SourceLocation` of each entity.
2. Read what the canonical study does not keep: the raw v1 `study.json` (creator, curators, licence, access, descriptions, comments, section notes, PubMed ID), and every workbook a second time with formulas (openpyxl without `data_only`). A cell `ABS(X - mean)` in an `sd` or `se` column, where `mean` is the mean cell of the same row, becomes `error_bar` = X with `error_type` `sd` or `se`, and the `sd` or `se` cell stays empty.
3. Assign the source of each row: the sheet name for a workbook row, the sheet name taken from the file name for a hidden TSV row, and for an inline JSON entity the source of its `image`, otherwise `Text`. For outputs, timecourses and scatters the source names the file, so a sheet name outside the source pattern refuses the study (`not_converted`) and is listed; the curator renames the sheet in v1 and reruns. In `subjects`, `interventions` and `characteristica`, where `source` is curator data, a row from a sheet outside the pattern (such as `TabGroups`) takes the source of its `image`, otherwise an empty source.
4. Write the format 2 files into a temporary folder: the tables through the table specs and `render_tsv`, then `format_folder`. Each source image is copied as `<name>_<source>.png`; a JPG image is converted to PNG; any other image type refuses the study (`not_converted`). `study.json` is written through `StudyMetadata` with the mapping of the main spec 15.1. An existing `reference.json` is kept; a missing one is written by the reference resolver, and a failure makes the study `not_converted`.
5. Release and review. The `release` block comes from `study_identifiers.json`. The registry wins over the v1 `sid` and `date`; a difference is listed. `review.json` is `approved` for every study in the registry, with the maintainer named by `--approver` as its reviewer and `approved_by`, and the registry release date as `approved`. Every other study gets `draft`. Part B moves unreleased studies whose issue has the `check` label to `in_review` (section 5).

Command:

```
pkdb migrate <paths> --registry studies/study_identifiers.json --approver <user>
             --report migration.json [--dry-run] [--jobs N]
```

- `<paths>` are the `studies` folder, substance folders or study folders. Format 2 folders are skipped and listed.
- The run is incremental and in place. A study whose gate result is `identical` or `intended` replaces its v1 folder: the v1 `study.json`, the xlsx and the hidden TSV files are removed, the format 2 files are written. Every other study stays v1, so fixing it and rerunning converts it. `--dry-run` writes only the report.
- A folder without `study.json` moves to `papers/<substance>/<name>/` with all its files; an empty folder is removed. The report lists each move, and the folders that held an xlsx, so that a curator can start them again with `pkdb new` (section 6).
- `study_identifiers.json` is deleted by the run after which every registry entry is in the `release` block of a format 2 study.
- `--jobs N` converts studies in a process pool, by default with one process per CPU.
- The command needs the network only to resolve a missing `reference.json`. It writes nothing outside the given paths, `papers/` and the report.

## 4. Part A: equivalence gate and report

The gate runs on the temporary folder before anything replaces the v1 folder.

- A is the v1 folder prepared by today's `prepare()`. B is the converted folder read by the format 2 reader and prepared by the same `prepare_study`. B must also pass the format check and offline validation; an error makes the study a `mismatch`.
- Both are normalized: subjects by name, measurements by their natural key (subject, interventions, measurement type, substance, tissue, method, time, label), timecourses by label, scatter pairs by subject. Numbers compare with a relative tolerance of 1e-9. Text compares exactly after the one-line rule of the converter: a run of whitespace becomes one space, the ends are trimmed and a blank cell is empty.
- Intended changes are listed per study and do not fail the gate: a v1 group with count 1 becomes an individual; an `ABS(X - mean)` cell becomes `error_bar`, so `sd` or `se` is `calculated`; a geometric mean becomes `gmean`; an `array` output becomes an output, or a timecourse when it has a label; scatter outputs are renamed `<dataset>_x` and `<dataset>_y`; a JPG image becomes PNG; a characteristic of a measurement that needs a time, such as a concentration, gets time `NR` and keeps a v1 time unit if it has one, because v1 characteristica have no time (`time_not_reported`); a characteristic, output or timecourse point of a measurement of dtype `numeric` or `numeric_categorical` that holds neither a choice nor any statistic is dropped (`valueless_row`); text that the one-line rule changes is listed (`whitespace`).
- Dropped rows: a repeated row is dropped only because it is empty itself; a repeat with data stays and fails format 2 validation as `duplicate_row`. Rows that carry information without a value stay as well and fail format 2 validation for a curator: a row with a statistic but no central value, such as only an `sd`, or with only a count, a scatter point, and a row of a measurement whose existence is the information, that is a measurement named `abstinence` or `fasting` or starting with one of them and a space; in the bundled vocabulary these are the numeric `abstinence`, `abstinence alcohol`, `abstinence marijuana`, `abstinence medication`, `abstinence oral contraceptives`, `abstinence smoking` and `fasting (duration)`. The gate takes the dropped rows from the parsed v1 study, before `prepare` inherits counts, and checks each with a rule of its own: a dropped record with a choice or any statistic is a difference (`dropped record with data`), so the study is a `mismatch`.
- Metadata (sid, release, review, reference, attachments, notes) is not compared: the sid, release and review are new by design. Counts inherited from the subject need no rule, because both sides are prepared by the same `prepare_study`.

Each study gets one class:

| Class | Meaning | Written |
|---|---|---|
| `identical` | no difference | yes |
| `intended` | only intended changes, each listed | yes |
| `mismatch` | the data differs, or B is invalid; at most 50 differences listed with path, A and B | no, stays v1 |
| `invalid_v1` | A cannot be prepared; its issue codes listed | no, stays v1 |
| `not_converted` | the converter refused the study, with the reason | no, stays v1 |

`not_converted` extends the four classes of the main spec 15.2, because its fix differs: the v1 study is corrected so that the converter can read it.

The report has two files written from the same data. Both name the vocabulary of the run (version and SHA-256 hash), because the conversion depends on it; a rerun with another vocabulary than the earlier runs is a warning. `migration.json` holds per study the class, the changes, the differences and the manual decisions, plus the skipped format 2 folders and the moves to `papers/`; each dropped row is a decision of its own with its table, its v1 file, sheet and row or its place in `study.json`, label, subject, measurement, substance, tissue and comment. `migration.md` is for review in the pull request: counts per class, one table per class, and the lists for manual decisions of the main spec 15.1 (v1 groups with count 1, `array` outputs, geometric means with `sd` or `cv`, every converted dosing schedule, sheets that `study.json` never referenced, studies with two PKDB identifiers, registry paths that do not exist, dates that differ from the registry, non-PNG images, sheet names outside the source pattern, folders moved to `papers/`, and the dropped rows without any value of the studies that are written, or in a dry run would be, as one line per study, table and v1 file with the row ranges, the count and the measurements; the dropped rows of other studies are only counted).

## 5. Part B: GitHub issues

- Client: `python/src/pkdb/issues/github.py` on httpx2. It lists the issues of the repository in all states with paging, creates and updates issues (title, labels, assignees, state with reason), comments, and creates missing labels. The token comes from `GH_TOKEN` or `GITHUB_TOKEN`, the repository from `PKDB_ISSUES_REPO` (default `matthiaskoenig/pkdb_data`). Writes run one after another; the client waits for `Retry-After` and for the reset of an exhausted rate limit. The read-only assignee lookup of the curation app moves onto this client.
- Roster: the server gets `GET /api/v2/curators`, readable with any API key, which lists the username, name and GitHub login of every curator. Logins of users whose `github_visible` is false are listed too, because assigning them on GitHub shows them anyway; the documentation says so. The Python client exposes it as `curators()`. The pkdb_data workflow reads it with the secret `PKDB_API_KEY`.
- Desired state of the issue of each format 2 study: title `<substance>/<name>`; the substance label and exactly one workflow label, `curate` (draft), `check` (in_review) or `approved` (approved); as assignees exactly the curators and reviewers with a GitHub login, and a warning for each one without; closed as completed when the study has a `release` block and is `approved`, open otherwise.
- The sync changes only workflow labels and substance labels (labels named like a substance folder); other labels stay. An issue is matched by the `issue` number in `study.json`. A study without an issue is a warning, two studies with one issue number are an error, and an issue that no study names is left alone.
- `pkdb issues sync [--dry-run] [--json]` computes the plan of changes and applies it unless `--dry-run`. It never writes files.
- `pkdb issues sync --adopt --user <user>` is the only mode that writes files, through the revision-checked writers. For each study without `issue` it matches issues by the exact title or a title with a known prefix (`Curate `, `Check `, `Check and curate `). Among several matches it keeps the exact title over a prefixed one, then an open issue over a closed one, then the lowest number; it renames the kept issue to the canonical title and closes the others as not planned with the comment "Duplicate of #N". It records the number in `study.json`. An unreleased study whose kept issue has the `check` label becomes `in_review`. A study without a match gets a new issue.
- The workflow in pkdb_data that runs the sync on pushes to `develop` and nightly belongs to sub-project 6.

## 6. Part C: study lifecycle

- `pkdb new <substance>/<name> (--pmid N | --doi D) --licence open|closed --access public|private [--user U] [--agent A] [--no-issue]` creates a study. Licence and access are required, so that no default publishes a study by accident. It refuses an existing study folder and reserved or invalid names. When `papers/<substance>/<name>/` exists, its PDF and images move into the study; other files stay there and are named in the output, because a v1 `<name>.xlsx` would collide with the generated workbook; an emptied paper folder is removed. It writes `study.json` (creator: the author; provenance manual, or `automatic_curation` with `--agent`), `reference.json` through the resolver, `subjects.tsv` with the row `all` and `review.json` with status `draft`. Then it creates the issue, or adopts an issue with the exact title, and records its number; `--no-issue` leaves that to `pkdb issues sync --adopt`.
- `pkdb move <old> <new>` renames or moves a study. It refuses an existing target and an open workbook. It renames the folder and every file named after the study (PDF, images, raw tables, `.wpd.json`), rewrites the image name in each `.wpd.json` and the file names of the targets in `review.json`, and runs `format`, which rewrites the `study` column. It renames the issue right away; without a GitHub token it warns, because `pkdb issues sync` aligns titles anyway.
- `pkdb release <study>... [--date D]` requires status `approved`, no open review items and no validation errors, and refuses a study that already has a `pkdb_id`. It assigns the next free numbers in argument order, starting after the largest `pkdb_id` of all `release` blocks in the repository, with today's date unless `--date` is given, and writes `study.json` with a revision check.
- `pkdb registry [--json] [--check]` lists the released studies by `pkdb_id` with location and date. `--check` exits non-zero when two studies share a `pkdb_id` or an issue number; pkdb_data CI (sub-project 6) runs it.
- Commands that scan all studies find the repository by walking up from the current folder to the folder that contains `studies/`, or take `--root`.
- Server: an upload whose sid matches no stored study and whose `pkdb_id` claims none takes over a stored format 2 study with the same `issue` number and another sid, when the uploader may write it. This reuses the takeover path of `pkdb_id`, so a moved study keeps its row whether or not it is released, and nothing on the server changes before the move is merged and uploaded. An Alembic migration adds a unique index on `studies.issue` for rows where it is set.

## 7. Cutover runbook

Part A adds `docs/study-format-2-cutover.md`, run after sub-project 6:

1. Fix the invalid `study.json` files and the studies that are invalid in v1 through normal pull requests. Merge or pause open curation pull requests.
2. On a branch, run `pkdb migrate --dry-run`, then fix v1 studies or the converter; run it for real and rerun until no study is `mismatch`, `invalid_v1` or `not_converted`. Tag `v1-final` on `develop`.
3. Merge the migration as one pull request, reviewed through `migration.md`, spot checks and green CI.
4. Run `pkdb issues sync --adopt --dry-run`, review the plan, then run it.
5. Re-upload all studies with processing version 9 to a staging database and compare counts and API output with production.
6. Delete the v1 code once no v1 branch is open.

## 8. Testing

- Converter: synthetic v1 fixtures in `python/tests`, one per pattern of the main spec 15.1: a mixed study, an inline study, a study with many formulas including `ABS(X - mean)`, a scatter study, an individual-level study, dosing schedules, a group with count 1, a geometric mean and JPG images. Each has its expected format 2 output, compared byte for byte. The real studies named in the main spec 16 are not copied into the repository, because `acetaminophen/Abernethy1982` and `caffeine/Harder1988` have licence `closed`.
- Gate: one fixture per class, and unit tests of the normalization and the tolerance.
- Corpus: opt-in tests with `PKDB_STUDY_CORPUS`, as in `backend/corpus_tests`, run the gate on `acetaminophen/Abernethy1982`, `caffeine/Harder1988`, `albuterol/Guo2016`, a caffeine scatter study and an individual-level study, and on the whole corpus.
- GitHub: sync, adopt, `pkdb new` and `pkdb move` against a mocked GitHub API through an httpx2 mock transport; the client's paging and rate-limit waits.
- Backend: the curators route, the takeover by issue number and the migration of the unique index.
- Lifecycle: release numbering with gaps and with several studies in one call, its refusals, `pkdb registry --check` with duplicates, and `pkdb move` with review targets, `.wpd.json` files and raw tables.
