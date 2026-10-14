"""Files of a study folder and the table specifications of study format 2."""

import re
from dataclasses import dataclass
from typing import Literal

from pkdb.studyformat import columns as c

ROOT = "all"
TEXT_SOURCE = "Text"
SOURCE_PATTERN = re.compile(r"Text|(?:Tab|Fig)[A-Za-z0-9_-]+")
STUDY_JSON = "study.json"
REFERENCE_JSON = "reference.json"
REVIEW_JSON = "review.json"
JSON_FILES = (STUDY_JSON, REFERENCE_JSON, REVIEW_JSON)
# The kind of a raw table, the paper table as printed, beside the table kinds.
RAW_KIND = "raw"


@dataclass(frozen=True)
class TableSpec:
    """Declaration of one table kind: columns, sort order and split by source."""

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
        c.INTERVENTION_CHOICE,
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
# The order of the tables in a workbook, in a study folder listing and in the curation app: the
# subjects with their characteristica, then the interventions, then the tables of the data.
KIND_ORDER = {
    kind: index
    for index, kind in enumerate(
        (
            "subjects",
            "characteristica",
            "interventions",
            "outputs",
            "timecourses",
            "scatters",
        )
    )
}
InfoClass = Literal["subjects", "interventions", "data", "raw"]
# The class of information of each table kind and of a raw table, by which the curation app
# groups and colors the tables (it tints the columns by `column_class`): the subjects with their characteristica, the interventions, the
# data of the paper, and the paper tables as printed.
INFO_CLASSES: dict[str, InfoClass] = {
    "subjects": "subjects",
    "characteristica": "subjects",
    "interventions": "interventions",
    "outputs": "data",
    "timecourses": "data",
    "scatters": "data",
    RAW_KIND: "raw",
}
ColumnClass = Literal["subjects", "interventions", "data", "meta"]
# The columns that say where a row comes from, which the curation app mutes.
META_COLUMNS = frozenset({"study", "source"})


def column_class(kind: str, name: str) -> ColumnClass:
    """The class of information of the column `name` of a table of `kind`.

    The curation app tints a column by it. `study` and `source` are `meta`. Every other column of
    the subjects and characteristica tables is `subjects`, of the interventions table
    `interventions`. In the tables of the data, `subjects`, `parent` and `*_subjects` are
    `subjects`, `interventions` and `*_interventions` are `interventions`, and every other column
    is `data`.
    """
    if name in META_COLUMNS:
        return "meta"
    if kind in ("subjects", "characteristica"):
        return "subjects"
    if kind == "interventions":
        return "interventions"
    if name in ("subjects", "parent") or name.endswith("_subjects"):
        return "subjects"
    if name == "interventions" or name.endswith("_interventions"):
        return "interventions"
    return "data"


def column_classes(spec: TableSpec) -> tuple[ColumnClass, ...]:
    """The classes of the columns of a table kind in header order; a raw table has none."""
    return tuple(column_class(spec.kind, name) for name in spec.names)


# The names of the table kinds and of a raw table in the curation app.
KIND_LABELS = {
    "subjects": "Subjects",
    "characteristica": "Characteristica",
    "interventions": "Interventions",
    "outputs": "Outputs",
    "timecourses": "Timecourses",
    "scatters": "Scatters",
    RAW_KIND: "Raw table",
}


def table_file(kind: str, source: str | None = None) -> str:
    """File name of a table of a kind and, for tables split by source, its source."""
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


def has_header(file: str) -> bool:
    """Whether a file is a table with a header line, `<kind>[_<source>].tsv`.

    Its header is line 0 and its first entry line 1, and line n is row n + 1 of
    its sheet. A raw table `<study>_<source>.tsv` has no header: its first line
    is line 1 and row 1.
    """
    return parse_table_file(file) is not None


def workbook_row(file: str, line: int) -> int:
    """The row of the sheet in the workbook that shows a line of a file.

    Line n of a table with a header is row n + 1. The lines of a raw table are
    their rows, and so are the rows of the workbook itself, whose issues name
    the rows of its sheets.
    """
    return line + 1 if has_header(file) else line


def table_line(file: str, physical: int) -> int:
    """The line of a file that is its 1-based physical line `physical`.

    A table with a header counts from its header, line 0; other files count
    from 1.
    """
    return physical - 1 if has_header(file) else physical


def image_file(study: str, source: str) -> str:
    """File name `<study>_<source>.png` of the image of a paper table or figure."""
    return f"{study}_{source}.png"
