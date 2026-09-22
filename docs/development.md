# Development

The backend lives in `backend/`: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, and the `pkdb` CLI. Python 3.14 is required and tested in CI.

See [Accounts, authentication, and API keys](authentication.md) for same-origin browser configuration, provider setup, administrator recovery, and curator migration.

## Environment and tests

Install uv and Python 3.14 for the application, tests, and development hooks. Run from the repository root:

```bash
uv sync --project backend --locked --python 3.14
uv run --project backend pre-commit install
docker compose -f compose.test.yaml up -d --wait
export PKDB_TEST_DATABASE_URL=postgresql+psycopg://pkdb_test:local-test-only@127.0.0.1:15439/pkdb_test
uv run --project backend pytest backend/tests -q -x
uv run --project backend python -m pytest tools/backend_migration -q -x
uv run --project backend ruff check .
uv run --project backend ruff format --check .
uv run --project backend ty check --project backend
```

The test database uses temporary container storage. Tests create isolated schemas. Keep it separate from your upload-testing database. Stop it with `docker compose -f compose.test.yaml down`.

Image lifecycle and backup/restore tests live in `backend/system_tests`. They require Docker, a built image selected by `PKDB_TEST_IMAGE`, and the test database URL. CI runs these tests for both Python versions. Corpus tests require explicitly configured source data and are not part of the default suite.

## Migrations

Commit Alembic migrations in `backend/alembic/versions/`. Compose applies them before starting the API. The ASGI application itself does not mutate database schemas. For native development, set `PKDB_DATABASE_URL`, change into `backend/`, and run `uv run alembic upgrade head`. Check model/schema agreement with `uv run alembic check`.

## Documentation

Zensical builds independently of the backend:

```bash
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
uv run --no-project --python 3.14 python scripts/llms_txt.py
```

## Branches and releases

Use a topic branch and a pull request against `develop`. Required checks are `tests`, `ruff`, `ty`, and `docs`. The `tests` check includes both Python versions and a fresh Compose startup/restart smoke test. Release automation uses `.bumpversion.toml` to update package metadata, the lockfile, and the runtime version together. Do not edit generated changelogs manually.
