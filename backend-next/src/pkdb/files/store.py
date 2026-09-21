"""Durable, owner-scoped immutable bytes; original names never become paths."""

import hashlib
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from pkdb.db.models.files import StoredFile, StudyAttachment
from pkdb.db.models.studies import Study, StudyUser
from pkdb.db.models.users import User
from pkdb.schemas.security import Principal, StudyAccess
from pkdb.services.authorization import AuthorizationDenied, authorize


class FileTooLarge(ValueError):
    pass


class StagedFile(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)
    id: UUID
    owner_id: int
    digest: str
    storage_key: str
    size: int
    original_name: str
    expires_at: datetime


def study_access(study: Study, session: Session) -> StudyAccess:
    members = list(
        session.scalars(select(StudyUser).where(StudyUser.study_id == study.id))
    )
    if study.creator_id is None:
        raise AuthorizationDenied("Study ownership is not configured")
    return StudyAccess.model_validate(
        {
            "sid": study.sid,
            "access": study.access,
            "licence": study.licence,
            "creator_id": study.creator_id,
            "curator_ids": frozenset(m.user_id for m in members if m.role == "curator"),
            "collaborator_ids": frozenset(
                m.user_id for m in members if m.role == "collaborator"
            ),
        }
    )


class FileStore:
    def __init__(
        self, root: Path, session_factory: sessionmaker[Session], max_bytes: int
    ):
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        if root.is_symlink():
            raise ValueError("File root cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve()
        self.session_factory = session_factory
        self.max_bytes = max_bytes

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}(?:\.partial)?", key):
            raise ValueError("Invalid storage key")
        path = self.root / key
        if path.is_symlink():
            raise ValueError("Storage paths cannot be symlinks")
        return path

    def stage(
        self, owner: Principal, original_name: str, source: BinaryIO
    ) -> StagedFile:
        if (
            not original_name
            or original_name in {".", ".."}
            or any(c in original_name for c in "/\\\0")
        ):
            raise ValueError("Invalid original filename")
        if owner.user_id is None:
            raise AuthorizationDenied("File staging requires authentication")
        now = datetime.now(UTC)
        file_id = uuid4()
        key = file_id.hex
        with self.session_factory.begin() as session:
            user = session.get(User, owner.user_id)
            if user is None or not user.active:
                raise AuthorizationDenied("Inactive file owner")
            session.add(
                StoredFile(
                    id=file_id,
                    owner_id=user.id,
                    storage_key=key,
                    digest="",
                    size=0,
                    original_name=original_name,
                    ready=False,
                    expires_at=now + timedelta(hours=24),
                    lease_until=now + timedelta(hours=1),
                )
            )
        temporary = self.path(key + ".partial")
        final = self.path(key)
        digest = hashlib.sha256()
        size = 0
        try:
            fd = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(fd, "wb") as destination:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise FileTooLarge("Attachment exceeds configured byte limit")
                    digest.update(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            with self.session_factory.begin() as session:
                row = session.scalar(
                    select(StoredFile).where(StoredFile.id == file_id).with_for_update()
                )
                if row is None:
                    raise ValueError("File staging lease expired")
                os.replace(temporary, final)
                directory_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                row.digest = digest.hexdigest()
                row.size = size
                row.ready = True
                row.lease_until = None
                session.flush()
                result = StagedFile.model_validate(row)
            return result
        except BaseException:
            temporary.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
            with self.session_factory.begin() as session:
                row = session.get(StoredFile, file_id)
                if row is not None:
                    session.delete(row)
            raise

    def verify(self, staged: StagedFile) -> None:
        digest = hashlib.sha256()
        size = 0
        fd = os.open(self.path(staged.storage_key), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as source:
            while chunk := source.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        if size != staged.size or digest.hexdigest() != staged.digest:
            raise ValueError("Attachment integrity check failed")

    def open_authorized(self, principal: Principal, attachment_id: UUID) -> BinaryIO:
        with self.session_factory.begin() as session:
            row = session.scalar(
                select(StoredFile)
                .where(StoredFile.id == attachment_id)
                .with_for_update(read=True)
            )
            if row is None or not row.ready:
                raise FileNotFoundError("Attachment unavailable")
            studies = list(
                session.scalars(
                    select(Study)
                    .join(StudyAttachment)
                    .where(StudyAttachment.file_id == row.id)
                )
            )
            allowed = False
            for study in studies:
                try:
                    authorize(principal, "read_file", study_access(study, session))
                    allowed = True
                    break
                except AuthorizationDenied:
                    pass
            if not studies and principal.user_id == row.owner_id:
                user = session.get(User, principal.user_id)
                allowed = user is not None and user.active
            if not allowed:
                raise AuthorizationDenied("Attachment access denied")
            fd = os.open(self.path(row.storage_key), os.O_RDONLY | os.O_NOFOLLOW)
            return os.fdopen(fd, "rb")
