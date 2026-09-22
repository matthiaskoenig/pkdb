# Preserved legacy client tests

These tests exercise `backend/pkdb_data`, the preserved curation/upload client.
They are separate from the Django backend tests because the client source and its
metadata dependency require a newer Python than the Django runtime's Python 3.9.
The client environment is test-only and is not installed into either backend image.

From this directory:

```bash
uv run --locked --python 3.13 pytest -q -x
uv run --locked --python 3.13 ty check
```

CI includes both commands in the required `tests` aggregate. The existing Django
suite still runs from `backend/tests` with its unchanged dependencies.

Tests copy the preserved vocabulary caches into a temporary directory. The
registry fixture is a subset of the public identifiers.org namespace registry,
containing namespaces referenced by this client. External requests are disabled:
metadata queries use cached responses or the existing offline error path; PubMed
XML is synthetic, and the workbook test creates and checks an actual temporary
workbook. No source corpus, live web service or working account is needed.

The replacement backend has its own tests in `backend-next/tests`. See
`docs/local-upload-testing.md` for testing the new `pkdb upload` command.
