from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Owned, Scientific


class Intervention(Owned, Scientific, Base):
    __tablename__ = "interventions"
    name: Mapped[str]
    time: Mapped[float | None]
    time_text: Mapped[str | None]
    time_end: Mapped[float | None]
    time_unit: Mapped[str | None]
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
        CheckConstraint(
            "origin IN ('reported', 'normalized', 'calculated')", name="origin"
        ),
        CheckConstraint("count IS NULL OR count >= 0", name="count"),
    )
