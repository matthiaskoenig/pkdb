"""Verified external identities and expiring browser-bound OAuth transactions."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Identity, Timestamped


class ExternalIdentity(Identity, Timestamped, Base):
    __tablename__ = "external_identities"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(16))
    issuer: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        UniqueConstraint("provider", "issuer", "subject"),
        UniqueConstraint("user_id", "provider"),
    )


class OAuthTransaction(Identity, Timestamped, Base):
    __tablename__ = "oauth_transactions"
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    browser_digest: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(16))
    intent: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("browser_sessions.id", ondelete="CASCADE")
    )
    code_verifier: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    identity: Mapped[dict | None] = mapped_column(JSONB)
    onboarding_digest: Mapped[str | None] = mapped_column(String(64), unique=True)
