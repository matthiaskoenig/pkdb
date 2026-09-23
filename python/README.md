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
