"""Explicit legacy analysis wire schemas; declaration order is CSV column order."""

from pkdb.schemas.responses import ResponseModel


class AnalysisStudy(ResponseModel):
    sid: str | None
    name: str | None
    licence: str | None
    access: str | None
    date: str | None
    creator: str | None
    curators: list[str]
    substances: list[str]
    reference_pmid: str | None
    reference_title: str | None
    reference_date: str | None


class AnalysisGroup(ResponseModel):
    study_sid: str | None
    study_name: str | None
    group_pk: int | None
    group_name: str | None
    group_count: int | None
    group_parent_pk: int | None
    characteristica_pk: int | None
    count: int | None
    tissue: str | None
    method: str | None
    time: float | None
    time_unit: str | None
    measurement_type: str | None
    calculation_type: str | None
    choice: str | None
    substance: str | None
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    sd: float | None
    se: float | None
    cv: float | None
    gmean: float | None
    gsd: float | None
    gcv: float | None
    error_bar: float | None
    error_type: str | None
    unit: str | None


class AnalysisIndividual(ResponseModel):
    study_sid: str | None
    study_name: str | None
    individual_pk: int | None
    individual_name: str | None
    individual_group_pk: int | None
    characteristica_pk: int | None
    count: int | None
    tissue: str | None
    method: str | None
    time: float | None
    time_unit: str | None
    measurement_type: str | None
    calculation_type: str | None
    choice: str | None
    substance: str | None
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    sd: float | None
    se: float | None
    cv: float | None
    gmean: float | None
    gsd: float | None
    gcv: float | None
    error_bar: float | None
    error_type: str | None
    unit: str | None


class AnalysisIntervention(ResponseModel):
    study_sid: str | None
    study_name: str | None
    intervention_pk: int | None
    raw_pk: int | None
    normed: bool
    name: str | None
    route: str | None
    route_label: str | None
    form: str | None
    form_label: str | None
    application: str | None
    application_label: str | None
    tissue: str | None
    tissue_label: str | None
    method: str | None
    method_label: str | None
    time: float | list[float] | None
    time_end: float | None
    interval: float | None
    doses: int | None
    time_unit: str | None
    subject_pk: int | None
    measurement_type: str | None
    measurement_type_label: str | None
    calculation_type: str | None
    calculation_type_label: str | None
    choice: str | None
    choice_label: str | None
    substance: str | None
    substance_label: str | None
    count: int | None
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    sd: float | None
    se: float | None
    cv: float | None
    gmean: float | None
    gsd: float | None
    gcv: float | None
    error_bar: float | None
    error_type: str | None
    unit: str | None


class AnalysisOutput(ResponseModel):
    study_sid: str | None
    study_name: str | None
    output_pk: int | None
    intervention_pk: int | None
    group_pk: int | None
    individual_pk: int | None
    normed: bool
    calculated: bool
    tissue: str | None
    tissue_label: str | None
    method: str | None
    method_label: str | None
    label: str | None
    output_type: str | None
    time: float | None
    time_unit: str | None
    measurement_type: str | None
    measurement_type_label: str | None
    calculation_type: str | None
    calculation_type_label: str | None
    choice: str | None
    choice_label: str | None
    substance: str | None
    substance_label: str | None
    count: int | None
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    sd: float | None
    se: float | None
    cv: float | None
    gmean: float | None
    gsd: float | None
    gcv: float | None
    error_bar: float | None
    error_type: str | None
    unit: str | None


class AnalysisTimecourse(ResponseModel):
    study_sid: str | None
    study_name: str | None
    output_pk: list[int]
    subset_pk: int | None
    subset_name: str | None
    intervention_pk: list[int]
    group_pk: int | None
    individual_pk: int | None
    normed: bool
    tissue: str | None
    tissue_label: str | None
    method: str | None
    method_label: str | None
    label: str | None
    time: list[float | None] | None
    time_unit: str | None
    measurement_type: str | None
    measurement_type_label: str | None
    choice: str | None
    choice_label: str | None
    substance: str | None
    substance_label: str | None
    count: list[int | None] | None
    mean: list[float | None] | None
    median: list[float | None] | None
    min: list[float | None] | None
    max: list[float | None] | None
    sd: list[float | None] | None
    se: list[float | None] | None
    cv: list[float | None] | None
    gmean: list[float | None] | None
    gsd: list[float | None] | None
    gcv: list[float | None] | None
    error_bar: list[float | None] | None
    error_type: list[str | None] | None
    unit: str | None


class AnalysisData(ResponseModel):
    study_sid: str | None
    study_name: str | None
    data_pk: int | None
    data_name: str | None
    data_type: str | None
    subset_pk: int | None
    subset_name: str | None
    data_point_pk: int | None
    output_pk: int | None
    dimension: int | None


ANALYSIS_MODELS = {
    "studies": AnalysisStudy,
    "groups": AnalysisGroup,
    "individuals": AnalysisIndividual,
    "interventions": AnalysisIntervention,
    "outputs": AnalysisOutput,
    "timecourses": AnalysisTimecourse,
    "data": AnalysisData,
}
