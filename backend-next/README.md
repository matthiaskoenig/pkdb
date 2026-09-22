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

## Legacy staged uploads

The compatibility sequence stages a reference at `POST /api/v1/_references/`,
attachments at `POST /api/v1/_datafiles/`, and study core at
`POST /api/v1/_studies/`. PATCH the related sets to `/_studies/{sid}/` and send
`dataset` last, including an empty object when absent. The final dataset patch
seals the generation; a subsequent patch reopens it unless it includes dataset.
`POST /api/v1/update_index/` with `{"sid": "..."}` then validates and publishes
synchronously. It performs no indexing job. Unsupported actions are rejected.

Drafts and references belong to their staging account and expire after 24 hours.
Their owner can inspect them with `GET /api/v1/_studies/{sid}/` and
`GET /api/v1/_references/{sid}/`. Reference PATCH changes the staged reference;
a study snapshots that reference when its draft begins. Later reference edits
apply to subsequent study drafts and never mutate an existing generation.
A second begin or overlapping operation for the same account/study returns 409.
A retry after successful finalization returns the legacy success response for an
authorized existing study. A newer incomplete draft cannot be finalized by that
retry. Clients without generation identifiers must keep each upload sequence
strictly serial; delayed requests from separate sessions cannot be distinguished.

An explicit `DELETE /api/v1/_studies/{sid}/` really deletes an authorized study.
Delete-before-upload clients therefore cannot preserve old data after a failed
replacement and should use the complete-bundle CLI. Failed staged finalization
itself leaves the previous publication unchanged. Editable reads of already
published source templates, PUT and remaining reference adapter contracts are
still under implementation.


## Browser and container configuration

Set `PKDB_CORS_ORIGINS` to a JSON list of exact frontend origins, for example
`["http://localhost:8080"]`. Authentication uses the Authorization header;
cookie credentials are not enabled. Allowed browsers can read upload-limit errors
and download disposition headers.

Build `docker build -t pkdb-next .` from this directory. Python 3.14 is the default;
`--build-arg PYTHON_VERSION=3.13` selects the other supported interpreter. Python
and uv base digests are pinned. The runtime contains an installed wheel and locked
runtime dependencies, runs as UID/GID 10001, and needs a writable attachment volume
at `/data/files` plus `PKDB_DATABASE_URL`. Apply Alembic explicitly before startup;
application startup never changes the schema.

Provision the first operator locally with
`pkdb create-admin OPERATOR --email EMAIL`. Password input is hidden in a terminal;
`--password-stdin` supports protected automation input. Existing identities are
never upgraded or rekeyed by this command. See the migration runbook for rebuild
accounting and remaining cutover gates.

Legacy administrator account routes support `POST /api/v1/_users/` and
`GET`, `PATCH`, `PUT /api/v1/_users/{id}/` (including JSON suffixes). Creation
returns a new API token once; subsequent reads omit credentials and email, matching
the legacy read serializer. Existing tokens immediately observe role changes.
The new schema has one application role: legacy `basic` maps to `user`;
`curator`, `reviewer`, and `admin` map directly. Multiple or unknown groups are
rejected. Username remains read-only during updates. Arbitrary Django permission
group CRUD is not implemented by this adapter.

Administrator role catalogue reads are available at `GET /api/v1/_user_groups/`
and `GET /api/v1/_user_groups/{id}/`, including JSON suffixes and pagination.
Fresh database IDs 1–4 identify basic, admin, reviewer, and curator respectively;
historical Django group IDs are not preserved. Permission arrays are empty because
authorization uses application policy. Custom group/permission mutation remains
unimplemented and requires a compatibility disposition before cutover.
