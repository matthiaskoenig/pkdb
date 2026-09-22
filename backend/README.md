# PK-DB backend

This is the sole backend implementation: FastAPI, SQLAlchemy, PostgreSQL, and the
`pkdb` command-line interface. Python 3.13 and 3.14 are supported.

From the repository root, run `docker compose up --build --wait`. Startup applies
migrations and imports the bundled vocabulary. The API documentation is available
at <http://localhost:18083/docs>.

See [installation](../docs/installation.md), [local study upload testing](../docs/local-upload-testing.md),
and [development](../docs/development.md) for complete commands.

## Layout

- `src/pkdb`: API, CLI, scientific validation, persistence, and attachment storage.
- `alembic`: versioned schema migrations.
- `bootstrap`: offline vocabulary and provenance; no credentials.
- `tests`: regular scientific, API, CLI, and PostgreSQL tests.
- `system_tests`: container lifecycle and database/attachment restore tests.
- `corpus_tests`: opt-in source corpus verification.

`pkdb validate` checks a study without persisting it. `pkdb upload` stores a valid
study atomically and replaces an existing study with the same SID. Both authenticate
using `PKDB_API_TOKEN`. Local administration commands are `create-admin`, `bootstrap`,
`bootstrap-study`, and `cleanup`. The last command removes eligible orphaned attachments;
it is not a database reset command.
