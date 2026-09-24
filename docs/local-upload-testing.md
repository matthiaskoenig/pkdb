# Test a study upload locally

!!! important "For developers and operators only"

    This section is for working on PK-DB itself or running a separate server. General users do not need a source checkout, Docker, a database, or administrator access. To use PK-DB, start with [Browse and access data](web-interface.md) or the [Python client and API](python-client.md).

## Minimal local setup

Use Docker Compose for the server and the `pkdb` Python package on your host to validate and upload data. You need Git, Docker with Compose, and [uv](https://docs.astral.sh/uv/getting-started/installation/). Run the following steps in Bash from the repository root. If you do not have a checkout yet:

```bash
git clone --branch develop https://github.com/matthiaskoenig/pkdb.git
cd pkdb
```

### Start the server

On a first setup, start directly with `up`. To erase an existing local setup first, run the optional reset command below.

!!! warning "Optional reset deletes local data"

    `docker compose --profile dev down --volumes --remove-orphans` deletes this Compose project's database and attachments, including all accounts and uploaded studies. Skip it to preserve existing data.

```bash
docker compose --profile dev up --build --wait
```

Startup applies migrations and loads the vocabulary. Defaults work without a `.env` file. The frontend runs at <http://localhost:8080> and the API at <http://localhost:18083>.

### Create the administrator and import users

Choose your administrator username and email, then enter a password at the hidden prompt:

```bash
export PKDB_ADMIN=mkoenig
export PKDB_ADMIN_EMAIL=your-email@example.org
docker compose exec backend pkdb-server create-admin "$PKDB_ADMIN" \
  --email "$PKDB_ADMIN_EMAIL"

docker compose exec backend pkdb-server import-users \
  /app/bootstrap/curator-roster.json \
  --avatar-root /app/frontend/public --apply
```

Create the administrator once per fresh database. Its email is verified by this operator command, so local login and API-key creation need no SMTP. The imported roster supplies historical study attribution; newly imported accounts have login disabled. Your administrator performs the upload. For more account options, see [local setup and development](installation.md#populate-the-database-with-our-users).

## Select a study and prepare attribution accounts

Set an absolute path to a study folder containing `study.json`, its reference, and the referenced spreadsheets and attachments. For example:

```bash
export PKDB_STUDY_DIR=/absolute/path/to/pkdb_data/studies/apixaban/Frost2014
export PKDB_STUDY_NAME="$(basename "$PKDB_STUDY_DIR")"
docker compose run --rm --no-deps \
  --volume "$PKDB_STUDY_DIR:/studies/$PKDB_STUDY_NAME:ro" \
  backend pkdb-server bootstrap-study /studies
```

The folder is mounted read-only and retains its original name, which must match the study name. `bootstrap-study` creates missing accounts named in study attribution, including comment authors, with login disabled. It preserves existing passwords, roles, and activation. Your administrator account performs the upload; you do not need to change the study's creator. This is local database administration, not an API operation.

## Create a personal API key

Sign in at <http://localhost:8080> with your administrator account. In **Account settings → API keys**, create a named key with `read` and `studies:write` scopes. Confirm administrator identity when prompted. Copy the secret shown once. The old `/api-token-auth/` endpoint is retired. A key with `studies:write` can upload studies with either `access: public` or `access: private`; no private draft is required. Visibility is preserved from the source, and an authorized writer can change it on replacement. Private data is visible only to assigned curators and the administrator. Account administration, changing existing ownership, and changing an existing licence still require the appropriate administrator session.

Read it into your shell without echoing it or recording it in command history:

```bash
read -r -s -p 'Personal API key: ' PKDB_API_KEY
printf '\n'
export PKDB_API_KEY
```

## Install the package, validate, and upload

Install the `pkdb` package from the same checkout as the server so their processing versions match. uv supplies Python 3.14 if needed:

```bash
uv tool install --python 3.14 ./python
export PKDB_ENDPOINT=http://localhost:18083

pkdb vocabulary sync
pkdb validate "$PKDB_STUDY_DIR" --offline
pkdb upload "$PKDB_STUDY_DIR"
```

If `pkdb` is already installed with uv from another checkout or release, reinstall it with `uv tool install --reinstall --python 3.14 ./python`. If your shell cannot find `pkdb`, run `uv tool update-shell` and open a new shell, then restore the study path, endpoint, and API-key variables above.

`pkdb vocabulary sync` caches the local server's vocabulary. Validation uses that snapshot without uploading; upload also validates automatically before sending the source bundle. These commands run on your host, so use `http://localhost:18083`, not the Docker-internal address `http://backend:8000`. The public package reads `PKDB_API_KEY` for authentication.

Each command prints a JSON result and exits nonzero if any study fails. Validation does not persist the study. A first upload returns status 201; uploading the same study again returns status 200 and replaces that study atomically.

Open **Explore data** at <http://localhost:8080> to see your study. To inspect the stored study, use the API interface's study endpoints with the token, or make an authenticated request from your shell:

```bash
curl --fail -H "Authorization: Bearer $PKDB_API_KEY" \
  http://localhost:18083/api/v1/studies/PKDB01110/
```

Replace `PKDB01110` with your study SID. The Frost2014 example contains one group, 70 individuals, 782 measurements, and eight timecourses.

## Test multiple studies

Set `PKDB_STUDY_DIR` to a parent directory, update `PKDB_STUDY_NAME`, and repeat the same commands. The CLI discovers study folders recursively and reports each result. Start with one known study to make validation failures easy to inspect. Existing corpus validation failures are not automatically excluded or repaired.

## Troubleshooting

- Unknown attribution user: rerun `bootstrap-study` against the same folder.
- HTTP 401: create a personal key on this local backend and export it again.
- Validation failure: inspect the structured errors and correct your source data. Do not bypass validation to make an upload pass.
- Port already in use: set `PKDB_HTTP_PORT` in `.env`, restart Compose, and update `PKDB_ENDPOINT` and curl URLs to use that port. Set `PKDB_DEV_API_TARGET` if running Vite on the host. The Docker frontend needs no proxy change. The backend continues using port 8000 inside Docker.
- Vocabulary mismatch: run `pkdb vocabulary sync` against the local endpoint and validate again. For a processing-version mismatch, reinstall the package from the same checkout used to build the backend.
- Startup failure: run `docker compose logs --tail=100 backend db`.

Stop with `docker compose --profile dev stop`; resume with `docker compose --profile dev up --wait`. Database and attachments persist across restarts. Finish with `unset PKDB_API_KEY`.

## Add an allowed term

Edit the [vocabulary definitions](vocabulary.md) and run the JSON update script, then rebuild the Docker backend before validating the study again.

## Isolated frontend browser checks

Build the frontend with its pinned Node/npm versions (`npm ci`, `npm run build` under `frontend/`), install Playwright browsers (`npx playwright install --with-deps`), then run `npm run test:e2e`. The harness starts `compose.frontend-test.yaml` under the distinct `pkdb-frontend-test` project, serves the production artifact at `http://127.0.0.1:18184`, and cleans up only that project's disposable resources. It neither uploads to nor removes the local development deployment.

The fixture loader fails closed unless its database is exactly `pkdb_frontend_test` on the isolated Compose database host with the dedicated test username and explicit fixture flag. Scientific data are artificial and shared with backend scope contract tests. Test-only accounts use the documented fixture password; do not reuse it for any deployment. No provider credentials or MFA setup are used. Real mail delivery is not required by the harness and remains a separate staging check.
