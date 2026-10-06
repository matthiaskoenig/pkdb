# Python client and API

[![PyPI](https://img.shields.io/pypi/v/pkdb.svg)](https://pypi.org/project/pkdb/) [![Python versions](https://img.shields.io/pypi/pyversions/pkdb.svg)](https://pypi.org/project/pkdb/)

The public `pkdb` package prepares, validates, uploads, and queries studies. Prepare study folders on your machine, then use your account at `beta.pk-db.com` for authenticated data access and curation. Preparation and offline validation do not need an account.

## Install

Install [pkdb from PyPI](https://pypi.org/project/pkdb/) with Python 3.14 or 3.15:

```bash
python -m pip install pkdb
```

In a uv project, use `uv add pkdb`. For just the command-line tools, use `uv tool install pkdb` and run `pkdb --help`. No source checkout is needed.

### Automatic updates

The client and the server share one release version. Before a command runs, `pkdb` checks PyPI at most every six hours, and immediately after it has seen a server running a newer release. When a newer release exists, `pkdb` upgrades itself with the installer that owns it (`uv tool upgrade pkdb`, `pipx upgrade pkdb`, or `pip`/`uv pip` in a virtual environment) and reruns the command with the new release. A failed or offline check continues with the installed release. Source checkouts, VCS installations, and interpreters outside a virtual environment are never modified; `pkdb` prints the manual update command instead.

Run `pkdb update` to update immediately or `pkdb update --check` to only report whether an update exists. Disable automatic updates with `--no-update` or `PKDB_NO_UPDATE=1`, for example in pinned continuous-integration environments.

### Environment variables

| Variable | Default for |
| --- | --- |
| `PKDB_ENDPOINT` | Server address (`--endpoint`, `Client(endpoint=...)`, curation connection settings) |
| `PKDB_API_KEY` | Personal API key for authenticated reads and uploads |
| `PKDB_USER` | Expected PK-DB username (`--user`, `Client(user=...)`); uploads and the curation app stop when the API key belongs to another account |
| `PKDB_AGENT` | Name of the AI agent (`--agent`) that writes review items; an agent cannot approve a study |
| `PKDB_NO_UPDATE` | Set to `1` to disable automatic updates |

Explicit options and arguments always take precedence over the environment.

## Query studies and measurements

All user data access and curation examples use [beta.pk-db.com](https://beta.pk-db.com). Set it as the endpoint in your environment; the client reads `PKDB_ENDPOINT` when no endpoint is passed. Public browsing works without a key:

```bash
export PKDB_ENDPOINT=https://beta.pk-db.com
```

```python
from pkdb import Client

with Client() as client:
    page = client.studies.list(page=1, page_size=20)
    print(f"{page.count} studies across {page.pages} pages")
    for item in page.items:
        print(item.sid)

    if page.items:
        sid = page.items[0].sid
        measurements = client.query("measurements", study_sid=sid, page=1, page_size=20)
        for measurement in measurements.items:
            print(measurement.model_dump())
```

A study in study format 2 is identified by `<substance>/<name>`; `client.studies.get("caffeine/Harder1988")` reads it. The PKDB identifier of a released study works as well, `client.studies.get("PKDB00198")`, because the client follows the permanent redirect (308) of a read to the canonical route, at most five times and only within the origin of its endpoint. The returned study has the canonical `sid`, `metadata.release`, `metadata.issue` and `metadata.review`; list results (`client.studies.list()`) carry `pkdb_id`, `release_date`, `issue`, `review_status` and `open_review_items`. Writes and POST queries never follow redirects. See [study identifiers](api.md#study-identifiers-and-redirects).

Measurement, characteristic and intervention rows have no `value`: the value of one subject and of an `unspecified summary` is in `mean`, `cv` and `gcv` are fractions, and interventions have structured schedules. See [statistics in responses](api.md#statistics-in-responses) for the statistics of a row.

The client uses the v2 data API. `measurements` is the public name for measurement rows; `outputs` remains an accepted alias. `client.query()` also accepts `groups`, `individuals`, `interventions`, `references`, and `studies`. Results are paginated: use `page` and `page_size`, and inspect `count` and `pages`. The client preserves its `count` and `pages` convenience attributes while REST responses use `total`, `page`, and `page_size`. See the [REST API guide](api.md) and [executable HTTP examples](api-examples.md).

## Download data

Create a read key in [Account settings](https://beta.pk-db.com/account) and provide it in your environment as `PKDB_API_KEY`. The client reads it automatically:

```python
from pkdb import Client

with Client() as client:
    client.download("dataset.zip", studies__sid="STUDY_SID")
```

Replace `STUDY_SID` with an identifier from your search. Downloads require an active account even for public studies and include only accessible data. Review each study's licence before reuse. For expiry, rotation, and access permissions, see [Accounts and API keys](authentication.md).

## Literature references

Create and enrich `reference.json` from a PMID, DOI, or manual citation with `pkdb reference resolve`. When a study's reference is a PMID, `prepare`, `validate`, and `upload` create a missing `reference.json` or replace one that names another publication. The [reference metadata guide](reference-metadata.md) covers previews, candidate search, cached offline use, and preserved curator corrections.

## Prepare, validate, and upload a study folder

The development version includes a [local curation app](local-curation.md) with file watching, external file opening, and validation/upload on save. Launch it with `pkdb curate /path/to/pkdb_data`; the illustrated guide covers setup and offline work. This command is not yet available in a published release.

Pass the existing study directory from `pkdb_data` directly. Keep its original `study.json`, `reference.json`, workbooks, tables, and attachments together. The directory name must match the study's name. The parser understands existing spreadsheet sheet names, second-row workbook headers, `col==...` expressions, and TSV sources; no intermediate conversion is needed. A folder whose `study.json` contains `"format": 2` is a [study format 2](study-format.md) folder; `prepare`, `validate`, and `upload` accept both formats, and for study format 2 the folder is located as `<substance>/<name>` (for example `studies/caffeine/Harder1988`).

```bash
pkdb prepare /path/to/pkdb_data/studies/ExampleStudy --output prepared.json
pkdb validate /path/to/pkdb_data/studies/ExampleStudy --offline
```

Both commands run on your machine, using a bundled vocabulary snapshot by default, and leave source files unchanged, with two exceptions that keep derived files current. A missing or mismatched PubMed `reference.json` is recreated in the study folder (see [automatic repair](reference-metadata.md#automatic-repair-during-validation-and-upload)). Hidden TSV tables are regenerated from the study workbook (see below). For study format 2 folders, neither command writes to the study folder. Store generated reports outside the study directory so they do not become source attachments. Errors identify the source file, sheet, row, and column where available. The command returns a nonzero exit code on failure. Interactive terminals show readable progress and diagnostics; redirected output defaults to JSON Lines for scripts and continuous integration.

For curation, your account needs upload permission and a key with `studies:write`. To upload, set `PKDB_API_KEY` in your environment using an API key from your profile. `PKDB_ENDPOINT` supplies the default API endpoint; `--endpoint` overrides it. Set `PKDB_USER` (or pass `--user`) to confirm the key's account before any study is sent.

```bash
export PKDB_ENDPOINT=https://beta.pk-db.com
pkdb upload /path/to/pkdb_data/studies/ExampleStudy
```

Upload automatically prepares and validates the folder (a study format 2 folder with a [workbook](workbooks.md) is synced and formatted first), checks compatibility with the processing engine used by the service and vocabulary, then sends the original source bundle. Uploading an existing study identifier replaces that study, subject to your study permissions. A study format 2 folder is uploaded to `PUT /api/v2/studies/{substance}/{name}`: the client sends the exact text of `study.json` and `reference.json` and every other file of the study, and the server reads them with the same loader, validator and reader, so it reports the issues that `pkdb validate` reports. A released study whose `study.json` has a `release.pkdb_id` takes over and renames the study stored under that PKDB identifier; a study format 2 folder without a `release.pkdb_id`, or whose PKDB identifier no stored study has, takes over the study format 1 study of the same publication and source if you may edit it. The upload result and `--format json` output name the former identifier in `renamed_from`, and reads by the former identifier redirect to the study. The service validates the bundle again and checks authorization. An offline validation result does not grant upload permission. A valid key with `studies:write` can upload either a public or a private study. The study's `access` field determines visibility: public data is visible to everyone; private data is visible only to its assigned curators and the administrator. An authorized uploader can also change visibility when replacing a study. The uploader receives a curator assignment on creation; source contributor attribution alone does not grant access. Writes are not retried automatically.

The public commands also accept a parent directory containing multiple study folders. In JSON mode they emit one record per attempted study. `--output` requires a single study folder.

## Progress and upload reports

```bash
pkdb upload /path/to/pkdb_data/studies/apixaban --report upload-report.json
pkdb validate /path/to/pkdb_data/studies/apixaban --format human --verbose
pkdb upload /path/to/pkdb_data/studies/apixaban --format json > upload-results.jsonl
```

Each study is identified by its path relative to the input batch folder, for example `apixaban/Frost2013` when uploading the `studies` directory. Single-study uploads show the study folder name. Confirmed uploads include a compact server-reported object summary, such as `groups=3, individuals=0, interventions=2, measurements=48, timecourses=4, attachments=2`. JSON output and batch reports also include `relative_path` alongside the existing path and name fields.

The terminal shows source reading, parsing, validation, server compatibility checks, bytes transferred, and waiting for server validation/save. Transferring all bytes does not mean a study has been saved: success appears only after the server confirms creation or replacement. A synchronous server response cannot expose a reliable processing percentage, so this stage shows elapsed time. `--format human` also works without a terminal using stable text lines; `--format json` emits machine-readable JSON without animation. `NO_COLOR` disables color.

Errors show the source file, worksheet, physical row/cell where known, offending value, expected rule, and correction guidance. Repeated errors are grouped for readability. By default the terminal shows five issue groups; `--verbose` shows all returned groups. Candidate vocabulary terms are suggestions to review against the publication, not automatic scientific corrections. A report marked incomplete or truncated does not enumerate every possible issue: fix the reported problems and validate again.

`--report` writes a batch JSON report after each study, including confirmed outcomes, all returned diagnostics, request IDs, rule versions, and summary counts. Choose a path outside the input study folders. An existing report requires `--overwrite-report`; `--output` and `--report` must use different paths. Reports may contain source values, so handle them as study data.

Study-specific validation failures and HTTP 403 permission rejections allow the batch to continue; rejected studies remain failed in the report and the command exits with status 1. `--fail-fast` stops at the first failure, including a 403. Authentication failures (401), rate limits (429), server errors (5xx), and compatibility failures stop the batch. Rate limits are reported separately from permission errors, with the server’s `Retry-After` value when available; the tool does not automatically retry writes. A lost upload response is marked **unknown** and also stops the batch: inspect the server before retrying, because it may have committed the study. Ctrl-C preserves completed outcomes in the batch report and marks an interrupted in-flight write as unknown.

Exit codes are 0 for all studies successful, 1 for a failure or unknown outcome (including report-writing failure), 2 for invalid command syntax, and 130 for interruption. Warnings alone do not fail the command. The summary distinguishes created, replaced, validated, failed, unknown, and unattempted studies.

Permission feedback includes a stable `code`, explanatory message, and correction guidance. Upload codes distinguish `missing_scope`, `upload_role_required`, `study_write_forbidden`, `licence_change_forbidden`, and `creator_change_forbidden`. The current server exempts authenticated uploads from request quotas. Its rate-limit responses use HTTP 429 (`rate_limit`); temporary capacity failures use 503. Older deployments or external proxies may behave differently. JSON results and batch reports preserve `status_code`, `code`, `retry_after`, and `request_id` when available so clients can display or diagnose the rejection.

## TSV tables from the study workbook

`pkdb prepare`, `validate`, and `upload`, as well as validation and upload in the local curation app, first write each non-empty `Tab…` or `Fig…` sheet of `<Study>/<Study>.xlsx` to a hidden `.<Study>_<Sheet>.tsv` file next to it, as the previous upload scripts did. The first row of a sheet is its description and is skipped, lines starting with `#` are comments, unnamed columns and empty rows are dropped, and missing values are written as `NA`. Files are only written when their content changes, and each result reports the created, updated, and removed files.

A hidden TSV whose sheet was deleted or emptied is removed, unless `study.json` still uses that sheet or file name; then it is kept as the last copy of the table and validation reports the missing sheet. Validation always reads the workbook itself; the TSV files are a reviewable text copy for version control. Folders without a workbook are not changed.

## Pin a vocabulary snapshot

A vocabulary snapshot contains the measurement rules, substances, and allowed terms needed for scientific validation. Synchronization is an explicit network operation:

```bash
pkdb vocabulary sync --endpoint "$PKDB_ENDPOINT" --output vocabulary.lock.json
pkdb validate /path/to/pkdb_data/studies/ExampleStudy --offline --vocabulary vocabulary.lock.json
pkdb upload /path/to/pkdb_data/studies/ExampleStudy --endpoint "$PKDB_ENDPOINT" --vocabulary vocabulary.lock.json
```

Keep the lock file with your project, outside the study folder. Snapshots include a content hash checked on loading. The client also caches snapshots by endpoint. Set `PKDB_CACHE_DIR` or pass `--cache-dir` to choose the cache location. Passing `--endpoint` to local commands selects an existing cached snapshot without network access; `--vocabulary` pins an explicit snapshot. Preparation records the vocabulary hash, processing version, and source-file hashes, allowing you to identify the inputs used. A prepared result becomes unusable for upload when its source files change: prepare the folder again after editing it.

If the API rejects a vocabulary or processing version mismatch, explicitly synchronize the vocabulary or install the matching client release, then prepare and validate again. Processing version 9 introduced study format 2; clients of version 8 or older are refused by a version 9 server, and every study stored by an older server must be uploaded again. Local validation never silently downloads new rules.

## Prepare and upload from Python

```python
from pkdb import Client, Vocabulary, prepare

vocabulary = Vocabulary.load("vocabulary.lock.json")
prepared = prepare("/path/to/pkdb_data/studies/ExampleStudy", vocabulary=vocabulary)

study = prepared.study       # CanonicalStudy Pydantic model
report = prepared.report     # source-aware validation report
print(study.sid, report.valid)  # study.sid is <substance>/<name> for study format 2

# Client reads PKDB_ENDPOINT and PKDB_API_KEY when they are not passed.
with Client() as client:
    result = client.upload(prepared)
    page = client.studies.list()
    downloaded_study = client.studies.get(study.sid)
    # Dataset downloads require authentication.
    client.download("dataset.zip", studies__sid=study.sid)
```

Catch `pkdb.schemas.validation.StudyValidationError` to inspect `error.report` for local validation failures. The API checks account permissions and study ownership again during upload.

Use the client version compatible with the API deployment. If compatibility checks reject a request, follow the reported instructions before retrying.

## Inspect a rejected upload

An HTTP 422 response means the API rejected the study bundle. The CLI presents the validation code, message, and source diagnostics; JSON output and `--report` retain the returned structured details. In Python, catch `pkdb.errors.ClientError` and inspect its `report`, `request_id`, `stage`, and `persistence` attributes. When supported by the server, `envelope` retains the full versioned API response.

- `unknown_user`: an attribution identity in the study is absent from the destination. Ask its administrator to provision the identity; changing attribution is not a substitute for preserving the original contributors.

Offline validation cannot check destination account records or study-editing permissions. If an older client prints only the HTTP status, update the client to a release containing detailed validation reporting or use the [source checkout](development.md#install-the-python-package-from-source).

## External data imports

Use `pkdb import osp --creator USER --output NEW_DIRECTORY` to convert the pinned OSP observed-data release into source-qualified study folders. See the [OSP import guide](osp-import.md) for provenance, scientific mappings, offline conversion, and server loading.

`pkdb import frdb`, `pkdb import cvtdb`, and `pkdb import warfarin` use the same creator/output options. Install `pkdb[imports]` for the R-format sources. See [public dataset imports](public-dataset-imports.md) for exact coverage, source terms, row-level provenance and weekly checks.

## Study format 2 folders

Study folders whose `study.json` contains `"format": 2` keep their data in fixed tab-separated tables; see [Study format](study-format.md). `pkdb format FOLDER` writes every file of such folders in canonical form, and `pkdb format FOLDER --check` only reports the files that would change. `pkdb validate FOLDER` checks layout, format, rows, relationships between tables and vocabulary terms, then reads the folder into the canonical study and runs the postprocessing of the server (derived statistics, unit normalization, datasets and pharmacokinetics), and reports every issue with file, row and column. `pkdb schema export --output DIR` writes JSON Schema files for `study.json`, `review.json` and every table, and `pkdb schema docs --output FILE` writes the column reference. `pkdb prepare FOLDER` writes the prepared canonical study of such a folder, and `pkdb upload FOLDER` uploads it as described above; `pkdb upload` also accepts a parent folder with study format 2 folders, and a batch refuses two folders with the same `<substance>/<name>` or the same publication (the PubMed ID or normalized DOI of `study.json`). Study folders cannot be named `publication` or `validate`, because PK-DB uses these names in study URLs.

`pkdb tables open STUDY` creates and opens a workbook `<name>.xlsx` of the tables of a study format 2 folder, `pkdb tables sync FOLDER` keeps the workbook and the tables in step with a three-way merge (`--keep workbook|tables` resolves conflicts, `--check` only reports, `--format json` prints one JSON line per study), and `pkdb tables add STUDY outputs_Tab3` adds the empty sheet of a new table. Git ignores the workbook and only the tables are committed; see [Edit tables in a workbook](workbooks.md). `pkdb upload` syncs a study format 2 folder that has a workbook, then formats it, before preparing it, and stops without uploading on conflicts or sync errors. `pkdb validate` and `pkdb prepare` never write to the study folder; they report workbook changes that are not in the tables yet and name `pkdb tables sync`.

In study format 2, `mean` is the arithmetic mean, the value of one subject, or the central value of an `unspecified summary`; `cv` and `gcv` are entered in percent and are fractions in the prepared study and the API; geometric summaries have their own columns (`gmean`, `gsd`, `gcv`); and a digitized `error_bar` with `error_type` completes `sd`, `se` or `gsd`. Interventions give `time` as a number, or as a `;`-separated list for an irregular schedule (`0;12;40`); a regular schedule uses `interval` and `doses` instead. The prepared study derives the missing statistics, reports contradicting ones as the warning `inconsistent_statistics` at the cell of the statistic that disagrees with the most others, and uses processing version 9. Study format 1 sources keep working: their `value` is read as `mean`, and schedule strings `0|12|40` and `S<start>T<interval>R<n>` (`R` counts administrations) become a time list or `time`, `interval` and `doses`; any other schedule text is `invalid_schedule`.

The curation commands read and edit a study folder with checked, atomic writes; `--format json` prints one JSON object for agents (it is the default when the output is not a terminal), including the `revision` of the file. A write with `--revision` is refused when the file changed since that revision.

| Command | Purpose |
| --- | --- |
| `pkdb study show FOLDER` | Print `study.json` with its revision |
| `pkdb study patch FOLDER --json TEXT` or `--file FILE` | Apply a JSON merge patch to `study.json`; a changed PubMed ID or DOI refreshes `reference.json` (`--offline`, `--cache-dir`) |
| `pkdb study reference FOLDER --pmid ID` or `--doi DOI` | Set the PubMed ID or DOI and refresh `reference.json`, also when the identifiers are unchanged (`--offline`, `--cache-dir`) |
| `pkdb review show FOLDER` | Print the review items with the revision and the number of rows each target matches (`--state open\|resolved\|dismissed`) |
| `pkdb review add FOLDER --kind question\|uncertainty\|issue --text TEXT` | Add an item, optionally for `--file`, `--rows COL=VALUE ...`, `--column` or a warning `--acknowledges CODE` |
| `pkdb review reply FOLDER ID --text TEXT` | Add a reply to the thread of an item |
| `pkdb review resolve FOLDER ID` | Resolve an open item |
| `pkdb review dismiss FOLDER ID` | Dismiss an open or resolved item; a dismissed item no longer acknowledges a warning |
| `pkdb review reopen FOLDER ID` | Reopen a resolved or dismissed item |
| `pkdb review status FOLDER draft\|in_review\|approved` | Set the review status; `approved` records `approved_by` and `approved`, and needs zero open items and zero validation errors |
| `pkdb review acknowledge FOLDER CODE --file FILE --text TEXT` | Acknowledge a validation warning with a resolved item (`--line`, `--column`); one item covers the warnings of one location, such as several `unknown_dataset` warnings of a `.wpd.json` file |
| `pkdb digitize import FOLDER SOURCE FILE` | Write `<study>_<source>.wpd.json` from a WebPlotDigitizer 4 `.json` or `.tar` project, after checking it against the figure image |
| `pkdb plot FOLDER` | Render the figure image with its digitized points and mapped rows to `<out>/<study>_<source>.plot.png` (`--source`, `--out` outside the study folder); by default every figure with a digitization, timecourses or scatters, and lists the series without dataset |
| `pkdb tables add FOLDER --raw Tab2` | Add the empty sheet of the raw table of a paper table |

Review writes name the person with `--user` or `PKDB_USER`, or the AI agent with `--agent` or `PKDB_AGENT`. Agents may add, reply, resolve and dismiss items, but approving a study is refused for agents and needs a person. Approving an approved study changes nothing. While a study is approved, adding an open item or reopening an item is refused; set the status to `in_review` first. See [Study format](study-format.md) for the raw extraction files (`<study>_<source>.tsv`, `.wpd.json`) and the review file.
