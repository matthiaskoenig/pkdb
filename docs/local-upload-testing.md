# Test a study upload locally

This guide runs the replacement backend and its **`pkdb upload`** command on your
machine. It uses PostgreSQL, FastAPI and a local attachment directory. Start with
one study, inspect the result, then test replacement of that same study.

The replacement currently lives in `backend-next/` on the
`backend/fastapi-replacement` branch. These instructions require that checkout;
`develop` does not yet contain the new backend. The legacy backend remains until
migration acceptance is complete.

## Requirements

- Bash on Linux or macOS, Docker, Git and `uv`.
- Python 3.14, which `uv` can install. Python 3.13 is also supported; use the same
  version throughout the commands below.
- The separate study corpus, including the complete study folder and attachments.
  The example uses `apixaban/Frost2014`, which passes the migration's scientific
  comparison tests. `Frost2014a` is a different study with known validation errors.
- Available local ports **15437** (PostgreSQL) and **18083** (API).

Run the following commands from the **migration checkout root**, in one Bash
terminal. For the existing local migration checkout:

```bash
cd /tmp/pkdb-backend-replacement

git branch --show-current
test -f backend-next/pyproject.toml
export PKDB_REPO="$PWD"
export PKDB_UPLOAD_WORK="$(mktemp -d /tmp/pkdb-upload.XXXXXX)"
export PKDB_UPLOAD_URL=http://127.0.0.1:18083
export PKDB_DATABASE_URL=postgresql+psycopg://pkdb_upload:local-upload-only@127.0.0.1:15437/pkdb_upload
export PKDB_FILE_ROOT="$PKDB_UPLOAD_WORK/files"
mkdir -p "$PKDB_FILE_ROOT"
printf 'Local test workspace: %s\n' "$PKDB_UPLOAD_WORK"

uv sync --project backend-next --locked --python 3.14
```

If your checkout lives elsewhere, change the first `cd`. The credentials above
are only for the dedicated local test database. Keep using this terminal so the
exported variables remain available. `/tmp` is temporary storage; use a durable
workspace path instead if you want to retain the test across machine cleanup.

## Start PostgreSQL and apply migrations

This creates a separate database container with a named volume and binds its
port only to localhost. Existing PK-DB containers can stay running.

```bash
docker run -d --name pkdb-upload-local \
  -e POSTGRES_DB=pkdb_upload \
  -e POSTGRES_USER=pkdb_upload \
  -e POSTGRES_PASSWORD=local-upload-only \
  -p 127.0.0.1:15437:5432 \
  -v pkdb-upload-local-pg:/var/lib/postgresql \
  --health-cmd='pg_isready -U pkdb_upload -d pkdb_upload' \
  --health-interval=2s --health-timeout=5s --health-retries=30 \
  postgres:18.0

until docker exec pkdb-upload-local pg_isready -U pkdb_upload -d pkdb_upload; do
  sleep 2
done

(
  cd "$PKDB_REPO/backend-next"
  uv run --locked --python 3.14 alembic upgrade head
  uv run --locked --python 3.14 alembic check
)
```

`alembic check` should report no new upgrade operations. If the container already
exists from an earlier session, use `docker start pkdb-upload-local` instead of
`docker run`. If startup fails, inspect `docker logs pkdb-upload-local` before
continuing.

## Select a study and bootstrap its identities

Set the path to your **existing corpus study folder**. The path below matches the
local corpus checkout; adjust it on another machine.

```bash
export PKDB_SOURCE_STUDY=/home/mkoenig/git/pkdb_data/studies/apixaban/Frost2014

test -f "$PKDB_SOURCE_STUDY/study.json"
test -f "$PKDB_SOURCE_STUDY/reference.json"
mkdir -p "$PKDB_UPLOAD_WORK/studies"
cp -a "$PKDB_SOURCE_STUDY" "$PKDB_UPLOAD_WORK/studies/"
export PKDB_UPLOAD_STUDY="$PKDB_UPLOAD_WORK/studies/$(basename "$PKDB_SOURCE_STUDY")"
```

Keep the folder's name and all workbook, TSV, image and PDF files. The CLI reads
source files without modifying them; this copy also gives you a place to make
experimental edits without changing the corpus.

The backend needs the vocabulary and every identity named by the study, including
comment authors. This script reads the study through the new importer and writes
a local bootstrap directory. It does not load historical account exports or
create working credentials for the study's authors.

```bash
uv run --project backend-next --locked --python 3.14 python - <<'PY'
import json
import os
import shutil
from pathlib import Path

from pkdb.domain.provenance import comment_authors
from pkdb.importers.folder import load_folder, parse_bundle

study = parse_bundle(load_folder(Path(os.environ["PKDB_UPLOAD_STUDY"])))
names = {
    study.metadata.creator,
    *study.metadata.collaborators,
    *(curator.user for curator in study.metadata.curators),
    *comment_authors(study),
}
bootstrap = Path(os.environ["PKDB_UPLOAD_WORK"]) / "bootstrap"
bootstrap.mkdir(exist_ok=True)
shutil.copyfile(
    Path(os.environ["PKDB_REPO"]) / "backend-next/bootstrap/vocabulary.json",
    bootstrap / "vocabulary.json",
)
(bootstrap / "users.json").write_text(
    json.dumps([{"username": name, "role": "user"} for name in sorted(names)])
)
print(f"Prepared {len(names)} disabled study identities")
PY

uv run --project backend-next --locked --python 3.14 \
  pkdb bootstrap "$PKDB_UPLOAD_WORK/bootstrap"
```

Expect `"ok": true` and an empty `errors` list. Bootstrapped identities are disabled
and have no passwords. The administrator created next can upload a study while
preserving its original creator and curator attribution.

## Create your local operator and start the API

```bash
export PKDB_UPLOAD_USER=upload-tester

uv run --project backend-next --locked --python 3.14 \
  pkdb create-admin "$PKDB_UPLOAD_USER" --email upload-tester@example.org
```

Enter a new local test password at the hidden prompt, using at least 12 characters.
Remember it for login below. This account is verified locally, so no SMTP setup is
needed. Creation returns `"ok": true`; rerunning it does not reset an existing
account or change its role.

Start the API in the background from the same terminal:

```bash
uv run --project backend-next --locked --python 3.14 \
  uvicorn pkdb.app:create_app --factory --host 127.0.0.1 --port 18083 \
  > "$PKDB_UPLOAD_WORK/api.log" 2>&1 &
export PKDB_UPLOAD_API_PID=$!

curl --retry 20 --retry-connrefused --retry-delay 1 --fail \
  "$PKDB_UPLOAD_URL/health/ready"
```

Readiness must return HTTP 200. Open
[http://127.0.0.1:18083/docs](http://127.0.0.1:18083/docs) to inspect the API.
If readiness fails, check `tail -n 40 "$PKDB_UPLOAD_WORK/api.log"`.

Log in and place the token in the environment. The password prompt is hidden;
the token is captured without printing it:

```bash
export PKDB_API_TOKEN="$(uv run --project backend-next --locked --python 3.14 python - <<'PY'
import getpass
import os
import sys

import httpx

response = httpx.post(
    os.environ["PKDB_UPLOAD_URL"] + "/api-token-auth/",
    json={
        "username": os.environ["PKDB_UPLOAD_USER"],
        "password": getpass.getpass("Local operator password: "),
    },
    timeout=30,
)
if response.status_code != 200:
    print(f"Login failed: HTTP {response.status_code}", file=sys.stderr)
    raise SystemExit(1)
print(response.json()["token"])
PY
)"
test -n "$PKDB_API_TOKEN"
```

Do not continue if login fails. Both remote CLI commands use `PKDB_API_TOKEN` and
an explicit `--api-url`; database settings are only needed by the server and local
administration commands.

## Validate, upload and inspect the study

First validate without publishing:

```bash
uv run --project backend-next --locked --python 3.14 \
  pkdb validate "$PKDB_UPLOAD_STUDY" --api-url "$PKDB_UPLOAD_URL"
```

Expect a JSON line containing `"ok": true` and `"status": 200`. Then upload:

```bash
uv run --project backend-next --locked --python 3.14 \
  pkdb upload "$PKDB_UPLOAD_STUDY" --api-url "$PKDB_UPLOAD_URL"
```

A first publication returns `"ok": true`, `"status": 201`, the study `sid` and its
`digest`. The command exits with status 0 only when every selected study succeeds.
A successful upload is already queryable; there is no indexing command to run.

Read the published canonical study using the same token:

```bash
uv run --project backend-next --locked --python 3.14 python - <<'PY'
import json
import os
from pathlib import Path
from urllib.parse import quote

import httpx

source = json.loads((Path(os.environ["PKDB_UPLOAD_STUDY"]) / "study.json").read_text())
sid = str(source["sid"])
response = httpx.get(
    os.environ["PKDB_UPLOAD_URL"] + "/api/v2/studies/" + quote(sid, safe=""),
    headers={"Authorization": "Token " + os.environ["PKDB_API_TOKEN"]},
    timeout=30,
)
response.raise_for_status()
study = response.json()
assert study["sid"] == sid
print(json.dumps({
    "sid": study["sid"],
    **{key: len(study[key]) for key in ("groups", "individuals", "measurements", "timecourses")},
}, indent=2))
PY
```

For the unchanged Frost2014 fixture used in the migration, expect 1 group,
70 individuals, 782 measurements and 8 reported/normalized timecourses.
A different source revision can have different counts.

Run the same `pkdb upload` command again. Expect HTTP 200 and the same counts,
with no duplicate studies or measurements. Replacement is atomic: it replaces all
study-owned data, and an invalid replacement leaves the last valid publication
intact. To exercise an error, edit only the copied study, validate it again, and
inspect the returned `issues`.

To test another study, select and copy its folder, then repeat the identity
bootstrap before validation/upload. You can also pass a directory of studies to
`pkdb upload`; it discovers `study.json` recursively and prints one outcome per
study. Start with one known-good study so setup errors are easy to distinguish
from corpus validation failures.

## Troubleshooting

| Result | What to check |
| --- | --- |
| `pkdb: command not found` or missing `backend-next` | Use the migration checkout and the `uv run --project backend-next ...` command above. |
| Connection refused | Start PostgreSQL/API and verify the chosen ports and readiness endpoint. |
| HTTP 401 | Repeat login; verify `PKDB_API_TOKEN` in the terminal running the upload. |
| HTTP 403 | Use the local administrator; disabled source identities cannot log in or upload. |
| `unknown_user` | Rebuild the local identity bootstrap for the selected study, including comment authors, then run `pkdb bootstrap` again. |
| HTTP 422 or `"ok": false` with `issues` | Inspect the issue code and source location. Check missing attachments, vocabulary terms and scientific values. Validation can succeed before upload detects an unknown user during publication. |
| HTTP 413 | The default total request limit is 256 MiB. If appropriate for your machine, set `PKDB_UPLOAD_MAX_BYTES` before restarting the API. |
| Timeout / unknown publication outcome | Check the study with the read command, then retry the complete upload. The CLI does not automatically retry. |
| `Local administration failed` | Check database settings, migrations, bootstrap files and whether the operator already exists. |

The full corpus still has known validation and duplicate-identity blockers. Do not
weaken validation or edit the original corpus to turn a test green. Successful
local upload testing is one migration gate; full compatibility, corpus accounting
and acceptance review are still required before removing the legacy backend.

## Stop and resume

Stop the API and PostgreSQL when you finish:

```bash
kill "$PKDB_UPLOAD_API_PID"
docker stop pkdb-upload-local
unset PKDB_API_TOKEN
```

The PostgreSQL named volume and attachment directory remain. To resume, restore
the same workspace/database/file-root variables, run `docker start
pkdb-upload-local`, start the API and log in again. Keep the database and attachment
directory together; the database alone cannot restore uploaded files.

## Preview this guide in Zensical

From the migration checkout root:

```bash
uvx --python 3.14 --with-requirements docs/requirements.txt \
  zensical serve --dev-addr 127.0.0.1:18084
```

Open [http://127.0.0.1:18084/local-upload-testing/](http://127.0.0.1:18084/local-upload-testing/).
