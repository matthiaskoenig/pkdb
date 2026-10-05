"""Columns of the study format 2 tables.

This module is the single source for column names, order, types and descriptions.
The formatter, validator, JSON Schema export, documentation and workbook template
read their column information from here.
"""

from dataclasses import dataclass, replace
from enum import StrEnum


class ColumnType(StrEnum):
    TEXT = "text"
    NAME = "name"
    NAMES = "names"
    NUMBER = "number"
    INTEGER = "integer"
    TIME = "time"
    TIMES = "times"
    UNIT = "unit"
    TERM = "term"
    ENUM = "enum"
    SOURCE = "source"


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    description: str
    example: str = ""
    # Vocabulary attribute holding the allowed terms, for example "measurements".
    vocabulary: str | None = None
    # Table kind whose `name` column this column refers to.
    references: str | None = None
    choices: tuple[str, ...] = ()
    allows_nr: bool = False
    # Written by `pkdb format`; never edited by people or agents.
    owned: bool = False

    def but(self, **changes) -> Column:
        return replace(self, **changes)


T = ColumnType

STUDY = Column(
    "study",
    T.TEXT,
    "Study name, written by `pkdb format` from the folder name. Do not edit.",
    "Guo2016",
    owned=True,
)
SOURCE = Column(
    "source",
    T.SOURCE,
    "Paper table or figure the row comes from, such as `Tab1` or `Fig2A`, or `Text` for the article text. Except for `Text`, the image `<study>_<source>.png` must exist.",
    "Tab1",
)
OWNED_SOURCE = SOURCE.but(
    description="Paper table or figure of the row, written by `pkdb format` from the file name. Do not edit.",
    owned=True,
)
SUBJECTS = Column(
    "subjects",
    T.NAME,
    "Name of the subject in `subjects.tsv` that the row describes: a group, or an individual with count 1.",
    "all",
    references="subjects",
)
INTERVENTIONS = Column(
    "interventions",
    T.NAMES,
    "Comma-separated names of the interventions in `interventions.tsv` that the subjects received before the measurement. Empty for none.",
    "D1",
    references="interventions",
)
MEASUREMENT = Column(
    "measurement",
    T.TERM,
    "Measured quantity from the vocabulary, such as `cmax`, `age` or `weight`.",
    "cmax",
    vocabulary="measurements",
)
CALCULATION = Column(
    "calculation",
    T.TERM,
    "How the central value was obtained, from the vocabulary. `unspecified summary` marks a central value whose statistic the publication does not state; enter it in `mean`.",
    "unspecified summary",
    vocabulary="calculation_types",
)
SUBSTANCE = Column(
    "substance",
    T.TERM,
    "Substance from the vocabulary.",
    "caffeine",
    vocabulary="substances",
)
TISSUE = Column(
    "tissue",
    T.TERM,
    "Tissue or matrix from the vocabulary.",
    "plasma",
    vocabulary="tissues",
)
METHOD = Column(
    "method",
    T.TERM,
    "Analytical method from the vocabulary.",
    "HPLC",
    vocabulary="methods",
)
CHOICE = Column(
    "choice",
    T.TEXT,
    "Categorical value of a categorical measurement, such as `M` for `sex`.",
    "M",
)
TIME = Column(
    "time",
    T.TIME,
    "Time point in `time_unit`, or `NR` when the publication does not report it.",
    "2",
    allows_nr=True,
)
TIME_UNIT = Column(
    "time_unit",
    T.UNIT,
    "Unit of `time`, or `NR` when the publication does not report it.",
    "h",
    allows_nr=True,
)
COUNT = Column(
    "count",
    T.INTEGER,
    "Number of subjects the row describes. Leave empty when it equals the count of the referenced subject. In a `choice` row, the number of subjects with that choice.",
    "12",
)
MEAN = Column(
    "mean",
    T.NUMBER,
    "Arithmetic mean. For a single subject (count 1) and for `unspecified summary`, the reported value.",
    "2.9",
)
SD = Column("sd", T.NUMBER, "Standard deviation.", "0.7")
SE = Column("se", T.NUMBER, "Standard error of the mean.", "0.2")
CV = Column("cv", T.NUMBER, "Coefficient of variation in percent.", "24")
GMEAN = Column("gmean", T.NUMBER, "Geometric mean.", "2.7")
GSD = Column(
    "gsd",
    T.NUMBER,
    "Geometric standard deviation as a dimensionless factor of at least 1.",
    "1.3",
)
GCV = Column("gcv", T.NUMBER, "Geometric coefficient of variation in percent.", "26")
MEDIAN = Column("median", T.NUMBER, "Median.", "2.8")
MIN = Column("min", T.NUMBER, "Minimum.", "1.9")
MAX = Column("max", T.NUMBER, "Maximum.", "4.1")
UNIT = Column(
    "unit",
    T.UNIT,
    "Unit of `mean`, `sd`, `se`, `gmean`, `median`, `min`, `max` and `error_bar`.",
    "mg/l",
)
ERROR_BAR = Column(
    "error_bar",
    T.NUMBER,
    "Digitized end of an error bar on the value axis, in `unit`. The statistic named in `error_type` is derived from it.",
    "3.6",
)
ERROR_TYPE = Column(
    "error_type",
    T.ENUM,
    "Statistic the error bar shows: `sd`, `se` or `gsd`.",
    "sd",
    choices=("sd", "se", "gsd"),
)
COMMENT = Column("comment", T.TEXT, "Free-text comment.")

STATISTICS = (
    COUNT,
    MEAN,
    SD,
    SE,
    CV,
    GMEAN,
    GSD,
    GCV,
    MEDIAN,
    MIN,
    MAX,
    UNIT,
    ERROR_BAR,
    ERROR_TYPE,
)
OBSERVATION_DETAILS = (CALCULATION, SUBSTANCE, TISSUE, METHOD, CHOICE)
CHARACTERISTICA_MEASUREMENT = MEASUREMENT.but(
    description="Baseline quantity from the vocabulary, such as `age`, `weight` or `sex`.",
    example="age",
)
OUTPUT_MEASUREMENT = MEASUREMENT.but(
    description="Measured quantity from the vocabulary, such as `cmax`, `auc_inf` or `thalf`.",
)
TIMECOURSE_MEASUREMENT = MEASUREMENT.but(
    description="Measured quantity from the vocabulary, such as `concentration`.",
    example="concentration",
)

SUBJECT_NAME = Column(
    "name", T.NAME, "Unique subject name. The root group is `all`.", "all"
)
PARENT = Column(
    "parent",
    T.NAME,
    "Name of the parent group. Empty only for `all`.",
    "all",
    references="subjects",
)
SUBJECT_COUNT = Column(
    "count",
    T.INTEGER,
    "Number of subjects. A count of 1 makes the row an individual; any other count, or an empty cell, makes it a group.",
    "12",
)

INTERVENTION_NAME = Column(
    "name",
    T.NAME,
    "Unique intervention name, referenced from the `interventions` columns of other tables.",
    "D1",
)
INTERVENTION_SUBJECTS = SUBJECTS.but(
    description="Subject that the dose statistics describe, for body-weight-adjusted doses with `sd`, `min` or `max`. Usually empty.",
)
INTERVENTION_MEASUREMENT = MEASUREMENT.but(
    description="Kind of intervention from the vocabulary, such as `dosing`, `qualitative dosing` or `fasting`.",
    example="dosing",
)
INTERVENTION_CHOICE = CHOICE.but(
    description="Categorical value of a categorical intervention, such as `Y` for `fasting`.",
    example="Y",
)
ROUTE = Column(
    "route",
    T.TERM,
    "Administration route from the vocabulary.",
    "oral",
    vocabulary="routes",
)
FORM = Column(
    "form",
    T.TERM,
    "Administration form from the vocabulary.",
    "tablet",
    vocabulary="forms",
)
APPLICATION = Column(
    "application",
    T.TERM,
    "Application from the vocabulary, such as `single dose`.",
    "single dose",
    vocabulary="applications",
)
INTERVENTION_COUNT = COUNT.but(
    description="Number of subjects the dose statistics describe. Usually empty.",
)
INTERVENTION_TIME_UNIT = TIME_UNIT.but(
    description="Unit of `time`, `time_end` and `interval`, or `NR` when the publication does not report it.",
)
INTERVENTION_TIME = Column(
    "time",
    T.TIMES,
    "Time of the first administration in `time_unit`. An irregular schedule is a `;`-separated list such as `0;12;40`.",
    "0",
    allows_nr=True,
)
TIME_END = Column(
    "time_end", T.NUMBER, "End of a continuous administration in `time_unit`.", "2"
)
INTERVAL = Column("interval", T.NUMBER, "Dosing interval in `time_unit`.", "24")
DOSES = Column("doses", T.INTEGER, "Number of administrations.", "7")
DOSE = MEAN.but(
    description="Dose. A fixed dose is entered as its value, such as `100` with unit `mg`.",
    example="100",
)

LABEL = Column(
    "label",
    T.NAME,
    "Name of the timecourse. Rows with the same label form one series; labels are unique across the study.",
    "caffeine_plasma_D1",
)
SCATTER_NAME = Column(
    "name",
    T.NAME,
    "Name of the scatter dataset, unique across the study.",
    "clearance_vs_crcl",
)
SCATTER_SUBJECTS = SUBJECTS.but(
    description="Subject of the point, usually an individual with count 1.",
)
POINT_VALUE = MEAN.but(description="Value of the point.", example="2.9")
POINT_UNIT = UNIT.but(description="Unit of the value.")


def axis(prefix: str) -> tuple[Column, ...]:
    """Columns of one scatter axis, such as `x_measurement`."""
    columns = (
        INTERVENTIONS,
        MEASUREMENT,
        SUBSTANCE,
        TISSUE,
        METHOD,
        TIME,
        TIME_UNIT,
        POINT_VALUE,
        POINT_UNIT,
    )
    label = f"{prefix.upper()} axis"
    descriptions = {
        TIME.name: f"time point in `{prefix}_{TIME_UNIT.name}`, or `NR` when the publication does not report it.",
        TIME_UNIT.name: f"unit of `{prefix}_{TIME.name}`, or `NR` when the publication does not report it.",
    }
    return tuple(
        column.but(
            name=f"{prefix}_{column.name}",
            description=f"{label}: "
            + descriptions.get(
                column.name, column.description[0].lower() + column.description[1:]
            ),
        )
        for column in columns
    )
