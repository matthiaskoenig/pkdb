"""Operator-controlled security state and idempotent account migration records."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Identity, Timestamped


class SecurityConfiguration(Base):
    __tablename__ = "security_configuration"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    designated_administrator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id")
    )
    legacy_token_cutoff: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)


class UserImportRun(Identity, Timestamped, Base):
    __tablename__ = "user_import_runs"
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    provenance: Mapped[dict] = mapped_column(JSONB)
    report: Mapped[dict] = mapped_column(JSONB)
