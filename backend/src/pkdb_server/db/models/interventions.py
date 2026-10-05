from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from pkdb_server.db.models.base import Base, Owned, Scientific


class Intervention(Owned, Scientific, Base):
    __tablename__ = "interventions"
    image: Mapped[str | None]
    name: Mapped[str]
    time: Mapped[float | None]
    time_list: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    time_end: Mapped[float | None]
    interval: Mapped[float | None]
    doses: Mapped[int | None]
    time_unit: Mapped[str | None]
    subject_id: Mapped[int | None] = mapped_column(index=True)
    route: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    application: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    form: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    derived_from_id: Mapped[int | None]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        UniqueConstraint("study_id", "name", "origin"),
        ForeignKeyConstraint(
            ["study_id", "derived_from_id"],
            ["interventions.study_id", "interventions.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "subject_id"],
            ["subjects.study_id", "subjects.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "origin IN ('reported', 'normalized', 'calculated')", name="origin"
        ),
        CheckConstraint("count IS NULL OR count >= 0", name="count"),
        CheckConstraint("error_type IN ('sd', 'se', 'gsd')", name="error_type"),
        CheckConstraint("doses IS NULL OR doses >= 1", name="doses"),
        CheckConstraint(
            "time_list IS NULL OR (time IS NULL AND cardinality(time_list) >= 2)",
            name="time_list",
        ),
    )
