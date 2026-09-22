# PK-DB replacement backend

Implementation in progress. The legacy backend remains in place until the
migration acceptance gates pass. Runtime dependencies are PostgreSQL and a
persistent attachment directory; Elasticsearch and Redis are not used.

## Development

Use standard GIL-enabled CPython 3.13 or 3.14. From this directory:

```bash
uv sync --locked --python 3.14
uv run --locked --python 3.14 alembic upgrade head
uv run --locked --python 3.14 uvicorn pkdb.app:create_app --factory
```

Set `PKDB_DATABASE_URL` and `PKDB_FILE_ROOT` first. Apply migrations explicitly;
startup does not modify the schema. Bootstrap vocabulary and account identities
before uploading studies. SMTP is configured through `PKDB_SMTP_*` settings.
The final cutover runbook and legacy draft adapters are still being built.

Tests require an isolated PostgreSQL database named by
`PKDB_TEST_DATABASE_URL`. Each test owns and removes its own random schema.
Run `uv run --locked --python 3.14 pytest -q`, then repeat with `3.13`.
Real-corpus tests require an explicit `PKDB_STUDY_CORPUS` and are separate from
the regular test suite.

## REST and MCP

REST supports complete multipart validation at `POST /api/v2/studies/validate`
and atomic replacement at `PUT /api/v2/studies/{sid}`. Supply `study` and
`reference` JSON fields plus optional `files` attachments. Failed validation
leaves the previous publication intact. Legacy read routes use `/api/v1/`.

Streamable HTTP MCP is mounted at `/mcp/`. Authenticate with
`Authorization: Bearer <token>`, using the same opaque account token as REST.
Anonymous MCP connections are rejected. Revoked/expired tokens and disabled
accounts are checked again for subsequent requests and tool execution.

Exactly four tools are exposed:

- `search_studies(query)`: the shared bounded query model, with entity `studies`.
- `get_study(sid)`: the complete authorized canonical study.
- `validate_study(bundle)`: validation report without publication.
- `replace_study(sid, bundle)`: atomic complete-study replacement.

A bundle contains `study`, `reference`, and an optional `handles` list. Obtain
handles with authenticated `POST /api/v2/files`, containing one multipart part
named `file`. The response includes an opaque `id`, original name, size, SHA-256,
and expiry. Only the owner can use a handle. Duplicate, expired, oversized,
or corrupted attachments are rejected. Server filesystem paths are never inputs.

Scientific validation failures return structured reports with `valid: false`,
source locations, total error count, and a bounded issue list. Authorization and
invalid-handle failures are MCP tool errors. Queries and scientific work run off
the ASGI event loop with independent database sessions. Both interfaces share
request byte/admission limits configured with `PKDB_UPLOAD_*` settings.

## Commands

Set `PKDB_API_TOKEN` in the environment for remote commands. Supply either one
study folder or a directory containing study folders. Commands read source files
without editing them and print one JSON outcome per study. Any failure produces
a nonzero exit status. Upload makes one complete-bundle PUT per study, waits for
publication, and never deletes the previous study before uploading.

```bash
pkdb validate ../pkdb_data/studies/apixaban/Frost2014 --api-url http://localhost:8000
pkdb upload ../pkdb_data/studies/apixaban --api-url http://localhost:8000
```

A timed-out upload has an unknown outcome; rerun the complete bundle. The CLI
does not follow redirects or automatically repeat a request. API tokens are not
accepted as command-line arguments.

Local administrators use the configured `PKDB_DATABASE_URL` and `PKDB_FILE_ROOT`:

```bash
pkdb bootstrap bootstrap
pkdb cleanup
```

Bootstrap applies the reviewed offline vocabulary and account identities in one
transaction. Cleanup removes expired saved criteria and eligible staged/crash
files, preserving publication references and active file leases. Schedule cleanup
through the deployment environment; no background queue is required.
