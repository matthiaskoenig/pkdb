import io
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pkdb.db.models.files import StoredFile
from pkdb.db.models.users import User
from pkdb.files.cleanup import cleanup_expired_files
from pkdb.files.store import FileStore, FileTooLarge
from pkdb.schemas.security import Principal
from pkdb.services.authorization import AuthorizationDenied


@pytest.fixture
def owner(session_factory):
    with session_factory.begin() as session:
        user = User(username=uuid4().hex, active=True, role="curator")
        session.add(user)
        session.flush()
        return Principal(user_id=user.id, username=user.username, role=user.role)


@pytest.fixture
def file_store(tmp_path, session_factory):
    return FileStore(tmp_path, session_factory, max_bytes=1024)


def test_staged_file_is_owner_only(file_store, owner):
    staged = file_store.stage(owner, "paper.pdf", io.BytesIO(b"%PDF-test"))
    with pytest.raises(AuthorizationDenied):
        file_store.open_authorized(Principal(), staged.id)
    with file_store.open_authorized(owner, staged.id) as handle:
        assert handle.read() == b"%PDF-test"


@pytest.mark.parametrize("name", ["../paper", "/etc/passwd", "a/b", "a\\b", ".", ".."])
def test_traversal_names_are_rejected(file_store, owner, name):
    with pytest.raises(ValueError):
        file_store.stage(owner, name, io.BytesIO(b"test"))


def test_oversized_stream_leaves_no_bytes(file_store, owner):
    with pytest.raises(FileTooLarge):
        file_store.stage(owner, "large", io.BytesIO(b"x" * 1025))
    assert not list(file_store.root.iterdir())


def test_cleanup_reclaims_only_expired_unleased_files(
    file_store, owner, session_factory
):
    old = file_store.stage(owner, "old", io.BytesIO(b"old"))
    live = file_store.stage(owner, "live", io.BytesIO(b"live"))
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        row = session.get(StoredFile, old.id)
        row.expires_at = now - timedelta(seconds=1)
        row.lease_until = None
        row = session.get(StoredFile, live.id)
        row.expires_at = now - timedelta(seconds=1)
        row.lease_until = now + timedelta(hours=1)
    assert cleanup_expired_files(now, session_factory, file_store) == 1
    with file_store.open_authorized(owner, live.id) as handle:
        assert handle.read() == b"live"


def test_corrupt_file_is_rejected(file_store, owner):
    staged = file_store.stage(owner, "paper", io.BytesIO(b"original"))
    (file_store.root / staged.storage_key).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        file_store.verify(staged)


def test_duplicate_names_have_distinct_storage(file_store, owner):
    one = file_store.stage(owner, "paper", io.BytesIO(b"one"))
    two = file_store.stage(owner, "paper", io.BytesIO(b"two"))
    assert one.storage_key != two.storage_key


def test_symlink_bytes_are_never_opened(file_store, owner, tmp_path):
    staged = file_store.stage(owner, "paper", io.BytesIO(b"original"))
    outside = tmp_path.parent / f"outside-{uuid4().hex}"
    outside.write_bytes(b"private")
    try:
        path = file_store.root / staged.storage_key
        path.unlink()
        path.symlink_to(outside)
        with pytest.raises(ValueError, match="symlink"):
            file_store.open_authorized(owner, staged.id)
    finally:
        outside.unlink()


def test_published_file_survives_expiry_cleanup(file_store, owner, session_factory):
    from pkdb.db.models.files import StudyAttachment
    from pkdb.db.models.studies import Study

    staged = file_store.stage(owner, "paper", io.BytesIO(b"published"))
    now = datetime.now(UTC)
    with session_factory.begin() as session:
        study = Study(
            sid=uuid4().hex,
            name="public",
            access="public",
            licence="open",
            creator_id=owner.user_id,
        )
        session.add(study)
        session.flush()
        session.add(StudyAttachment(study_id=study.id, file_id=staged.id, name="paper"))
        session.get(StoredFile, staged.id).expires_at = now - timedelta(seconds=1)
    cleanup_expired_files(now, session_factory, file_store)
    with pytest.raises(AuthorizationDenied, match="Authentication required"):
        file_store.open_authorized(Principal(), staged.id)
    with file_store.open_authorized(owner, staged.id) as handle:
        assert handle.read() == b"published"


def test_untracked_files_have_a_grace_period(file_store, session_factory):
    import os

    from pkdb.files.cleanup import cleanup_untracked_files

    old = file_store.root / uuid4().hex
    fresh = file_store.root / uuid4().hex
    old.write_bytes(b"orphan")
    fresh.write_bytes(b"writing")
    now = datetime.now(UTC)
    old_time = (now - timedelta(hours=25)).timestamp()
    os.utime(old, (old_time, old_time))
    assert cleanup_untracked_files(now, session_factory, file_store) == 1
    assert fresh.exists()
