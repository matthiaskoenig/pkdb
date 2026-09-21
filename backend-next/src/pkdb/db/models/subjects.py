from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pkdb.db.models.base import Base, Owned, Scientific


class Group(Owned, Base):
    __tablename__ = "groups"
    name: Mapped[str]
    count: Mapped[int]
    parent_id: Mapped[int | None] = mapped_column(index=True)
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        UniqueConstraint("study_id", "name"),
        ForeignKeyConstraint(
            ["study_id", "parent_id"],
            ["groups.study_id", "groups.id"],
            deferrable=True,
            initially="IMMEDIATE",
        ),
        CheckConstraint("count >= 0", name="count"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_self"),
    )


class Individual(Owned, Base):
    __tablename__ = "individuals"
    name: Mapped[str]
    group_id: Mapped[int | None] = mapped_column(index=True)
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        UniqueConstraint("study_id", "name"),
        ForeignKeyConstraint(
            ["study_id", "group_id"], ["groups.study_id", "groups.id"]
        ),
    )


class Characteristic(Owned, Scientific, Base):
    __tablename__ = "characteristics"
    group_id: Mapped[int | None]
    individual_id: Mapped[int | None]
    derived_from_id: Mapped[int | None]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        ForeignKeyConstraint(
            ["study_id", "group_id"],
            ["groups.study_id", "groups.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "individual_id"],
            ["individuals.study_id", "individuals.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "derived_from_id"],
            ["characteristics.study_id", "characteristics.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(group_id IS NULL) <> (individual_id IS NULL)", name="one_subject"
        ),
        CheckConstraint(
            "origin IN ('reported', 'normalized', 'calculated')", name="origin"
        ),
        CheckConstraint("count IS NULL OR count >= 0", name="count"),
    )
