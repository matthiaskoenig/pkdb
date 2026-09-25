# PK-DB Python client

[![PyPI](https://img.shields.io/pypi/v/pkdb.svg)](https://pypi.org/project/pkdb/) [![Python versions](https://img.shields.io/pypi/pyversions/pkdb.svg)](https://pypi.org/project/pkdb/)

Prepare, validate, query, and upload pharmacokinetic studies with the same scientific validation engine used by the PK-DB server. Python 3.14 and 3.15 are supported on Linux, macOS, and Windows.

Install [pkdb from PyPI](https://pypi.org/project/pkdb/) with `python -m pip install pkdb`. For source installation, see [Development](https://matthiaskoenig.github.io/pkdb/development/).

Existing `pkdb_data` study folders work directly:

```bash
pkdb prepare studies/ExampleStudy
pkdb validate studies/ExampleStudy --offline
pkdb upload studies/ExampleStudy --endpoint https://alpha.pk-db.com
```

Preparation and validation work offline using the bundled vocabulary. Upload validates locally first and then the server validates the original files again. Set `PKDB_API_KEY` for authenticated operations and optionally `PKDB_ENDPOINT` for the default endpoint.

```python
from pkdb import prepare

prepared = prepare("studies/ExampleStudy")
print(prepared.study.sid)
```

See the [client documentation](https://matthiaskoenig.github.io/pkdb/python-client/) for vocabulary snapshots, structured reports, authentication, queries, and downloads.

### Parallel batch uploads and recovery

```bash
# PKDB_API_KEY is read from the environment, never written to reports.
pkdb upload ./studies --endpoint http://localhost:18083 --jobs 4 --report ./batch.json
pkdb upload ./studies --endpoint http://localhost:18083 --jobs 4 --resume ./batch.json
```

`--jobs` defaults to 1. Larger values use spawned processes, each with its own
reusable HTTP client and one private source snapshot at a time. Preparation and
transfers overlap; server validation remains independent. Duplicate study SIDs
and shared reference ownership are rejected before submission. JSON results are
emitted as tasks complete; report results retain discovery order.

Reports checkpoint queued, preparing, submitting, confirmed, failed, and unknown
states. The parent saves the submitting state before allowing a worker to send a
PUT. `--fail-fast` stops new work after an error; already submitted requests may
still commit. Authentication, compatibility, rate-limit, server and uncertain
write failures stop new submissions automatically. Interrupts allow ten seconds
for active requests to finish; outstanding writes are recorded as unknown.
A report-write failure also stops new submissions.

Resume requires the same endpoint, folder list and processing/vocabulary identity.
It compares saved source file hashes and rechecks server publication state.
Matching publications are skipped. Unknown writes with different or missing
publications require explicit resolution and are never automatically replayed.
Changed sources for previous successful or unknown writes are rejected; resolve
those outcomes before starting a new report. Reports from the older version-2
sequential format are not resumable. Keep reports outside source folders.

For Python callers, `pkdb.upload_many()` accepts a list of folders, endpoint,
API key, vocabulary, and `pkdb.batch.BatchOptions`. Progress and result callbacks
run in the parent. Guard process-based calls with `if __name__ == "__main__":`.
The existing `Client.upload(prepared)` mutation checks remain unchanged.

Client jobs and API worker processes are separate settings. Begin by measuring
1, 2, 4 and 8 client jobs on a disposable endpoint; four is a trial setting, not
a measured deployment recommendation. Budget memory and temporary disk for each
active snapshot, and database connections across API workers. Use
`scripts/benchmark_batch_upload.py` with `--endpoint`, `--vocabulary`, and a new
`--reports` directory. Run each first-import measurement on a fresh test database;
subsequent runs against the same endpoint measure replacement. Reports include
client stage durations and, with an updated server, validation, attachment staging
and publication durations in `server_report.timings`. Publication time includes
lock waits. Monitor server CPU, connection use, database waits, peak RSS and
snapshot disk use alongside throughput. No full-corpus speedup is assumed.
