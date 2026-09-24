# Local setup and development

!!! important "For developers and operators only"

    This section is for working on PK-DB itself or running a separate server. General users do not need a source checkout, Docker, a database, or administrator access. To use PK-DB, start with [Browse and access data](web-interface.md) or the [Python client and API](python-client.md).

Run the backend, frontend, and PostgreSQL locally with Docker Engine and the Docker Compose plugin. No host Python, Node.js, PostgreSQL, mail server, or external authentication service is needed for this setup.

## Quick start

Clone the repository (`git clone https://github.com/matthiaskoenig/pkdb.git`) and change into it (`cd pkdb`). From the repository root, run these two commands, replacing `PKDB_ADMIN` and `PKDB_ADMIN_EMAIL` with your chosen administrator username and email address:

```bash
PKDB_BUILD_COMMIT="$(git rev-parse HEAD)" docker compose --profile dev up --build --wait
docker compose exec backend pkdb-server create-admin PKDB_ADMIN --email PKDB_ADMIN_EMAIL
```

Enter a password at the hidden prompt. Create the administrator once; subsequent starts preserve the account. There is one designated administrator per database, identified by its internal account ID. The username is your choice. The email is marked verified by this operator command, so local login and API-key creation work without SMTP.

The first build downloads dependencies. Startup applies database migrations and loads the bundled vocabulary. Defaults work without an environment file.

| Open | Purpose |
| --- | --- |
| <http://localhost:8080> | Frontend; sign in with the username and password you chose |
| <http://localhost:18083/docs> | Backend API documentation |
| <http://localhost:18083/health/ready> | Backend readiness check |

The frontend proxies API requests to the backend, including browser session cookies and CSRF. Use `localhost` consistently for browser login. Both HTTP ports bind only to the local machine.

## Populate the database with our users

As the third setup command, load the bundled historical curator/reviewer roster and avatars:

```bash
docker compose exec backend pkdb-server import-users /app/bootstrap/curator-roster.json --avatar-root /app/frontend/public --apply
```

Use `--dry-run` instead of `--apply` to preview changes first, especially on an existing database. The public roster contains 69 historical entries: 67 curator/reviewer accounts are imported on a fresh database; the historical test account is excluded, and the historical administrator profile is skipped unless it matches the already designated administrator. Choosing another admin username does not rename or adopt that historical identity. The empty `users.json` is not the user roster. Compose mounts the bundled avatars read-only and the importer copies them into persistent backend storage.

Imported users retain their attribution, roles, and profile data, but new imported accounts have no usable password and remain disabled. Repeating the same import is safe: it preserves credentials, account state, and later profile edits. Existing role or study-assignment changes require a reviewed dry run and `--update-existing` on both preview and apply.

### Active accounts for local testing

For immediate login as a curator, create a separate test account with a username absent from the historical roster:

```bash
docker compose exec backend pkdb-server create-user local-curator --role curator --email local-curator@example.org
```

Enter its password when prompted. Use `--role reviewer` to test reviewer access to public studies, or omit `--role` for an ordinary reader. Private-study access requires an explicit curator assignment unless the account is the administrator. Email is optional for browser login; supply it when testing personal API keys. These commands create new accounts and never overwrite imported users or reset existing passwords.

### Invite the real users

Provide reviewed email addresses in a private JSON file outside the repository, for example `/absolute/path/contacts.json`:

```json
[
  {"username": "MariiaMysh", "email": "reviewed-contact@example.org"}
]
```

Mount it read-only for the import. Preview, resolve any conflicts, then repeat with `--apply` in place of `--dry-run`:

```bash
docker compose run --rm --no-deps \
  --volume /absolute/path/contacts.json:/private/contacts.json:ro \
  backend pkdb-server import-users /app/bootstrap/curator-roster.json \
  --avatar-root /app/frontend/public --contacts /private/contacts.json --dry-run
```

Configure SMTP in `.env` and recreate the backend with `docker compose --profile dev up -d --wait`. Sign in as the administrator and use **User administration → Invite**. Recipients accept the invitation and choose their own password. Importing does not send mail or activate users. See [account administration](administration.md#existing-curators-and-avatars) for contact overlays, existing account IDs, and study assignments.

## Load studies and test uploads

The initial database contains vocabulary and any users you imported, but no studies. Follow the [minimal local upload setup](local-upload-testing.md#minimal-local-setup) for the complete sequence: start Docker, create the administrator, import users, prepare attribution accounts, and validate and upload with the `pkdb` Python package. This uses the same running stack and does not require another backend installation.

## Daily development

Start the live frontend at **http://localhost:8080** with:

```bash
docker compose --profile dev up --build --wait
```

Keep this stack running while editing the GUI. Save a Vue, TypeScript, or CSS file under `frontend/src/` and Vite updates the open browser through hot module replacement, preserving component state where possible. Changes to assets in `frontend/public/` trigger a page reload. You do not need to rebuild the image or refresh the browser for these edits. The source directories are mounted into the Vite container. Docker development uses polling every 250 ms so changes are detected even when bind-mount filesystem events are missed. Set `PKDB_DEV_USE_POLLING=false` in `.env` to use native filesystem events when those work reliably. Rebuild after dependency or frontend configuration changes. Backend code is built into its image; after changing it, run:

```bash
PKDB_BUILD_COMMIT="$(git rev-parse HEAD)" docker compose --profile dev up --build --wait
```

Stop and resume without losing database or attachment data:

```bash
docker compose --profile dev stop
docker compose --profile dev up --wait
```

`docker compose --profile dev down` also preserves named volumes. Adding `--volumes` deletes the local database and attachments. The project is named `pkdb-current`; it does not reuse older deployment volumes. Inspect failures with `docker compose --profile dev logs --tail=100 backend db frontend`.

### Configuration

Copy `.env.example` to `.env` if you need overrides. `PKDB_HTTP_PORT` changes the backend's host port (default `18083`); the container frontend always reaches it on `http://backend:8000`. Keep `PKDB_BROWSER_ORIGIN=http://localhost:8080` for the default frontend. The database password must be URL-safe because it appears in the connection URL. Changing it after database initialization does not change the stored PostgreSQL password.

### Native frontend and frontend checks

For a host frontend with the Docker backend, start only the database and API with `docker compose up --build --wait`. If you use the [native backend](#native-backend-server) instead, keep that process running and skip this Compose startup. Stop any Docker frontend with `docker compose --profile dev stop frontend`. Install Node **24.21.0** and npm **12.1.0**, then run:

```bash
cd frontend
npm install --global npm@12.1.0
npm ci
npm run dev
```

The development proxy defaults to `http://127.0.0.1:18083`. Set `PKDB_DEV_API_TARGET=http://127.0.0.1:YOUR_PORT` when starting Vite if you changed the backend host port. Keep `VITE_API_BASE` empty for same-origin requests. Native Vite uses filesystem events by default; set `PKDB_DEV_USE_POLLING=true` if your filesystem does not reliably deliver change notifications.

Run frontend checks from `frontend/`:

```bash
npm run test:source
npm run typecheck
npm run lint
npm run test:unit -- --run
npm run build
npx playwright install --with-deps
npm run test:e2e
```

Browser tests use a separate disposable Compose project. See [isolated frontend browser checks](local-upload-testing.md#isolated-frontend-browser-checks).

## Native backend server

Use this workflow when you need automatic backend reloads. Stop the Compose backend first so port `18083` is free; this native workflow uses a separate development database and file directory:

```bash
docker compose --profile dev stop backend frontend
docker run --detach --name pkdb-native-db \
  --publish 127.0.0.1:15438:5432 \
  --env POSTGRES_DB=pkdb_dev --env POSTGRES_USER=pkdb_dev \
  --env POSTGRES_PASSWORD=local-development-only \
  --mount source=pkdb-native-database,target=/var/lib/postgresql \
  postgres:18.6
docker exec pkdb-native-db pg_isready -U pkdb_dev -d pkdb_dev
```

Wait for `pg_isready` to report that PostgreSQL accepts connections. On subsequent starts, use `docker start pkdb-native-db` instead of creating it again. From the repository root:

```bash
uv sync --project backend --locked --python 3.14
export PKDB_DATABASE_URL=postgresql+psycopg://pkdb_dev:local-development-only@127.0.0.1:15438/pkdb_dev
export PKDB_FILE_ROOT="$PWD/.cache/native-files"
export PKDB_BROWSER_ORIGIN=http://localhost:8080
export PKDB_SECURE_COOKIES=false
mkdir -p "$PKDB_FILE_ROOT"
cd backend
uv run --locked alembic upgrade head
uv run --locked pkdb-server bootstrap bootstrap
uv run --locked pkdb-server create-admin PKDB_ADMIN --email PKDB_ADMIN_EMAIL
uv run --locked uvicorn pkdb_server.app:create_app --factory --reload --host 127.0.0.1 --port 18083
```

Create the administrator only once and choose its password at the prompt. In another terminal, start the [native frontend](#native-frontend-and-frontend-checks); its default proxy reaches this API on port `18083`. Keep the environment variables set for subsequent native API and migration commands. This local database and its accounts are independent of `alpha.pk-db.com`.

## Backend tests and checks

The library and backend support Python 3.14 and 3.15 (currently tested with 3.15.0rc2). Python 3.15 currently uses the Pydantic 2.14 beta for native dependency wheels and the beartype 0.23 release candidate for MCP compatibility. Python 3.14 remains the default for local development, hooks, and Docker. To build the Python 3.15 runtime, use `docker build --build-arg PYTHON_VERSION=3.15 -f backend/Dockerfile .`.

Install uv and Python 3.14 for the development hooks. Run from the repository root (use `--python 3.15` to select Python 3.15):

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

Image lifecycle and backup/restore tests live in `backend/system_tests`. They require Docker, a built image selected by `PKDB_TEST_IMAGE`, and the test database URL. CI runs these tests on Python 3.14 and 3.15. Corpus tests require explicitly configured source data and are not part of the default suite.

## Migrations

Commit Alembic migrations in `backend/alembic/versions/`. Compose applies them before starting the API. The ASGI application itself does not mutate database schemas. For native development, set `PKDB_DATABASE_URL`, change into `backend/`, and run `uv run alembic upgrade head`. Check model/schema agreement with `uv run alembic check`.

The unified data-model baseline (`p001initial`) requires an empty database and fresh study uploads. Historical migration revisions are no longer supported. Follow the [local upload guide](local-upload-testing.md) for account setup and uploading, and the [data-model guide](data-model.md#fresh-database-setup) for the baseline details.

## Documentation

Zensical builds independently of the backend:

```bash
uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean
uv run --no-project --python 3.14 python scripts/llms_txt.py
```

## Branches and releases

Use a topic branch and a pull request against `develop`. Required checks are `tests`, `ruff`, `ty`, and `docs`. The `tests` check covers both Python versions and a fresh Compose startup/restart smoke test. Release automation uses `.bumpversion.toml` to update package metadata, the lockfile, and the runtime version together. Do not edit generated changelogs manually.
