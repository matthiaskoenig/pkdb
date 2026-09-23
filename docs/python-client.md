# Python client and API

[![PyPI](https://img.shields.io/pypi/v/pkdb.svg)](https://pypi.org/project/pkdb/) [![Python versions](https://img.shields.io/pypi/pyversions/pkdb.svg)](https://pypi.org/project/pkdb/)

The public `pkdb` package prepares, validates, uploads, and queries studies. Prepare study folders on your machine, then use your account at `alpha.pk-db.com` for authenticated data access and curation. Preparation and offline validation do not need an account.

## Install

Install [pkdb from PyPI](https://pypi.org/project/pkdb/) with Python 3.14 or 3.15:

```bash
python -m pip install pkdb
```

In a uv project, use `uv add pkdb`. For just the command-line tools, use `uv tool install pkdb` and run `pkdb --help`. No source checkout is needed.

## Query studies and measurements

All user data access and curation examples use [alpha.pk-db.com](https://alpha.pk-db.com). Public browsing works without a key:

```python
from pkdb import Client

with Client(endpoint="https://alpha.pk-db.com") as client:
    page = client.studies.list(page=1, page_size=20)
    print(f"{page.count} studies across {page.pages} pages")
    for item in page.items:
        print(item.sid)

    if page.items:
        sid = page.items[0].sid
        measurements = client.query("outputs", study_sid=sid, page=1, page_size=20)
        for measurement in measurements.items:
            print(measurement.model_dump())
```

`client.query()` also accepts `groups`, `individuals`, `interventions`, `references`, and `studies`. Results are paginated: use `page` and `page_size`, and inspect `count` and `pages`. See the [REST API guide](api.md) for response structure and endpoint references.

## Download data

Create a read key in [Account settings](https://alpha.pk-db.com/account) and provide it in your environment as `PKDB_API_KEY`. The client reads it automatically:

```python
from pkdb import Client

with Client(endpoint="https://alpha.pk-db.com") as client:
    client.download("dataset.zip", studies__sid="STUDY_SID")
```

Replace `STUDY_SID` with an identifier from your search. Downloads require an active account even for public studies and include only accessible data. Review each study's licence before reuse. For expiry, rotation, and access permissions, see [Accounts and API keys](authentication.md).

## Prepare, validate, and upload a study folder

Pass the existing study directory from `pkdb_data` directly. Keep its original `study.json`, `reference.json`, workbooks, tables, and attachments together. The directory name must match the study's name. The parser understands existing spreadsheet sheet names, second-row workbook headers, `col==...` expressions, and TSV sources; no intermediate conversion is needed.

```bash
pkdb prepare /path/to/pkdb_data/studies/ExampleStudy --output prepared.json
pkdb validate /path/to/pkdb_data/studies/ExampleStudy --offline
```

Both commands run on your machine, using a bundled vocabulary snapshot by default, and leave source files unchanged. Store generated reports outside the study directory so they do not become source attachments. Errors identify the source file, sheet, row, and column where available. The command returns a nonzero exit code on failure and produces JSON suitable for scripts and continuous integration.

For curation, your account needs upload permission and a key with `studies:write`. To upload, set `PKDB_API_KEY` in your environment using an API key from your profile. `PKDB_ENDPOINT` supplies the default API endpoint; `--endpoint` overrides it.

```bash
export PKDB_ENDPOINT=https://alpha.pk-db.com
pkdb upload /path/to/pkdb_data/studies/ExampleStudy
```

Upload automatically prepares and validates the folder, checks compatibility with the processing engine used by the service and vocabulary, then sends the original source bundle. Uploading an existing SID replaces that study, subject to your study permissions. The service validates the bundle again and checks authorization. An offline validation result does not grant upload permission. A valid key with `studies:write` can upload either a public or a private study. The study's `access` field determines visibility: public data is visible to everyone; private data is visible only to its assigned curators and the administrator. An authorized uploader can also change visibility when replacing a study. The uploader receives a curator assignment on creation; source contributor attribution alone does not grant access. Writes are not retried automatically.

The public commands also accept a parent directory containing multiple study folders, emitting one JSON record per study and returning a nonzero exit code if any study fails. `--output` requires a single study folder.

## Pin a vocabulary snapshot

A vocabulary snapshot contains the measurement rules, substances, and allowed terms needed for scientific validation. Synchronization is an explicit network operation:

```bash
pkdb vocabulary sync --endpoint https://alpha.pk-db.com --output vocabulary.lock.json
pkdb validate /path/to/pkdb_data/studies/ExampleStudy --offline --vocabulary vocabulary.lock.json
pkdb upload /path/to/pkdb_data/studies/ExampleStudy --endpoint https://alpha.pk-db.com --vocabulary vocabulary.lock.json
```

Keep the lock file with your project, outside the study folder. Snapshots include a content hash checked on loading. The client also caches snapshots by endpoint. Set `PKDB_CACHE_DIR` or pass `--cache-dir` to choose the cache location. Passing `--endpoint` to local commands selects an existing cached snapshot without network access; `--vocabulary` pins an explicit snapshot. Preparation records the vocabulary hash, processing version, and source-file hashes, allowing you to identify the inputs used. A prepared result becomes unusable for upload when its source files change: prepare the folder again after editing it.

If the API rejects a vocabulary or processing version mismatch, explicitly synchronize the vocabulary or install the matching client release, then prepare and validate again. Local validation never silently downloads new rules.

## Prepare and upload from Python

```python
from pkdb import Client, Vocabulary, prepare

vocabulary = Vocabulary.load("vocabulary.lock.json")
prepared = prepare("/path/to/pkdb_data/studies/ExampleStudy", vocabulary=vocabulary)

study = prepared.study       # CanonicalStudy Pydantic model
report = prepared.report     # source-aware validation report
print(study.sid, report.valid)

# Client reads PKDB_API_KEY when api_key is omitted.
with Client(endpoint="https://alpha.pk-db.com") as client:
    result = client.upload(prepared)
    page = client.studies.list()
    downloaded_study = client.studies.get(study.sid)
    # Dataset downloads require authentication.
    client.download("dataset.zip", studies__sid=study.sid)
```

Catch `pkdb.schemas.validation.StudyValidationError` to inspect `error.report` for local validation failures. The API checks account permissions and study ownership again during upload.

Use the client version compatible with the API deployment. If compatibility checks reject a request, follow the reported instructions before retrying.

## Inspect a rejected upload

An HTTP 422 response means the API rejected the study bundle. The CLI prints the validation code and message, plus the full `report` with source locations when available. In Python, catch `pkdb.errors.ClientError` and inspect its `report` attribute.

- `unknown_user`: an attribution identity in the study is absent from the destination. Ask its administrator to provision the identity; changing attribution is not a substitute for preserving the original contributors.

Offline validation cannot check destination account records or study-editing permissions. If an older client prints only the HTTP status, update the client to a release containing detailed validation reporting or use the [source checkout](development.md#install-the-python-package-from-source).
