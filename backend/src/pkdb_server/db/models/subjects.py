"""One subject identity for groups and individually identified participants."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, synonym

from pkdb_server.db.models.base import Base, Owned


class Subject(Owned, Base):
    __tablename__ = "subjects"
    kind: Mapped[str]
    image: Mapped[str | None]
    name: Mapped[str]
    count: Mapped[int] = mapped_column(default=1)
    parent_id: Mapped[int | None] = mapped_column(index=True)
    __mapper_args__ = {"polymorphic_on": "kind"}
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "kind", "key"),
        UniqueConstraint("study_id", "kind", "name"),
        ForeignKeyConstraint(
            ["study_id", "parent_id"],
            ["subjects.study_id", "subjects.id"],
            deferrable=True,
            initially="IMMEDIATE",
        ),
        CheckConstraint("kind IN ('group', 'individual')", name="kind"),
        CheckConstraint("count >= 0", name="count"),
        CheckConstraint("kind <> 'individual' OR count = 1", name="individual_count"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_self"),
    )


class Group(Subject):
    __mapper_args__ = {"polymorphic_identity": "group"}


class Individual(Subject):
    __mapper_args__ = {"polymorphic_identity": "individual"}
    group_id = synonym("parent_id")


# Compatibility import for the public query/read modules. Both kinds are mapped
# to observations; characteristics no longer have a separate physical table.
from pkdb_server.db.models.measurements import (  # noqa: E402
    Characteristic as Characteristic,
)
