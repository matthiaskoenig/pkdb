# Backend replacement rehearsal

The replacement runs from `backend-next/` until all acceptance gates pass.
The full source corpus currently contains unresolved invalid studies and duplicate
SIDs. A successful subset upload is not authorization to retire the legacy system.

## Prepare an isolated environment

Use Python 3.13 or 3.14, PostgreSQL 18 and an empty attachment directory. Configure
`PKDB_DATABASE_URL` and `PKDB_FILE_ROOT`; install with
`uv sync --project backend-next --locked --python 3.14`. Apply Alembic from
`backend-next/` with `uv run --locked alembic upgrade head` and verify
`uv run --locked alembic check`.

Prepare a reviewed offline bootstrap directory containing `vocabulary.json` and
`users.json`. The checked-in vocabulary snapshot is in `backend-next/bootstrap/`.
User entries contain username, optional email and role; imported identities start
disabled, without passwords. Bootstrap never changes existing credentials or roles.
Run `uv run --project backend-next --locked pkdb bootstrap DIRECTORY`.
Provision a new administrator locally with
`uv run --project backend-next --locked pkdb create-admin OPERATOR --email EMAIL`.
The password is read without echo from the terminal; automation can use
`--password-stdin` with protected standard input. The command hashes the password,
creates a verified email and refuses to alter an existing username or email.
Use an operator identity distinct from disabled imported study identities.
Obtain an API token through normal authentication before the remote rebuild.

Start `uv run --project backend-next --locked uvicorn pkdb.app:create_app --factory`.
`/health/live` checks process availability; `/health/ready` checks the exact schema
revision and writable attachment storage. MCP is mounted at `/mcp/` and uses the
same application lifecycle and database-backed bearer authentication.

## Account for every source folder

Set `PKDB_API_TOKEN` through protected environment configuration. From the repository
root, run:

```bash
uv run --project backend-next --locked python tools/backend_migration/rebuild.py \
  --corpus ../pkdb_data/studies \
  --api-url http://127.0.0.1:8000 \
  --report /tmp/pkdb-rebuild-report.json
```

Keep the report outside the source corpus. The command inventories every folder,
hashes its files, blocks every occurrence of a duplicate SID and records malformed
identities. Valid candidates use one atomic complete-study PUT. No source files are
rewritten and no DELETE is issued. The report is atomically checkpointed before
network work and after every outcome; interruption leaves unattempted entries
`pending`. Exit status is nonzero unless every discovered folder is `published`.

Running the same command resumes by comparing the source fingerprint and live
publication metadata. A study is skipped only when its source digest, processing
version and vocabulary digest still match, and both versions remain current on
the server. A changed or missing publication is uploaded again. A digest change
between upload and verification is a failed verification, not a successful rebuild.
Use `--no-resume` to explicitly reattempt all unambiguous source folders.

Inspect every `blocked` and `failed` entry. Preserve invalid input and its diagnostic;
do not edit sources or weaken validation to turn the report green. Reviewed source
corrections or explicit release-corpus dispositions are required before cutover.
Folder paths are the accounting identity because malformed and duplicate SIDs
cannot uniquely identify every source folder.

## Back up and restore together

A recoverable backup needs both PostgreSQL and the immutable attachment volume.
Quiesce writes while taking the database dump and attachment copy so they describe
the same publication state. Restore into a separate empty database/file directory,
apply the matching application revision, then check readiness, scientific reads,
protected attachment access and a new atomic upload. Keep the original backup and
legacy deployment until restore and cutover acceptance are signed off.

Both Python container variants pass local non-root REST/MCP, analytical PK,
protected attachment and graceful shutdown gates. The full database and file
restore rehearsal is recorded in `restore-checkpoint.json`; repeat against the final accepted release corpus.
Production deployment, data deletion and retiring the legacy runtime are separate
operations and are not performed by this runbook's rebuild command.

## Maintenance

`pkdb cleanup` uses the configured local database and attachment directory. It
removes expired saved filters/drafts and eligible expired/untracked staged files;
published attachments and active leases remain protected. Schedule this through
the host's ordinary job scheduler; no application queue or Redis service is needed.
