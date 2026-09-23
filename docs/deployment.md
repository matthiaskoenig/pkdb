# Deployment

!!! important "For developers and operators only"

    This section is for working on PK-DB itself or running a separate server. General users do not need a source checkout, Docker, a database, or administrator access. To use PK-DB, start with [Browse and access data](web-interface.md) or the [Python client and API](python-client.md).

The root `compose.yaml` is a local setup with an optional `dev` profile for the frontend. It runs the API and PostgreSQL, applies Alembic migrations, and loads the bundled vocabulary. See [Installation](installation.md) for startup and [Local upload testing](local-upload-testing.md) for the upload workflow.

## Deployment requirements

For an externally accessible deployment, provide a TLS reverse proxy, managed secrets, a durable PostgreSQL database, persistent attachment storage, and an appropriate backup policy. Configure the backend with `PKDB_DATABASE_URL`, `PKDB_FILE_ROOT`, and explicit `PKDB_CORS_ORIGINS` when using a separately hosted frontend. Additional settings are listed in `backend/src/pkdb_server/config.py`. The local default database password is only for local testing. The repository does not install a production reverse proxy.

The container runs as UID 10001. A custom attachment mount must be writable by that user. Do not expose PostgreSQL publicly. Apply migrations once before starting API workers; the Compose startup command handles this for the single local API service.

## Backup and restore

PostgreSQL records and attachment files form one dataset. Quiesce writes, back up both together, and retain the application version and configuration needed to restore. The local Compose volumes are `database` and `attachments`, prefixed by the project name. Never point a new deployment at historical volumes without an explicit migration.

Test restoration into an isolated database and attachment volume before relying on a backup. The backend system tests exercise database and attachment restoration together. A database dump alone does not preserve attachments.

## Migration status

The current backend is the only backend shipped in this repository. Removing the previous implementation is not a production data migration or a claim that every historical client or source study passes acceptance. Historical validation and compatibility evidence remains in [the migration records](backend-migration/README.md).

## Frontend static artifact

The modern frontend uses Node 24.21.0 and npm 12.1.0 with a committed lockfile. `frontend/Dockerfile-production` runs `npm ci`, type checks, and builds `dist/`, then copies the static artifact to `/vue`. This image remains an artifact carrier; the existing deployment supplies its HTTP server. No frontend service is added to the default backend Compose stack.

Use `frontend/tests/deployment/nginx.conf` as the concrete reverse-proxy example and `compose.frontend-test.yaml` to exercise it against isolated test data. Proxy `/api`, `/accounts`, `/media`, `/static` and `/health` before history fallback. Missing JS/CSS assets must return 404, API failures must remain API responses, and `index.html` must be revalidated while fingerprinted assets may be cached immutably. Match `PKDB_BROWSER_ORIGIN` to the external origin and preserve same-origin cookies/CSRF. `VITE_API_BASE` is public API-origin build configuration, normally empty for same-origin requests, never a place for secrets.

Before release, verify these rules in the real deployment proxy and retain the previous deployed artifact in durable storage. Rollback restores that static artifact atomically; this frontend migration introduces no database migration. Local recovered baseline checksums are in `frontend/docs/modernization-baseline.md`; local `/tmp` copies do not replace production rollback retention.

## Deployment configuration

Serve the frontend and backend behind one HTTPS origin. Forward `/api/` and `/accounts/` to FastAPI, together with any enabled MCP route. Keep the frontend API base relative (`VITE_API_BASE=""`). A browser origin includes the scheme, hostname and optional port, with no path.

| Environment variable | Production setting or behavior |
| --- | --- |
| `PKDB_DATABASE_URL` | PostgreSQL connection URL |
| `PKDB_FILE_ROOT` | Persistent managed file directory; includes avatars |
| `PKDB_BROWSER_ORIGIN` | Exact public origin, such as `https://pk-db.example.org` |
| `PKDB_SECURE_COOKIES` | `true` for HTTPS production |
| `PKDB_SMTP_HOST`, `PKDB_SMTP_SENDER` | Required to send verification, recovery and invitation mail |
| `PKDB_SMTP_PORT` | Defaults to `587` |
| `PKDB_SMTP_USERNAME`, `PKDB_SMTP_PASSWORD` | Optional SMTP authentication; provide both when required |
| `PKDB_SMTP_STARTTLS` | Defaults to `true`; SMTP transport uses STARTTLS, not implicit TLS |
| `PKDB_CORS_ORIGINS` | Explicit JSON array when needed; same-origin deployment normally needs none |

Production cookies are Secure, HttpOnly and SameSite=Lax, with `__Host-` names. Insecure cookies are restricted to local development hosts. Browser mutations require the expected Origin and a CSRF token obtained from `GET /api/v1/auth/csrf`; the frontend handles this automatically. An invalid explicit Authorization header does not fall back to a browser cookie.

SMTP is needed for public registration verification, password recovery, and invitations. Existing active accounts with a password can sign in without SMTP. Local development accounts can be provisioned directly with the operator command below. Invitation recipients enter their one-use token at `/invitation` and choose a password.

Back up PostgreSQL and managed file storage together. Do not log Authorization headers, one-use tokens, passwords, or request bodies from authentication routes.
