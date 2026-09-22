"""Typed scientific records, independent of transport and database models."""

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

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
    name: Identifier
    date: Date | None = None
    creator: Identifier
    curators: list[Curator] = Field(default_factory=list)
    collaborators: list[str] = Field(default_factory=list)
    licence: Literal["open", "closed"] = "closed"
    access: Literal["public", "private"] = "private"


class Author(Record):
    first_name: str = ""
    last_name: str


class Reference(Record):
    sid: Sid
    name: str
    pmid: str | None = None
    doi: str | None = None
    title: str | None = None
    abstract: str | None = None
    journal: str | None = None
    date: Date | None = None
    authors: list[Author] = Field(default_factory=list)


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


class ScientificRecord(Notes):
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


class Group(Notes):
    image: str | None = None
    key: RecordKey
    name: Identifier
    count: Annotated[int, Field(strict=True, ge=0)]
    parent: str | None = None
    characteristica: list[ScientificRecord] = Field(default_factory=list)
    source: SourceLocation | None = None


class Individual(Notes):
    image: str | None = None
    key: RecordKey
    name: Identifier
    group: str | None = None
    characteristica: list[ScientificRecord] = Field(default_factory=list)
    source: SourceLocation | None = None


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
