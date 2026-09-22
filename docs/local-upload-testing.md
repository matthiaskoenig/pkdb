# Test a study upload locally

Use the current `pkdb validate` and `pkdb upload` commands against your local backend. All commands below run from the repository root. Use Docker and Docker Compose, Node.js 22 for the account frontend, and a local study folder.

## Start the backend

Copy `.env.example` to `.env` if you do not already have a local configuration. Set `PKDB_HTTP_PORT=8000` for the frontend development proxy and keep `PKDB_BROWSER_ORIGIN=http://localhost:8080`. Generate and persist `PKDB_MFA_ENCRYPTION_KEY` following [Administrator bootstrap and MFA](authentication.md#administrator-bootstrap-and-mfa) before signing in. Keep this key across restarts.

```bash
docker compose up --build --wait
docker compose exec backend pkdb create-admin mkoenig --email YOUR_EMAIL
```

Enter an administrator password at the hidden prompt. Create this account once; subsequent restarts preserve it. The sole administrator username is `mkoenig`. Open <http://localhost:8000/docs>.

Start the account frontend in another terminal using Node.js 22:

```bash
cd frontend
npm install
NODE_OPTIONS=--openssl-legacy-provider npm run serve
```

Open <http://localhost:8080>, sign in as `mkoenig`, and enroll an authenticator in account settings. Save the recovery codes securely. Browser authentication uses cookies through the frontend proxy.

## Select a study and prepare attribution accounts

Set an absolute path to a study folder containing `study.json`, its reference, and the referenced spreadsheets and attachments. For example:

```bash
export STUDY_DIR=/absolute/path/to/pkdb_data/studies/apixaban/Frost2014
export STUDY_NAME=$(basename "$STUDY_DIR")
docker compose run --rm --no-deps \
  --volume "$STUDY_DIR:/studies/$STUDY_NAME:ro" \
  backend pkdb bootstrap-study /studies
```

The folder is mounted read-only and retains its original name, which must match the study name. `bootstrap-study` creates missing accounts named in study attribution, including comment authors, with login disabled. It preserves existing passwords, roles, and activation. Your administrator account performs the upload; you do not need to change the study's creator. This is local database administration, not an API operation.

## Create a personal API key

In **Account settings → API keys**, create a named key with `read` and `studies:write` scopes. Confirm administrator identity when prompted. Copy the secret shown once. The old `/api-token-auth/` endpoint is retired. API keys cannot perform administrator account or study-access changes; new uploads are private. Use the MFA-authenticated browser to change study visibility or protected ownership fields.

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
  backend pkdb validate /studies --api-url http://backend:8000

docker compose run --rm --no-deps -e PKDB_API_TOKEN \
  --volume "$STUDY_DIR:/studies/$STUDY_NAME:ro" \
  backend pkdb upload /studies --api-url http://backend:8000
```

Inside Compose, the backend address is `http://backend:8000`. Your browser uses `http://localhost:8000`. Do not use localhost for the container's API URL.

Each command prints a JSON result and exits nonzero if any study fails. Validation does not persist the study. A first upload returns status 201; uploading the same study again returns status 200 and replaces that study atomically.

To inspect the stored study, use the API interface's study endpoints with the token, or make an authenticated request from your shell:

```bash
curl --fail -H "Authorization: Bearer $PKDB_API_TOKEN" \
  http://localhost:8000/api/v1/studies/PKDB01110/
```

Replace `PKDB01110` with your study SID. The Frost2014 example contains one group, 70 individuals, 782 measurements, and eight timecourses.

## Test multiple studies

Set `STUDY_DIR` to a parent directory, update `STUDY_NAME`, and repeat the same commands. The CLI discovers study folders recursively and reports each result. Start with one known study to make validation failures easy to inspect. Existing corpus validation failures are not automatically excluded or repaired.

## Troubleshooting

- Unknown attribution user: rerun `bootstrap-study` against the same folder.
- HTTP 401: create a personal key on this local backend and export it again.
- Validation failure: inspect the structured errors and correct your source data. Do not bypass validation to make an upload pass.
- Port already in use: set `PKDB_HTTP_PORT` in `.env`, restart Compose, and use that port in browser and curl URLs, and update the proxy targets in `frontend/vue.config.js`. Container commands continue using port 8000.
- Startup failure: run `docker compose logs --tail=100 backend db`.

Stop with `docker compose stop`; resume with `docker compose up --wait`. Database and attachments persist across restarts. Finish with `unset PKDB_API_TOKEN`.

## Add an allowed term

Edit the [vocabulary definitions](vocabulary.md) and run the JSON update script, then rebuild the Docker backend before validating the study again.

## Isolated frontend browser checks

Build the frontend with its pinned Node/npm versions (`npm ci`, `npm run build` under `frontend/`), install Playwright browsers (`npx playwright install --with-deps`), then run `npm run test:e2e`. The harness starts `compose.frontend-test.yaml` under the distinct `pkdb-frontend-test` project, serves the production artifact at `http://127.0.0.1:18184`, and cleans up only that project's disposable resources. It neither uploads to nor removes the local development deployment.

The fixture loader fails closed unless its database is exactly `pkdb_frontend_test` on the isolated Compose database host with the dedicated test username and explicit fixture flag. Scientific data are artificial and shared with backend scope contract tests. Test-only accounts use the documented fixture password; do not reuse it for any deployment. Provider credentials and real mail delivery are not required by the harness and remain separate staging checks.
