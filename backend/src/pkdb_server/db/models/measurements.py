from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pkdb_server.db.models.base import Base, Owned, Scientific


class Timecourse(Owned, Base):
    __tablename__ = "timecourses"
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
    )


class MeasurementSource(Owned, Base):
    __tablename__ = "measurement_sources"
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
    )


class Measurement(Owned, Scientific, Base):
    __tablename__ = "measurements"
    source_id: Mapped[int | None]
    group_id: Mapped[int | None] = mapped_column(index=True)
    individual_id: Mapped[int | None] = mapped_column(index=True)
    derived_from_id: Mapped[int | None]
    derived_from_course_id: Mapped[int | None]
    series_key: Mapped[str | None]
    label: Mapped[str | None]
    output_type: Mapped[str] = mapped_column(default="output")
    time: Mapped[float | None]
    time_unit: Mapped[str | None]
    time_not_reported: Mapped[bool] = mapped_column(default=False)
    time_unit_not_reported: Mapped[bool] = mapped_column(default=False)
    tissue: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    method: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    image: Mapped[str | None]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        ForeignKeyConstraint(
            ["study_id", "source_id"],
            ["measurement_sources.study_id", "measurement_sources.id"],
        ),
        ForeignKeyConstraint(
            ["study_id", "group_id"], ["groups.study_id", "groups.id"]
        ),
        ForeignKeyConstraint(
            ["study_id", "individual_id"], ["individuals.study_id", "individuals.id"]
        ),
        ForeignKeyConstraint(
            ["study_id", "derived_from_id"],
            ["measurements.study_id", "measurements.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "derived_from_course_id"],
            ["timecourses.study_id", "timecourses.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "(group_id IS NULL) <> (individual_id IS NULL)", name="one_subject"
        ),
        CheckConstraint(
            "origin IN ('reported', 'normalized', 'calculated')", name="origin"
        ),
        CheckConstraint(
            "output_type IN ('output', 'timecourse', 'array')", name="output_type"
        ),
        CheckConstraint("count IS NULL OR count >= 0", name="count"),
    )


class TimecoursePoint(Base):
    __tablename__ = "timecourse_points"
    study_id: Mapped[int] = mapped_column(primary_key=True)
    timecourse_id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    measurement_id: Mapped[int]
    __table_args__ = (
        ForeignKeyConstraint(
            ["study_id", "timecourse_id"],
            ["timecourses.study_id", "timecourses.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "measurement_id"],
            ["measurements.study_id", "measurements.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("timecourse_id", "measurement_id"),
        CheckConstraint("position >= 0", name="position"),
    )


class MeasurementIntervention(Base):
    __tablename__ = "measurement_interventions"
    study_id: Mapped[int] = mapped_column(primary_key=True)
    measurement_id: Mapped[int] = mapped_column(primary_key=True)
    intervention_id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int]
    __table_args__ = (
        ForeignKeyConstraint(
            ["study_id", "measurement_id"],
            ["measurements.study_id", "measurements.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "intervention_id"],
            ["interventions.study_id", "interventions.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("measurement_id", "position"),
    )


class Scatter(Owned, Base):
    __tablename__ = "scatters"
    name: Mapped[str]
    data_type: Mapped[str]
    image: Mapped[str | None]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
    )


class Subset(Owned, Base):
    __tablename__ = "subsets"
    scatter_id: Mapped[int]
    shared_fields: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    dimension_labels: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    name: Mapped[str]
    position: Mapped[int]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        UniqueConstraint("scatter_id", "position"),
        ForeignKeyConstraint(
            ["study_id", "scatter_id"],
            ["scatters.study_id", "scatters.id"],
            ondelete="CASCADE",
        ),
    )


class SubsetPoint(Owned, Base):
    __tablename__ = "subset_points"
    subset_id: Mapped[int]
    position: Mapped[int]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
        UniqueConstraint("study_id", "subset_id", "id"),
        UniqueConstraint("subset_id", "position"),
        ForeignKeyConstraint(
            ["study_id", "subset_id"],
            ["subsets.study_id", "subsets.id"],
            ondelete="CASCADE",
        ),
    )


class SubsetDimension(Base):
    __tablename__ = "subset_dimensions"
    study_id: Mapped[int] = mapped_column(primary_key=True)
    subset_id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    dimension: Mapped[str]
    point_id: Mapped[int]
    measurement_id: Mapped[int]
    shared: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ["study_id", "subset_id", "point_id"],
            ["subset_points.study_id", "subset_points.subset_id", "subset_points.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "subset_id"],
            ["subsets.study_id", "subsets.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "measurement_id"],
            ["measurements.study_id", "measurements.id"],
            ondelete="CASCADE",
        ),
    )
