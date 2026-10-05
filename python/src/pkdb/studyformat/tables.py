"""Files of a study folder and the table specifications of study format 2."""

import re
from dataclasses import dataclass

from pkdb.studyformat import columns as c

ROOT = "all"
TEXT_SOURCE = "Text"
SOURCE_PATTERN = re.compile(r"Text|(?:Tab|Fig)[A-Za-z0-9_-]+")
STUDY_JSON = "study.json"
REFERENCE_JSON = "reference.json"
REVIEW_JSON = "review.json"
JSON_FILES = (STUDY_JSON, REFERENCE_JSON, REVIEW_JSON)


@dataclass(frozen=True)
class TableSpec:
    kind: str
    description: str
    columns: tuple[c.Column, ...]
    required_columns: frozenset[str]
    sort_columns: tuple[str, ...]
    per_source: bool = False
    required: bool = False

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def column(self, name: str) -> c.Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(name)


def _observation(measurement: c.Column) -> tuple[c.Column, ...]:
    return (
        measurement,
        *c.OBSERVATION_DETAILS,
        c.TIME,
        c.TIME_UNIT,
        *c.STATISTICS,
    )


SUBJECTS = TableSpec(
    kind="subjects",
    description="Groups and individuals. A subject with count 1 is an individual; every subject except `all` has a parent group.",
    columns=(c.STUDY, c.SUBJECT_NAME, c.PARENT, c.SUBJECT_COUNT, c.SOURCE, c.COMMENT),
    required_columns=frozenset({"name"}),
    sort_columns=("name",),
    required=True,
)
INTERVENTIONS = TableSpec(
    kind="interventions",
    description="Interventions such as doses, fasting or smoking, referenced by name from the other tables.",
    columns=(
        c.STUDY,
        c.SOURCE,
        c.INTERVENTION_NAME,
        c.INTERVENTION_SUBJECTS,
        c.INTERVENTION_MEASUREMENT,
        c.CALCULATION,
        c.SUBSTANCE,
        c.TISSUE,
        c.METHOD,
        c.CHOICE,
        c.ROUTE,
        c.FORM,
        c.APPLICATION,
        c.INTERVENTION_TIME,
        c.TIME_END,
        c.INTERVAL,
        c.DOSES,
        c.INTERVENTION_TIME_UNIT,
        c.INTERVENTION_COUNT,
        c.DOSE,
        *c.STATISTICS[2:],
        c.COMMENT,
    ),
    required_columns=frozenset({"name", "measurement"}),
    sort_columns=("name",),
)
CHARACTERISTICA = TableSpec(
    kind="characteristica",
    description="Baseline values of subjects, such as age, weight, sex or creatinine clearance.",
    columns=(
        c.STUDY,
        c.SOURCE,
        c.SUBJECTS,
        *_observation(c.CHARACTERISTICA_MEASUREMENT),
        c.COMMENT,
    ),
    required_columns=frozenset({"source", "subjects", "measurement"}),
    sort_columns=("subjects", "source", "measurement", "substance", "choice"),
)
OUTPUTS = TableSpec(
    kind="outputs",
    description="Single values after interventions, such as pharmacokinetic parameters, from one paper table or figure.",
    columns=(
        c.STUDY,
        c.OWNED_SOURCE,
        c.SUBJECTS,
        c.INTERVENTIONS,
        *_observation(c.OUTPUT_MEASUREMENT),
        c.COMMENT,
    ),
    required_columns=frozenset({"subjects", "measurement"}),
    sort_columns=(
        "subjects",
        "interventions",
        "measurement",
        "calculation",
        "substance",
        "tissue",
        "method",
        "choice",
        "time",
    ),
    per_source=True,
)
TIMECOURSES = TableSpec(
    kind="timecourses",
    description="Timecourse points from one paper figure or table. Rows with the same label form one series.",
    columns=(
        c.STUDY,
        c.OWNED_SOURCE,
        c.LABEL,
        c.SUBJECTS,
        c.INTERVENTIONS,
        *_observation(c.TIMECOURSE_MEASUREMENT),
        c.COMMENT,
    ),
    required_columns=frozenset(
        {"label", "subjects", "measurement", "time", "time_unit"}
    ),
    sort_columns=("label", "time"),
    per_source=True,
)
SCATTERS = TableSpec(
    kind="scatters",
    description="Points of scatter plots, one row per point with an x and a y value.",
    columns=(
        c.STUDY,
        c.OWNED_SOURCE,
        c.SCATTER_NAME,
        c.SCATTER_SUBJECTS,
        *c.axis("x"),
        *c.axis("y"),
        c.COMMENT,
    ),
    required_columns=frozenset(
        {"name", "subjects", "x_measurement", "x_mean", "y_measurement", "y_mean"}
    ),
    sort_columns=("name", "subjects"),
    per_source=True,
)

TABLES = {
    spec.kind: spec
    for spec in (
        SUBJECTS,
        INTERVENTIONS,
        CHARACTERISTICA,
        OUTPUTS,
        TIMECOURSES,
        SCATTERS,
    )
}
KIND_ORDER = {kind: index for index, kind in enumerate(TABLES)}


def table_file(kind: str, source: str | None = None) -> str:
    return f"{kind}_{source}.tsv" if source else f"{kind}.tsv"


def parse_table_file(name: str) -> tuple[TableSpec, str | None] | None:
    """Return the table and source of a table file name, or None."""
    if not name.endswith(".tsv"):
        return None
    stem = name.removesuffix(".tsv")
    spec = TABLES.get(stem)
    if spec is not None:
        return None if spec.per_source else (spec, None)
    kind, separator, source = stem.partition("_")
    spec = TABLES.get(kind)
    if separator and spec and spec.per_source and SOURCE_PATTERN.fullmatch(source):
        return spec, source
    return None


def image_file(study: str, source: str) -> str:
    return f"{study}_{source}.png"
