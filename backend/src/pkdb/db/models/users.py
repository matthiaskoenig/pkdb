from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Identity, Timestamped


class User(Identity, Timestamped, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(150), unique=True)
    email: Mapped[str | None] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(16), default="user", server_default="user")
    active: Mapped[bool] = mapped_column(default=False)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_name: Mapped[str] = mapped_column(default="", server_default="")
    last_name: Mapped[str] = mapped_column(default="", server_default="")
    pending_verification: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    password_hash: Mapped[str | None]
    display_name: Mapped[str | None] = mapped_column(String(200))
    affiliation: Mapped[str | None] = mapped_column(String(250))
    title: Mapped[str | None] = mapped_column(String(100))
    github: Mapped[str | None] = mapped_column(String(39))
    orcid: Mapped[str | None] = mapped_column(String(19))
    github_visible: Mapped[bool] = mapped_column(default=True, server_default="true")
    orcid_visible: Mapped[bool] = mapped_column(default=True, server_default="true")
    github_provenance: Mapped[str | None] = mapped_column(String(16))
    orcid_provenance: Mapped[str | None] = mapped_column(String(16))
    profile_edited_fields: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    avatar_key: Mapped[str | None] = mapped_column(String(32))
    avatar_initialized: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    __table_args__ = (
        Index("uq_users_username_lower", func.lower(username), unique=True),
        Index(
            "uq_users_sole_admin",
            "role",
            unique=True,
            postgresql_where=text("role = 'admin'"),
        ),
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
    __table_args__ = (
        Index(
            "uq_email_addresses_primary_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )


class AccountThrottle(Base):
    __tablename__ = "account_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AvatarAsset(Timestamped, Base):
    __tablename__ = "avatar_assets"
    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    media_type: Mapped[str] = mapped_column(String(32))
    width: Mapped[int]
    height: Mapped[int]
    checksum: Mapped[str] = mapped_column(String(64))
    source_kind: Mapped[str] = mapped_column(String(32))
    provenance: Mapped[dict | None] = mapped_column(JSONB)
