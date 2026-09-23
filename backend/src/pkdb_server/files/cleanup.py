"""Collect expired, unreferenced metadata while holding publication's row lock."""

from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, sessionmaker

from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.files.store import FileStore


def cleanup_expired_files(
    now: datetime, session_factory: sessionmaker[Session], file_store: FileStore
) -> int:
    removed = 0
    with session_factory.begin() as session:
        candidates = session.scalars(
            select(StoredFile)
            .where(
                StoredFile.expires_at < now,
                (StoredFile.lease_until.is_(None)) | (StoredFile.lease_until < now),
            )
            .with_for_update(skip_locked=True)
        )
        for row in candidates:
            if session.scalar(
                select(exists().where(StudyAttachment.file_id == row.id))
            ):
                continue
            file_store.path(row.storage_key).unlink(missing_ok=True)
            file_store.path(row.storage_key + ".partial").unlink(missing_ok=True)
            session.delete(row)
            removed += 1
    return removed


def cleanup_untracked_files(
    now: datetime, session_factory: sessionmaker[Session], file_store: FileStore
) -> int:
    """Only crash leftovers older than 24 hours qualify; staging registers first."""
    import re
    from datetime import timedelta

    removed = 0
    cutoff = (now - timedelta(hours=24)).timestamp()
    with session_factory() as session:
        for path in file_store.root.iterdir():
            if (
                not re.fullmatch(r"[0-9a-f]{32}(?:\.partial)?", path.name)
                or path.is_symlink()
            ):
                continue
            try:
                if path.stat().st_mtime >= cutoff:
                    continue
                key = path.name.removesuffix(".partial")
                if session.scalar(
                    select(exists().where(StoredFile.storage_key == key))
                ):
                    continue
                path.unlink()
                removed += 1
            except FileNotFoundError:
                continue
    return removed
