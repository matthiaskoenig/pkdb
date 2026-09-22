# Test a study upload locally

Use the current `pkdb validate` and `pkdb upload` commands against your local
backend. All commands below run from the repository root. Only Docker and Docker
Compose are required, together with a local study folder.

## Start the backend

```bash
docker compose up --build --wait
docker compose exec backend pkdb create-admin tester --email tester@example.org
```

Enter an administrator password at the hidden prompt. Create this account once;
subsequent restarts preserve it. Open <http://localhost:18083/docs>.

## Select a study and prepare attribution accounts

Set an absolute path to a study folder containing `study.json`, its reference,
and the referenced spreadsheets and attachments. For example:

```bash
export STUDY_DIR=/absolute/path/to/pkdb_data/studies/apixaban/Frost2014
export STUDY_NAME=$(basename "$STUDY_DIR")
docker compose run --rm --no-deps \
  --volume "$STUDY_DIR:/studies/$STUDY_NAME:ro" \
  backend pkdb bootstrap-study /studies
```

The folder is mounted read-only and retains its original name, which must match
the study name. `bootstrap-study` creates missing accounts named
in study attribution, including comment authors, with login disabled. It preserves
existing passwords, roles, and activation. Your administrator account performs the
upload; you do not need to change the study's creator. This is local database
administration, not an API operation.

## Get an API token

In the API interface, expand `POST /api-token-auth/`, choose **Try it out**, and
submit your username and password. Copy the returned `token` value.

Read it into your shell without echoing it or recording it in command history:

```bash
read -r -s -p 'API token: ' PKDB_API_TOKEN
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

Inside Compose, the backend address is `http://backend:8000`. Your browser uses
`http://localhost:18083`. Do not use localhost for the container's API URL.

Each command prints a JSON result and exits nonzero if any study fails. Validation
does not persist the study. A first upload returns status 201; uploading the same
study again returns status 200 and replaces that study atomically.

To inspect the stored study, use the API interface's study endpoints with the token,
or make an authenticated request from your shell:

```bash
curl --fail -H "Authorization: Token $PKDB_API_TOKEN" \
  http://localhost:18083/api/v1/studies/PKDB01110/
```

Replace `PKDB01110` with your study SID. The Frost2014 example contains one group,
70 individuals, 782 measurements, and eight timecourses.

## Test multiple studies

Set `STUDY_DIR` to a parent directory, update `STUDY_NAME`, and repeat the same commands. The CLI discovers
study folders recursively and reports each result. Start with one known study to
make validation failures easy to inspect. Existing corpus validation failures are
not automatically excluded or repaired.

## Troubleshooting

- Unknown attribution user: rerun `bootstrap-study` against the same folder.
- HTTP 401: obtain a token from this local backend and export it again.
- Validation failure: inspect the structured errors and correct your source data.
  Do not bypass validation to make an upload pass.
- Port already in use: set `PKDB_HTTP_PORT` in `.env`, restart Compose, and use that
  port in browser and curl URLs. Container commands continue using port 8000.
- Startup failure: run `docker compose logs --tail=100 backend db`.

Stop with `docker compose stop`; resume with `docker compose up --wait`. Database
and attachments persist across restarts. Finish with `unset PKDB_API_TOKEN`.

## Add an allowed term

Edit the [vocabulary definitions](vocabulary.md) and run the JSON update script,
then rebuild the Docker backend before validating the study again.
