"""Typed scientific records, independent of transport and database models."""

import re
from collections.abc import Iterator
from datetime import date as Date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from pkdb.schemas.provenance import ManualCuration, StudyProvenance
from pkdb.schemas.source import SourceLocation

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1)]
Sid = Annotated[str, Field(min_length=1, max_length=255)]
MAX_RECORD_KEY_LENGTH = 512
RecordKey = Annotated[str, Field(min_length=1, max_length=MAX_RECORD_KEY_LENGTH)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Description(Record):
    text: str


class Comment(Description):
    user: str | None = None


class Notes(Record):
    descriptions: list[Description] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)


class Curator(Record):
    user: Identifier
    rating: Annotated[float, Field(ge=0, le=5)] = 0


class Metadata(Notes):
    provenance: StudyProvenance = Field(default_factory=ManualCuration)
    name: Identifier
    date: Date | None = None
    creator: Identifier
    curators: list[Curator] = Field(default_factory=list)
    collaborators: list[str] = Field(default_factory=list)
    licence: Literal["open", "closed"] = "closed"
    access: Literal["public", "private"] = "private"


class Author(Record):
    first_name: str = ""
    last_name: str = ""
    organization: str | None = None

    @model_validator(mode="after")
    def author_name(self):
        if not self.last_name.strip() and not (self.organization or "").strip():
            raise ValueError("Author requires a last name or organization")
        return self


class Reference(Record):
    sid: Sid
    name: str
    pmid: str | None = None
    doi: str | None = None
    url: str | None = None
    title: str | None = None
    abstract: str | None = None
    journal: str | None = None
    date: Date | None = None
    authors: list[Author] = Field(default_factory=list)
    publication_date: str | None = None
    provenance: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def matching_publication_dates(self):
        if (
            self.date
            and self.publication_date
            and not self.date.isoformat().startswith(self.publication_date)
        ):
            raise ValueError("Exact date must agree with publication_date")
        return self

    @field_validator("publication_date")
    @classmethod
    def valid_publication_date(cls, value):
        if value is not None:
            if not re.fullmatch(r"[0-9]{4}(?:-[0-9]{2})?(?:-[0-9]{2})?", value):
                raise ValueError(
                    "Publication date must be YYYY, YYYY-MM, or YYYY-MM-DD"
                )
            Date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])
        return value


class Statistics(Record):
    value: Number | None = None
    mean: Number | None = None
    median: Number | None = None
    min: Number | None = None
    max: Number | None = None
    sd: Number | None = None
    se: Number | None = None
    cv: Number | None = None
    count: Annotated[int, Field(strict=True, ge=0)] | None = None


class Observation(Notes):
    """Scientific values and provenance shared by characteristics and outputs."""

    key: RecordKey
    measurement_type: Identifier
    calculation_type: str | None = None
    choice: str | None = None
    substance: str | None = None
    statistics: Statistics = Field(default_factory=Statistics)
    unit: str | None = None
    source: SourceLocation | None = None
    origin: Literal["reported", "normalized", "calculated"] = "reported"
    derived_from: str | None = None
    calculated: bool = False


# Source and API compatibility name; all scientific records share Observation.
ScientificRecord = Observation


class Subject(Notes):
    """Identity fields shared by groups and individually identified participants."""

    image: str | None = None
    key: RecordKey
    name: Identifier
    characteristica: list[Observation] = Field(default_factory=list)
    source: SourceLocation | None = None


class Group(Subject):
    count: Annotated[int, Field(strict=True, ge=0)] | None
    parent: str | None = None


class Individual(Subject):
    group: str | None = None


class Intervention(ScientificRecord):
    image: str | None = None
    name: Identifier
    time: Number | str | None = None
    time_end: Number | None = None
    time_unit: str | None = None
    route: str | None = None
    application: str | None = None
    form: str | None = None


class Measurement(ScientificRecord):
    series_key: str | None = None
    time_not_reported: bool = False
    time_unit_not_reported: bool = False
    group: str | None = None
    individual: str | None = None
    interventions: list[str] = Field(default_factory=list)
    tissue: str | None = None
    method: str | None = None
    label: str | None = None
    output_type: Literal["output", "timecourse", "array"] = "output"
    time: Number | None = None
    time_unit: str | None = None
    image: str | None = None


class Dimension(Notes):
    dimension: str
    output: str


class Subset(Notes):
    name: str
    dimensions: list[Dimension] = Field(default_factory=list)
    shared: list[str] = Field(default_factory=list)
    points: list[list[str]] = Field(default_factory=list)


class DataRecord(Notes):
    key: RecordKey
    name: str
    data_type: str
    image: str | None = None
    subsets: list[Subset] = Field(default_factory=list)
    source: SourceLocation | None = None


class Timecourse(Record):
    key: RecordKey
    points: list[Measurement]


class Attachment(Record):
    name: str
    sha256: str
    size: int


class CanonicalStudy(Notes):
    sid: Sid
    metadata: Metadata
    reference: Reference
    groups: list[Group] = Field(default_factory=list)
    individuals: list[Individual] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)
    measurements: list[Measurement] = Field(default_factory=list)
    timecourses: list[Timecourse] = Field(default_factory=list)
    scatters: list[DataRecord] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    section_notes: dict[str, Notes] = Field(default_factory=dict)
    source_digest: str


def subject_observations(
    study: CanonicalStudy,
) -> Iterator[tuple[Subject, Observation]]:
    """Yield subject/observation pairs for characteristics and measured outputs."""
    groups = {subject.name: subject for subject in study.groups}
    individuals = {subject.name: subject for subject in study.individuals}
    for subject in [*study.groups, *study.individuals]:
        for observation in subject.characteristica:
            yield subject, observation
    for observation in study.measurements:
        subject = (
            groups.get(observation.group)
            if observation.group
            else individuals.get(observation.individual)
        )
        if subject is not None:
            yield subject, observation
