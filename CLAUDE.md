# Repository guide

The only backend is `backend/`, a Python 3.14 FastAPI application using PostgreSQL, SQLAlchemy, Alembic, and Pydantic. Runtime code lives in `backend/src/pkdb`. The `pkdb` CLI validates and uploads source study folders. The frontend remains in `frontend/`; documentation is built with Zensical from `docs/` and `zensical.toml`.

Run `docker compose --profile dev up --build --wait` for the local frontend, API, and database. Follow `docs/installation.md` to create an administrator with a chosen username and import the user roster. See `docs/local-upload-testing.md` for real study uploads. Use `compose.test.yaml` for a separate disposable test database. Never delete or reuse existing deployment data volumes as part of source cleanup.

Follow `docs/installation.md` for tests, lint, types, migrations, and documentation. Commit Alembic migrations. Do not edit generated changelogs. Use topic branches and pull requests against `develop`; required checks are tests, ruff, ty, and docs.

Historical migration reports are evidence, not current installation instructions. Do not claim unresolved corpus or compatibility gates passed merely because the previous implementation has been removed.

Write Markdown paragraphs on a single source line. Use editor soft wrapping instead of inserting line breaks for visual width. Preserve structural line breaks for headings, lists, tables, and code blocks.

Keep `README.md` and the documentation landing page (`docs/index.md`) aligned when updating shared descriptions, features, images, notices, citations, licensing, funding, or copyright. Adapt relative links and markup for each location, preserve documentation-specific navigation, and keep the copyright footer in `zensical.toml` consistent.
