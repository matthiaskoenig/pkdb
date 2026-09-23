from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from pkdb_server.db.models.base import Base, Timestamped


class StoredFile(Timestamped, Base):
    __tablename__ = "files"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    digest: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(unique=True)
    size: Mapped[int] = mapped_column(BigInteger)
    original_name: Mapped[str]
    ready: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("size >= 0", name="size"),)


class StudyAttachment(Base):
    __tablename__ = "study_attachments"
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id"), primary_key=True)
    name: Mapped[str]
    __table_args__ = (UniqueConstraint("study_id", "name"),)
