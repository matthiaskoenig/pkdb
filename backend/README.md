# PK-DB backend

This is the sole backend implementation: FastAPI, SQLAlchemy, PostgreSQL, and the `pkdb-server` command-line interface. Python 3.14 and 3.15 are supported.

From the repository root, run `docker compose --profile dev up --build --wait`. Startup applies migrations and imports the bundled vocabulary. The API documentation is available at <http://localhost:18083/docs>.

See [local setup and development](../docs/installation.md) and [local study upload testing](../docs/local-upload-testing.md) for complete commands.

## Layout

- `src/pkdb_server`: API, administration CLI, persistence, and attachment storage.
- `../python/src/pkdb`: shared scientific validation, schemas, parsers, and public Python client.
- `alembic`: versioned schema migrations.
- `bootstrap`: offline vocabulary and provenance; no credentials.
- `tests`: regular scientific, API, CLI, and PostgreSQL tests.
- `system_tests`: container lifecycle and database/attachment restore tests.
- `corpus_tests`: opt-in source corpus verification.

`pkdb-server validate` checks a study without persisting it. `pkdb-server upload` stores a valid study atomically and replaces an existing study with the same SID. Both authenticate using `PKDB_API_TOKEN`. Local administration commands are `create-admin`, `bootstrap`, `bootstrap-study`, and `cleanup`. The last command removes eligible orphaned attachments; it is not a database reset command.

## Legacy upload retirement

Apply migrations before starting this version (`alembic -c backend/alembic.ini upgrade head` from the repository root, with `PKDB_DATABASE_URL` configured). Revision `p002retirelegacy` removes legacy draft/handle tables and ineffective collaborator access grants. It preserves published studies, source attachments, curator grants, and contributor attribution. Pending legacy drafts must be uploaded again as complete bundles; downgrade restores the old schema, not discarded draft data.

The admin access API now accepts curator assignments only; `reader_ids` is rejected rather than silently stored without granting access. Authenticated requests remain unthrottled. The unused account/key/upload/export quota settings and account usage display have been removed; anonymous controls and upload/export size limits remain.
