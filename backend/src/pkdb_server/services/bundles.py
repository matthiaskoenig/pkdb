"""Resolve owned handles into a bounded temporary source bundle."""

import hashlib
import os
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from pkdb.schemas.source import SourceBundle
from pkdb.schemas.validation import fail
from sqlalchemy import select

from pkdb_server.db.models.files import StoredFile
from pkdb_server.db.models.users import User
from pkdb_server.services.authorization import AuthorizationDenied


@contextmanager
def materialize_bundle(bundle, principal, file_store, settings):
    if len(bundle.handles) > settings.upload_max_files or len(
        set(bundle.handles)
    ) != len(bundle.handles):
        fail("invalid_handles", "Too many or duplicate attachment handles")
    with TemporaryDirectory(prefix="pkdb-mcp-") as directory:
        files = {}
        total = 0
        for handle in bundle.handles:
            with ExitStack() as opened:
                # A shared row lock protects opening against cleanup. Once open,
                # immutable bytes remain readable even if cleanup later unlinks them.
                with file_store.session_factory.begin() as session:
                    user = session.get(User, principal.user_id)
                    row = session.scalar(
                        select(StoredFile)
                        .where(StoredFile.id == handle)
                        .with_for_update(read=True)
                    )
                    if (
                        user is None
                        or not user.active
                        or row is None
                        or row.owner_id != principal.user_id
                        or not row.ready
                        or row.expires_at <= datetime.now(UTC)
                    ):
                        raise AuthorizationDenied("Attachment handle unavailable")
                    if row.original_name in files:
                        fail(
                            "duplicate_file",
                            "Attachment handles must have unique filenames",
                        )
                    name, expected_size, expected_digest = (
                        row.original_name,
                        row.size,
                        row.digest,
                    )
                    total += expected_size
                    if total > settings.upload_max_bytes:
                        fail("file_limit", "Attachments exceed configured byte limit")
                    source = opened.enter_context(
                        os.fdopen(
                            os.open(
                                file_store.path(row.storage_key),
                                os.O_RDONLY | os.O_NOFOLLOW,
                            ),
                            "rb",
                        )
                    )
                target = Path(directory) / name
                digest = hashlib.sha256()
                with target.open("wb") as output:
                    remaining = expected_size
                    while chunk := source.read(min(1024 * 1024, remaining + 1)):
                        remaining -= len(chunk)
                        if remaining < 0:
                            fail("source_changed", "Stored attachment size changed")
                        output.write(chunk)
                        digest.update(chunk)
                    if remaining or digest.hexdigest() != expected_digest:
                        fail(
                            "source_changed", "Stored attachment integrity check failed"
                        )
                files[name] = target
        yield SourceBundle(study=bundle.study, reference=bundle.reference, files=files)
