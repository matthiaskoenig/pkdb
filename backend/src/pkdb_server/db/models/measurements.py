"""Unified scientific observations and ordered, array-backed datasets."""

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Sequence,
    UniqueConstraint,
    case,
    func,
    join,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, column_property, mapped_column, synonym

from pkdb_server.db.models.base import Base, Owned

dataset_row_id_sequence = Sequence("dataset_row_id_seq", metadata=Base.metadata)


class Dataset(Owned, Base):
    __tablename__ = "datasets"
    kind: Mapped[str]
    parent_id: Mapped[int | None] = mapped_column(index=True)
    name: Mapped[str | None]
    data_type: Mapped[str | None]
    image: Mapped[str | None]
    position: Mapped[int | None]
    measurement_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), default=list, server_default="{}"
    )
    point_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), default=list, server_default="{}"
    )
    shared_fields: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    row_metadata: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    dimension_labels: Mapped[list] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    __mapper_args__ = {"polymorphic_on": "kind"}
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "kind", "key"),
        UniqueConstraint("parent_id", "position"),
        Index("ix_datasets_measurement_ids", "measurement_ids", postgresql_using="gin"),
        ForeignKeyConstraint(
            ["study_id", "parent_id"],
            ["datasets.study_id", "datasets.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("kind IN ('course', 'dataset', 'series')", name="kind"),
        CheckConstraint("position IS NULL OR position >= 0", name="position"),
        CheckConstraint(
            "(kind = 'series') = (parent_id IS NOT NULL)", name="parent_kind"
        ),
    )


class Timecourse(Dataset):
    __mapper_args__ = {"polymorphic_identity": "course"}


class Scatter(Dataset):
    __mapper_args__ = {"polymorphic_identity": "dataset"}


class Subset(Dataset):
    __mapper_args__ = {"polymorphic_identity": "series"}
    scatter_id = synonym("parent_id")


class MeasurementSource(Owned, Base):
    __tablename__ = "measurement_sources"
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "key"),
    )


class ObservationContext(Owned, Base):
    __tablename__ = "observations"
    kind: Mapped[str]
    subject_id: Mapped[int] = mapped_column(index=True)
    source_id: Mapped[int | None]
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
    calculated: Mapped[bool] = mapped_column(default=False, server_default="false")
    series_key: Mapped[str | None]
    label: Mapped[str | None]
    output_type: Mapped[str] = mapped_column(default="output", server_default="output")
    time: Mapped[float | None]
    time_unit: Mapped[str | None]
    time_not_reported: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    time_unit_not_reported: Mapped[bool] = mapped_column(
        default=False, server_default="false"
    )
    tissue: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    method: Mapped[str | None] = mapped_column(ForeignKey("vocabulary_nodes.sid"))
    image: Mapped[str | None]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("study_id", "kind", "key"),
        ForeignKeyConstraint(
            ["study_id", "subject_id"],
            ["subjects.study_id", "subjects.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "source_id"],
            ["measurement_sources.study_id", "measurement_sources.id"],
        ),
        CheckConstraint("kind IN ('characteristic', 'output')", name="kind"),
        CheckConstraint(
            "output_type IN ('output', 'timecourse', 'array')", name="output_type"
        ),
    )


class ObservationValue(Owned, Base):
    __tablename__ = "observation_values"
    observation_id: Mapped[int] = mapped_column(index=True)
    origin: Mapped[str] = mapped_column("representation", default="reported")
    unit: Mapped[str | None]
    value: Mapped[float | None]
    mean: Mapped[float | None]
    median: Mapped[float | None]
    minimum: Mapped[float | None]
    maximum: Mapped[float | None]
    sd: Mapped[float | None]
    se: Mapped[float | None]
    cv: Mapped[float | None]
    count: Mapped[int | None]
    derived_from_id: Mapped[int | None]
    derived_from_course_id: Mapped[int | None]
    __table_args__ = (
        UniqueConstraint("study_id", "id"),
        UniqueConstraint("observation_id", "representation"),
        ForeignKeyConstraint(
            ["study_id", "observation_id"],
            ["observations.study_id", "observations.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "derived_from_id"],
            ["observation_values.study_id", "observation_values.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "derived_from_course_id"],
            ["datasets.study_id", "datasets.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "representation IN ('reported', 'normalized', 'calculated')",
            name="representation",
        ),
        CheckConstraint("count IS NULL OR count >= 0", name="count"),
    )


_context = ObservationContext.__table__
_values = ObservationValue.__table__


class Observation(Base):
    """Read adapter: one row per representation, sharing its context identity."""

    __table__ = join(_context, _values, _context.c.id == _values.c.observation_id)
    id = _values.c.id
    observation_id = column_property(_context.c.id, _values.c.observation_id)
    study_id = column_property(_context.c.study_id, _values.c.study_id)
    key = column_property(_values.c.key)
    context_key = column_property(_context.c.key)
    context_source = column_property(_context.c.source)
    value_source = column_property(_values.c.source)
    value_source_present = column_property(_values.c.source.is_not(None))
    origin = _values.c.representation
    __mapper_args__ = {
        "polymorphic_on": _context.c.kind,
        "primary_key": [_values.c.id],
    }

    if TYPE_CHECKING:
        subject_id: Mapped[int]
        subject_kind: Mapped[str]
        measurement_type: Mapped[str]
        substance: Mapped[str | None]
        calculation_type: Mapped[str | None]
        choice: Mapped[str | None]
        calculated: Mapped[bool]
        source_id: Mapped[int | None]
        series_key: Mapped[str | None]
        label: Mapped[str | None]
        output_type: Mapped[str]
        time: Mapped[float | None]
        time_unit: Mapped[str | None]
        time_not_reported: Mapped[bool]
        time_unit_not_reported: Mapped[bool]
        tissue: Mapped[str | None]
        method: Mapped[str | None]
        image: Mapped[str | None]
        unit: Mapped[str | None]
        value: Mapped[float | None]
        mean: Mapped[float | None]
        median: Mapped[float | None]
        minimum: Mapped[float | None]
        maximum: Mapped[float | None]
        sd: Mapped[float | None]
        se: Mapped[float | None]
        cv: Mapped[float | None]
        count: Mapped[int | None]
        derived_from_id: Mapped[int | None]
        derived_from_course_id: Mapped[int | None]

    def __init__(self, **kwargs):
        group_id = kwargs.pop("group_id", None)
        individual_id = kwargs.pop("individual_id", None)
        if group_id is not None and individual_id is not None:
            raise ValueError("An observation has exactly one subject")
        if group_id is not None or individual_id is not None:
            kwargs["subject_id"] = group_id if group_id is not None else individual_id
            self.subject_kind = "group" if group_id is not None else "individual"
        kwargs.setdefault("context_key", kwargs.get("key"))
        if "source" in kwargs:
            kwargs["context_source"] = kwargs.pop("source")
        super().__init__(**kwargs)

    @hybrid_property
    def source(self):
        return self.value_source if self.value_source_present else self.context_source

    @source.inplace.expression
    @classmethod
    def _source_expression(cls):
        return func.coalesce(cls.value_source, cls.context_source)

    @hybrid_property
    def group_id(self):
        return self.subject_id if self.subject_kind == "group" else None

    @group_id.inplace.expression
    @classmethod
    def _group_expression(cls):
        return case((cls.subject_kind == "group", cls.subject_id))

    @hybrid_property
    def individual_id(self):
        return self.subject_id if self.subject_kind == "individual" else None

    @individual_id.inplace.expression
    @classmethod
    def _individual_expression(cls):
        return case((cls.subject_kind == "individual", cls.subject_id))


class Characteristic(Observation):
    __mapper_args__ = {"polymorphic_identity": "characteristic"}


class Measurement(Observation):
    __mapper_args__ = {"polymorphic_identity": "output"}


class ObservationIntervention(Base):
    __tablename__ = "observation_interventions"
    study_id: Mapped[int] = mapped_column(primary_key=True)
    observation_id: Mapped[int] = mapped_column(primary_key=True)
    intervention_id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int]
    __table_args__ = (
        ForeignKeyConstraint(
            ["study_id", "observation_id"],
            ["observations.study_id", "observations.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "intervention_id"],
            ["interventions.study_id", "interventions.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("observation_id", "position"),
    )


_links = ObservationIntervention.__table__


class MeasurementIntervention(Base):
    """Read-only projection of context interventions onto representations."""

    __table__ = (
        select(
            _links.c.study_id,
            _links.c.observation_id,
            _values.c.id.label("measurement_id"),
            _links.c.intervention_id,
            _links.c.position,
        )
        .select_from(
            join(_links, _values, _links.c.observation_id == _values.c.observation_id)
        )
        .subquery("measurement_intervention_projection")
    )
    __mapper_args__ = {
        "primary_key": [__table__.c.measurement_id, __table__.c.intervention_id]
    }
    if TYPE_CHECKING:
        study_id: Mapped[int]
        observation_id: Mapped[int]
        measurement_id: Mapped[int]
        intervention_id: Mapped[int]
        position: Mapped[int]


from pkdb_server.db.models.subjects import Subject  # noqa: E402

Observation.subject_kind = column_property(
    select(Subject.kind)
    .where(Subject.id == Observation.subject_id)
    .correlate_except(Subject)
    .scalar_subquery()
)
