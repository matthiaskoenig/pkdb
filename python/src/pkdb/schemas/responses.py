"""Explicit public scientific response contracts."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


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


class AuthorResponse(ResponseModel):
    pk: int
    first_name: str
    last_name: str
    organization: str | None = None


class ReferenceResponse(ResponseModel):
    pk: int
    sid: str
    name: str
    pmid: str | None
    doi: str | None
    title: str | None
    abstract: str | None
    journal: str | None
    date: str | None
    authors: list[AuthorResponse]
    publication_date: str | None = None
    provenance: dict[str, JsonValue] = Field(default_factory=dict)


class EmptyResponse(ResponseModel):
    pass


class SourceReference(ResponseModel):
    pk: int


class ArrayOutput(ResponseModel):
    pk: int
    group: GroupSummary | EmptyResponse
    individual: SubjectSummary | EmptyResponse
    interventions: list[SubjectSummary]
    ex: SourceReference | EmptyResponse
    normed: bool
    value: float | None
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    se: float | None
    sd: float | None
    cv: float | None
    unit: str | None
    time_unit: str | None
    time: float | None
    tissue: NodeResponse | None
    method: NodeResponse | None
    measurement_type: NodeResponse
    substance: NodeResponse | None
    choice: NodeResponse | None
    label: str | None


class SubsetResponse(ResponseModel):
    pk: int
    study: StudySummary
    name: str
    data_type: str
    array: list[list[ArrayOutput]]


class DescriptionResponse(ResponseModel):
    pk: int
    text: str


class CommentResponse(DescriptionResponse):
    username: str | None


class NotesResponse(ResponseModel):
    descriptions: list[DescriptionResponse]
    comments: list[CommentResponse]


class UserResponse(ResponseModel):
    display_name: str | None = None
    affiliation: str | None = None
    title: str | None = None
    github: str | None = None
    github_provenance: str | None = None
    orcid: str | None = None
    orcid_provenance: str | None = None
    avatar_url: str | None = None
    username: str
    first_name: str
    last_name: str
    organization: str | None = None


class CuratorResponse(UserResponse):
    rating: float


class GroupSetResponse(NotesResponse):
    groups: list[int]


class IndividualSetResponse(NotesResponse):
    individuals: list[int]


class InterventionSetResponse(NotesResponse):
    interventions: list[int]


class OutputSetResponse(NotesResponse):
    outputs: list[int]


class DatasetResponse(NotesResponse):
    subsets: list[int]


class StudyReferenceResponse(ReferenceResponse):
    study: StudySummary


class AttachmentResponse(ResponseModel):
    pk: str
    name: str
    file: str


class StudyResponse(NotesResponse):
    pk: str
    sid: str
    name: str
    licence: str
    access: str
    date: str | None
    group_count: int
    individual_count: int
    intervention_count: int
    output_count: int
    output_calculated_count: int
    subset_count: int
    timecourse_count: int
    scatter_count: int
    reference: StudyReferenceResponse | None
    reference_date: str | None
    creator: UserResponse | None
    curators: list[CuratorResponse]
    collaborators: list[UserResponse]
    files: list[AttachmentResponse]
    substances: list[NodeResponse]
    groupset: GroupSetResponse
    individualset: IndividualSetResponse
    interventionset: InterventionSetResponse
    outputset: OutputSetResponse
    dataset: DatasetResponse


class SubstanceProperties(ResponseModel):
    mass: float | None
    charge: int | None
    formula: str | None


class MeasurementProperties(ResponseModel):
    units: list[str]
    choices: list[NodeResponse]


class VocabularyResponse(NodeResponse):
    deprecated: bool
    ntype: str
    dtype: str
    description: str | None
    synonyms: list[str]
    parents: list[NodeResponse]
    annotations: list[dict]
    xrefs: list[dict]
    measurement_type: MeasurementProperties | None
    substance: SubstanceProperties | None
