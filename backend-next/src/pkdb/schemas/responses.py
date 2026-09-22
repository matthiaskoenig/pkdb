"""Explicit public scientific response contracts."""

from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NodeResponse(ResponseModel):
    sid: str
    name: str
    label: str


class StudySummary(ResponseModel):
    sid: str
    name: str


class SubjectSummary(ResponseModel):
    pk: int
    name: str


class GroupSummary(SubjectSummary):
    count: int


class ScientificResponse(ResponseModel):
    pk: int
    measurement_type: NodeResponse
    calculation_type: NodeResponse | None
    choice: NodeResponse | None
    substance: NodeResponse | None
    value: float | None
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    sd: float | None
    se: float | None
    cv: float | None
    unit: str | None


class OutputResponse(ScientificResponse):
    normed: bool
    calculated: bool
    tissue: NodeResponse | None
    method: NodeResponse | None
    label: str | None
    output_type: str
    study: StudySummary
    group: GroupSummary | None
    individual: SubjectSummary | None
    interventions: list[SubjectSummary]
    time: float | None
    time_unit: str | None


class CharacteristicResponse(ScientificResponse):
    count: int | None
    group_count: int | None


class GroupResponse(GroupSummary):
    parent: GroupSummary | None
    study: StudySummary
    characteristica: list[CharacteristicResponse]


class IndividualResponse(SubjectSummary):
    group: GroupSummary | None
    study: StudySummary
    characteristica: list[CharacteristicResponse]


class InterventionResponse(ScientificResponse):
    normed: bool
    name: str
    route: NodeResponse | None
    form: NodeResponse | None
    application: NodeResponse | None
    time: str | None
    time_end: float | None
    time_unit: str | None
    study: StudySummary
