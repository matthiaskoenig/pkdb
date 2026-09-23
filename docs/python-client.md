# Python client and command line

The public `pkdb` package prepares, validates, uploads, and queries studies. It contains the same Pydantic models, folder parser, and scientific validation engine used by the server. Local preparation needs neither a running server nor an account.

## Install

Python 3.14 is required. From a checkout of this repository:

```bash
uv tool install ./python
pkdb --help
```

For use in a Python project, install the local distribution with `uv add /path/to/pkdb/python`. The separate `pkdb-server` package contains the backend and administrative commands such as `pkdb-server create-admin`.

## Prepare, validate, and upload a study folder

Pass the existing study directory from `pkdb_data` directly. Keep its original `study.json`, `reference.json`, workbooks, tables, and attachments together. The directory name must match the study's name. The parser understands existing spreadsheet sheet names, second-row workbook headers, `col==...` expressions, and TSV sources; no intermediate conversion is needed.

```bash
pkdb prepare /path/to/pkdb_data/studies/ExampleStudy --output prepared.json
pkdb validate /path/to/pkdb_data/studies/ExampleStudy --offline
```

Both commands run locally, using a bundled vocabulary snapshot by default, and leave source files unchanged. Store generated reports outside the study directory so they do not become source attachments. Errors identify the source file, sheet, row, and column where available. The command returns a nonzero exit code on failure and produces JSON suitable for scripts and continuous integration.

To upload, set `PKDB_API_KEY` in your environment using an API key from your profile. `PKDB_ENDPOINT` supplies the default server URL; `--endpoint` overrides it.

```bash
export PKDB_ENDPOINT=https://pk-db.com
pkdb upload /path/to/pkdb_data/studies/ExampleStudy
```

Upload automatically prepares and validates the folder, checks compatibility with the server's processing engine and vocabulary, then sends the original source bundle. Uploading an existing SID replaces that study, subject to server permissions. The server validates the bundle again and checks authorization. An offline validation result does not grant upload permission. Writes are not retried automatically.

The public commands also accept a parent directory containing multiple study folders, emitting one JSON record per study and returning a nonzero exit code if any study fails. `--output` requires a single study folder. For server administration, including preparing attribution accounts for local corpus imports, see [Local upload testing](local-upload-testing.md).

## Pin a vocabulary snapshot

A vocabulary snapshot contains the measurement rules, substances, and allowed terms needed for scientific validation. Synchronization is an explicit network operation:

```bash
pkdb vocabulary sync --endpoint https://pk-db.com --output vocabulary.lock.json
pkdb validate /path/to/pkdb_data/studies/ExampleStudy --offline --vocabulary vocabulary.lock.json
pkdb upload /path/to/pkdb_data/studies/ExampleStudy --endpoint https://pk-db.com --vocabulary vocabulary.lock.json
```

Keep the lock file with your project, outside the study folder. Snapshots include a content hash checked on loading. The client also caches snapshots by endpoint. Set `PKDB_CACHE_DIR` or pass `--cache-dir` to choose the cache location. Passing `--endpoint` to local commands selects an existing cached snapshot without network access; `--vocabulary` pins an explicit snapshot. Preparation records the vocabulary hash, processing version, and source-file hashes, allowing you to identify the inputs used. A prepared result becomes unusable for upload when its source files change: prepare the folder again after editing it.

If the server rejects a vocabulary or processing version mismatch, explicitly synchronize its vocabulary or install the matching client release, then prepare and validate again. Local validation never silently downloads new rules.

## Python API

```python
from pkdb import Client, Vocabulary, prepare

vocabulary = Vocabulary.load("vocabulary.lock.json")
prepared = prepare("/path/to/pkdb_data/studies/ExampleStudy", vocabulary=vocabulary)

study = prepared.study       # CanonicalStudy Pydantic model
report = prepared.report     # source-aware validation report
print(study.sid, report.valid)

# Client reads PKDB_API_KEY when api_key is omitted.
with Client(endpoint="https://pk-db.com") as client:
    result = client.upload(prepared)
    page = client.studies.list()
    downloaded_study = client.studies.get(study.sid)
    # Dataset downloads require authentication.
    client.download("dataset.zip", studies__sid=study.sid)
```

Catch `pkdb.schemas.validation.StudyValidationError` to inspect `error.report` for local validation failures. The same `prepare_study` engine processes studies on the server, while account, ownership, and other database-dependent checks remain server-side.

Releases of the client and server are versioned together. The server depends on its matching public package release.
