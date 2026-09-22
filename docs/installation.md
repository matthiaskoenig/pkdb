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
docker compose exec backend pkdb create-admin tester --email tester@example.org
```

Enter a password at the hidden prompt. Then follow [Local upload testing](local-upload-testing.md) to authenticate, validate, and upload a study.

## Configuration and persistence

Defaults work without an environment file. To change the HTTP port, Python version, or local database password, copy `.env.example` to `.env` before first startup. The database password must be URL-safe because it is included in a connection URL. Changing it after database initialization does not change the stored database password.

The Compose project is named `pkdb-current`. Separate named volumes hold PostgreSQL data and attachments. Older deployment volumes are not reused or migrated.

```bash
docker compose stop
docker compose up --wait
```

These commands preserve data. `docker compose down` also preserves named volumes; adding `--volumes` deletes them. Inspect startup failures with `docker compose logs --tail=100 backend db`.
