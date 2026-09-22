"""Encrypted administrator MFA and append-only security events."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Identity, Timestamped


class MfaCredential(Base):
    __tablename__ = "mfa_credentials"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_secret: Mapped[str]
    confirmed: Mapped[bool] = mapped_column(default=False)
    last_step: Mapped[int] = mapped_column(default=-1)
    recovery_digests: Mapped[list[str]] = mapped_column(JSONB, default=list)


class AuditEvent(Identity, Timestamped, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(200))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)


class RoleRequest(Identity, Timestamped, Base):
    __tablename__ = "role_requests"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        Index(
            "uq_role_requests_pending",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )
