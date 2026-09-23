# Test a study upload locally

!!! important "For developers and operators only"

    This section is for working on PK-DB itself or running a separate server. General users do not need a source checkout, Docker, a database, or administrator access. To use PK-DB, start with [Browse and access data](web-interface.md) or the [Python client and API](python-client.md).

Use the current `pkdb-server validate` and `pkdb-server upload` commands against your local backend. Complete [Local setup and development](installation.md#quick-start) first, then sign in at <http://localhost:8080> with your chosen administrator username. All commands below run from the repository root and use Docker plus a local study folder.

## Select a study and prepare attribution accounts

Set an absolute path to a study folder containing `study.json`, its reference, and the referenced spreadsheets and attachments. For example:

```bash
export STUDY_DIR=/absolute/path/to/pkdb_data/studies/apixaban/Frost2014
export STUDY_NAME=$(basename "$STUDY_DIR")
docker compose run --rm --no-deps \
  --volume "$STUDY_DIR:/studies/$STUDY_NAME:ro" \
  backend pkdb-server bootstrap-study /studies
```

The folder is mounted read-only and retains its original name, which must match the study name. `bootstrap-study` creates missing accounts named in study attribution, including comment authors, with login disabled. It preserves existing passwords, roles, and activation. Your administrator account performs the upload; you do not need to change the study's creator. This is local database administration, not an API operation.

## Create a personal API key

In **Account settings → API keys**, create a named key with `read` and `studies:write` scopes. Confirm administrator identity when prompted. Copy the secret shown once. The old `/api-token-auth/` endpoint is retired. API keys cannot perform administrator account or study-access changes; new uploads are private. Use the password-authenticated browser to change study visibility or protected ownership fields.

Read it into your shell without echoing it or recording it in command history:

```bash
read -r -s -p 'Personal API key: ' PKDB_API_TOKEN
printf '\n'
export PKDB_API_TOKEN
```

## Validate, then upload

```bash
docker compose run --rm --no-deps -e PKDB_API_TOKEN \
  --volume "$STUDY_DIR:/studies/$STUDY_NAME:ro" \
  backend pkdb-server validate /studies --api-url http://backend:8000

docker compose run --rm --no-deps -e PKDB_API_TOKEN \
  --volume "$STUDY_DIR:/studies/$STUDY_NAME:ro" \
  backend pkdb-server upload /studies --api-url http://backend:8000
```

Inside Compose, the backend address is `http://backend:8000`. Your browser uses `http://localhost:18083`. Do not use localhost for the container's API URL.

Each command prints a JSON result and exits nonzero if any study fails. Validation does not persist the study. A first upload returns status 201; uploading the same study again returns status 200 and replaces that study atomically.

To inspect the stored study, use the API interface's study endpoints with the token, or make an authenticated request from your shell:

```bash
curl --fail -H "Authorization: Bearer $PKDB_API_TOKEN" \
  http://localhost:18083/api/v1/studies/PKDB01110/
```

Replace `PKDB01110` with your study SID. The Frost2014 example contains one group, 70 individuals, 782 measurements, and eight timecourses.

## Test multiple studies

Set `STUDY_DIR` to a parent directory, update `STUDY_NAME`, and repeat the same commands. The CLI discovers study folders recursively and reports each result. Start with one known study to make validation failures easy to inspect. Existing corpus validation failures are not automatically excluded or repaired.

## Troubleshooting

- Unknown attribution user: rerun `bootstrap-study` against the same folder.
- HTTP 401: create a personal key on this local backend and export it again.
- Validation failure: inspect the structured errors and correct your source data. Do not bypass validation to make an upload pass.
- Port already in use: set `PKDB_HTTP_PORT` in `.env`, restart Compose, and use that port in browser and curl URLs, and set `PKDB_DEV_API_TARGET` if running Vite on the host. The Docker frontend needs no proxy change. Container commands continue using port 8000.
- Startup failure: run `docker compose logs --tail=100 backend db`.

Stop with `docker compose --profile dev stop`; resume with `docker compose --profile dev up --wait`. Database and attachments persist across restarts. Finish with `unset PKDB_API_TOKEN`.

## Add an allowed term

Edit the [vocabulary definitions](vocabulary.md) and run the JSON update script, then rebuild the Docker backend before validating the study again.

## Isolated frontend browser checks

Build the frontend with its pinned Node/npm versions (`npm ci`, `npm run build` under `frontend/`), install Playwright browsers (`npx playwright install --with-deps`), then run `npm run test:e2e`. The harness starts `compose.frontend-test.yaml` under the distinct `pkdb-frontend-test` project, serves the production artifact at `http://127.0.0.1:18184`, and cleans up only that project's disposable resources. It neither uploads to nor removes the local development deployment.

The fixture loader fails closed unless its database is exactly `pkdb_frontend_test` on the isolated Compose database host with the dedicated test username and explicit fixture flag. Scientific data are artificial and shared with backend scope contract tests. Test-only accounts use the documented fixture password; do not reuse it for any deployment. No provider credentials or MFA setup are used. Real mail delivery is not required by the harness and remains a separate staging check.
