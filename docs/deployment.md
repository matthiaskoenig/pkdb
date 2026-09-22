# Deployment

The root `compose.yaml` is a local backend setup. It runs the API and PostgreSQL, applies Alembic migrations, and loads the bundled vocabulary. See [Installation](installation.md) for startup and [Local upload testing](local-upload-testing.md) for the upload workflow.

## Deployment requirements

For an externally accessible deployment, provide a TLS reverse proxy, managed secrets, a durable PostgreSQL database, persistent attachment storage, and an appropriate backup policy. Configure the backend with `PKDB_DATABASE_URL`, `PKDB_FILE_ROOT`, and explicit `PKDB_CORS_ORIGINS` when using a separately hosted frontend. Additional settings are listed in `backend/src/pkdb/config.py`. The local default database password is only for local testing. The repository does not install a production reverse proxy.

The container runs as UID 10001. A custom attachment mount must be writable by that user. Do not expose PostgreSQL publicly. Apply migrations once before starting API workers; the Compose startup command handles this for the single local API service.

## Backup and restore

PostgreSQL records and attachment files form one dataset. Quiesce writes, back up both together, and retain the application version and configuration needed to restore. The local Compose volumes are `database` and `attachments`, prefixed by the project name. Never point a new deployment at historical volumes without an explicit migration.

Test restoration into an isolated database and attachment volume before relying on a backup. The backend system tests exercise database and attachment restoration together. A database dump alone does not preserve attachments.

## Migration status

The current backend is the only backend shipped in this repository. Removing the previous implementation is not a production data migration or a claim that every historical client or source study passes acceptance. Historical validation and compatibility evidence remains in [the migration records](backend-migration/README.md).
