"""Relational metadata and reusable scientific columns."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, MetaData, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Identity:
    id: Mapped[int] = mapped_column(primary_key=True)


class Owned(Identity):
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(512))
    source: Mapped[dict | None] = mapped_column(JSONB)


class Scientific:
    measurement_type: Mapped[str] = mapped_column(
        ForeignKey("vocabulary_nodes.sid"), index=True
    )
    substance: Mapped[str | None] = mapped_column(
        ForeignKey("vocabulary_nodes.sid"), index=True
    )
    calculation_type: Mapped[str | None] = mapped_column(
        ForeignKey("vocabulary_nodes.sid")
    )
    choice: Mapped[str | None]
    unit: Mapped[str | None]
    value: Mapped[float | None] = mapped_column(Float)
    mean: Mapped[float | None] = mapped_column(Float)
    median: Mapped[float | None] = mapped_column(Float)
    minimum: Mapped[float | None] = mapped_column(Float)
    maximum: Mapped[float | None] = mapped_column(Float)
    sd: Mapped[float | None] = mapped_column(Float)
    se: Mapped[float | None] = mapped_column(Float)
    cv: Mapped[float | None] = mapped_column(Float)
    count: Mapped[int | None]
    calculated: Mapped[bool] = mapped_column(default=False, server_default="false")
    origin: Mapped[str] = mapped_column(String(16), default="reported")


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
