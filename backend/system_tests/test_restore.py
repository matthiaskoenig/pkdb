"""Restore a real PostgreSQL dump and immutable files into an isolated database."""

import os
import shutil
import subprocess
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pkdb.schemas.security import Principal
from sqlalchemy import create_engine, select, text

from pkdb_server.app import create_app
from pkdb_server.config import Settings
from pkdb_server.db.models.files import StoredFile
from pkdb_server.db.read import read_study
from pkdb_server.db.session import make_session_factory
from pkdb_server.files.store import FileStore
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.ingestion import IngestionService


def test_database_and_attachment_restore_preserves_science_and_permissions(
    ingestion_context, session_factory, valid_bundle, tmp_path
):
    container = os.environ["PKDB_TEST_POSTGRES_CONTAINER"]
    ingestion, actor = ingestion_context
    attachment = tmp_path / "notes.txt"
    attachment.write_bytes(b"preserved restore attachment")
    valid_bundle.files["notes.txt"] = attachment
    published = ingestion.replace(valid_bundle, actor)
    original = read_study(published.sid, actor, session_factory)
    url = session_factory.kw["bind"].url
    with session_factory() as session:
        schema = session.scalar(text("SELECT current_schema()"))
        file_id = session.scalar(select(StoredFile.id))
    environment = {**os.environ, "PGUSER": url.username, "PGPASSWORD": url.password}
    execute = ["docker", "exec", "--env", "PGUSER", "--env", "PGPASSWORD", container]
    dump = tmp_path / "backup.dump"
    with dump.open("wb") as handle:
        subprocess.run(
            [
                *execute,
                "pg_dump",
                "--host=127.0.0.1",
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--dbname=" + url.database,
                "--schema=" + schema,
            ],
            env=environment,
            stdout=handle,
            stderr=subprocess.PIPE,
            check=True,
        )
    restored_files = tmp_path / "restored-files"
    shutil.copytree(ingestion.file_store.root, restored_files)
    database = "restore_" + uuid4().hex
    admin = create_engine(url.set(query={}), isolation_level="AUTOCOMMIT")
    restored = None
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
            created = True
        with dump.open("rb") as handle:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "--interactive",
                    "--env",
                    "PGUSER",
                    "--env",
                    "PGPASSWORD",
                    container,
                    "pg_restore",
                    "--host=127.0.0.1",
                    "--exit-on-error",
                    "--no-owner",
                    "--no-privileges",
                    "--dbname=" + database,
                ],
                env=environment,
                stdin=handle,
                capture_output=True,
                check=True,
            )
        restored_url = url.set(database=database).render_as_string(hide_password=False)
        restored = make_session_factory(restored_url)
        assert read_study(published.sid, actor, restored) == original
        store = FileStore(restored_files, restored, 1024 * 1024)
        with store.open_authorized(actor, file_id) as handle:
            assert handle.read() == attachment.read_bytes()
        with pytest.raises(AuthorizationDenied):
            store.open_authorized(Principal(), file_id)
        settings = Settings(database_url=restored_url, file_root=restored_files)
        with TestClient(create_app(settings)) as client:
            assert client.get("/health/ready").status_code == 200
        result = IngestionService(restored, store, settings).replace(
            valid_bundle, actor
        )
        assert not result.created
        assert read_study(published.sid, actor, restored) == original
    finally:
        if restored is not None:
            restored.kw["bind"].dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{database}" WITH (FORCE)'))
        admin.dispose()
