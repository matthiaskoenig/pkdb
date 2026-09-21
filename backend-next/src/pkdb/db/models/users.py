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
    purpose: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
