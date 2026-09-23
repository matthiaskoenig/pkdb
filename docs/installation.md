# Installation

The backend runs with Docker Engine and the Docker Compose plugin. No host Python, PostgreSQL, or external search service is required.

```bash
git clone https://github.com/matthiaskoenig/pkdb.git
cd pkdb
docker compose up --build --wait
```

The first build downloads dependencies. Startup applies database migrations and loads the bundled vocabulary. Open <http://localhost:18083/docs> for the API interface, or <http://localhost:18083/health/ready> to check readiness.

The two services are the FastAPI backend and PostgreSQL 18. The API binds only to localhost. The frontend is maintained separately and is not part of this setup.

## Create an administrator

```bash
docker compose exec backend pkdb create-admin mkoenig --email YOUR_EMAIL
```

The sole administrator username is `mkoenig`. Enter a password at the hidden prompt. Sign in to the account frontend with that password and create a personal API key. No external provider or MFA setup is needed. For an ordinary local login, use `pkdb create-user developer`; see [Local development accounts](authentication.md#local-development-accounts). Follow [Local upload testing](local-upload-testing.md) to configure the frontend proxy port, authenticate, validate, and upload a study. The former `/api-token-auth/` endpoint is retired.

## Configuration and persistence

Defaults work without an environment file. To change the HTTP port, Python version, or local database password, copy `.env.example` to `.env` before first startup. The database password must be URL-safe because it is included in a connection URL. Changing it after database initialization does not change the stored database password.

The Compose project is named `pkdb-current`. Separate named volumes hold PostgreSQL data and attachments. Older deployment volumes are not reused or migrated.

```bash
docker compose stop
docker compose up --wait
```

These commands preserve data. `docker compose down` also preserves named volumes; adding `--volumes` deletes them. Inspect startup failures with `docker compose logs --tail=100 backend db`.
