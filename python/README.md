# PK-DB Python client

Prepare, validate, query, and upload pharmacokinetic studies with the same scientific validation engine used by the PK-DB server. Python 3.14 is supported on Linux, macOS, and Windows.

Install a published release with `pip install pkdb`, or install this checkout with `pip install ./python` from the repository root.

Existing `pkdb_data` study folders work directly:

```bash
pkdb prepare studies/ExampleStudy
pkdb validate studies/ExampleStudy --offline
pkdb upload studies/ExampleStudy --endpoint https://pk-db.com
```

Preparation and validation work offline using the bundled vocabulary. Upload validates locally first and then the server validates the original files again. Set `PKDB_API_KEY` for authenticated operations and optionally `PKDB_ENDPOINT` for the default endpoint.

```python
from pkdb import prepare

prepared = prepare("studies/ExampleStudy")
print(prepared.study.sid)
```

See the [client documentation](https://matthiaskoenig.github.io/pkdb/python-client/) for vocabulary snapshots, structured reports, authentication, queries, and downloads. The source repository contains the separate `pkdb-server` distribution, which depends on the exact matching public client release.
