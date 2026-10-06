---
search:
  exclude: true
---

# Study format v2, sub-project 2: canonical model, postprocessing and backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make study format 2 folders preparable, uploadable and servable end to end: a reader from `pkdb.studyformat` to the canonical model, the statistics redesign (no `value`; `gmean`, `gsd`, `gcv`, digitized error bars), explicit dosing schedules, study identity `<substance>/<name>` with release, issue and review data, processing version 9, and the matching database, API, MCP and frontend changes.

**Architecture:** The canonical model in `python/src/pkdb/schemas/study.py` stays the single contract between client, server and database. Changes land additively first (new columns, new fields), then the breaking switch (remove `value`, structured schedules, processing version 9) happens in one task across client and server so every commit keeps both test suites green. The format 2 reader maps `LoadedStudy` rows into the canonical model; the server runs the same loader, validator and reader on uploaded files. Format 1 keeps working through the existing importer, which maps its legacy fields into the new canonical fields.

**Tech Stack:** Python 3.14, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL 18, Starlette/FastAPI backend (`backend/src/pkdb_server`), Vue 3 + TypeScript frontend (`frontend/`), pytest, vitest/playwright (frontend), ruff, ty.

**Spec:** `docs/superpowers/specs/2026-10-05-study-format-v2-design.md`, sections 6, 7, 11, 12 and 12.1 (identity decisions).

## Global Constraints

- Python client: `cd python && uv run --locked pytest -q`, `ruff check .`, `ruff format --check .`, `ty check`.
- Backend: `docker compose -f compose.test.yaml up -d --wait`, then from the repo root `PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test uv run --project backend pytest backend/tests -q -x`; also `uv run --project backend ruff check .`, `ruff format --check .`, `ty check --project backend`. Baseline: 648 passed.
- Frontend: the commands in `frontend/package.json` and `docs/development.md` (unit, component and e2e tests, lint, type check).
- Docs: `uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean` without warnings.
- Every commit keeps all suites green. No new dependencies unless a task says so.
- Never use the em dash character; Markdown paragraphs on one line; no attribution lines in commits.
- Alembic: one new revision `p006studyformat` in `backend/alembic/versions/`, following the existing naming and the constraint naming convention; `SCHEMA_REVISION` in `backend/src/pkdb_server/app.py` and the revision count in `backend/tests/integration/test_migrations.py` follow it. The revision must upgrade, downgrade and pass `alembic check`.
- Canonical `cv` and `gcv` are fractions; source tables hold percent (the format 2 reader divides by 100).
- Format 1 uploads and reads keep working until the cutover (sub-project 5), with their legacy values mapped as described in Task 3.

## Review Focus

1. Uploading the same format 2 study twice is idempotent, and uploading a released study takes over the row whose `sid` or `pkdb_id` equals `release.pkdb_id` (rename on re-upload). Test owned by Task 5.
2. A study whose sid contains `/` is reachable through every read route (REST v1 and v2, exports, admin access, MCP `get_study`, frontend page), and PKDB identifiers redirect. Test owned by Task 6.
3. Existing database rows with `value` and `time_text` survive the migration with the same numbers in `mean` and structured schedules, and downgrade restores them. Test owned by Task 3.
4. Geometric statistics never feed arithmetic completion, and error-bar derivation never overwrites a reported statistic. Test owned by Task 2.
5. The format 2 reader gives every canonical record a source location (file, sheet, row, column), so layer 6 issues point at cells. Test owned by Task 4.

---

### Task 1: Additive schema (database and canonical fields)

**Files:**
- Create: `backend/alembic/versions/p006studyformat_study_format.py`
- Modify: `backend/src/pkdb_server/db/models/base.py` (`Scientific` mixin), `db/models/measurements.py` (`ObservationValue`, `Observation` read adapter typing block), `db/models/interventions.py`, `db/models/studies.py`, `backend/src/pkdb_server/app.py` (`SCHEMA_REVISION`), `backend/tests/integration/test_migrations.py`
- Modify: `python/src/pkdb/schemas/study.py`; create `python/src/pkdb/schemas/review.py`; modify `python/src/pkdb/studyformat/models.py` (import `Release`, `Review` and its parts from `pkdb.schemas.review` instead of defining them, re-export unchanged names)
- Modify: `backend/src/pkdb_server/db/replace.py`, `db/read.py` (write and read the new fields)
- Test: `backend/tests/integration/test_migrations.py`, a new `backend/tests/integration/test_study_format_fields.py`, `python/tests/test_canonical_fields.py`

**Interfaces (produced):**
- `pkdb.schemas.review`: `Release(pkdb_id, date)`, `ReviewTarget`, `ThreadEntry`, `ReviewItem`, `Review(status, reviewers, items)` exactly as today's `studyformat.models` definitions (moved, not changed).
- `Statistics` gains `gmean`, `gsd`, `gcv` (`Number | None`), `error_bar` (`Number | None`), `error_type` (`Literal["sd", "se", "gsd"] | None`). `value` stays for now.
- `Intervention` gains `interval: Number | None`, `doses: Annotated[int, Field(strict=True, ge=1)] | None`, `subject: str | None`; `time` accepts `Number | list[Number] | str | None` (lists have at least two entries).
- `Metadata` gains `issue: int | None` (>0), `release: Release | None`, `review: Review | None`.
- Database: `observation_values` and `interventions` gain `gmean`, `gsd`, `gcv`, `error_bar` (double precision) and `error_type` (varchar with CHECK in sd/se/gsd); `interventions` gains `interval` (double), `doses` (integer, CHECK >= 1), `time_list` (double precision[]), `subject_id` (nullable, composite FK `(study_id, subject_id)` to `subjects`, following the pattern in `measurements.py`); `studies` gains `pkdb_id` (varchar(16), unique, CHECK `pkdb_id ~ '^PKDB[0-9]{5}$'`), `release_date` (date), `issue` (integer, CHECK > 0), `review_status` (varchar, CHECK in draft/in_review/approved), `review` (JSONB).
- `insert_graph` writes every new field; `read_study` returns them (canonical round trip). An intervention list time is written to `time_list`; a numeric time to `time`; a string schedule still to `time_text`.

- [ ] **Step 1: Failing tests.** Migration test: revision count 6; upgrade/downgrade round trip with `alembic check`; existing data survives the round trip. Canonical round-trip test through the database (use the `ingestion_context` / `valid_bundle` fixtures or `insert_graph` + `read_study` directly): a study with `gmean`/`gsd`/`gcv`/`error_bar`/`error_type` on an output, an intervention with `time=[0, 12, 40]`, one with `time=0, interval=24, doses=7`, an intervention with `subject="all"`, and metadata with `issue`, `release` and `review` reads back equal. Python unit test: `Statistics` and `Intervention` validation of the new fields (doses >= 1, error_type enum, list time needs at least two entries).
- [ ] **Step 2: Implement** the migration, ORM models, canonical fields and `insert_graph`/`read_study` support. `studyformat.models` must import the moved classes so `canonical_review_json`, `StudyMetadata` and all study format 2 tests stay unchanged.
- [ ] **Step 3: Run** the backend suite, the Python suite, ruff and ty for both projects. All green.
- [ ] **Step 4: Commit** "Add study format 2 statistics, schedule, release and review fields".

---

### Task 2: Statistics derivations

**Files:**
- Modify: `python/src/pkdb/domain/statistics.py`, `domain/normalization.py` (`SCALED_FIELDS`), `domain/datasets.py` (`STATISTICS_FIELDS`), `domain/validation.py` (completion call sites, new warning)
- Modify: `python/src/pkdb/schemas/validation.py` only if a registry entry is needed for the new code
- Test: `backend/tests/unit/test_statistics.py` (or the existing statistics test module; find it with `rg -l complete_statistics backend/tests python/tests`), `python/tests/test_statistics_derivations.py`

**Rules (spec 11.2):**
- `complete_statistics(statistics, count=None)` fills only missing fields; reported values are never overwritten:
  - arithmetic (`sd`, `se`, `cv`) from each other with `count` and `mean`, as today;
  - geometric: `gcv = sqrt(exp(ln(gsd)^2) - 1)` and `gsd = exp(sqrt(ln(1 + gcv^2)))` (fractions); geometric values never feed arithmetic ones or the reverse;
  - error bar: with `error_type` `sd` or `se` and a `mean`, the missing field is `abs(error_bar - mean)`; with `gsd` and a `gmean`, `gsd = max(error_bar / gmean, gmean / error_bar)` (only when both are positive); afterwards the geometric rule can complete `gcv`.
- Over-determination: when a record reports at least two of `sd`, `se`, `cv` (with `count` and `mean` known) or both `gsd` and `gcv`, check them against each other with a relative tolerance of 2 percent and report a warning `inconsistent_statistics` on that record (code added to the issue registry with category `scientific`).
- `SCALED_FIELDS` (unit scaling during normalization) adds `gmean` and `error_bar`; `gsd`, `gcv` and `cv` are never scaled.
- `STATISTICS_FIELDS` in `domain/datasets.py` adds `gmean`, `gsd`, `gcv`.
- Completion keeps running only where it runs today (normalized group records with calculation `None` or `sample mean`), so format 1 behaviour is unchanged for records without the new fields.

- [ ] **Step 1: Failing tests** for each rule, including: reported `sd` kept when `error_bar` would give another value; `gsd`/`gcv` round trip (`gsd=1.3` gives `gcv` about 0.2655 and back); `error_type=gsd` with `error_bar < gmean` uses the inverse ratio; no arithmetic completion from `gmean`/`gsd`; unit scaling of `gmean` and `error_bar` but not `gsd`/`gcv`; `inconsistent_statistics` warning for `sd=1, se=1, count=4, mean=10`, none for `sd=2, se=1, count=4`.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Run** both suites, ruff, ty.
- [ ] **Step 4: Commit** "Derive geometric and error-bar statistics and flag inconsistent ones".

---

### Task 3: Remove `value`, structured schedules, processing version 9

This is the breaking switch. It touches client and server together and must end with all suites green in one or several commits within the task.

**Files (find every site with `rg -n "\bvalue\b" ...` restricted to statistics contexts; the exploration found these):**
- Canonical: `python/src/pkdb/schemas/study.py` (`Statistics.value` removed; `Intervention.time` no longer accepts `str`).
- Format 1 importer: `python/src/pkdb/importers/folder.py` (`_scientific` maps a source `value` to `mean`, including the source-location field alias so `for_field("mean")` points at the original cell; schedule strings are parsed, see below), `importers/osp/workbook.py` (individual and dose `value` to `mean`; geometric mean keeps `calculation_type="geometric mean"` but moves the number to `gmean`), `importers/datasets/common.py` and `importers/datasets/convert.py` (`value` to `mean`).
- Domain: `domain/validation.py` (`NUMERIC_FIELDS` without `value` and with `gmean`; individual records may carry `mean` but no spread, median, range or geometric statistics and no `calculation_type`; `unspecified summary` allows only `mean`; drop the `group_value` rules; recovery check over `mean`, `median`, `gmean`; `missing_dose` checks `mean`; calculation type `unspecified summary` is always accepted even when the vocabulary lacks it), `domain/pharmacokinetics.py` (dose from `mean`; curve statistic chosen from `mean`, then `median`), `domain/normalization.py`, `domain/datasets.py`, `PROCESSING_VERSION = "9"`.
- Wire schemas and querying: `python/src/pkdb/schemas/responses.py` (`ScientificResponse`, `ArrayOutput`: no `value`; add `gmean`, `gsd`, `gcv`, `error_bar`, `error_type`; `InterventionResponse.time` becomes `float | list[float] | None` and gains `interval`, `doses`, `subject`), `schemas/analysis.py` (same for analysis rows; keep `unit` last where the timecourse loop relies on it), `querying.py` `NUMBERS`.
- Backend: `db/replace.py` (`value_fields`), `db/read.py`, `db/serialize.py`, `db/analysis.py` (`VALUES`), `db/queries.py` (`OUTPUT_FIELDS`, intervention fields), `db/subject_filters.py`, `db/scatter_export.py`, `api/reads.py` (`NUMBERS`), the `Scientific` mixin and `ObservationValue` (drop `value`, `time_text`).
- Migration `p006studyformat` (extend the Task 1 revision; it is unreleased): before dropping, copy `value` into `mean` where `mean` is null (both tables), and convert `interventions.time_text` with the schedule rules below into `time`, `time_list`, `interval`, `doses`; an unparseable `time_text` aborts the upgrade with a message naming the intervention ids. Downgrade re-creates `value` and `time_text` and restores them from `mean` (for individual, unspecified-summary and intervention rows, as far as derivable) and from the structured schedule (written back as `0|12|40` or `S<start>T<interval>R<doses>`). Use set-based SQL; mind the observation triggers listed in the exploration (`observation_context_immutable`, deferred constraint triggers) and keep the upgrade fast on large tables.
- Tests and fixtures: `backend/tests/conftest.py` (`valid_study` uses `mean`), unit tests in `backend/tests/unit/` (validation, unified observations, pharmacokinetics: the "mean-only dose is ignored" test flips to "dose from mean"), integration filters (`value` filters become `mean`), API data tests, `python/tests/test_dataset_imports.py`, `test_osp_import.py`, `test_client.py`, golden files `backend/tests/fixtures/golden/frost2014-*.json` (regenerate with the corpus test's own update mechanism if it has one; otherwise transform `value` to `mean` with a one-off script that is not committed, and check the result by running the corpus tests against `/home/mkoenig/git/pkdb_data/studies` with the environment variables the corpus tests document).

**Schedule string rules (format 1 importer and migration):**
- `a|b|c` (numbers, optional spaces) gives `time=[a, b, c]`.
- `S<start>T<interval>R<n>` gives `time=start, interval=interval, doses=n` (R is the number of administrations, as in the OSP importer).
- A `|`-list that mixes plain numbers and `S..T..R..` parts expands every part into explicit times and gives a list.
- Anything else is `invalid_schedule` (importer error with the source location; migration abort).

- [ ] **Step 1: Failing tests** for: importer `value` to `mean` with the original cell location; schedule parsing (each rule plus an invalid string); individual records accept `mean` and reject `sd`; `unspecified summary` with `mean` passes and with `sd` fails; PK uses a `mean` dose; migration data test (insert rows with `value` and `time_text` at `p005vocabsearch`, upgrade, check `mean`/schedule columns; downgrade, check restored values); API responses carry no `value` and do carry `gmean`.
- [ ] **Step 2: Implement** across client and server, then update the remaining tests and fixtures.
- [ ] **Step 3: Run** both suites (and the corpus tests if the corpus is available locally), ruff and ty for both projects. All green.
- [ ] **Step 4: Commit(s)**, ending with "Remove the value statistic, structure dosing schedules and bump processing to version 9".

---

### Task 4: Format 2 reader and local preparation

**Files:**
- Create: `python/src/pkdb/studyformat/reader.py`
- Modify: `python/src/pkdb/studyformat/validation.py` (layer 6), `studyformat/layout.py` (reserved names), `studyformat/__init__.py` (exports), `python/src/pkdb/preparation.py` (accept format 2), `python/src/pkdb/cli.py` (`pkdb prepare` and `validate` accept format 2; `upload` still refuses until Task 5)
- Test: `python/tests/studyformat/test_studyformat_reader.py`, updates to `test_studyformat_validation.py`, `test_studyformat_cli.py`, `python/tests/test_preparation.py`

**Interfaces (produced):**
- `read_study(study: LoadedStudy) -> CanonicalStudy` (precondition: no structural or error issues from layers 1 to 5).
- `prepare_folder(folder: Path, vocabulary: Vocabulary) -> PreparedStudy` in `pkdb.studyformat`: runs layers 1 to 5; on errors raises `StudyValidationError` with the full report; otherwise `prepare_study(read_study(...), vocabulary)` and merges the layer 1 to 5 warnings into the prepared report.
- `validate_folder` adds layer 6: when layers 1 to 5 have no errors, it runs `prepare_study` and adds its issues (errors from `StudyValidationError.report`, warnings from the prepared report); acknowledgements apply to them as to other warnings.
- `scan_folder` reports `reserved_name` (error, layout) for study folders named `publication` or `validate`.

**Mapping (`read_study`):**
- `sid = "<substance>/<name>"`; `metadata.name` = folder name; `metadata.date` = `release.date` or None; `creator`, `curators`, `collaborators`, `licence`, `access`, `provenance`, `descriptions`, `comments`, `issue`, `release`, `review` from `study.json`/`review.json`; `section_notes` keyed by table kind from `notes`.
- `reference`: the validated `reference.json` (sid = pmid, else doi, as in `references.py`).
- Subjects: `count == 1` gives an `Individual(name, group=parent)`; any other count a `Group(name, count, parent)`; characteristica rows become observations of their subject.
- Interventions: name, measurement type, calculation, substance, tissue, method, choice, route, form, application, `time` (single value or list), `time_end`, `interval`, `doses`, `time_unit`, `subject`, statistics, unit. `NR` times set the existing not-reported flags where the model has them, else None.
- Outputs: measurements with `output_type="output"`; `group` or `individual` by the subject's kind; `interventions` list; `time`/`time_unit` with `NR` handling (`time_not_reported`, `time_unit_not_reported`).
- Timecourses: measurements with `output_type="timecourse"`, `label`, and `series_key = f"{file}:{label}"`.
- Scatters: two measurements per row (labels `<name>_x` and `<name>_y`, interventions per axis) and one `DataRecord(name, data_type="scatter", subsets=[Subset(name=<name>, dimensions=[{dimension: "0", output: "<name>_x"}, {dimension: "1", output: "<name>_y"}], shared=["individual" if the subjects are individuals else "group"])])`, matching what `compile_datasets` expects (check `domain/datasets.py`).
- Statistics: every statistic column; `cv` and `gcv` divided by 100; `error_bar`/`error_type` passed through; empty `count` stays None (prepare_study inherits it).
- Keys: subjects and interventions by name; observations `f"{file}:{line}"` (scatter axes add `:x`/`:y`); datasets `f"{file}:{name}"`.
- Source locations: every record gets `SourceLocation(file, sheet, row)` with its column map filled so `for_header(column)` gives the cell; images `<name>_<source>.png` for non-`Text` sources.
- Attachments and `source_digest`: computed from every file of the folder except `study.json` and `reference.json`, with the same functions the format 1 importer uses.

- [ ] **Step 1: Failing tests:** reading the `valid_study` fixture gives the expected canonical study (subjects, individuals, characteristica, interventions with schedule fields, outputs, a timecourse with label, a scatter dataset, cv percent to fraction, source locations with cell coordinates); `prepare_folder` succeeds on the valid study and raises with the layer 1 to 5 report on a broken one; layer 6 issues appear in `validate_folder` with cell locations (for example an `inconsistent_statistics` warning); reserved names; `pkdb prepare` on a format 2 folder succeeds and `pkdb upload` still refuses.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Run** the Python suite, ruff, ty; the backend suite (it imports the client package).
- [ ] **Step 4: Commit** "Read study format 2 folders into the canonical model and prepare them".

---

### Task 5: Format 2 upload and ingestion

**Files:**
- Modify: `python/src/pkdb/client.py` (format 2 bundle and route), `python/src/pkdb/batch.py` (identity, duplicates, resume), `python/src/pkdb/cli.py` (remove the upload refusal), `python/src/pkdb/preparation.py`
- Modify: `backend/src/pkdb_server/app.py` (routes), `backend/src/pkdb_server/services/ingestion.py`, `backend/src/pkdb_server/db/publications.py` if needed
- Test: `python/tests/test_client.py`, `test_batch.py`, `backend/tests/api/test_uploads.py` (or a new `test_study_format_uploads.py`), `backend/tests/integration/` as needed

**Requirements:**
- Client: for a format 2 folder, prepare locally with `prepare_folder`, then `PUT /api/v2/studies/{substance}/{name}` with the multipart parts `study` and `reference` carrying the exact text of `study.json` and `reference.json`, and `files` carrying every other non-ignored file of the folder. Compatibility headers and limits as for format 1. The server must confirm the same sid.
- Server routes: `PUT /api/v2/studies/{substance}/{name}`, `POST /api/v2/studies/{substance}/{name}/validate`, `GET /api/v2/studies/{substance}/{name}` and `GET /api/v2/studies/{substance}/{name}/publication`. Register the single-segment `{sid}/publication` route before the two-segment routes so `PKDB00198/publication` keeps its meaning. Single-segment upload and validate keep accepting format 1 bundles.
- Ingestion: a bundle whose `study` part parses to an object with `"format": 2` is written into a temporary folder `<tmp>/<substance>/<name>/` (exact part text for the two JSON files, the uploaded files by their names) and processed with `prepare_folder`, so the server applies the same layers including the format check. Errors return the usual validation report shape with file, sheet, row and column.
- Publish: `name` = folder name, `date` = release date, plus `pkdb_id`, `release_date`, `issue`, `review_status`, `review`. Rename on re-upload: when no row has the new sid and `release.pkdb_id` is set, the row whose `sid` or `pkdb_id` equals it is taken over and its `sid` set to the new identity (inside the existing advisory lock; lock both keys in a fixed order to avoid deadlocks). Publication assignment and uniqueness rules stay as they are.
- `batch.py`: the identity of a format 2 folder is `study_label(folder)`; duplicate checks and resume use it.

- [ ] **Step 1: Failing tests:** client sends the exact file text and the right route (mock transport, as existing client tests do); server accepts a valid format 2 bundle and the study reads back with sid `caffeine/Example`, name, release, issue and review fields; a second identical upload is a replacement (idempotent); rename on re-upload from a row with sid `PKDB00198` and from a row with `pkdb_id` `PKDB00198`; a non-canonical file in the bundle is rejected with `not_formatted`; format 1 uploads unchanged; `pkdb upload` of a format 2 folder works end to end against the test server (follow the existing end-to-end upload tests).
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Run** both suites, ruff, ty.
- [ ] **Step 4: Commit** "Upload study format 2 folders and ingest them on the server".

---

### Task 6: Read routes, identity redirects and API fields

**Files:**
- Modify: `backend/src/pkdb_server/api/reads.py` (`/api/v1/studies/...`, `/api/v1/references/...`), `api/exports.py` (`/pkdata/studies/...`), `api/management.py` (admin access routes), `api/curation.py` if it takes a sid, `api/compatibility.py` (suffix aliases), `db/read.py`, `db/serialize.py`, `db/study_responses.py`, `python/src/pkdb/schemas/responses.py` (`StudyResponse`), `backend/src/pkdb_server/mcp/server.py` docs strings if they mention sid formats
- Test: `backend/tests/api/` (reads, exports, management), `backend/tests/mcp/test_transport.py`

**Requirements:**
- Every read route that takes a study sid has a two-segment variant `{substance}/{name}`; the single-segment variant serves format 1 sids and answers `308 Permanent Redirect` to the two-segment URL when the given value is the `pkdb_id` (or legacy sid) of a study whose sid now has two segments.
- `StudyResponse` adds `pkdb_id`, `release_date`, `issue`, `review_status` and `open_review_items` (count of open items); keep `sid` as the canonical identifier.
- MCP `get_study(sid)` accepts `<substance>/<name>` and PKDB identifiers (resolved to the study).
- `studies__sid__in` search filters keep working with sids containing `/`.

- [ ] **Step 1: Failing tests:** for a format 2 study uploaded in the test: `/api/v1/studies/caffeine/Example/`, `/api/v2/studies/caffeine/Example`, exports and admin access routes respond; `/api/v1/studies/PKDB00198/` and `/api/v2/studies/PKDB00198` redirect with 308 to the two-segment URL; `StudyResponse` includes the new fields; MCP `get_study("caffeine/Example")` equals the REST response.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Run** the backend suite, ruff, ty.
- [ ] **Step 4: Commit** "Serve studies by substance and name and redirect PKDB identifiers".

---

### Task 7: Frontend

**Files:** `frontend/src/router/index.ts`, `features/results/columns.ts`, `features/results/cells.ts`, `features/details/types.ts` (labels for gmean, gsd, gcv, error bar), `features/details/components/StudyContents.vue`, `features/plots/types.ts`, `features/plots/ScientificPlot.vue`, `features/search/SearchPage.vue`, `features/account/AccountPage.vue` (study links), and their tests under `frontend/tests/` (unit, component, e2e); `backend/tests/fixtures/frontend_search.py` and `tools/frontend_testing/serve.py` if the e2e data needs format 2 fields.

**Requirements:**
- Statistics: show `mean` where `value` was shown (`mean ?? median ?? gmean ?? choice` for the compact cell); add columns or labels for `gmean`, `gsd`, `gcv`; plots use `mean`, then `median`, then `gmean` for the y value and `sd`/`se` (arithmetic) or `gsd` (geometric, as a multiplicative band) for errors; sorting by `mean` instead of `value`.
- Routes: `/data/:substance/:name` is the study page; `/data/:sid` stays for format 1 sids and PKDB identifiers and follows the API redirect; every generated study link uses the study's canonical sid split into two segments when it contains `/`.
- Study page: show the PKDB identifier and release date when released, the GitHub issue link (`https://github.com/matthiaskoenig/pkdb_data/issues/<issue>`) when known, and the review status with the number of open items.
- Interventions: show schedules readably (`0, 12, 40 h`; `every 24 h, 7 doses from 0 h`).
- Timecourse traces are labelled with the timecourse `label`.

- [ ] **Step 1: Failing tests** in the frontend suites for each requirement (unit tests for cells and plot models, component tests for the study page, router tests for both routes).
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Run** all frontend checks; the e2e suite against the frontend test server; the backend suite if fixtures changed.
- [ ] **Step 4: Commit** "Show study format 2 statistics, schedules, identity and review in the frontend".

---

### Task 8: Documentation and release notes

**Files:** `docs/api.md`, `docs/api-examples.md`, `docs/mcp.md`, `docs/data-model.md`, `docs/python-client.md`, `docs/web-interface.md` if it shows statistics, `python/src/pkdb/studyformat/export.py` (the generated page's introduction now says format 2 folders can be prepared and uploaded) and the regenerated `docs/study-format.md`, `release-notes/unreleased.md` (one entry for this change with the PR number, migration `p006studyformat`, processing version 9).

- [ ] **Step 1:** Update every example that shows `value`, schedule strings or PKDB-only study URLs; document the two-segment routes, redirects, new statistics fields, processing version 9 and the re-upload requirement.
- [ ] **Step 2:** Docs build without warnings; snapshot test of the generated page passes.
- [ ] **Step 3: Commit** "Document study format 2 uploads, statistics and identity".
