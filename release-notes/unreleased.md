# Unreleased

- Restore the authoritative `pkdb_data` vocabulary definitions and cached metadata. Regenerate backend JSON with `uv run --project backend --python 3.14 python scripts/update_vocabulary.py`; CI checks for stale outputs.

- Remove the previous Django backend, Elasticsearch setup, old uploader, nginx deployment configuration, and obsolete administration scripts.
- Move the current FastAPI backend to `backend/`. Start the backend and PostgreSQL with `docker compose up --build --wait`; migrations and vocabulary load automatically.
- Add `pkdb bootstrap-study` to prepare disabled attribution accounts for local uploads.
- Document Docker-based validation and upload testing in Zensical.
- Require Python 3.14 and drop Python 3.13 support and testing. Run the current backend CI on Python 3.14, including container lifecycle, database/attachment restore, and Compose startup checks.

Existing deployment data is not migrated or deleted by this source cleanup. Historical corpus validation and client compatibility acceptance gaps remain open.
