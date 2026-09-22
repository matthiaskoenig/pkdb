from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Identity, Timestamped


class User(Identity, Timestamped, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(150), unique=True)
    email: Mapped[str | None] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(16), default="curator")
    active: Mapped[bool] = mapped_column(default=False)
    first_name: Mapped[str] = mapped_column(default="", server_default="")
    last_name: Mapped[str] = mapped_column(default="", server_default="")
    pending_verification: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    password_hash: Mapped[str | None]
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'curator', 'reviewer', 'user')", name="role"
        ),
    )


class Token(Identity, Timestamped, Base):
    __tablename__ = "tokens"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    email_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_addresses.id", ondelete="CASCADE")
    )
    purpose: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailAddress(Identity, Timestamped, Base):
    __tablename__ = "email_addresses"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)
    is_primary: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)


class AccountThrottle(Base):
    __tablename__ = "account_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
