---
search:
  exclude: true
---

# Study format v2, sub-project 1: schema, formatter and validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `pkdb.studyformat` package that defines the study format 2 tables in one schema module, writes study folders in canonical form (`pkdb format`), validates layout, format, rows, relationships and vocabulary (`pkdb validate` on format 2 folders), and exports JSON Schema and a generated column reference (`pkdb schema`).

**Architecture:** `columns.py` and `tables.py` declare every column and table once. `text.py` and `cells.py` turn TSV bytes into canonical text and typed values. `load.py` reads a folder into a `LoadedStudy` without judging content. `formatter.py` renders canonical files from a `LoadedStudy`. `rows.py`, `relations.py` and `terms.py` each implement one validation layer; `validation.py` combines them into a `ValidationReport`. `export.py` derives JSON Schema and Markdown from the same declarations. Format 1 folders keep using the existing pipeline unchanged.

**Tech Stack:** Python 3.14, Pydantic 2, pint (existing `pkdb.domain.units.ureg`), pytest, ruff, ty. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-05-study-format-v2-design.md` (sections 4 to 10.1 and 16 for this sub-project).

## Global Constraints

- Python `>=3.14`; code must pass `uv run --locked ruff check .`, `uv run --locked ruff format --check .` and `uv run --locked ty check` in `python/`.
- Run tests with `uv run --locked pytest -q` in `python/`; the existing 331 tests must keep passing.
- No new runtime or development dependencies.
- Never use the em dash character anywhere (code, comments, docs, commit messages). Use "-".
- Markdown paragraphs are written on a single source line.
- Commit messages carry no agent attribution lines of any kind.
- Format 1 behavior (`pkdb prepare`, `validate`, `upload` on folders without `"format": 2`) must not change.
- Do not modify the `pkdb_data` repository in this sub-project.
- File and column names, column order, sort keys and rules are exactly those of spec sections 4 and 5; the code in this plan already encodes them.

## Review Focus

1. TSV files saved by spreadsheet applications or editors (CRLF line endings, byte order mark, cells wrapped in double quotes, dropped trailing tabs, non-breaking spaces): the formatter reads them and writes canonical files without losing data. Test owned by Task 7.
2. Numbers typed with a decimal comma (`2,9`): reported as `invalid_number` with the hint to use a decimal point, never silently read as text or as two values. Test owned by Task 3.
3. Format 1 column names (`measurement_type`, `group`, `individual`, `value`, `calculation_type`, `mean_pm`) in a TSV: `unknown_column` names the format 2 replacement. Test owned by Task 6.
4. Non-ASCII names (`Dahlström2007`, subject `Gruppe Ä`, unit `µg/l`): formatting and validation work and sorting is stable. Test owned by Task 11.
5. Large studies (20,000 timecourse rows): `validate_folder` finishes within 10 seconds on a developer machine; no quadratic checks. Test owned by Task 11.

## File Structure

Create in `python/src/pkdb/studyformat/`:

| File | Responsibility |
|---|---|
| `__init__.py` | Public API: `FORMAT_VERSION`, `is_v2_folder`, `format_folder`, `validate_folder` |
| `columns.py` | `ColumnType`, `Column` and every column definition with description and example |
| `tables.py` | `TableSpec`, `TABLES`, file names, source pattern, `parse_table_file`, `image_file` |
| `text.py` | TSV parsing and rendering, canonical numbers, natural sort key |
| `cells.py` | Canonical cell text and typed cell values with problems |
| `jsonio.py` | Strict JSON loading and canonical JSON dumping |
| `models.py` | `StudyMetadata`, `Review` and canonical JSON for both |
| `issues.py` | `make_issue`, `column_letter`, warning codes and categories |
| `layout.py` | `scan_folder`: classify the files of a study folder |
| `load.py` | `load_table`, `load_study`: read a folder into typed tables |
| `formatter.py` | `planned_files`, `format_folder` |
| `rows.py` | Layer 3: required cells, statistics, times, schedules, units |
| `relations.py` | Layer 4: references, subject tree, names, series, duplicates, images, study and review rules |
| `terms.py` | Layer 5: vocabulary terms, choices, signs, required time and unit, dosing fields |
| `validation.py` | `validate_folder`: all layers, format check, acknowledgements |
| `export.py` | `json_schemas`, `column_reference` |

Create `python/src/pkdb/studyformat_cli.py` (commands `format` and `schema`), `docs/study-format.md` (generated) and tests in `python/tests/studyformat/` (`conftest.py` plus `test_studyformat_*.py`; test file basenames must be unique across `python/tests`).

Modify `python/src/pkdb/cache.py` (add `atomic_text`), `python/src/pkdb/cli.py` (register commands, dispatch format 2 folders in `validate`, refuse them in `prepare` and `upload`) and `zensical.toml` (navigation).

---

### Task 1: Column and table declarations

**Files:**
- Create: `python/src/pkdb/studyformat/__init__.py`
- Create: `python/src/pkdb/studyformat/columns.py`
- Create: `python/src/pkdb/studyformat/tables.py`
- Create: `python/tests/studyformat/conftest.py`
- Test: `python/tests/studyformat/test_studyformat_tables.py`

**Interfaces:**
- Produces: `ColumnType` (StrEnum: `TEXT, NAME, NAMES, NUMBER, INTEGER, TIME, TIMES, UNIT, TERM, ENUM, SOURCE`); `Column(name, type, description, example="", vocabulary=None, references=None, choices=(), allows_nr=False, owned=False)` with `Column.but(**changes) -> Column`; `TableSpec(kind, description, columns, required_columns, sort_columns, per_source=False, required=False)` with `.names`, `.column(name)`; `TABLES: dict[str, TableSpec]` in the order subjects, interventions, characteristica, outputs, timecourses, scatters; `KIND_ORDER: dict[str, int]`; `ROOT = "all"`; `TEXT_SOURCE = "Text"`; `SOURCE_PATTERN` (compiled, use `fullmatch`); `STUDY_JSON`, `REFERENCE_JSON`, `REVIEW_JSON`, `JSON_FILES`; `table_file(kind, source=None) -> str`; `parse_table_file(name) -> tuple[TableSpec, str | None] | None`; `image_file(study, source) -> str`.

- [ ] **Step 1: Write the failing test**

`python/tests/studyformat/conftest.py` (fixtures used by later tasks; the `tsv` helper is used from Task 5 on):

```python
"""Fixtures for study format 2 tests."""

import pytest

from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary


@pytest.fixture
def sf_vocabulary():
    return Vocabulary(
        version="studyformat-test",
        measurements=(
            MeasurementRule(name="species", dtype="categorical", choices=("Homo sapiens",)),
            MeasurementRule(name="healthy", dtype="boolean", choices=("Y", "N")),
            MeasurementRule(name="sex", dtype="categorical", choices=("M", "F", "NR")),
            MeasurementRule(name="age", units=("yr",)),
            MeasurementRule(name="concentration", units=("mg/l",), time_required=True),
            MeasurementRule(name="cmax", units=("mg/l",)),
            MeasurementRule(name="dosing", units=("mg",)),
            MeasurementRule(name="change", units=("mg/l",), can_negative=True),
            MeasurementRule(name="old_measure", units=("mg/l",), deprecated=True),
        ),
        substances=(SubstanceDefinition(name="drug", sid="drug", mass=500),),
        tissues=("plasma",),
        methods=("HPLC",),
        routes=("oral",),
        forms=("tablet",),
        applications=("single dose", "multiple dose"),
        calculation_types=("calculation", "geometric mean", "sample mean"),
    )
```

`python/tests/studyformat/test_studyformat_tables.py`:

```python
from pkdb.studyformat.columns import ColumnType
from pkdb.studyformat.tables import (
    TABLES,
    image_file,
    parse_table_file,
    table_file,
)

STATS = (
    "count mean sd se cv gmean gsd gcv median min max unit error_bar error_type"
).split()
HEAD = "measurement calculation substance tissue method choice".split()


def test_tables_in_folder_order():
    assert list(TABLES) == [
        "subjects",
        "interventions",
        "characteristica",
        "outputs",
        "timecourses",
        "scatters",
    ]


def test_column_order_matches_spec():
    assert TABLES["subjects"].names == (
        "study", "name", "parent", "count", "source", "comment",
    )
    assert TABLES["characteristica"].names == (
        "study", "source", "subjects", *HEAD, "time", "time_unit", *STATS, "comment",
    )
    assert TABLES["interventions"].names == (
        "study", "source", "name", "subjects", *HEAD,
        "route", "form", "application",
        "time", "time_end", "interval", "doses", "time_unit", *STATS, "comment",
    )
    assert TABLES["outputs"].names == (
        "study", "source", "subjects", "interventions", *HEAD,
        "time", "time_unit", *STATS, "comment",
    )
    assert TABLES["timecourses"].names == (
        "study", "source", "label", "subjects", "interventions", *HEAD,
        "time", "time_unit", *STATS, "comment",
    )
    axis = "interventions measurement substance tissue method time time_unit mean unit"
    assert TABLES["scatters"].names == (
        "study", "source", "name", "subjects",
        *(f"x_{name}" for name in axis.split()),
        *(f"y_{name}" for name in axis.split()),
        "comment",
    )


def test_owned_columns():
    for spec in TABLES.values():
        assert spec.column("study").owned
    for kind in ("outputs", "timecourses", "scatters"):
        assert TABLES[kind].per_source
        assert TABLES[kind].column("source").owned
    for kind in ("subjects", "interventions", "characteristica"):
        assert not TABLES[kind].per_source
        assert not TABLES[kind].column("source").owned


def test_references_and_types():
    assert TABLES["outputs"].column("subjects").references == "subjects"
    assert TABLES["outputs"].column("interventions").references == "interventions"
    assert TABLES["outputs"].column("interventions").type is ColumnType.NAMES
    assert TABLES["subjects"].column("parent").references == "subjects"
    assert TABLES["scatters"].column("x_interventions").references == "interventions"
    assert TABLES["interventions"].column("time").type is ColumnType.TIMES
    assert TABLES["outputs"].column("time").type is ColumnType.TIME
    assert TABLES["outputs"].column("error_type").choices == ("sd", "se", "gsd")
    assert TABLES["outputs"].column("measurement").vocabulary == "measurements"
    assert TABLES["outputs"].column("calculation").vocabulary == "calculation_types"
    assert TABLES["interventions"].column("route").vocabulary == "routes"


def test_required_columns():
    assert TABLES["subjects"].required
    assert not TABLES["outputs"].required
    assert TABLES["timecourses"].required_columns == {
        "label", "subjects", "measurement", "time", "time_unit",
    }
    assert TABLES["scatters"].required_columns == {
        "name", "subjects", "x_measurement", "x_mean", "y_measurement", "y_mean",
    }


def test_every_column_is_documented():
    for spec in TABLES.values():
        for column in spec.columns:
            assert column.description.endswith(".")
            assert "\u2014" not in column.description


def test_file_names():
    assert table_file("subjects") == "subjects.tsv"
    assert table_file("outputs", "Tab2") == "outputs_Tab2.tsv"
    assert parse_table_file("subjects.tsv") == (TABLES["subjects"], None)
    assert parse_table_file("timecourses_Fig3A.tsv") == (TABLES["timecourses"], "Fig3A")
    assert parse_table_file("outputs_Text.tsv") == (TABLES["outputs"], "Text")
    assert parse_table_file("scatters_Fig1_group.tsv") == (TABLES["scatters"], "Fig1_group")
    assert parse_table_file("outputs.tsv") is None
    assert parse_table_file("subjects_Tab1.tsv") is None
    assert parse_table_file("outputs_Tab2.csv") is None
    assert parse_table_file("groups.tsv") is None
    assert image_file("Guo2016", "Fig2") == "Guo2016_Fig2.png"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_tables.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat'`

- [ ] **Step 3: Write the implementation**

`python/src/pkdb/studyformat/__init__.py`:

```python
"""Study format 2: fixed table templates committed as canonical TSV files."""

FORMAT_VERSION = 2
```

`python/src/pkdb/studyformat/columns.py`:

```python
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
    "Measured quantity from the vocabulary, such as `cmax`, `age` or `sex`.",
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
    "tissue", T.TERM, "Tissue or matrix from the vocabulary.", "plasma", vocabulary="tissues"
)
METHOD = Column(
    "method", T.TERM, "Analytical method from the vocabulary.", "HPLC", vocabulary="methods"
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
    "Unit of the time columns, or `NR` when the publication does not report it.",
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
    COUNT, MEAN, SD, SE, CV, GMEAN, GSD, GCV, MEDIAN, MIN, MAX, UNIT, ERROR_BAR, ERROR_TYPE,
)
OBSERVATION_HEAD = (MEASUREMENT, CALCULATION, SUBSTANCE, TISSUE, METHOD, CHOICE)

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
    description="Kind of intervention from the vocabulary, such as `dosing`, `qualitative dosing` or `circadian status`.",
    example="dosing",
)
ROUTE = Column(
    "route", T.TERM, "Administration route from the vocabulary.", "oral", vocabulary="routes"
)
FORM = Column(
    "form", T.TERM, "Administration form from the vocabulary.", "tablet", vocabulary="forms"
)
APPLICATION = Column(
    "application",
    T.TERM,
    "Application from the vocabulary, such as `single dose`.",
    "single dose",
    vocabulary="applications",
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
        INTERVENTIONS, MEASUREMENT, SUBSTANCE, TISSUE, METHOD, TIME, TIME_UNIT,
        POINT_VALUE, POINT_UNIT,
    )
    return tuple(
        column.but(
            name=f"{prefix}_{column.name}",
            description=f"{prefix.upper()} axis: {column.description}",
        )
        for column in columns
    )
```

`python/src/pkdb/studyformat/tables.py`:

```python
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


OBSERVATION = (*c.OBSERVATION_HEAD, c.TIME, c.TIME_UNIT, *c.STATISTICS)

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
        c.TIME_UNIT,
        c.COUNT,
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
    columns=(c.STUDY, c.SOURCE, c.SUBJECTS, *OBSERVATION, c.COMMENT),
    required_columns=frozenset({"source", "subjects", "measurement"}),
    sort_columns=("subjects", "source", "measurement", "substance", "choice"),
)
OUTPUTS = TableSpec(
    kind="outputs",
    description="Single values after interventions, such as pharmacokinetic parameters, from one paper table or figure.",
    columns=(c.STUDY, c.OWNED_SOURCE, c.SUBJECTS, c.INTERVENTIONS, *OBSERVATION, c.COMMENT),
    required_columns=frozenset({"subjects", "measurement"}),
    sort_columns=(
        "subjects", "interventions", "measurement", "calculation", "substance",
        "tissue", "method", "choice", "time",
    ),
    per_source=True,
)
TIMECOURSES = TableSpec(
    kind="timecourses",
    description="Timecourse points from one paper figure or table. Rows with the same label form one series.",
    columns=(
        c.STUDY, c.OWNED_SOURCE, c.LABEL, c.SUBJECTS, c.INTERVENTIONS, *OBSERVATION, c.COMMENT,
    ),
    required_columns=frozenset({"label", "subjects", "measurement", "time", "time_unit"}),
    sort_columns=("label", "time"),
    per_source=True,
)
SCATTERS = TableSpec(
    kind="scatters",
    description="Points of scatter plots, one row per point with an x and a y value.",
    columns=(
        c.STUDY, c.OWNED_SOURCE, c.SCATTER_NAME, c.SCATTER_SUBJECTS,
        *c.axis("x"), *c.axis("y"), c.COMMENT,
    ),
    required_columns=frozenset(
        {"name", "subjects", "x_measurement", "x_mean", "y_measurement", "y_mean"}
    ),
    sort_columns=("name", "subjects"),
    per_source=True,
)

TABLES = {
    spec.kind: spec
    for spec in (SUBJECTS, INTERVENTIONS, CHARACTERISTICA, OUTPUTS, TIMECOURSES, SCATTERS)
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
```

Note: `DOSE` replaces `MEAN` in the interventions statistics, so `c.STATISTICS[2:]` continues with `sd`; `c.COUNT` is placed explicitly before `DOSE` to keep the spec order `count, mean, sd, ...`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_tables.py -q`
Expected: PASS (8 tests)

- [ ] **Step 5: Lint, format, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat
cd .. && git add python/src/pkdb/studyformat python/tests/studyformat
git commit -m "Declare study format 2 columns and tables"
```

---

### Task 2: Canonical text helpers

**Files:**
- Create: `python/src/pkdb/studyformat/text.py`
- Test: `python/tests/studyformat/test_studyformat_text.py`

**Interfaces:**
- Produces: `parse_number(text) -> float | None`; `format_number(value: float) -> str`; `canonical_number(text) -> str | None`; `natural_key(text) -> tuple`; `unquote(cell) -> str`; `TsvError(ValueError)`; `TsvLine(number: int, cells: tuple[str, ...])`; `ParsedTsv(header: tuple[str, ...], lines: tuple[TsvLine, ...])`; `parse_tsv(data: bytes) -> ParsedTsv`; `render_tsv(header, rows) -> str`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from pkdb.studyformat.text import (
    TsvError,
    canonical_number,
    format_number,
    natural_key,
    parse_number,
    parse_tsv,
    render_tsv,
    unquote,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2.90", "2.9"),
        ("43.0", "43"),
        ("43", "43"),
        ("-0", "0"),
        ("+2", "2"),
        (".5", "0.5"),
        ("1e-3", "0.001"),
        ("0.00001", "1e-05"),
        ("1.94326186260799", "1.94326186260799"),
        ("1e16", "1e+16"),
        ("2,9", None),
        ("1_000", None),
        ("nan", None),
        ("inf", None),
        ("1e999", None),
        ("abc", None),
        ("", None),
    ],
)
def test_canonical_number(text, expected):
    assert canonical_number(text) == expected


def test_parse_and_format_number_round_trip():
    for value in (0.1, 1 / 3, 123456.789, -2.5e-12):
        assert parse_number(format_number(value)) == value


def test_natural_key_orders_numbers_by_value():
    names = ["Tab10", "Tab2", "Fig1", "tab3", "Tab2a"]
    assert sorted(names, key=natural_key) == ["Fig1", "Tab2", "Tab2a", "tab3", "Tab10"]


def test_natural_key_handles_non_ascii():
    assert sorted(["Ä2", "A10", "A2"], key=natural_key) == ["A2", "A10", "Ä2"]


def test_unquote():
    assert unquote('"D1,D2"') == "D1,D2"
    assert unquote('"say ""hi"""') == 'say "hi"'
    assert unquote('"a" and "b"') == '"a" and "b"'
    assert unquote("plain") == "plain"
    assert unquote('"') == '"'


def test_parse_tsv_normalizes_line_endings_bom_and_whitespace():
    data = "\ufeffname\tcount \r\n all\t\u00a04\r\n\r\n\t\t\r\nS1\t1\n".encode()
    parsed = parse_tsv(data)
    assert parsed.header == ("name", "count")
    assert [(line.number, line.cells) for line in parsed.lines] == [
        (2, ("all", "4")),
        (5, ("S1", "1")),
    ]


def test_parse_tsv_keeps_ragged_rows():
    parsed = parse_tsv(b"a\tb\tc\nx\n")
    assert parsed.lines[0].cells == ("x",)


def test_parse_tsv_empty_file():
    assert parse_tsv(b"").header == ()


def test_parse_tsv_rejects_non_utf8():
    with pytest.raises(TsvError, match="UTF-8"):
        parse_tsv("name\nDahlström".encode("latin-1"))


def test_render_tsv():
    assert render_tsv(("a", "b"), [("1", ""), ("x", "y")]) == "a\tb\n1\t\nx\ty\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_text.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.text'`

- [ ] **Step 3: Write the implementation**

```python
"""Canonical text: TSV parsing and rendering, numbers and natural sort order."""

import math
import re
from dataclasses import dataclass

NUMBER_PATTERN = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_DIGITS = re.compile(r"(\d+)")


def parse_number(text: str) -> float | None:
    """Parse a decimal number written with a decimal point; None otherwise."""
    if not NUMBER_PATTERN.fullmatch(text):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def format_number(value: float) -> str:
    """Shortest text that converts back to the same float; integers without point."""
    if value == 0:
        return "0"
    if value.is_integer() and abs(value) < 1e16:
        return str(int(value))
    return repr(value)


def canonical_number(text: str) -> str | None:
    value = parse_number(text)
    return None if value is None else format_number(value)


def natural_key(text: str) -> tuple:
    """Sort key that orders embedded numbers by value: Tab2 before Tab10."""
    return tuple(
        (0, int(part), part) if index % 2 else (1, part.casefold(), part)
        for index, part in enumerate(_DIGITS.split(text))
        if part
    )


def unquote(cell: str) -> str:
    """Remove spreadsheet export quoting from a cell wrapped in double quotes."""
    if len(cell) >= 2 and cell[0] == cell[-1] == '"':
        inner = cell[1:-1]
        if '"' not in inner.replace('""', ""):
            return inner.replace('""', '"').strip()
    return cell


class TsvError(ValueError):
    """The bytes are not a UTF-8 text table."""


@dataclass(frozen=True)
class TsvLine:
    number: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class ParsedTsv:
    header: tuple[str, ...]
    lines: tuple[TsvLine, ...]


def _cells(line: str) -> tuple[str, ...]:
    return tuple(unquote(cell.strip()) for cell in line.split("\t"))


def parse_tsv(data: bytes) -> ParsedTsv:
    """Read a tab-separated table leniently; blank lines are skipped."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise TsvError(f"File is not UTF-8 encoded (byte {error.start})") from None
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ParsedTsv((), ())
    return ParsedTsv(
        _cells(lines[0]),
        tuple(
            TsvLine(number, _cells(line))
            for number, line in enumerate(lines[1:], start=2)
            if line.strip()
        ),
    )


def render_tsv(header: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    return "".join("\t".join(cells) + "\n" for cells in (header, *rows))
```

`str.strip()` removes non-breaking spaces (`\u00a0`), which is why the parse test expects `"4"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_text.py -q`
Expected: PASS

- [ ] **Step 5: Lint, format, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat
cd .. && git add python/src/pkdb/studyformat/text.py python/tests/studyformat/test_studyformat_text.py
git commit -m "Add canonical TSV text helpers for study format 2"
```

---

### Task 3: Cell values

**Files:**
- Create: `python/src/pkdb/studyformat/cells.py`
- Test: `python/tests/studyformat/test_studyformat_cells.py`

**Interfaces:**
- Consumes: `Column`, `ColumnType` (Task 1); `SOURCE_PATTERN` (Task 1); `parse_number`, `format_number`, `natural_key` (Task 2).
- Produces: `NOT_REPORTED = "NR"`; `CellProblem(code, message, hint=None)`; `canonical_cell(column, text) -> str`; `parse_cell(column, text) -> tuple[object, CellProblem | None]` where `text` is canonical. Typed values: empty cell gives `None` (NAMES gives `()`); NUMBER `float`; INTEGER `int`; TIME `float` or `"NR"`; TIMES `tuple[float, ...]` or `"NR"`; NAMES `tuple[str, ...]`; every other type `str`.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from pkdb.studyformat.cells import canonical_cell, parse_cell
from pkdb.studyformat.tables import TABLES

OUT = TABLES["outputs"]
IV = TABLES["interventions"]
SUB = TABLES["subjects"]


@pytest.mark.parametrize(
    ("column", "text", "expected"),
    [
        (OUT.column("mean"), " 2.50 ", "2.5"),
        (OUT.column("mean"), "NA", ""),
        (OUT.column("mean"), "nan", ""),
        (OUT.column("mean"), "2,5", "2,5"),
        (OUT.column("count"), "17.0", "17"),
        (OUT.column("time"), "NR", "NR"),
        (OUT.column("time"), "0.50", "0.5"),
        (IV.column("time"), "0; 12.0 ;40", "0;12;40"),
        (OUT.column("interventions"), "D2, D10 ,D1", "D1,D2,D10"),
        (OUT.column("comment"), "NA", "NA"),
        (OUT.column("choice"), "NA", "NA"),
        (OUT.column("unit"), "mg/l", "mg/l"),
    ],
)
def test_canonical_cell(column, text, expected):
    assert canonical_cell(column, text) == expected


@pytest.mark.parametrize(
    ("column", "text", "value"),
    [
        (OUT.column("mean"), "", None),
        (OUT.column("interventions"), "", ()),
        (OUT.column("mean"), "2.5", 2.5),
        (OUT.column("count"), "17", 17),
        (OUT.column("time"), "NR", "NR"),
        (OUT.column("time_unit"), "NR", "NR"),
        (OUT.column("time"), "1.5", 1.5),
        (IV.column("time"), "0;12", (0.0, 12.0)),
        (IV.column("time"), "3", (3.0,)),
        (OUT.column("interventions"), "D1,D2", ("D1", "D2")),
        (OUT.column("subjects"), "Gruppe Ä", "Gruppe Ä"),
        (OUT.column("error_type"), "gsd", "gsd"),
        (SUB.column("source"), "Fig3A", "Fig3A"),
        (SUB.column("source"), "Text", "Text"),
    ],
)
def test_parse_cell_values(column, text, value):
    assert parse_cell(column, text) == (value, None)


@pytest.mark.parametrize(
    ("column", "text", "code"),
    [
        (OUT.column("mean"), "abc", "invalid_number"),
        (OUT.column("count"), "2.5", "invalid_integer"),
        (OUT.column("count"), "-1", "invalid_integer"),
        (OUT.column("time"), "early", "invalid_time"),
        (IV.column("time"), "0;x", "invalid_time"),
        (OUT.column("subjects"), "a;b", "invalid_name"),
        (OUT.column("interventions"), "D1,,D2", "invalid_name"),
        (OUT.column("error_type"), "SD", "invalid_enum"),
        (SUB.column("source"), "Table 2", "invalid_source"),
        (OUT.column("mean"), "NR", "invalid_number"),
    ],
)
def test_parse_cell_problems(column, text, code):
    value, problem = parse_cell(column, text)
    assert value is None
    assert problem is not None and problem.code == code


def test_decimal_comma_hint():
    _, problem = parse_cell(OUT.column("mean"), "2,9")
    assert problem.code == "invalid_number"
    assert "decimal point" in problem.hint
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_cells.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.cells'`

- [ ] **Step 3: Write the implementation**

```python
"""Canonical text and typed values of single TSV cells."""

import re
from dataclasses import dataclass

from pkdb.studyformat.columns import Column, ColumnType
from pkdb.studyformat.tables import SOURCE_PATTERN
from pkdb.studyformat.text import format_number, natural_key, parse_number

NOT_REPORTED = "NR"
NAME_PATTERN = re.compile(r"[^,;\t\r\n]+")
MISSING = frozenset({"NA", "nan", "NaN"})
DECIMAL_COMMA = re.compile(r"[+-]?\d+,\d+")


@dataclass(frozen=True)
class CellProblem:
    code: str
    message: str
    hint: str | None = None


def canonical_cell(column: Column, text: str) -> str:
    """Canonical text of a cell. Values that cannot be parsed stay unchanged."""
    text = text.strip()
    if column.type is not ColumnType.TEXT and text in MISSING:
        return ""
    if not text:
        return ""
    match column.type:
        case ColumnType.NUMBER | ColumnType.INTEGER | ColumnType.TIME:
            value = parse_number(text)
            return text if value is None else format_number(value)
        case ColumnType.TIMES:
            values = [parse_number(part.strip()) for part in text.split(";")]
            if any(value is None for value in values):
                return text
            return ";".join(format_number(value) for value in values if value is not None)
        case ColumnType.NAMES:
            names = [part.strip() for part in text.split(",")]
            if not all(names):
                return text
            return ",".join(sorted(names, key=natural_key))
        case _:
            return text


def _number_problem(text: str) -> CellProblem:
    hint = (
        f"Use a decimal point: {text.replace(',', '.')} instead of {text}."
        if DECIMAL_COMMA.fullmatch(text)
        else None
    )
    return CellProblem("invalid_number", f"Expected a number, found {text!r}", hint)


def parse_cell(column: Column, text: str) -> tuple[object, CellProblem | None]:
    """Typed value of a canonical cell, or None and the problem."""
    if not text:
        return ((), None) if column.type is ColumnType.NAMES else (None, None)
    if column.allows_nr and text == NOT_REPORTED:
        return NOT_REPORTED, None
    match column.type:
        case ColumnType.NUMBER:
            value = parse_number(text)
            return (value, None) if value is not None else (None, _number_problem(text))
        case ColumnType.INTEGER:
            value = parse_number(text)
            if value is None or not value.is_integer() or value < 0:
                return None, CellProblem(
                    "invalid_integer", f"Expected a whole number of at least 0, found {text!r}"
                )
            return int(value), None
        case ColumnType.TIME:
            value = parse_number(text)
            if value is None:
                return None, CellProblem(
                    "invalid_time", f"Expected a number or NR, found {text!r}"
                )
            return value, None
        case ColumnType.TIMES:
            values = [parse_number(part) for part in text.split(";")]
            if any(value is None for value in values):
                return None, CellProblem(
                    "invalid_time",
                    f"Expected a number, a ;-separated list of numbers or NR, found {text!r}",
                )
            return tuple(value for value in values if value is not None), None
        case ColumnType.NAME:
            if not NAME_PATTERN.fullmatch(text):
                return None, CellProblem(
                    "invalid_name", f"Names cannot contain commas or semicolons: {text!r}"
                )
            return text, None
        case ColumnType.NAMES:
            names = tuple(part.strip() for part in text.split(","))
            if not all(NAME_PATTERN.fullmatch(name) for name in names):
                return None, CellProblem(
                    "invalid_name",
                    f"Expected comma-separated names without empty entries, found {text!r}",
                )
            return names, None
        case ColumnType.ENUM:
            if text not in column.choices:
                return None, CellProblem(
                    "invalid_enum",
                    f"Expected one of {', '.join(column.choices)}, found {text!r}",
                )
            return text, None
        case ColumnType.SOURCE:
            if not SOURCE_PATTERN.fullmatch(text):
                return None, CellProblem(
                    "invalid_source",
                    f"Expected Tab or Fig followed by letters or digits (Tab1, Fig2A) or Text, found {text!r}",
                )
            return text, None
        case _:
            return text, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_cells.py -q`
Expected: PASS

- [ ] **Step 5: Lint, format, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat
cd .. && git add python/src/pkdb/studyformat/cells.py python/tests/studyformat/test_studyformat_cells.py
git commit -m "Parse study format 2 cells into canonical text and typed values"
```

---

### Task 4: study.json and review.json models

**Files:**
- Create: `python/src/pkdb/studyformat/jsonio.py`
- Create: `python/src/pkdb/studyformat/models.py`
- Test: `python/tests/studyformat/test_studyformat_models.py`

**Interfaces:**
- Consumes: `pkdb.schemas.provenance.ManualCuration`, `StudyProvenance`.
- Produces: `JsonFileError(ValueError)` with `.code` (`invalid_encoding`, `invalid_json`, `duplicate_key`); `load_json(data: bytes) -> object`; `dump_json(value) -> str` (2-space indent, UTF-8 characters kept, final newline). `TABLE_KINDS`; `StudyReference(pmid, doi)`; `Curator(user, rating)`; `Comment(user, text)`; `Notes(descriptions, comments)`; `Release(pkdb_id, date)`; `StudyMetadata` (fields in spec order: `format, reference, creator, curators, collaborators, licence, access, provenance, issue, release, descriptions, comments, notes`); `canonical_study_json(StudyMetadata) -> str`; `ReviewTarget(file, rows, column)`; `ThreadEntry(author, created, text)`; `ReviewItem(id, kind, state, target, acknowledges, text, author, agent, created, thread, resolved_by, resolved)`; `Review(status, reviewers, items)`; `canonical_review_json(Review) -> str`.

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest
from pydantic import ValidationError

from pkdb.studyformat.jsonio import JsonFileError, dump_json, load_json
from pkdb.studyformat.models import (
    Review,
    StudyMetadata,
    canonical_review_json,
    canonical_study_json,
)

STUDY = {
    "format": 2,
    "reference": {"pmid": "27129716"},
    "creator": "changlinh",
    "curators": [{"user": "changlinh", "rating": 1}],
    "licence": "closed",
    "access": "private",
}
ITEM = {
    "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    "kind": "uncertainty",
    "text": "Legend does not say SD or SE.",
    "author": "mkoenig",
    "created": "2026-10-05T10:12:00Z",
}


def test_load_json_rejects_duplicates_and_nan():
    with pytest.raises(JsonFileError) as duplicate:
        load_json(b'{"a": 1, "a": 2}')
    assert duplicate.value.code == "duplicate_key"
    with pytest.raises(JsonFileError) as nan:
        load_json(b'{"a": NaN}')
    assert nan.value.code == "invalid_json"
    with pytest.raises(JsonFileError) as syntax:
        load_json(b'{"reference":,}')
    assert syntax.value.code == "invalid_json"
    assert "line 1" in str(syntax.value)


def test_dump_json_keeps_unicode_and_ends_with_newline():
    assert dump_json({"name": "Dahlström"}) == '{\n  "name": "Dahlström"\n}\n'


def test_canonical_study_json_order_and_defaults():
    study = StudyMetadata.model_validate(
        {
            **STUDY,
            "release": {"pkdb_id": "PKDB01237", "date": "2026-09-28"},
            "issue": 2158,
            "notes": {"outputs": {"descriptions": []}, "subjects": {"descriptions": ["Q"]}},
            "provenance": {"kind": "manual_curation"},
        }
    )
    text = canonical_study_json(study)
    data = json.loads(text)
    assert list(data) == [
        "format", "reference", "creator", "curators", "licence", "access",
        "issue", "release", "notes",
    ]
    assert data["notes"] == {"subjects": {"descriptions": ["Q"]}}
    assert canonical_study_json(StudyMetadata.model_validate(data)) == text


@pytest.mark.parametrize(
    "change",
    [
        {"format": 1},
        {"reference": {}},
        {"reference": {"pmid": "PMID123"}},
        {"reference": {"doi": "doi:10.1/x"}},
        {"release": {"pkdb_id": "PKDB1237", "date": "2026-09-28"}},
        {"licence": "public"},
        {"groupset": {}},
        {"sid": "PKDB00198"},
        {"creator": ""},
        {"curators": [{"user": "a", "rating": 6}]},
        {"notes": {"groups": {}}},
    ],
)
def test_study_metadata_rejects(change):
    with pytest.raises(ValidationError):
        StudyMetadata.model_validate({**STUDY, **change})


def test_manual_reference_is_absent():
    data = dict(STUDY)
    del data["reference"]
    assert StudyMetadata.model_validate(data).reference is None


def test_canonical_review_json_sorts_items():
    later = {**ITEM, "id": "01JB0000000000000000000000"}
    review = Review.model_validate(
        {"status": "in_review", "items": [later, {**ITEM, "target": {"file": "outputs_Tab2.tsv"}}]}
    )
    data = json.loads(canonical_review_json(review))
    assert [item["id"] for item in data["items"]] == [ITEM["id"], later["id"]]
    assert data["items"][0]["target"] == {"file": "outputs_Tab2.tsv"}
    assert data["items"][0]["state"] == "open"
    assert data["items"][0]["created"] == "2026-10-05T10:12:00Z"
    assert "reviewers" not in data


@pytest.mark.parametrize(
    "change",
    [
        {"id": "not-a-ulid"},
        {"kind": "note"},
        {"state": "resolved"},
        {"resolved_by": "mkoenig", "resolved": "2026-10-06T08:00:00Z"},
        {"created": "2026-10-05T10:12:00"},
        {"target": {"rows": {"label": "x"}}},
        {"text": ""},
    ],
)
def test_review_item_rejects(change):
    with pytest.raises(ValidationError):
        Review.model_validate({"status": "draft", "items": [{**ITEM, **change}]})


def test_resolved_item():
    item = {**ITEM, "state": "resolved", "resolved_by": "mkoenig", "resolved": "2026-10-06T08:00:00Z"}
    assert Review.model_validate({"status": "approved", "items": [item]}).items[0].state == "resolved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_models.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`python/src/pkdb/studyformat/jsonio.py`:

```python
"""Strict JSON reading and canonical JSON writing for study folders."""

import json


class JsonFileError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise JsonFileError("duplicate_key", f"Duplicate key {key!r}")
        result[key] = value
    return result


def _constant(name: str):
    raise JsonFileError("invalid_json", f"{name} is not valid JSON")


def load_json(data: bytes) -> object:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise JsonFileError("invalid_encoding", "File is not UTF-8 encoded") from None
    try:
        return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    except json.JSONDecodeError as error:
        raise JsonFileError(
            "invalid_json",
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}",
        ) from None


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
```

`python/src/pkdb/studyformat/models.py`:

```python
"""study.json and review.json of study format 2."""

from datetime import date as Date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from pkdb.schemas.provenance import ManualCuration, StudyProvenance
from pkdb.studyformat.jsonio import dump_json

TABLE_KINDS = (
    "subjects", "interventions", "characteristica", "outputs", "timecourses", "scatters",
)
TableKind = Literal[
    "subjects", "interventions", "characteristica", "outputs", "timecourses", "scatters"
]
User = Annotated[str, Field(min_length=1, max_length=255, pattern=r"^\S+$")]
Text = Annotated[str, Field(min_length=1)]
Ulid = Annotated[str, Field(pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StudyReference(Model):
    """Identifiers of the publication; the single source for which paper is curated."""

    pmid: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")] | None = None
    doi: Annotated[str, Field(pattern=r"^10\.\d{4,9}/\S+$")] | None = None

    @model_validator(mode="after")
    def identifier(self):
        if self.pmid is None and self.doi is None:
            raise ValueError(
                "Give a pmid or a doi, or remove reference for a manual reference"
            )
        return self


class Curator(Model):
    user: User
    rating: Annotated[float, Field(ge=0, le=5)] = 0


class Comment(Model):
    user: User
    text: Text


class Notes(Model):
    descriptions: list[Text] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)


class Release(Model):
    pkdb_id: Annotated[str, Field(pattern=r"^PKDB[0-9]{5}$")]
    date: Date


class StudyMetadata(Model):
    format: Literal[2]
    reference: StudyReference | None = None
    creator: User
    curators: list[Curator] = Field(default_factory=list)
    collaborators: list[Text] = Field(default_factory=list)
    licence: Literal["open", "closed"]
    access: Literal["public", "private"]
    provenance: StudyProvenance = Field(default_factory=ManualCuration)
    issue: Annotated[int, Field(gt=0)] | None = None
    release: Release | None = None
    descriptions: list[Text] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    notes: dict[TableKind, Notes] = Field(default_factory=dict)


def _without_empty(data: dict, keys: tuple[str, ...]) -> dict:
    return {key: value for key, value in data.items() if key not in keys or value}


def canonical_study_json(study: StudyMetadata) -> str:
    data = study.model_dump(mode="json", exclude_none=True)
    if data["provenance"] == ManualCuration().model_dump(mode="json"):
        del data["provenance"]
    notes = {}
    for kind in TABLE_KINDS:
        if kind in data["notes"]:
            entry = _without_empty(data["notes"][kind], ("descriptions", "comments"))
            if entry:
                notes[kind] = entry
    data["notes"] = notes
    return dump_json(
        _without_empty(
            data, ("curators", "collaborators", "descriptions", "comments", "notes")
        )
    )


class ReviewTarget(Model):
    file: str | None = None
    rows: dict[str, str] = Field(default_factory=dict)
    column: str | None = None

    @model_validator(mode="after")
    def file_required(self):
        if (self.rows or self.column) and self.file is None:
            raise ValueError("rows and column require file")
        return self


class ThreadEntry(Model):
    author: User
    created: AwareDatetime
    text: Text


class ReviewItem(Model):
    id: Ulid
    kind: Literal["question", "uncertainty", "issue"]
    state: Literal["open", "resolved", "dismissed"] = "open"
    target: ReviewTarget | None = None
    acknowledges: str | None = None
    text: Text
    author: User
    agent: str | None = None
    created: AwareDatetime
    thread: list[ThreadEntry] = Field(default_factory=list)
    resolved_by: User | None = None
    resolved: AwareDatetime | None = None

    @model_validator(mode="after")
    def resolution(self):
        closed = self.state != "open"
        if closed != (self.resolved_by is not None) or closed != (
            self.resolved is not None
        ):
            raise ValueError(
                "resolved_by and resolved are set exactly when the state is resolved or dismissed"
            )
        return self


class Review(Model):
    status: Literal["draft", "in_review", "approved"]
    reviewers: list[User] = Field(default_factory=list)
    items: list[ReviewItem] = Field(default_factory=list)


def canonical_review_json(review: Review) -> str:
    data = review.model_dump(mode="json", exclude_none=True)
    items = []
    for item in sorted(data["items"], key=lambda entry: entry["id"]):
        if "target" in item:
            target = _without_empty(item["target"], ("rows",))
            if target:
                item["target"] = target
            else:
                del item["target"]
        items.append(_without_empty(item, ("thread",)))
    data["items"] = items
    return dump_json(_without_empty(data, ("reviewers", "items")))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_models.py -q`
Expected: PASS. If Pydantic serializes the UTC datetime as `2026-10-05T10:12:00+00:00` instead of `...Z`, add `ser_json_timedelta`-independent handling: annotate `created` and `resolved` with `PlainSerializer(lambda v: v.astimezone(UTC).isoformat().replace("+00:00", "Z"), when_used="json")` and keep the test unchanged.

- [ ] **Step 5: Lint, format, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat
cd .. && git add python/src/pkdb/studyformat/jsonio.py python/src/pkdb/studyformat/models.py python/tests/studyformat/test_studyformat_models.py
git commit -m "Model study.json and review.json of study format 2"
```

---
### Task 5: Issue helper and folder layout

**Files:**
- Create: `python/src/pkdb/studyformat/issues.py`
- Create: `python/src/pkdb/studyformat/layout.py`
- Modify: `python/tests/studyformat/conftest.py` (add `make_study`, `tsv`, `valid_files`)
- Test: `python/tests/studyformat/test_studyformat_layout.py`

**Interfaces:**
- Consumes: `TABLES`, `KIND_ORDER`, `JSON_FILES`, `parse_table_file` (Task 1); `natural_key`, `render_tsv` (Task 2); `dump_json` (Task 4); `pkdb.source_files.ignored_source`; `pkdb.schemas.validation.ValidationIssue`, `Suggestion`; `pkdb.schemas.source.SourceLocation`.
- Produces: `WARNINGS`, `CATEGORIES`, `column_letter(index: int) -> str` (0 is `A`), `make_issue(code, message, *, file=None, line=None, column=None, header=None, severity=None, hint=None, candidates=(), **details) -> ValidationIssue` where `column` is the 0-based index of the column in the file header; TSV issues get `sheet` = file name without `.tsv`. `TableFile(name, spec, source)`; `Layout(folder, study, substance, files, tables, attachments, issues)` with `files: frozenset[str]` (every non-ignored file name, including JSON and tables); `scan_folder(folder: Path) -> Layout`.

- [ ] **Step 1: Write the failing test**

Add to `python/tests/studyformat/conftest.py` (merge the new imports into the import block at the top of the file; ruff rejects imports below code):

```python
from pathlib import Path

from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.text import render_tsv


@pytest.fixture
def make_study(tmp_path):
    def make(files, *, name="Example", substance="caffeine") -> Path:
        folder = tmp_path / substance / name
        folder.mkdir(parents=True)
        for file, content in files.items():
            path = folder / file
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8", newline="")
        return folder

    return make


@pytest.fixture
def tsv():
    def render(kind, *rows):
        spec = TABLES[kind]
        return render_tsv(
            spec.names, [tuple(row.get(name, "") for name in spec.names) for row in rows]
        )

    return render


@pytest.fixture
def valid_files(tsv):
    """A complete, valid study before formatting (owned columns still empty)."""
    timecourse = {
        "label": "drug_plasma",
        "subjects": "all",
        "interventions": "D1",
        "measurement": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "time_unit": "h",
        "unit": "mg/l",
    }
    point = {
        "name": "age_vs_cmax",
        "x_measurement": "age",
        "x_unit": "yr",
        "y_interventions": "D1",
        "y_measurement": "cmax",
        "y_substance": "drug",
        "y_tissue": "plasma",
        "y_unit": "mg/l",
    }
    return {
        "study.json": dump_json(
            {
                "format": 2,
                "reference": {"pmid": "123"},
                "creator": "curator",
                "curators": [{"user": "curator", "rating": 3}],
                "licence": "open",
                "access": "private",
            }
        ),
        "reference.json": dump_json(
            {"sid": "123", "name": "Example", "pmid": "123", "title": "Example study"}
        ),
        "review.json": dump_json({"status": "draft"}),
        "subjects.tsv": tsv(
            "subjects",
            {"name": "all", "count": "2", "source": "Tab1"},
            {"name": "S1", "parent": "all", "count": "1", "source": "TabA"},
            {"name": "S2", "parent": "all", "count": "1", "source": "TabA"},
        ),
        "interventions.tsv": tsv(
            "interventions",
            {
                "source": "Text",
                "name": "D1",
                "measurement": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "single dose",
                "time": "0",
                "time_unit": "h",
                "mean": "100",
                "unit": "mg",
            },
        ),
        "characteristica.tsv": tsv(
            "characteristica",
            {"source": "Tab1", "subjects": "all", "measurement": "species", "choice": "Homo sapiens"},
            {"source": "Tab1", "subjects": "all", "measurement": "healthy", "choice": "Y"},
            {"source": "Tab1", "subjects": "all", "measurement": "sex", "choice": "M"},
            {"source": "TabA", "subjects": "S1", "measurement": "age", "mean": "30", "unit": "yr"},
            {"source": "TabA", "subjects": "S2", "measurement": "age", "mean": "40", "unit": "yr"},
        ),
        "outputs_Tab2.tsv": tsv(
            "outputs",
            {
                "subjects": "all",
                "interventions": "D1",
                "measurement": "cmax",
                "substance": "drug",
                "tissue": "plasma",
                "mean": "2.5",
                "sd": "0.5",
                "unit": "mg/l",
            },
        ),
        "timecourses_Fig1.tsv": tsv(
            "timecourses",
            *({**timecourse, "time": t, "mean": m} for t, m in (("0", "0"), ("1", "2"), ("2", "1"))),
        ),
        "scatters_Fig2.tsv": tsv(
            "scatters",
            {**point, "subjects": "S1", "x_mean": "30", "y_mean": "2"},
            {**point, "subjects": "S2", "x_mean": "40", "y_mean": "3"},
        ),
        "Example.pdf": b"%PDF",
        "Example_Tab1.png": b"png",
        "Example_TabA.png": b"png",
        "Example_Tab2.png": b"png",
        "Example_Fig1.png": b"png",
        "Example_Fig2.png": b"png",
    }
```

`python/tests/studyformat/test_studyformat_layout.py`:

```python
from pkdb.studyformat.issues import column_letter, make_issue
from pkdb.studyformat.layout import scan_folder


def codes(issues):
    return sorted((issue.code, issue.source.file if issue.source else None) for issue in issues)


def test_column_letter():
    assert [column_letter(i) for i in (0, 25, 26, 701, 702)] == ["A", "Z", "AA", "ZZ", "AAA"]


def test_make_issue_location_and_defaults():
    issue = make_issue(
        "invalid_number", "Expected a number", file="outputs_Tab2.tsv", line=3, column=13, header="mean"
    )
    assert issue.severity == "error"
    assert issue.category == "schema"
    assert issue.stage == "parse"
    assert issue.source.sheet == "outputs_Tab2"
    assert (issue.source.row, issue.source.column, issue.source.cell) == (3, "N", "N3")
    assert issue.source.header == "mean"
    warning = make_issue("unused_subject", "unused", file="subjects.tsv", line=2)
    assert warning.severity == "warning"
    assert warning.stage == "validate"
    assert make_issue("missing_file", "x", file="study.json").source.sheet is None


def test_make_issue_suggestions():
    issue = make_issue("unknown_column", "x", file="a.tsv", candidates=["measurement"])
    assert issue.suggestions[0].candidates == ["measurement"]


def test_scan_valid_folder(make_study, valid_files):
    folder = make_study({**valid_files, "Example.xlsx": b"wb", "~$Example.xlsx": b"lock"})
    layout = scan_folder(folder)
    assert layout.issues == []
    assert (layout.study, layout.substance) == ("Example", "caffeine")
    assert [table.name for table in layout.tables] == [
        "subjects.tsv",
        "interventions.tsv",
        "characteristica.tsv",
        "outputs_Tab2.tsv",
        "timecourses_Fig1.tsv",
        "scatters_Fig2.tsv",
    ]
    assert layout.attachments == [
        "Example.pdf",
        "Example_Fig1.png",
        "Example_Fig2.png",
        "Example_Tab1.png",
        "Example_Tab2.png",
        "Example_TabA.png",
    ]
    assert "study.json" in layout.files and "Example.xlsx" not in layout.files


def test_scan_reports_unknown_legacy_and_missing_files(make_study):
    folder = make_study(
        {
            "study.json": "{}",
            "groups.tsv": "name\n",
            "outputs.tsv": "a\n",
            "data.csv": "a\n",
            "Other.xlsx": b"x",
            "notes.json": "{}",
            ".Example_Tab1.tsv": "a\n",
            ".gitkeep": "",
            "Example.docx": b"doc",
        }
    )
    (folder / "figures").mkdir()
    (folder / ".pkdb").mkdir()
    layout = scan_folder(folder)
    assert codes(layout.issues) == [
        ("legacy_file", ".Example_Tab1.tsv"),
        ("missing_file", "reference.json"),
        ("missing_file", "review.json"),
        ("missing_file", "subjects.tsv"),
        ("unknown_directory", "figures"),
        ("unknown_file", "Other.xlsx"),
        ("unknown_file", "data.csv"),
        ("unknown_file", "groups.tsv"),
        ("unknown_file", "notes.json"),
        ("unknown_file", "outputs.tsv"),
    ]
    assert layout.attachments == ["Example.docx"]


def test_scan_rejects_symlinks(make_study, valid_files, tmp_path):
    folder = make_study(valid_files)
    (tmp_path / "outside.png").write_bytes(b"png")
    (folder / "Example_Fig9.png").symlink_to(tmp_path / "outside.png")
    assert ("symlink", "Example_Fig9.png") in codes(scan_folder(folder).issues)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_layout.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

`python/src/pkdb/studyformat/issues.py`:

```python
"""Validation issues of study format 2, located by file, sheet, row and column."""

from collections.abc import Iterable

from pkdb.schemas.source import SourceLocation
from pkdb.schemas.validation import Suggestion, ValidationIssue

WARNINGS = frozenset(
    {
        "outside_range",
        "duplicate_observation",
        "unused_intervention",
        "unused_subject",
        "review_target_unmatched",
        "deprecated_measurement",
    }
)
_GROUPS = {
    "layout": (
        "unknown_directory", "symlink", "unknown_file", "legacy_file", "missing_file",
        "missing_image",
    ),
    "format": (
        "invalid_encoding", "missing_header", "unknown_column", "duplicate_column",
        "extra_cells", "invalid_json", "duplicate_key", "not_formatted",
    ),
    "schema": (
        "invalid_study_json", "invalid_review_json", "invalid_reference_json",
        "invalid_number", "invalid_integer", "invalid_time", "invalid_name",
        "invalid_enum", "invalid_source", "missing_required", "invalid_count",
    ),
    "scientific": (
        "missing_value", "choice_statistics", "individual_statistics",
        "unspecified_summary_statistics", "incomplete_error_bar", "error_bar_conflict",
        "reversed_range", "outside_range", "invalid_statistic", "missing_time_unit",
        "invalid_time_unit", "time_dimension", "invalid_unit", "schedule_conflict",
        "invalid_schedule",
    ),
    "reference": (
        "unknown_reference", "duplicate_reference", "duplicate_name", "duplicate_label",
        "missing_root", "root_parent", "missing_parent", "subject_cycle",
        "subject_count_exceeds_parent", "inconsistent_series", "duplicate_time",
        "duplicate_row", "duplicate_observation", "unused_intervention", "unused_subject",
        "reference_mismatch", "public_requires_release",
    ),
    "review": ("approved_with_open_items", "unknown_review_target", "review_target_unmatched"),
    "vocabulary": (
        "unknown_measurement", "unknown_substance", "unknown_tissue", "unknown_method",
        "unknown_route", "unknown_form", "unknown_application", "unknown_calculation",
        "retired_calculation", "invalid_choice", "missing_choice", "negative_value",
        "deprecated_measurement", "missing_time", "missing_unit", "missing_dosing_field",
    ),
}
CATEGORIES = {code: category for category, codes in _GROUPS.items() for code in codes}
_PARSE = frozenset({"layout", "format", "schema"})


def column_letter(index: int) -> str:
    """Spreadsheet letter of a 0-based column index: 0 is A, 26 is AA."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def make_issue(
    code: str,
    message: str,
    *,
    file: str | None = None,
    line: int | None = None,
    column: int | None = None,
    header: str | None = None,
    severity: str | None = None,
    hint: str | None = None,
    candidates: Iterable[str] = (),
    **details,
) -> ValidationIssue:
    source = None
    if file is not None:
        letter = column_letter(column) if column is not None else None
        source = SourceLocation(
            file=file,
            sheet=file.removesuffix(".tsv") if file.endswith(".tsv") else None,
            row=line,
            column=letter,
            cell=f"{letter}{line}" if letter and line else None,
            header=header,
        )
    candidates = list(candidates)
    suggestions = (
        [Suggestion(kind="fix", message=hint or "Did you mean one of these?", candidates=candidates)]
        if hint or candidates
        else []
    )
    category = CATEGORIES.get(code)
    return ValidationIssue(
        code=code,
        severity=severity or ("warning" if code in WARNINGS else "error"),
        message=message,
        source=source,
        category=category,
        stage="parse" if category in _PARSE else "validate",
        suggestions=suggestions,
        **details,
    )
```

`python/src/pkdb/studyformat/layout.py`:

```python
"""Classify the files of a study format 2 folder."""

from dataclasses import dataclass, field
from pathlib import Path

from pkdb.schemas.validation import ValidationIssue
from pkdb.source_files import ignored_source
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.tables import (
    JSON_FILES,
    KIND_ORDER,
    REFERENCE_JSON,
    REVIEW_JSON,
    STUDY_JSON,
    TableSpec,
    parse_table_file,
)
from pkdb.studyformat.text import natural_key

DATA_SUFFIXES = frozenset({".tsv", ".json", ".csv", ".xls", ".xlsx"})
REQUIRED_FILES = (STUDY_JSON, REFERENCE_JSON, REVIEW_JSON, "subjects.tsv")
TABLE_NAMES = (
    "Table files are subjects.tsv, interventions.tsv, characteristica.tsv or "
    "<kind>_<source>.tsv with kind outputs, timecourses or scatters and a source "
    "such as Tab1, Fig2A or Text."
)


@dataclass(frozen=True)
class TableFile:
    name: str
    spec: TableSpec
    source: str | None


@dataclass
class Layout:
    folder: Path
    study: str
    substance: str
    files: frozenset[str]
    tables: list[TableFile] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def scan_folder(folder: Path) -> Layout:
    folder = Path(folder)
    study = folder.name
    files, tables, attachments, issues = set(), [], [], []
    for path in sorted(folder.iterdir(), key=lambda item: natural_key(item.name)):
        name = path.name
        if path.is_symlink():
            issues.append(make_issue("symlink", "Symbolic links are not accepted", file=name))
            continue
        if path.is_dir():
            if not name.startswith("."):
                issues.append(
                    make_issue(
                        "unknown_directory",
                        f"Unexpected folder {name!r}; a study folder contains files only",
                        file=name,
                    )
                )
            continue
        if ignored_source(Path(name)) or name == f"{study}.xlsx":
            continue
        files.add(name)
        if name in JSON_FILES:
            continue
        if (table := parse_table_file(name)) is not None:
            tables.append(TableFile(name, *table))
            continue
        suffix = path.suffix.lower()
        if name.startswith("."):
            if suffix == ".tsv":
                issues.append(
                    make_issue(
                        "legacy_file",
                        f"{name} is a hidden table of study format 1; remove it",
                        file=name,
                    )
                )
            continue
        if suffix in DATA_SUFFIXES:
            hint = TABLE_NAMES if suffix == ".tsv" else (
                f"Only {study}.xlsx, the generated workbook, is allowed"
                if suffix in {".xls", ".xlsx"}
                else None
            )
            issues.append(
                make_issue("unknown_file", f"Unknown data file {name!r}", file=name, hint=hint)
            )
            continue
        attachments.append(name)
    for required in REQUIRED_FILES:
        if required not in files:
            issues.append(make_issue("missing_file", f"{required} is required", file=required))
    tables.sort(key=lambda table: (KIND_ORDER[table.spec.kind], natural_key(table.source or "")))
    return Layout(folder, study, folder.parent.name, frozenset(files), tables, attachments, issues)
```

Note: the expected order in `test_scan_reports_unknown_legacy_and_missing_files` comes from sorting `(code, file)`, not from scan order.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_layout.py -q`
Expected: PASS

- [ ] **Step 5: Lint, format, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat
cd .. && git add python/src/pkdb/studyformat/issues.py python/src/pkdb/studyformat/layout.py python/tests/studyformat
git commit -m "Classify study format 2 folder files and locate issues"
```

---

### Task 6: Load a study folder

**Files:**
- Create: `python/src/pkdb/studyformat/load.py`
- Test: `python/tests/studyformat/test_studyformat_load.py`

**Interfaces:**
- Consumes: Tasks 1 to 5; `pkdb.schemas.study.Reference` for `reference.json`.
- Produces: `LEGACY_COLUMNS: dict[str, str]`; `STRUCTURAL: frozenset[str]` (codes that stop a file from loading or formatting); `Row(line: int, cells: dict[str, str], values: dict[str, object])` (cells are canonical text for every template column; rows whose non-owned cells are all empty are skipped); `LoadedTable(file, spec, source, header, rows)` with `.kind` and `.column_index(name) -> int | None` (index in the file's own header, for locations); `LoadedStudy(layout, tables, broken, metadata, review, reference, issues)` with `.folder`, `.name`, `.table(file) -> LoadedTable | None`, `.of_kind(kind) -> list[LoadedTable]`, `.rows(kind) -> Iterator[tuple[LoadedTable, Row]]`; `load_table(file, data, spec, source) -> tuple[LoadedTable | None, list[ValidationIssue]]`; `load_study(folder) -> LoadedStudy`.

- [ ] **Step 1: Write the failing test**

```python
from pkdb.studyformat.load import load_study, load_table
from pkdb.studyformat.tables import TABLES

OUT = TABLES["outputs"]


def codes(issues):
    return [issue.code for issue in issues]


def test_load_valid_study(make_study, valid_files):
    study = load_study(make_study(valid_files))
    assert study.issues == []
    assert study.name == "Example"
    assert [table.file for table in study.tables][:2] == ["subjects.tsv", "interventions.tsv"]
    outputs = study.of_kind("outputs")[0]
    assert outputs.source == "Tab2"
    row = outputs.rows[0]
    assert row.line == 2
    assert row.values["mean"] == 2.5
    assert row.values["interventions"] == ("D1",)
    assert row.cells["sd"] == "0.5"
    assert study.table("interventions.tsv").rows[0].values["time"] == (0.0,)
    assert study.metadata.creator == "curator"
    assert study.review.status == "draft"
    assert study.reference["pmid"] == "123"
    assert [row.cells["name"] for _, row in study.rows("subjects")] == ["all", "S1", "S2"]


def test_legacy_column_names_suggest_replacements():
    data = b"measurement_type\tgroup\tvalue\tmean_pm\nauc\tall\t1\t2\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1")
    assert table is None
    found = {issue.source.header: issue.suggestions[0].candidates for issue in issues}
    assert found == {
        "measurement_type": ["measurement"],
        "group": ["subjects"],
        "value": ["mean"],
        "mean_pm": ["error_bar"],
    }
    assert {issue.code for issue in issues} == {"unknown_column"}


def test_unknown_column_close_match():
    table, issues = load_table("outputs_Tab1.tsv", b"subject\tmeasurment\n", OUT, "Tab1")
    assert table is None
    assert [issue.suggestions[0].candidates for issue in issues] == [["subjects"], ["measurement"]]


def test_structural_problems():
    _, duplicate = load_table("outputs_Tab1.tsv", b"mean\tmean\n1\t2\n", OUT, "Tab1")
    assert codes(duplicate) == ["duplicate_column"]
    _, extra = load_table("outputs_Tab1.tsv", b"subjects\tmean\nall\t1\tx\n", OUT, "Tab1")
    assert codes(extra) == ["extra_cells"]
    assert (extra[0].source.row, extra[0].source.column) == (2, "C")
    _, empty = load_table("outputs_Tab1.tsv", b"", OUT, "Tab1")
    assert codes(empty) == ["missing_header"]
    _, latin = load_table("outputs_Tab1.tsv", "subjects\nä".encode("latin-1"), OUT, "Tab1")
    assert codes(latin) == ["invalid_encoding"]


def test_trailing_empty_columns_and_reordered_columns_load():
    data = b"mean\tsubjects\t\t\n2.50\tall\t\t\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1")
    assert issues == []
    assert table.rows[0].cells["mean"] == "2.5"
    assert table.rows[0].cells["measurement"] == ""
    assert table.column_index("subjects") == 1
    assert table.column_index("measurement") is None


def test_cell_problems_keep_the_table():
    data = b"subjects\tmean\tcount\nall\t2,5\t1.5\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1")
    assert table is not None and table.rows[0].values["mean"] is None
    # Issues follow the template column order, where count precedes mean.
    assert [(i.code, i.source.cell, i.source.header) for i in issues] == [
        ("invalid_integer", "C2", "count"),
        ("invalid_number", "B2", "mean"),
    ]


def test_owned_cells_are_not_judged_and_blank_rows_are_skipped():
    data = b"study\tsource\tsubjects\nOther\tweird source\tall\nExample\tTab1\t\n"
    table, issues = load_table("outputs_Tab1.tsv", data, OUT, "Tab1")
    assert issues == []
    assert [row.line for row in table.rows] == [2]


def test_broken_files_are_reported(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "study.json": '{"format": 2, "creator": "x", "licence": "open"}',
            "review.json": "{",
            "reference.json": '{"pmid": "123"}',
            "outputs_Tab2.tsv": "group\nall\n",
        }
    )
    study = load_study(folder)
    assert study.metadata is None and study.review is None
    assert "outputs" in study.broken
    assert study.of_kind("outputs") == []
    found = sorted({(issue.code, issue.source.file) for issue in study.issues})
    assert found == [
        ("invalid_json", "review.json"),
        ("invalid_reference_json", "reference.json"),
        ("invalid_study_json", "study.json"),
        ("unknown_column", "outputs_Tab2.tsv"),
    ]
    study_issue = next(i for i in study.issues if i.code == "invalid_study_json")
    assert study_issue.field == "access"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_load.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
"""Read a study format 2 folder into typed tables without judging the content."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

from pydantic import BaseModel, ValidationError

from pkdb.schemas.study import Reference
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.cells import canonical_cell, parse_cell
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import Layout, scan_folder
from pkdb.studyformat.models import Review, StudyMetadata
from pkdb.studyformat.tables import REFERENCE_JSON, REVIEW_JSON, STUDY_JSON, TableSpec
from pkdb.studyformat.text import TsvError, parse_tsv

# Column names of study format 1 sheets and their format 2 replacement.
LEGACY_COLUMNS = {
    "measurement_type": "measurement",
    "calculation_type": "calculation",
    "group": "subjects",
    "individual": "subjects",
    "subject": "subjects",
    "intervention": "interventions",
    "value": "mean",
    "group_count": "count",
    "n": "count",
    "mean_pm": "error_bar",
    "figure": "source",
    "image": "source",
    "x_measurement_type": "x_measurement",
    "y_measurement_type": "y_measurement",
    "x_value": "x_mean",
    "y_value": "y_mean",
}
STRUCTURAL = frozenset(
    {
        "invalid_encoding", "missing_header", "unknown_column", "duplicate_column",
        "extra_cells", "invalid_json", "duplicate_key", "invalid_study_json",
        "invalid_review_json", "invalid_reference_json",
    }
)


@dataclass(frozen=True)
class Row:
    line: int
    cells: dict[str, str]
    values: dict[str, object]


@dataclass
class LoadedTable:
    file: str
    spec: TableSpec
    source: str | None
    header: tuple[str, ...]
    rows: list[Row]

    @property
    def kind(self) -> str:
        return self.spec.kind

    def column_index(self, name: str) -> int | None:
        return self.header.index(name) if name in self.header else None


@dataclass
class LoadedStudy:
    layout: Layout
    tables: list[LoadedTable] = field(default_factory=list)
    broken: set[str] = field(default_factory=set)
    metadata: StudyMetadata | None = None
    review: Review | None = None
    reference: dict | None = None
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def folder(self) -> Path:
        return self.layout.folder

    @property
    def name(self) -> str:
        return self.layout.study

    def table(self, file: str) -> LoadedTable | None:
        return next((table for table in self.tables if table.file == file), None)

    def of_kind(self, kind: str) -> list[LoadedTable]:
        return [table for table in self.tables if table.kind == kind]

    def rows(self, kind: str) -> Iterator[tuple[LoadedTable, Row]]:
        for table in self.of_kind(kind):
            for row in table.rows:
                yield table, row


def _candidates(name: str, spec: TableSpec) -> list[str]:
    replacement = LEGACY_COLUMNS.get(name)
    if replacement in spec.names:
        return [replacement]
    return get_close_matches(name, spec.names, n=3, cutoff=0.6)


def load_table(
    file: str, data: bytes, spec: TableSpec, source: str | None
) -> tuple[LoadedTable | None, list[ValidationIssue]]:
    try:
        parsed = parse_tsv(data)
    except TsvError as error:
        return None, [make_issue("invalid_encoding", str(error), file=file)]
    if not any(parsed.header):
        return None, [
            make_issue(
                "missing_header", "The first line must contain the column names", file=file, line=1
            )
        ]
    issues = []
    positions: dict[str, int] = {}
    width = len(parsed.header)
    for index, name in enumerate(parsed.header):
        if name in spec.names:
            if name in positions:
                issues.append(
                    make_issue(
                        "duplicate_column",
                        f"Column {name!r} appears twice",
                        file=file, line=1, column=index, header=name,
                    )
                )
            else:
                positions[name] = index
        elif name == "" and not any(
            index < len(line.cells) and line.cells[index] for line in parsed.lines
        ):
            continue
        else:
            issues.append(
                make_issue(
                    "unknown_column",
                    f"{file} has an unknown column {name!r}",
                    file=file, line=1, column=index, header=name,
                    candidates=_candidates(name, spec),
                )
            )
    for line in parsed.lines:
        extra = [index for index in range(width, len(line.cells)) if line.cells[index]]
        if extra:
            issues.append(
                make_issue(
                    "extra_cells",
                    f"Row has values beyond the {width} header columns",
                    file=file, line=line.number, column=extra[0],
                )
            )
    if issues:
        return None, issues
    rows = []
    for line in parsed.lines:
        cells, values = {}, {}
        for column in spec.columns:
            index = positions.get(column.name)
            raw = line.cells[index] if index is not None and index < len(line.cells) else ""
            text = canonical_cell(column, raw)
            value, problem = parse_cell(column, text)
            cells[column.name], values[column.name] = text, value
            if problem and not column.owned:
                issues.append(
                    make_issue(
                        problem.code,
                        problem.message,
                        file=file, line=line.number, column=index, header=column.name,
                        hint=problem.hint, actual=text,
                    )
                )
        if any(cells[column.name] for column in spec.columns if not column.owned):
            rows.append(Row(line.number, cells, values))
    return LoadedTable(file, spec, source, parsed.header, rows), issues


def _read_json(study: LoadedStudy, name: str) -> object | None:
    path = study.folder / name
    if not path.is_file():
        return None
    try:
        return load_json(path.read_bytes())
    except JsonFileError as error:
        study.issues.append(make_issue(error.code, str(error), file=name))
        return None


def _validate[M: BaseModel](
    study: LoadedStudy, name: str, model: type[M], code: str
) -> M | None:
    data = _read_json(study, name)
    if data is None:
        return None
    try:
        return model.model_validate(data)
    except ValidationError as error:
        for detail in error.errors(include_url=False):
            path = ".".join(str(part) for part in detail["loc"])
            study.issues.append(
                make_issue(
                    code,
                    f"{path or name}: {detail['msg']}",
                    file=name,
                    field=path or None,
                )
            )
        return None


def load_study(folder: Path) -> LoadedStudy:
    study = LoadedStudy(layout=(layout := scan_folder(Path(folder))))
    study.issues.extend(layout.issues)
    for table_file in layout.tables:
        table, issues = load_table(
            table_file.name,
            (layout.folder / table_file.name).read_bytes(),
            table_file.spec,
            table_file.source,
        )
        study.issues.extend(issues)
        if table is None:
            study.broken.add(table_file.spec.kind)
        else:
            study.tables.append(table)
    study.metadata = _validate(study, STUDY_JSON, StudyMetadata, "invalid_study_json")
    study.review = _validate(study, REVIEW_JSON, Review, "invalid_review_json")
    if _validate(study, REFERENCE_JSON, Reference, "invalid_reference_json") is not None:
        reference = _read_json(study, REFERENCE_JSON)
        study.reference = reference if isinstance(reference, dict) else None
    return study
```

Note: `_validate` with a type parameter uses PEP 695 syntax (Python 3.12+). `reference.json` is re-read after validation to keep its original key order for formatting; the second read cannot fail because the first succeeded.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_load.py -q`
Expected: PASS

- [ ] **Step 5: Lint, format, type check, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat && uv run --locked ty check
cd .. && git add python/src/pkdb/studyformat/load.py python/tests/studyformat/test_studyformat_load.py
git commit -m "Load study format 2 folders into typed tables"
```

---

### Task 7: Formatter

**Files:**
- Modify: `python/src/pkdb/cache.py` (add `atomic_text`, make `atomic_json` use it)
- Create: `python/src/pkdb/studyformat/formatter.py`
- Modify: `python/src/pkdb/studyformat/__init__.py` (export `format_folder`)
- Modify: `python/tests/studyformat/conftest.py` (add `valid_study`)
- Test: `python/tests/studyformat/test_studyformat_formatter.py`, `python/tests/test_cache.py` (one test)

**Interfaces:**
- Consumes: `load_study`, `LoadedStudy`, `LoadedTable`, `STRUCTURAL` (Task 6); `canonical_study_json`, `canonical_review_json`, `dump_json` (Task 4); `render_tsv`, `natural_key`, `parse_number` (Task 2); `ROOT` (Task 1).
- Produces: `atomic_text(path: Path, text: str) -> None` in `pkdb.cache` (writes LF line endings on every platform); `FileChange(file, action)` with action `"write"` or `"delete"`; `FormatResult(folder, changes, issues)` with `.ok`; `subject_order(table: LoadedTable | None) -> dict[str, int]`; `render_table(table, study_name, order) -> str | None` (None means the optional table has no rows and is removed); `planned_files(study: LoadedStudy) -> dict[str, str | None]`; `format_folder(folder, *, check=False) -> FormatResult`.

- [ ] **Step 1: Write the failing test**

Append to `python/tests/studyformat/conftest.py`:

```python
@pytest.fixture
def valid_study(make_study, valid_files):
    from pkdb.studyformat.formatter import format_folder

    folder = make_study(valid_files)
    assert format_folder(folder).ok
    return folder
```

Append to `python/tests/test_cache.py`:

```python
def test_atomic_text_writes_lf(tmp_path):
    from pkdb.cache import atomic_text

    target = tmp_path / "a" / "table.tsv"
    atomic_text(target, "x\ty\n1\t2\n")
    assert target.read_bytes() == b"x\ty\n1\t2\n"
```

`python/tests/studyformat/test_studyformat_formatter.py`:

```python
import json

from pkdb.studyformat.formatter import format_folder, subject_order
from pkdb.studyformat.load import load_table
from pkdb.studyformat.tables import TABLES


def read(folder, name):
    return (folder / name).read_text(encoding="utf-8")


def test_valid_study_is_stable(valid_study):
    assert format_folder(valid_study).changes == []


def test_owned_columns_are_filled(valid_study):
    lines = read(valid_study, "outputs_Tab2.tsv").splitlines()
    assert lines[1].startswith("Example\tTab2\tall\tD1\tcmax")
    assert read(valid_study, "subjects.tsv").splitlines()[1].startswith("Example\tall\t")


def test_messy_spreadsheet_export_is_normalized(make_study, valid_files):
    # Review focus 1: CRLF, BOM, quoted cells, dropped trailing tabs, NBSP, NA,
    # reordered and missing columns, wrong owned values, unsorted rows.
    messy = (
        "\ufeffmean\tsubjects\tstudy\tinterventions\tmeasurement\tunit\r\n"
        "2.50\tS2\tWrong\t\"D1\"\tcmax\tmg/l\r\n"
        "\u00a03.0\tall\t\tD1\tcmax\tmg/l\r\n"
        "NA\tS1\t\tD1\tcmax\r\n"
        "\t\t\t\t\t\r\n"
    )
    folder = make_study({**valid_files, "outputs_Tab2.tsv": messy})
    result = format_folder(folder)
    assert result.ok
    lines = read(folder, "outputs_Tab2.tsv").splitlines()
    assert lines[0].split("\t") == list(TABLES["outputs"].names)
    rows = [line.split("\t") for line in lines[1:]]
    names = TABLES["outputs"].names
    assert [row[names.index("subjects")] for row in rows] == ["all", "S1", "S2"]
    assert [row[names.index("mean")] for row in rows] == ["3", "", "2.5"]
    assert {row[names.index("study")] for row in rows} == {"Example"}
    assert {row[names.index("source")] for row in rows} == {"Tab2"}
    assert b"\r" not in (folder / "outputs_Tab2.tsv").read_bytes()
    assert format_folder(folder).changes == []


def test_check_mode_writes_nothing(make_study, valid_files):
    folder = make_study(valid_files)
    before = read(folder, "subjects.tsv")
    result = format_folder(folder, check=True)
    assert {change.file for change in result.changes} >= {"subjects.tsv", "study.json"}
    assert read(folder, "subjects.tsv") == before


def test_empty_optional_tables_are_removed(make_study, valid_files, tsv):
    folder = make_study(
        {**valid_files, "outputs_Tab9.tsv": tsv("outputs"), "characteristica.tsv": tsv("characteristica")}
    )
    result = format_folder(folder)
    assert {(c.file, c.action) for c in result.changes} >= {
        ("outputs_Tab9.tsv", "delete"),
        ("characteristica.tsv", "delete"),
    }
    assert not (folder / "outputs_Tab9.tsv").exists()


def test_empty_subjects_table_keeps_its_header(make_study, valid_files, tsv):
    folder = make_study({**valid_files, "subjects.tsv": tsv("subjects")})
    format_folder(folder)
    assert read(folder, "subjects.tsv") == "\t".join(TABLES["subjects"].names) + "\n"


def test_unformattable_file_is_left_unchanged(make_study, valid_files):
    folder = make_study({**valid_files, "outputs_Tab2.tsv": "group\tmean\nall\t1\n"})
    result = format_folder(folder)
    assert not result.ok
    assert [issue.code for issue in result.issues] == ["unknown_column"]
    assert read(folder, "outputs_Tab2.tsv") == "group\tmean\nall\t1\n"
    assert "outputs_Tab2.tsv" not in {change.file for change in result.changes}


def test_json_files_are_canonical(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "reference.json": json.dumps({"sid": "123", "name": "Example", "pmid": "123"}, indent=4),
            "review.json": '{"status": "draft", "reviewers": []}',
        }
    )
    format_folder(folder)
    assert read(folder, "reference.json") == (
        '{\n  "sid": "123",\n  "name": "Example",\n  "pmid": "123"\n}\n'
    )
    assert read(folder, "review.json") == '{\n  "status": "draft"\n}\n'
    assert json.loads(read(folder, "study.json"))["curators"] == [{"user": "curator", "rating": 3.0}]


def test_invalid_json_is_not_touched(make_study, valid_files):
    folder = make_study({**valid_files, "study.json": '{"reference":,}'})
    result = format_folder(folder)
    assert [issue.code for issue in result.issues] == ["invalid_json"]
    assert read(folder, "study.json") == '{"reference":,}'


def test_subject_order_is_depth_first_with_all_first():
    data = (
        "name\tparent\n"
        "b2\tb\nS10\ta\nb\tall\na\tall\nS2\ta\nall\t\norphan\tmissing\nx\ty\ny\tx\n"
    ).encode()
    table, _ = load_table("subjects.tsv", data, TABLES["subjects"], None)
    order = subject_order(table)
    assert sorted(order, key=order.get) == [
        "all", "a", "S2", "S10", "b", "b2", "orphan", "x", "y",
    ]


def test_timecourse_points_sort_by_label_then_numeric_time(make_study, valid_files, tsv):
    base = {"subjects": "all", "measurement": "concentration", "time_unit": "h"}
    rows = [
        {**base, "label": "b", "time": "1"},
        {**base, "label": "a", "time": "10"},
        {**base, "label": "a", "time": "2"},
        {**base, "label": "a", "time": "NR"},
    ]
    folder = make_study({**valid_files, "timecourses_Fig1.tsv": tsv("timecourses", *rows)})
    format_folder(folder)
    names = TABLES["timecourses"].names
    body = [line.split("\t") for line in read(folder, "timecourses_Fig1.tsv").splitlines()[1:]]
    assert [(r[names.index("label")], r[names.index("time")]) for r in body] == [
        ("a", "2"), ("a", "10"), ("a", "NR"), ("b", "1"),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_formatter.py tests/test_cache.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.formatter'` and `ImportError: cannot import name 'atomic_text'`

- [ ] **Step 3: Write the implementation**

In `python/src/pkdb/cache.py`, replace `atomic_json` with:

```python
def atomic_text(path: Path, text: str) -> None:
    """Replace a file atomically; line endings are written as LF on every platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_json(path: Path, value: dict) -> None:
    atomic_text(
        path, json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    )
```

`python/src/pkdb/studyformat/formatter.py`:

```python
"""Canonical form of study format 2 folders."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pkdb.cache import atomic_text
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.columns import Column, ColumnType
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.load import STRUCTURAL, LoadedStudy, LoadedTable, load_study
from pkdb.studyformat.models import canonical_review_json, canonical_study_json
from pkdb.studyformat.tables import REFERENCE_JSON, REVIEW_JSON, ROOT, STUDY_JSON, TableSpec
from pkdb.studyformat.text import natural_key, parse_number, render_tsv


@dataclass(frozen=True)
class FileChange:
    file: str
    action: Literal["write", "delete"]


@dataclass
class FormatResult:
    folder: Path
    changes: list[FileChange] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def subject_order(table: LoadedTable | None) -> dict[str, int]:
    """Depth-first order of the subject tree: `all` first, children by name."""
    if table is None:
        return {}
    parents: dict[str, str] = {}
    for row in table.rows:
        name = row.cells["name"]
        if name and name not in parents:
            parents[name] = row.cells["parent"]
    children: dict[str, list[str]] = defaultdict(list)
    roots = []
    for name, parent in parents.items():
        if parent and parent in parents and parent != name:
            children[parent].append(name)
        else:
            roots.append(name)
    order: dict[str, int] = {}
    stack = sorted(roots, key=lambda name: (name != ROOT, natural_key(name)), reverse=True)
    while stack:
        name = stack.pop()
        if name in order:
            continue
        order[name] = len(order)
        stack.extend(sorted(children[name], key=natural_key, reverse=True))
    for name in sorted(parents, key=natural_key):
        order.setdefault(name, len(order))
    return order


def _cell_key(column: Column, text: str, order: dict[str, int]) -> tuple:
    if not text:
        return (0,)
    if column.references == "subjects" and column.type is ColumnType.NAME:
        return (1, order.get(text, len(order)), natural_key(text))
    if column.type is ColumnType.TIME:
        value = parse_number(text)
        return (1, value, ()) if value is not None else (2, 0.0, natural_key(text))
    return (1, natural_key(text))


def _row_key(spec: TableSpec, cells: tuple[str, ...], order: dict[str, int]) -> tuple:
    by_name = dict(zip(spec.names, cells, strict=True))
    if spec.kind == "subjects":
        name = by_name["name"]
        keys: tuple = ((order.get(name, len(order)), natural_key(name)),)
    else:
        keys = tuple(
            _cell_key(spec.column(name), by_name[name], order) for name in spec.sort_columns
        )
    return (*keys, "\t".join(cells))


def render_table(table: LoadedTable, study_name: str, order: dict[str, int]) -> str | None:
    spec = table.spec
    rows = []
    for row in table.rows:
        cells = dict(row.cells)
        cells["study"] = study_name
        if spec.per_source:
            cells["source"] = table.source or ""
        rows.append(tuple(cells[name] for name in spec.names))
    if not rows and not spec.required:
        return None
    rows.sort(key=lambda cells: _row_key(spec, cells, order))
    return render_tsv(spec.names, rows)


def planned_files(study: LoadedStudy) -> dict[str, str | None]:
    """Canonical content of every loadable file; None removes an empty table."""
    subjects = study.of_kind("subjects")
    order = subject_order(subjects[0] if subjects else None)
    plan: dict[str, str | None] = {
        table.file: render_table(table, study.name, order) for table in study.tables
    }
    if study.metadata is not None:
        plan[STUDY_JSON] = canonical_study_json(study.metadata)
    if study.review is not None:
        plan[REVIEW_JSON] = canonical_review_json(study.review)
    if study.reference is not None:
        plan[REFERENCE_JSON] = dump_json(study.reference)
    return plan


def format_folder(folder: Path, *, check: bool = False) -> FormatResult:
    folder = Path(folder)
    study = load_study(folder)
    result = FormatResult(
        folder, issues=[issue for issue in study.issues if issue.code in STRUCTURAL]
    )
    for name, text in planned_files(study).items():
        path = folder / name
        if text is None:
            result.changes.append(FileChange(name, "delete"))
            if not check:
                path.unlink()
        elif path.read_bytes() != text.encode("utf-8"):
            result.changes.append(FileChange(name, "write"))
            if not check:
                atomic_text(path, text)
    return result
```

Replace `python/src/pkdb/studyformat/__init__.py` with:

```python
"""Study format 2: fixed table templates committed as canonical TSV files."""

from pkdb.studyformat.formatter import format_folder

FORMAT_VERSION = 2

__all__ = ["FORMAT_VERSION", "format_folder"]
```

No submodule may import names from the package `pkdb.studyformat` itself; they import from the submodules, which keeps the package import free of cycles.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd python && uv run --locked pytest tests/studyformat tests/test_cache.py -q`
Expected: PASS

- [ ] **Step 5: Run the whole suite, lint, type check, commit**

```bash
cd python && uv run --locked pytest -q && uv run --locked ruff format . && uv run --locked ruff check . && uv run --locked ty check
cd .. && git add python/src/pkdb/cache.py python/src/pkdb/studyformat python/tests
git commit -m "Write study format 2 folders in canonical form"
```

---
### Task 8: Row rules (layer 3)

**Files:**
- Modify: `python/src/pkdb/studyformat/issues.py` (add `row_issue`)
- Create: `python/src/pkdb/studyformat/rows.py`
- Test: `python/tests/studyformat/test_studyformat_rows.py`

**Interfaces:**
- Consumes: `LoadedStudy`, `LoadedTable`, `Row`, `load_study` (Task 6); `NOT_REPORTED` (Task 3); `pkdb.domain.units.ureg`.
- Produces: `row_issue(table, row, code, message, column=None, **details) -> ValidationIssue` in `issues.py` (locates the issue at the row's line and, when `column` is given, at that column of the file header); `time_unit_status(unit) -> str` and `unit_known(unit) -> bool` (both cached, because pint parsing dominates the run time of large tables); `subject_counts(study) -> dict[str, int | None]`; `check_rows(study: LoadedStudy) -> list[ValidationIssue]`.

Rules (spec 5.5):

| Code | Condition | Column |
|---|---|---|
| `missing_required` | a column in `spec.required_columns` is empty | that column |
| `invalid_count` | subject `count` below 1 | `count` |
| `missing_value` | observation row (characteristica, interventions, outputs, timecourses) without `choice`, `mean`, `gmean`, `median`, `min` or `max` | none |
| `choice_statistics` | `choice` set and any of `mean, sd, se, cv, gmean, gsd, gcv, median, min, max, error_bar` set | each such column |
| `individual_statistics` | effective count is 1 (row `count`, else the subject's count) and any of `sd, se, cv, gmean, gsd, gcv, median, min, max` set | each such column |
| `unspecified_summary_statistics` | `calculation` is `unspecified summary` and any of `sd, se, cv, gmean, gsd, gcv, median, min, max, error_bar` set | each such column |
| `incomplete_error_bar` | exactly one of the `error_bar` and `error_type` cells is filled; or type `sd`/`se` without `mean`, `gsd` without `gmean` | the missing column |
| `error_bar_conflict` | the column named by `error_type` is also reported | that column |
| `reversed_range` | `min > max` | `min` |
| `outside_range` (warning) | `mean` or `median` outside `[min, max]` | that column |
| `invalid_statistic` | `sd`, `se`, `cv`, `gcv` negative; `gsd < 1`; `gmean <= 0` | that column |
| `invalid_time` | `time` is `NR` in a timecourse | `time` |
| `missing_time_unit` | a numeric time column (`time`, interventions `time_end`, `interval`; scatter `x_time`, `y_time`) without its unit | the unit column |
| `time_dimension` | time unit parses but is not a time | the unit column |
| `invalid_time_unit` | time unit does not parse | the unit column |
| `invalid_unit` | `unit`, `x_unit`, `y_unit` with characters outside `[\/^_*.() µα-ωΑ-Ωa-zA-Z0-9]` or not parsed by pint | that column |
| `schedule_conflict` | `;`-separated `time` list together with `interval` or `doses` | that column |
| `invalid_schedule` | `interval <= 0`; `interval` without `doses`; `doses < 1`; `doses > 1` without `interval`; `time_end` before `time` | the offending column |

- [ ] **Step 1: Write the failing test**

```python
import pytest

from pkdb.studyformat.load import load_study
from pkdb.studyformat.rows import check_rows

CMAX = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "cmax",
    "substance": "drug",
    "tissue": "plasma",
    "unit": "mg/l",
}


@pytest.fixture
def run(make_study, valid_files, tsv):
    def check(kind=None, *rows, file=None, **files):
        if kind is not None:
            files[file or f"{kind}.tsv"] = tsv(kind, *rows)
        study = load_study(make_study({**valid_files, **files}))
        return {(issue.code, issue.source.header) for issue in check_rows(study)}

    return check


def test_valid_study_passes(run):
    assert run() == set()


def test_required_and_missing_value(run):
    found = run("outputs", {"subjects": "all", "comment": "x"}, file="outputs_Tab2.tsv")
    assert found == {("missing_required", "measurement"), ("missing_value", None)}


def test_subject_count(run, tsv):
    found = run("subjects", {"name": "all", "count": "0"})
    assert ("invalid_count", "count") in found


def test_choice_rows_have_no_statistics(run):
    row = {"source": "Tab1", "subjects": "all", "measurement": "sex", "choice": "M", "mean": "3"}
    assert run("characteristica", row) == {("choice_statistics", "mean")}


def test_individual_statistics(run):
    individual = {"source": "TabA", "subjects": "S1", "measurement": "age", "mean": "30", "sd": "2", "unit": "yr"}
    explicit = {"source": "TabA", "subjects": "all", "measurement": "age", "count": "1", "mean": "30", "min": "1", "unit": "yr"}
    assert run("characteristica", individual, explicit) == {
        ("individual_statistics", "sd"),
        ("individual_statistics", "min"),
    }


def test_unspecified_summary(run):
    row = {**CMAX, "calculation": "unspecified summary", "mean": "2", "se": "0.1"}
    assert run("outputs", row, file="outputs_Tab2.tsv") == {("unspecified_summary_statistics", "se")}


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"mean": "2", "error_bar": "3"}, {("incomplete_error_bar", "error_type")}),
        ({"mean": "2", "error_type": "sd"}, {("incomplete_error_bar", "error_bar")}),
        ({"mean": "2", "error_bar": "3", "error_type": "gsd"}, {("incomplete_error_bar", "gmean")}),
        ({"mean": "2", "sd": "1", "error_bar": "3", "error_type": "sd"}, {("error_bar_conflict", "sd")}),
        ({"mean": "2", "error_bar": "3", "error_type": "se"}, set()),
    ],
)
def test_error_bars(run, extra, expected):
    assert run("outputs", {**CMAX, **extra}, file="outputs_Tab2.tsv") == expected


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"min": "5", "max": "1"}, {("reversed_range", "min")}),
        ({"mean": "10", "min": "1", "max": "5"}, {("outside_range", "mean")}),
        ({"mean": "2", "sd": "-1"}, {("invalid_statistic", "sd")}),
        ({"gmean": "2", "gsd": "0.5"}, {("invalid_statistic", "gsd")}),
        ({"gmean": "0"}, {("invalid_statistic", "gmean")}),
        ({"mean": "2", "cv": "-3"}, {("invalid_statistic", "cv")}),
    ],
)
def test_ranges_and_spreads(run, extra, expected):
    assert run("outputs", {**CMAX, **extra}, file="outputs_Tab2.tsv") == expected


def test_outside_range_is_a_warning(make_study, valid_files, tsv):
    files = {**valid_files, "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "mean": "10", "min": "1", "max": "5"})}
    issues = check_rows(load_study(make_study(files)))
    assert [issue.severity for issue in issues] == ["warning"]


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"mean": "2", "time": "1"}, {("missing_time_unit", "time_unit")}),
        ({"mean": "2", "time": "1", "time_unit": "kg"}, {("time_dimension", "time_unit")}),
        ({"mean": "2", "time": "1", "time_unit": "blorp"}, {("invalid_time_unit", "time_unit")}),
        ({"mean": "2", "time": "NR", "time_unit": "NR"}, set()),
        ({"mean": "2", "unit": "mg%"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "foo"}, {("invalid_unit", "unit")}),
        ({"mean": "2", "unit": "µg/l"}, set()),
    ],
)
def test_times_and_units(run, extra, expected):
    assert run("outputs", {**CMAX, **extra}, file="outputs_Tab2.tsv") == expected


def test_timecourse_needs_numeric_time(run):
    row = {"label": "a", "subjects": "all", "measurement": "concentration", "time": "NR", "time_unit": "h", "mean": "1"}
    assert run("timecourses", row, file="timecourses_Fig1.tsv") == {("invalid_time", "time")}


DOSE = {
    "source": "Text",
    "name": "D1",
    "measurement": "dosing",
    "substance": "drug",
    "route": "oral",
    "time_unit": "h",
    "mean": "100",
    "unit": "mg",
}


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({"time": "0;12", "interval": "12"}, {("schedule_conflict", "interval")}),
        ({"time": "0;12", "doses": "2"}, {("schedule_conflict", "doses")}),
        ({"time": "0", "interval": "24"}, {("invalid_schedule", "doses")}),
        ({"time": "0", "interval": "0", "doses": "2"}, {("invalid_schedule", "interval")}),
        ({"time": "0", "doses": "3"}, {("invalid_schedule", "interval")}),
        ({"time": "0", "doses": "0"}, {("invalid_schedule", "doses")}),
        ({"time": "2", "time_end": "1"}, {("invalid_schedule", "time_end")}),
        ({"time": "0", "interval": "24", "doses": "7"}, set()),
        ({"time": "0;12;40"}, set()),
    ],
)
def test_schedules(run, extra, expected):
    assert run("interventions", {**DOSE, **extra}) == expected


def test_scatter_axes(run):
    row = {
        "name": "s", "subjects": "S1",
        "x_measurement": "age", "x_mean": "30", "x_unit": "yr", "x_time": "2",
        "y_measurement": "cmax", "y_mean": "2", "y_unit": "mg%",
    }
    assert run("scatters", row, file="scatters_Fig2.tsv") == {
        ("missing_time_unit", "x_time_unit"),
        ("invalid_unit", "y_unit"),
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_rows.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.rows'`

- [ ] **Step 3: Write the implementation**

Append to `python/src/pkdb/studyformat/issues.py`:

```python
def row_issue(table, row, code: str, message: str, column: str | None = None, **details) -> ValidationIssue:
    """Issue at a row of a loaded table, optionally at one of its columns."""
    return make_issue(
        code,
        message,
        file=table.file,
        line=row.line,
        column=table.column_index(column) if column else None,
        header=column,
        **details,
    )
```

`python/src/pkdb/studyformat/rows.py`:

```python
"""Layer 3: required cells, statistics, times, schedules and units of single rows."""

import re
from collections.abc import Iterator
from functools import lru_cache
from typing import cast

import pint

from pkdb.domain.units import ureg
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.cells import NOT_REPORTED
from pkdb.studyformat.issues import row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row

UNIT_PATTERN = re.compile(r"[\/^_*.() µα-ωΑ-Ωa-zA-Z0-9]*")
UNSPECIFIED = "unspecified summary"
CENTRAL = ("choice", "mean", "gmean", "median", "min", "max")
SPREAD = ("sd", "se", "cv", "gmean", "gsd", "gcv", "median", "min", "max")
NUMERIC = ("mean", "sd", "se", "cv", "gmean", "gsd", "gcv", "median", "min", "max", "error_bar")
PINT_ERRORS = (pint.PintError, ValueError, TypeError, AttributeError)
Issues = Iterator[ValidationIssue]


@lru_cache(maxsize=1024)
def time_unit_status(unit: str) -> str:
    """`ok`, `dimension` (parses but is no time) or `invalid`; cached for large tables."""
    try:
        return "ok" if ureg(unit).check("[time]") else "dimension"
    except PINT_ERRORS:
        return "invalid"


@lru_cache(maxsize=4096)
def unit_known(unit: str) -> bool:
    try:
        ureg.Quantity(1, unit)
    except PINT_ERRORS:
        return False
    return True


def subject_counts(study: LoadedStudy) -> dict[str, int | None]:
    return {
        row.cells["name"]: cast(int | None, row.values["count"])
        for _, row in study.rows("subjects")
        if row.cells["name"]
    }


def check_rows(study: LoadedStudy) -> list[ValidationIssue]:
    counts = subject_counts(study)
    issues: list[ValidationIssue] = []
    for table in study.tables:
        for row in table.rows:
            issues.extend(_required(table, row))
            if table.kind == "subjects":
                issues.extend(_subject(table, row))
            elif table.kind == "scatters":
                for prefix in ("x", "y"):
                    issues.extend(_times(table, row, f"{prefix}_time", f"{prefix}_time_unit"))
                    issues.extend(_unit(table, row, f"{prefix}_unit"))
            else:
                issues.extend(_statistics(table, row, counts))
                issues.extend(_error_bar(table, row))
                issues.extend(_ranges(table, row))
                issues.extend(_times(table, row, "time", "time_unit"))
                issues.extend(_unit(table, row, "unit"))
                if table.kind == "interventions":
                    issues.extend(_schedule(table, row))
    return issues


def _required(table: LoadedTable, row: Row) -> Issues:
    for name in sorted(table.spec.required_columns):
        if not row.cells[name]:
            yield row_issue(table, row, "missing_required", f"{name} is required in {table.kind} rows", name)


def _subject(table: LoadedTable, row: Row) -> Issues:
    count = row.values["count"]
    if isinstance(count, int) and count < 1:
        yield row_issue(table, row, "invalid_count", "A subject count is at least 1", "count")


def _statistics(table: LoadedTable, row: Row, counts: dict[str, int | None]) -> Issues:
    values = row.values
    count = values["count"]
    if count is None and isinstance(values["subjects"], str):
        count = counts.get(values["subjects"])
    if all(values[name] is None for name in CENTRAL):
        yield row_issue(
            table, row, "missing_value", "Enter a value: mean, gmean, median, min, max or choice"
        )
    if values["choice"] is not None:
        for name in NUMERIC:
            if values[name] is not None:
                yield row_issue(
                    table, row, "choice_statistics",
                    "A choice row has no numeric statistics; count holds the number of subjects with the choice",
                    name,
                )
    elif count == 1:
        for name in SPREAD:
            if values[name] is not None:
                yield row_issue(
                    table, row, "individual_statistics",
                    "A single subject has one value; enter it in mean", name,
                )
    if values["calculation"] == UNSPECIFIED:
        for name in (*SPREAD, "error_bar"):
            if values[name] is not None:
                yield row_issue(
                    table, row, "unspecified_summary_statistics",
                    "An unspecified summary has only a mean", name,
                )


def _error_bar(table: LoadedTable, row: Row) -> Issues:
    has_bar, has_type = bool(row.cells["error_bar"]), bool(row.cells["error_type"])
    if has_bar != has_type:
        missing = "error_bar" if has_type else "error_type"
        yield row_issue(
            table, row, "incomplete_error_bar", "error_bar and error_type are entered together", missing
        )
        return
    kind = row.values["error_type"]
    if not isinstance(kind, str):
        return
    center = "gmean" if kind == "gsd" else "mean"
    if row.values[center] is None:
        yield row_issue(
            table, row, "incomplete_error_bar", f"An error bar of type {kind} needs {center}", center
        )
    if row.values[kind] is not None:
        yield row_issue(
            table, row, "error_bar_conflict",
            f"{kind} is reported and also derived from error_bar; keep one", kind,
        )


def _ranges(table: LoadedTable, row: Row) -> Issues:
    values = row.values
    low, high = values["min"], values["max"]
    if isinstance(low, float) and isinstance(high, float):
        if low > high:
            yield row_issue(table, row, "reversed_range", f"min {low:g} exceeds max {high:g}", "min")
        else:
            for name in ("mean", "median"):
                value = values[name]
                if isinstance(value, float) and not low <= value <= high:
                    yield row_issue(table, row, "outside_range", f"{name} lies outside [min, max]", name)
    for name in ("sd", "se", "cv", "gcv"):
        value = values[name]
        if isinstance(value, float) and value < 0:
            yield row_issue(table, row, "invalid_statistic", f"{name} cannot be negative", name)
    gsd, gmean = values["gsd"], values["gmean"]
    if isinstance(gsd, float) and gsd < 1:
        yield row_issue(table, row, "invalid_statistic", "gsd is a factor of at least 1", "gsd")
    if isinstance(gmean, float) and gmean <= 0:
        yield row_issue(table, row, "invalid_statistic", "gmean must be positive", "gmean")


def _times(table: LoadedTable, row: Row, time: str, unit_column: str) -> Issues:
    values = row.values
    if table.kind == "timecourses" and values[time] == NOT_REPORTED:
        yield row_issue(table, row, "invalid_time", "Timecourse points need a numeric time", time)
    timed = [
        name
        for name in (time, "time_end", "interval")
        if name in values and values[name] not in (None, NOT_REPORTED)
    ]
    unit = row.cells[unit_column]
    if timed and not unit:
        yield row_issue(table, row, "missing_time_unit", f"{timed[0]} needs {unit_column}", unit_column)
    if unit and unit != NOT_REPORTED:
        status = time_unit_status(unit)
        if status == "invalid":
            yield row_issue(table, row, "invalid_time_unit", f"Unknown time unit {unit!r}", unit_column)
        elif status == "dimension":
            yield row_issue(table, row, "time_dimension", f"{unit} is not a unit of time", unit_column)


def _unit(table: LoadedTable, row: Row, column: str) -> Issues:
    unit = row.cells[column]
    if not unit:
        return
    if not UNIT_PATTERN.fullmatch(unit):
        yield row_issue(table, row, "invalid_unit", f"Unit {unit!r} contains unsupported characters", column)
        return
    if not unit_known(unit):
        yield row_issue(table, row, "invalid_unit", f"Unknown unit {unit!r}", column)


def _schedule(table: LoadedTable, row: Row) -> Issues:
    values = row.values
    times = values["time"]
    if isinstance(times, tuple) and len(times) > 1:
        for name in ("interval", "doses"):
            if values[name] is not None:
                yield row_issue(
                    table, row, "schedule_conflict",
                    "A ;-separated time list replaces interval and doses", name,
                )
        return
    interval, doses, end = values["interval"], values["doses"], values["time_end"]
    if isinstance(interval, float):
        if interval <= 0:
            yield row_issue(table, row, "invalid_schedule", "interval must be positive", "interval")
        if doses is None:
            yield row_issue(
                table, row, "invalid_schedule",
                "interval needs doses, the number of administrations", "doses",
            )
    if isinstance(doses, int):
        if doses < 1:
            yield row_issue(table, row, "invalid_schedule", "doses is at least 1", "doses")
        elif doses > 1 and interval is None:
            yield row_issue(
                table, row, "invalid_schedule",
                "More than one dose needs an interval or a ;-separated time list", "interval",
            )
    if isinstance(end, float) and isinstance(times, tuple) and end < times[0]:
        yield row_issue(table, row, "invalid_schedule", "time_end lies before time", "time_end")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_rows.py -q`
Expected: PASS. If pint parses `kg` through `ureg(...)` differently (for example returning a plain number for unit-less input), keep the `PINT_ERRORS` tuple and adjust only how the dimension is read, not the test.

- [ ] **Step 5: Lint, format, type check, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat && uv run --locked ty check
cd .. && git add python/src/pkdb/studyformat python/tests/studyformat
git commit -m "Check study format 2 rows: statistics, times, schedules and units"
```

---

### Task 9: Relationship rules (layer 4)

**Files:**
- Create: `python/src/pkdb/studyformat/relations.py`
- Test: `python/tests/studyformat/test_studyformat_relations.py`

**Interfaces:**
- Consumes: `LoadedStudy` (Task 6); `row_issue`, `make_issue` (Tasks 5, 8); `ROOT`, `TEXT_SOURCE`, `image_file`, `STUDY_JSON`, `REFERENCE_JSON`, `REVIEW_JSON` (Task 1).
- Produces: `SERIES_COLUMNS`, `OBSERVATION_KEYS`, `check_relations(study: LoadedStudy) -> list[ValidationIssue]`.

Rules:

| Code | Condition |
|---|---|
| `duplicate_name` | a subject or intervention name defined twice; a scatter `name` used in two scatter files |
| `duplicate_label` | a timecourse label used in two timecourse files (reported once per file and label) |
| `unknown_reference` | a `subjects`, `parent`, `interventions`, `x_interventions` or `y_interventions` entry without a row of that name; skipped when the referenced kind is broken; candidates from `difflib` |
| `duplicate_reference` | the same name twice in one list cell |
| `missing_root` | no subject `all` |
| `root_parent` | `all` has a parent |
| `missing_parent` | a subject other than `all` without parent |
| `subject_cycle` | a subject is its own ancestor (reported for every member of the cycle) |
| `subject_count_exceeds_parent` | child count greater than parent count, both known |
| `inconsistent_series` | rows of one label differ in `subjects, interventions, measurement, calculation, substance, tissue, method` |
| `duplicate_time` | the same numeric time and time unit twice in one series |
| `duplicate_row` | identical content (all columns except `study`, `comment` and owned columns) twice in one characteristica, outputs, timecourses or scatters file |
| `duplicate_observation` (warning) | same key, other values in one file; keys: characteristica `subjects, measurement, calculation, substance, tissue, method, choice, time, time_unit`; outputs the same plus `interventions`; scatters `name, subjects` |
| `unused_intervention`, `unused_subject` (warnings) | never referenced; skipped when any table is broken |
| `missing_image` | `<study>_<source>.png` missing for a per-source file or a `source` cell (not `Text`); reported once per source |
| `public_requires_release` | `access` is `public` without `release` |
| `reference_mismatch` | `reference.pmid` differs from `reference.json` `pmid`, or `reference.doi` from its `doi` (case-insensitive) |
| `approved_with_open_items` | review status `approved` with open items |
| `unknown_review_target` | target file missing (a non-table file with neither rows nor column is allowed), or rows/column naming unknown columns |
| `review_target_unmatched` (warning) | the `rows` filter matches no row |

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.load import load_study
from pkdb.studyformat.relations import check_relations

CMAX = {"subjects": "all", "interventions": "D1", "measurement": "cmax", "mean": "2", "unit": "mg/l"}
POINT = {"label": "a", "subjects": "all", "interventions": "D1", "measurement": "concentration", "time_unit": "h"}
ITEM = {
    "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    "kind": "question",
    "text": "Check this.",
    "author": "curator",
    "created": "2026-10-05T10:12:00Z",
}


@pytest.fixture
def run(make_study, valid_files):
    def check(**files):
        study = load_study(make_study({**valid_files, **files}))
        return {(issue.code, issue.source.file if issue.source else None, issue.source.header if issue.source else None) for issue in check_relations(study)}

    return check


def test_valid_study_passes(run):
    assert run() == set()


def test_unknown_and_duplicate_references(run, tsv):
    found = run(
        **{
            "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "subjects": "S9", "interventions": "D1,D2"}),
            "scatters_Fig2.tsv": tsv(
                "scatters",
                {"name": "s", "subjects": "S1", "x_measurement": "age", "x_mean": "1",
                 "y_interventions": "D1,D1", "y_measurement": "cmax", "y_mean": "2"},
                {"name": "s", "subjects": "S2", "x_measurement": "age", "x_mean": "2",
                 "y_measurement": "cmax", "y_mean": "3"},
            ),
        }
    )
    assert found == {
        ("unknown_reference", "outputs_Tab2.tsv", "subjects"),
        ("unknown_reference", "outputs_Tab2.tsv", "interventions"),
        ("duplicate_reference", "scatters_Fig2.tsv", "y_interventions"),
    }


def test_unknown_reference_candidates(make_study, valid_files, tsv):
    files = {**valid_files, "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "subjects": "S11"})}
    issue = next(i for i in check_relations(load_study(make_study(files))) if i.code == "unknown_reference")
    assert issue.suggestions[0].candidates == ["S1"]


def test_broken_subjects_table_suppresses_reference_noise(run):
    found = run(**{"subjects.tsv": "group\nall\n"})
    assert not any(code == "unknown_reference" for code, _, _ in found)


def test_subject_tree(run, tsv):
    found = run(
        **{
            "subjects.tsv": tsv(
                "subjects",
                {"name": "all", "parent": "S1", "count": "2"},
                {"name": "S1", "parent": "all", "count": "5"},
                {"name": "S2", "count": "1"},
                {"name": "x", "parent": "y"},
                {"name": "y", "parent": "x"},
                {"name": "S1"},
            )
        }
    )
    assert {
        ("root_parent", "subjects.tsv", "parent"),
        ("missing_parent", "subjects.tsv", "parent"),
        ("subject_cycle", "subjects.tsv", "parent"),
        ("subject_count_exceeds_parent", "subjects.tsv", "count"),
        ("duplicate_name", "subjects.tsv", "name"),
    } <= found


def test_missing_root(run, tsv):
    found = run(**{"subjects.tsv": tsv("subjects", {"name": "S1", "count": "1"})})
    assert ("missing_root", "subjects.tsv", None) in found


def test_series_rules(run, tsv):
    rows = [
        {**POINT, "time": "0", "mean": "1"},
        {**POINT, "time": "0", "mean": "2"},
        {**POINT, "time": "1", "mean": "2", "substance": "drug"},
    ]
    found = run(**{"timecourses_Fig1.tsv": tsv("timecourses", *rows)})
    assert found == {
        ("duplicate_time", "timecourses_Fig1.tsv", "time"),
        ("inconsistent_series", "timecourses_Fig1.tsv", "substance"),
    }


def test_labels_and_scatter_names_are_unique_across_files(run, tsv, valid_files):
    other = tsv("timecourses", {**POINT, "label": "drug_plasma", "time": "0", "mean": "1"})
    found = run(**{"timecourses_Fig3.tsv": other, "Example_Fig3.png": b"png"})
    assert found == {("duplicate_label", "timecourses_Fig3.tsv", "label")}


def test_duplicates(run, tsv):
    rows = [CMAX, CMAX, {**CMAX, "mean": "3"}]
    found = run(**{"outputs_Tab2.tsv": tsv("outputs", *rows)})
    assert found == {
        ("duplicate_row", "outputs_Tab2.tsv", None),
        ("duplicate_observation", "outputs_Tab2.tsv", None),
    }


def test_unused_names(run, tsv, valid_files):
    subjects = valid_files["subjects.tsv"] + "\tS3\tall\t1\t\t\n"
    interventions = tsv(
        "interventions",
        {"name": "D1", "measurement": "dosing", "mean": "1"},
        {"name": "D2", "measurement": "dosing", "mean": "1"},
    )
    found = run(**{"subjects.tsv": subjects, "interventions.tsv": interventions})
    assert found == {
        ("unused_subject", "subjects.tsv", "name"),
        ("unused_intervention", "interventions.tsv", "name"),
    }


def test_missing_images(run, tsv, valid_files):
    found = run(
        **{
            "outputs_Tab9.tsv": tsv("outputs", CMAX),
            "characteristica.tsv": valid_files["characteristica.tsv"].replace("TabA", "Tab7"),
        }
    )
    assert found == {
        ("missing_image", "outputs_Tab9.tsv", None),
        ("missing_image", "characteristica.tsv", "source"),
    }


def test_study_rules(run, valid_files):
    study = json.loads(valid_files["study.json"])
    found = run(
        **{
            "study.json": dump_json({**study, "access": "public", "reference": {"pmid": "999"}}),
        }
    )
    assert found == {
        ("public_requires_release", "study.json", None),
        ("reference_mismatch", "reference.json", None),
    }


def test_review_rules(run):
    items = [
        {**ITEM, "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A1", "target": {"file": "outputs_Tab2.tsv", "rows": {"subjects": "S9"}}},
        {**ITEM, "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A2", "target": {"file": "outputs_Tab5.tsv"}},
        {**ITEM, "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A3", "target": {"file": "outputs_Tab2.tsv", "column": "group"}},
        {**ITEM, "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2A4", "target": {"file": "Example.pdf"}},
    ]
    found = run(**{"review.json": dump_json({"status": "approved", "items": items})})
    assert found == {
        ("approved_with_open_items", "review.json", None),
        ("review_target_unmatched", "review.json", None),
        ("unknown_review_target", "review.json", None),
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_relations.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.relations'`

- [ ] **Step 3: Write the implementation**

```python
"""Layer 4: relationships between rows, tables and files."""

from collections import defaultdict
from collections.abc import Iterator
from difflib import get_close_matches

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue, row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    REVIEW_JSON,
    ROOT,
    STUDY_JSON,
    TEXT_SOURCE,
    image_file,
)

SERIES_COLUMNS = (
    "subjects", "interventions", "measurement", "calculation", "substance", "tissue", "method",
)
_CHARACTERISTICA_KEY = (
    "subjects", "measurement", "calculation", "substance", "tissue", "method", "choice",
    "time", "time_unit",
)
OBSERVATION_KEYS = {
    "characteristica": _CHARACTERISTICA_KEY,
    "outputs": (*_CHARACTERISTICA_KEY, "interventions"),
    "scatters": ("name", "subjects"),
}
DATA_KINDS = frozenset({"characteristica", "outputs", "timecourses", "scatters"})
Issues = Iterator[ValidationIssue]


def check_relations(study: LoadedStudy) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for check in (
        _unique_names, _references, _subject_tree, _series, _duplicates, _unused,
        _images, _study_rules, _review_rules,
    ):
        issues.extend(check(study))
    return issues


def _names(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return value
    return (value,) if isinstance(value, str) and value else ()


def _unique_names(study: LoadedStudy) -> Issues:
    for kind in ("subjects", "interventions"):
        seen: dict[str, int] = {}
        for table, row in study.rows(kind):
            name = row.cells["name"]
            if not name:
                continue
            if name in seen:
                yield row_issue(table, row, "duplicate_name", f"{name!r} is already defined in line {seen[name]}", "name")
            else:
                seen[name] = row.line
    for kind, column, code in (("timecourses", "label", "duplicate_label"), ("scatters", "name", "duplicate_name")):
        owner: dict[str, str] = {}
        reported: set[tuple[str, str]] = set()
        for table, row in study.rows(kind):
            value = row.cells[column]
            if not value:
                continue
            first = owner.setdefault(value, table.file)
            if first != table.file and (table.file, value) not in reported:
                reported.add((table.file, value))
                yield row_issue(
                    table, row, code,
                    f"{value!r} is also used in {first}; {column}s are unique across the study",
                    column,
                )


def _references(study: LoadedStudy) -> Issues:
    known = {
        kind: sorted({row.cells["name"] for _, row in study.rows(kind) if row.cells["name"]})
        for kind in ("subjects", "interventions")
    }
    for table in study.tables:
        for column in table.spec.columns:
            target = column.references
            if target is None or target in study.broken:
                continue
            names = set(known[target])
            for row in table.rows:
                seen: set[str] = set()
                for name in _names(row.values[column.name]):
                    if name in seen:
                        yield row_issue(table, row, "duplicate_reference", f"{name!r} is listed twice", column.name)
                    seen.add(name)
                    if name not in names:
                        yield row_issue(
                            table, row, "unknown_reference",
                            f"{target}.tsv has no row named {name!r}",
                            column.name,
                            actual=name,
                            candidates=get_close_matches(name, known[target], n=5, cutoff=0.6),
                        )


def _subject_tree(study: LoadedStudy) -> Issues:
    tables = study.of_kind("subjects")
    if not tables:
        return
    table = tables[0]
    rows: dict[str, Row] = {}
    for row in table.rows:
        if row.cells["name"]:
            rows.setdefault(row.cells["name"], row)
    if ROOT not in rows:
        yield make_issue("missing_root", "subjects.tsv needs the root group 'all'", file=table.file)
    parents = {name: row.cells["parent"] for name, row in rows.items()}
    for name, row in rows.items():
        if name == ROOT and parents[name]:
            yield row_issue(table, row, "root_parent", "The root group 'all' has no parent", "parent")
        elif name != ROOT and not parents[name]:
            yield row_issue(table, row, "missing_parent", f"{name!r} needs a parent group", "parent")
    done: set[str] = set()
    for start in parents:
        path: list[str] = []
        position: dict[str, int] = {}
        current = start
        while current in parents and current not in done:
            if current in position:
                for member in path[position[current]:]:
                    yield row_issue(table, rows[member], "subject_cycle", f"{member!r} is its own ancestor", "parent")
                break
            position[current] = len(path)
            path.append(current)
            current = parents[current]
        done.update(path)
    for name, row in rows.items():
        parent = rows.get(parents[name])
        child_count = row.values["count"]
        parent_count = parent.values["count"] if parent else None
        if isinstance(child_count, int) and isinstance(parent_count, int) and child_count > parent_count:
            yield row_issue(
                table, row, "subject_count_exceeds_parent",
                f"count {child_count} exceeds the count {parent_count} of {parents[name]!r}",
                "count",
            )


def _series(study: LoadedStudy) -> Issues:
    for table in study.of_kind("timecourses"):
        series: dict[str, list[Row]] = defaultdict(list)
        for row in table.rows:
            if row.cells["label"]:
                series[row.cells["label"]].append(row)
        for label, rows in series.items():
            first = rows[0]
            times: dict[tuple[float, str], int] = {}
            for row in rows:
                if row is not first:
                    for name in SERIES_COLUMNS:
                        if row.cells[name] != first.cells[name]:
                            yield row_issue(
                                table, row, "inconsistent_series",
                                f"Series {label!r} has {name} {first.cells[name]!r} in line {first.line}",
                                name,
                            )
                time = row.values["time"]
                if isinstance(time, float):
                    key = (time, row.cells["time_unit"])
                    if key in times:
                        yield row_issue(
                            table, row, "duplicate_time",
                            f"Time {row.cells['time']} appears twice in series {label!r} (line {times[key]})",
                            "time",
                        )
                    else:
                        times[key] = row.line


def _duplicates(study: LoadedStudy) -> Issues:
    for table in study.tables:
        if table.kind not in DATA_KINDS:
            continue
        content_names = [
            column.name
            for column in table.spec.columns
            if not column.owned and column.name not in {"study", "comment"}
        ]
        keys = OBSERVATION_KEYS.get(table.kind)
        rows_seen: dict[tuple[str, ...], int] = {}
        keys_seen: dict[tuple[str, ...], int] = {}
        for row in table.rows:
            content = tuple(row.cells[name] for name in content_names)
            if content in rows_seen:
                yield row_issue(table, row, "duplicate_row", f"Row repeats line {rows_seen[content]}")
                continue
            rows_seen[content] = row.line
            if keys:
                key = tuple(row.cells[name] for name in keys)
                if key in keys_seen:
                    yield row_issue(
                        table, row, "duplicate_observation",
                        f"Line {keys_seen[key]} describes the same observation with other values",
                    )
                else:
                    keys_seen[key] = row.line


def _unused(study: LoadedStudy) -> Issues:
    if study.broken:
        return
    used: dict[str, set[str]] = {"subjects": set(), "interventions": set()}
    for table in study.tables:
        for column in table.spec.columns:
            if column.references:
                for row in table.rows:
                    used[column.references].update(_names(row.values[column.name]))
    for kind, code in (("subjects", "unused_subject"), ("interventions", "unused_intervention")):
        for table, row in study.rows(kind):
            name = row.cells["name"]
            if name and name not in used[kind]:
                yield row_issue(table, row, code, f"{name!r} is not referenced by any row", "name")


def _images(study: LoadedStudy) -> Issues:
    reported: set[str] = set()
    for table in study.tables:
        entries: list[tuple[str | None, Row | None]] = []
        if table.spec.per_source:
            entries.append((table.source, None))
        else:
            for row in table.rows:
                source = row.values.get("source")
                if isinstance(source, str):
                    entries.append((source, row))
        for source, row in entries:
            if not source or source == TEXT_SOURCE or source in reported:
                continue
            image = image_file(study.name, source)
            if image in study.layout.files:
                continue
            reported.add(source)
            if row is None:
                yield make_issue("missing_image", f"{image} is missing for {table.file}", file=table.file)
            else:
                yield row_issue(table, row, "missing_image", f"{image} is missing for source {source}", "source")


def _study_rules(study: LoadedStudy) -> Issues:
    metadata = study.metadata
    if metadata is None:
        return
    if metadata.access == "public" and metadata.release is None:
        yield make_issue(
            "public_requires_release",
            "Only released studies can be public; set access to private or release the study",
            file=STUDY_JSON, field="access",
        )
    if study.reference is None or metadata.reference is None:
        return
    for name, expected in (("pmid", metadata.reference.pmid), ("doi", metadata.reference.doi)):
        if expected is None:
            continue
        actual = study.reference.get(name)
        found = "" if actual is None else str(actual)
        same = found.lower() == expected.lower() if name == "doi" else found == expected
        if not same:
            yield make_issue(
                "reference_mismatch",
                f"study.json names {name} {expected} but reference.json has {found or 'none'}; run pkdb reference to refresh reference.json",
                file=REFERENCE_JSON, field=name,
            )


def _review_rules(study: LoadedStudy) -> Issues:
    review = study.review
    if review is None:
        return
    open_items = sum(item.state == "open" for item in review.items)
    if review.status == "approved" and open_items:
        yield make_issue(
            "approved_with_open_items",
            f"An approved study has no open review items; {open_items} are open",
            file=REVIEW_JSON, field="status",
        )
    table_names = {table_file.name for table_file in study.layout.tables}
    for item in review.items:
        target = item.target
        if target is None or target.file is None:
            continue
        table: LoadedTable | None = study.table(target.file)
        if table is None:
            plain = target.file in study.layout.files and target.file not in table_names
            if (plain and not target.rows and not target.column) or target.file in table_names:
                continue
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets {target.file}, which is not a file of this study",
                file=REVIEW_JSON,
            )
            continue
        columns = [*target.rows, *([target.column] if target.column else [])]
        unknown = [name for name in columns if name not in table.spec.names]
        if unknown:
            yield make_issue(
                "unknown_review_target",
                f"Review item {item.id} targets unknown columns {', '.join(unknown)} of {target.file}",
                file=REVIEW_JSON,
            )
            continue
        if target.rows and not any(
            all(row.cells[key] == value for key, value in target.rows.items()) for row in table.rows
        ):
            yield make_issue(
                "review_target_unmatched",
                f"Review item {item.id} no longer matches a row of {target.file}",
                file=REVIEW_JSON,
            )
```

Note: `target.file in table_names` without a loaded table means the table is broken; its issues are reported elsewhere.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_relations.py -q`
Expected: PASS

- [ ] **Step 5: Lint, format, type check, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat && uv run --locked ty check
cd .. && git add python/src/pkdb/studyformat/relations.py python/tests/studyformat/test_studyformat_relations.py
git commit -m "Check relationships between study format 2 tables"
```

---

### Task 10: Vocabulary rules (layer 5)

**Files:**
- Create: `python/src/pkdb/studyformat/terms.py`
- Test: `python/tests/studyformat/test_studyformat_terms.py`

**Interfaces:**
- Consumes: `LoadedStudy` (Task 6); `row_issue` (Task 8); `pkdb.domain.vocabulary.Vocabulary`, `MeasurementRule`.
- Produces: `vocabulary_terms(vocabulary) -> dict[str, frozenset[str]]` (keys are `Column.vocabulary` values; `calculation_types` excludes `geometric mean` and includes `unspecified summary`); `check_terms(study, vocabulary) -> list[ValidationIssue]`.

Rules:

| Code | Condition |
|---|---|
| `unknown_measurement`, `unknown_substance`, `unknown_tissue`, `unknown_method`, `unknown_route`, `unknown_form`, `unknown_application`, `unknown_calculation` | a term column value not in the vocabulary; candidates from `difflib` (n=10, cutoff 0.6) |
| `retired_calculation` | `calculation` is `geometric mean` |
| `invalid_choice` | `choice` set but the measurement is not categorical, boolean or numeric categorical, or the choice is not allowed; candidates are the allowed choices |
| `missing_choice` | categorical or boolean measurement with choices and no `choice` |
| `negative_value` | `mean`, `gmean`, `median`, `min`, `max`, `error_bar` (scatter: `x_mean`, `y_mean`) below 0 and the measurement cannot be negative |
| `deprecated_measurement` (warning) | measurement is deprecated |
| `missing_time` | measurement requires a time and the time cell is empty in characteristica, outputs, timecourses or scatters (`NR` satisfies it) |
| `missing_unit` | a numeric value is present, the measurement has units other than `NO_UNIT`, and the unit cell is empty |
| `missing_dosing_field` | intervention with measurement `dosing` or `medication` lacks `substance` or `route` |

- [ ] **Step 1: Write the failing test**

```python
import pytest

from pkdb.studyformat.load import load_study
from pkdb.studyformat.terms import check_terms, vocabulary_terms

CMAX = {
    "subjects": "all", "interventions": "D1", "measurement": "cmax",
    "substance": "drug", "tissue": "plasma", "mean": "2", "unit": "mg/l",
}


@pytest.fixture
def run(make_study, valid_files, tsv, sf_vocabulary):
    def check(kind=None, *rows, file=None):
        files = dict(valid_files)
        if kind is not None:
            files[file or f"{kind}.tsv"] = tsv(kind, *rows)
        study = load_study(make_study(files))
        return {(issue.code, issue.source.header) for issue in check_terms(study, sf_vocabulary)}

    return check


def test_valid_study_passes(run):
    assert run() == set()


def test_calculation_terms(sf_vocabulary):
    terms = vocabulary_terms(sf_vocabulary)["calculation_types"]
    assert "unspecified summary" in terms and "geometric mean" not in terms


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"measurement": "cmaxx"}, {("unknown_measurement", "measurement")}),
        ({"substance": "drugg"}, {("unknown_substance", "substance")}),
        ({"tissue": "blood"}, {("unknown_tissue", "tissue")}),
        ({"method": "LCMS"}, {("unknown_method", "method")}),
        ({"calculation": "median"}, {("unknown_calculation", "calculation")}),
        ({"calculation": "geometric mean"}, {("retired_calculation", "calculation")}),
        ({"calculation": "unspecified summary"}, set()),
        ({"mean": "-1"}, {("negative_value", "mean")}),
        ({"measurement": "change", "mean": "-1"}, set()),
        ({"unit": ""}, {("missing_unit", "unit")}),
        ({"measurement": "old_measure"}, {("deprecated_measurement", "measurement")}),
        ({"measurement": "concentration"}, {("missing_time", "time")}),
        ({"measurement": "concentration", "time": "NR", "time_unit": "NR"}, set()),
    ],
)
def test_output_terms(run, change, expected):
    assert run("outputs", {**CMAX, **change}, file="outputs_Tab2.tsv") == expected


def test_unknown_term_candidates(make_study, valid_files, tsv, sf_vocabulary):
    files = {**valid_files, "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "measurement": "cmaxx"})}
    issue = check_terms(load_study(make_study(files)), sf_vocabulary)[0]
    assert issue.suggestions[0].candidates == ["cmax"]


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"measurement": "sex", "choice": "X"}, {("invalid_choice", "choice")}),
        ({"measurement": "sex"}, {("missing_choice", "choice")}),
        ({"measurement": "age", "choice": "old", "unit": "yr"}, {("invalid_choice", "choice")}),
        ({"measurement": "healthy", "choice": "N"}, set()),
    ],
)
def test_choices(run, row, expected):
    assert run("characteristica", {"source": "Tab1", "subjects": "all", **row}) == expected


def test_interventions(run):
    dose = {"name": "D1", "measurement": "dosing", "mean": "100", "unit": "mg", "route": "iv"}
    assert run("interventions", dose) == {
        ("unknown_route", "route"),
        ("missing_dosing_field", "substance"),
    }


def test_scatter_axes(run):
    row = {
        "name": "s", "subjects": "S1",
        "x_measurement": "agee", "x_mean": "30",
        "y_measurement": "cmax", "y_mean": "-2", "y_unit": "mg/l",
    }
    assert run("scatters", row, file="scatters_Fig2.tsv") == {
        ("unknown_measurement", "x_measurement"),
        ("negative_value", "y_mean"),
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_terms.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.terms'`

- [ ] **Step 3: Write the implementation**

```python
"""Layer 5: vocabulary terms, choices, signs, required times and units."""

from collections.abc import Iterator
from difflib import get_close_matches

from pkdb.domain.vocabulary import MeasurementRule, Vocabulary
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.columns import Column
from pkdb.studyformat.issues import row_issue
from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row

RETIRED_CALCULATION = "geometric mean"
UNSPECIFIED = "unspecified summary"
DOSING = frozenset({"dosing", "medication"})
CHOICE_TYPES = frozenset({"categorical", "boolean", "numeric_categorical"})
REQUIRED_CHOICE_TYPES = frozenset({"categorical", "boolean"})
TIMED_KINDS = frozenset({"characteristica", "outputs", "timecourses", "scatters"})
VALUES = ("mean", "gmean", "median", "min", "max", "error_bar")
CODES = {
    "measurements": "unknown_measurement",
    "substances": "unknown_substance",
    "tissues": "unknown_tissue",
    "methods": "unknown_method",
    "routes": "unknown_route",
    "forms": "unknown_form",
    "applications": "unknown_application",
    "calculation_types": "unknown_calculation",
}
Issues = Iterator[ValidationIssue]


def vocabulary_terms(vocabulary: Vocabulary) -> dict[str, frozenset[str]]:
    return {
        "measurements": frozenset(rule.name for rule in vocabulary.measurements),
        "substances": frozenset(substance.name for substance in vocabulary.substances),
        "tissues": frozenset(vocabulary.tissues),
        "methods": frozenset(vocabulary.methods),
        "routes": frozenset(vocabulary.routes),
        "forms": frozenset(vocabulary.forms),
        "applications": frozenset(vocabulary.applications),
        "calculation_types": (frozenset(vocabulary.calculation_types) - {RETIRED_CALCULATION})
        | {UNSPECIFIED},
    }


def check_terms(study: LoadedStudy, vocabulary: Vocabulary) -> list[ValidationIssue]:
    terms = vocabulary_terms(vocabulary)
    rules = vocabulary.measurement_map()
    issues: list[ValidationIssue] = []
    for table in study.tables:
        columns = [column for column in table.spec.columns if column.vocabulary]
        prefixes: tuple[str, ...] = (
            ("x_", "y_") if table.kind == "scatters" else () if table.kind == "subjects" else ("",)
        )
        for row in table.rows:
            for column in columns:
                issues.extend(_term(table, row, column, terms))
            for prefix in prefixes:
                rule = rules.get(row.cells[f"{prefix}measurement"])
                if rule is not None:
                    issues.extend(_measurement(table, row, rule, prefix))
            if table.kind == "interventions" and row.cells["measurement"] in DOSING:
                for name in ("substance", "route"):
                    if not row.cells[name]:
                        issues.append(
                            row_issue(table, row, "missing_dosing_field", f"{name} is required for dosing", name)
                        )
    return issues


def _term(table: LoadedTable, row: Row, column: Column, terms: dict[str, frozenset[str]]) -> Issues:
    value = row.cells[column.name]
    if not value or column.vocabulary is None:
        return
    if column.vocabulary == "calculation_types" and value == RETIRED_CALCULATION:
        yield row_issue(
            table, row, "retired_calculation",
            "Enter geometric statistics in gmean, gsd and gcv instead of calculation 'geometric mean'",
            column.name,
        )
    elif value not in terms[column.vocabulary]:
        yield row_issue(
            table, row, CODES[column.vocabulary],
            f"Unknown {column.name.removeprefix('x_').removeprefix('y_')}: {value}",
            column.name,
            actual=value,
            hint="Candidates are spelling suggestions, not equivalent terms.",
            candidates=get_close_matches(value, sorted(terms[column.vocabulary]), n=10, cutoff=0.6),
        )


def _measurement(table: LoadedTable, row: Row, rule: MeasurementRule, prefix: str) -> Issues:
    if rule.deprecated:
        yield row_issue(table, row, "deprecated_measurement", f"{rule.name} is deprecated", f"{prefix}measurement")
    if not prefix:
        choice = row.cells["choice"]
        if choice:
            if rule.dtype not in CHOICE_TYPES or choice not in rule.choices:
                yield row_issue(
                    table, row, "invalid_choice", f"{choice!r} is not a choice of {rule.name}",
                    "choice", candidates=list(rule.choices),
                )
        elif rule.dtype in REQUIRED_CHOICE_TYPES and rule.choices:
            yield row_issue(
                table, row, "missing_choice", f"{rule.name} needs a choice", "choice",
                candidates=list(rule.choices),
            )
    values = (f"{prefix}mean",) if prefix else VALUES
    if not rule.can_negative:
        for name in values:
            value = row.values.get(name)
            if isinstance(value, float) and value < 0:
                yield row_issue(
                    table, row, "negative_value", f"{name} cannot be negative for {rule.name}",
                    name, actual=value,
                )
    if rule.time_required and table.kind in TIMED_KINDS and not row.cells[f"{prefix}time"]:
        yield row_issue(
            table, row, "missing_time",
            f"{rule.name} needs a time; use NR when the publication does not report it",
            f"{prefix}time",
        )
    has_value = any(isinstance(row.values.get(name), float) for name in values if name != "error_bar")
    if has_value and rule.units and "NO_UNIT" not in rule.units and not row.cells[f"{prefix}unit"]:
        yield row_issue(
            table, row, "missing_unit", f"{rule.name} needs a unit", f"{prefix}unit",
            candidates=list(rule.units),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_terms.py -q`
Expected: PASS

- [ ] **Step 5: Lint, format, type check, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat && uv run --locked ty check
cd .. && git add python/src/pkdb/studyformat/terms.py python/tests/studyformat/test_studyformat_terms.py
git commit -m "Check study format 2 terms against the vocabulary"
```

---

### Task 11: validate_folder

**Files:**
- Create: `python/src/pkdb/studyformat/validation.py`
- Modify: `python/src/pkdb/studyformat/__init__.py` (export `is_v2_folder`, `validate_folder`)
- Test: `python/tests/studyformat/test_studyformat_validation.py`

**Interfaces:**
- Consumes: Tasks 6 to 10; `planned_files` (Task 7); `ValidationReport`.
- Produces: `is_v2_folder(folder: Path) -> bool`; `format_issues(study) -> list[ValidationIssue]` (code `not_formatted`, error); `acknowledged(issue, study) -> bool` (only warnings; a review item with `acknowledges` equal to the code and a target matching the issue's file, row filter and column, or no target for study-wide acknowledgement); `validate_folder(folder, vocabulary, *, max_issues=1000) -> ValidationReport`.

- [ ] **Step 1: Write the failing test**

```python
import time

from pkdb.studyformat import is_v2_folder, validate_folder
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json

CMAX = {
    "subjects": "all", "interventions": "D1", "measurement": "cmax",
    "substance": "drug", "tissue": "plasma", "mean": "2.5", "sd": "0.5", "unit": "mg/l",
}
ITEM = {
    "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    "kind": "issue",
    "state": "resolved",
    "text": "The paper reports two values.",
    "author": "curator",
    "created": "2026-10-05T10:12:00Z",
    "resolved_by": "curator",
    "resolved": "2026-10-05T11:00:00Z",
}


def codes(report):
    return {issue.code for issue in report.issues}


def test_valid_study(valid_study, sf_vocabulary):
    report = validate_folder(valid_study, sf_vocabulary)
    assert report.issues == []
    assert report.valid


def test_unformatted_study_is_invalid(make_study, valid_files, sf_vocabulary):
    report = validate_folder(make_study(valid_files), sf_vocabulary)
    assert codes(report) == {"not_formatted"}
    assert not report.valid


def test_all_layers_are_collected(make_study, valid_files, tsv, sf_vocabulary):
    files = {
        **valid_files,
        "notes.csv": "x\n",
        "outputs_Tab2.tsv": tsv("outputs", {**CMAX, "subjects": "S9", "measurement": "cmaxx", "count": "x"}),
    }
    folder = make_study(files)
    format_folder(folder)
    found = codes(validate_folder(folder, sf_vocabulary))
    assert {"unknown_file", "invalid_integer", "unknown_reference", "unknown_measurement"} <= found


def test_warnings_can_be_acknowledged(valid_study, tsv, sf_vocabulary):
    (valid_study / "outputs_Tab2.tsv").write_text(
        tsv("outputs", CMAX, {**CMAX, "mean": "3"}), encoding="utf-8"
    )
    format_folder(valid_study)
    assert codes(validate_folder(valid_study, sf_vocabulary)) == {"duplicate_observation"}
    item = {
        **ITEM,
        "acknowledges": "duplicate_observation",
        "target": {"file": "outputs_Tab2.tsv", "rows": {"subjects": "all", "measurement": "cmax"}},
    }
    (valid_study / "review.json").write_text(dump_json({"status": "draft", "items": [item]}), encoding="utf-8")
    format_folder(valid_study)
    assert validate_folder(valid_study, sf_vocabulary).issues == []


def test_errors_cannot_be_acknowledged(valid_study, tsv, sf_vocabulary):
    (valid_study / "outputs_Tab2.tsv").write_text(tsv("outputs", {**CMAX, "subjects": "S9"}), encoding="utf-8")
    format_folder(valid_study)
    item = {**ITEM, "acknowledges": "unknown_reference"}
    (valid_study / "review.json").write_text(dump_json({"status": "draft", "items": [item]}), encoding="utf-8")
    format_folder(valid_study)
    assert "unknown_reference" in codes(validate_folder(valid_study, sf_vocabulary))


def test_non_ascii_names(make_study, valid_files, sf_vocabulary):
    # Review focus 4.
    files = {}
    for name, content in valid_files.items():
        name = name.replace("Example", "Dahlström2007")
        if isinstance(content, str) and name.endswith(".tsv"):
            content = content.replace("S1", "Gruppe Ä")
        if name.startswith("outputs_"):
            content = content.replace("mg/l", "µg/l")
        files[name] = content
    folder = make_study(files, name="Dahlström2007")
    assert format_folder(folder).ok
    report = validate_folder(folder, sf_vocabulary)
    assert report.issues == []


def test_large_study_is_fast(valid_study, tsv, sf_vocabulary):
    # Review focus 5: 200 series with 100 points each.
    base = {"subjects": "all", "interventions": "D1", "measurement": "concentration",
            "substance": "drug", "tissue": "plasma", "time_unit": "h", "unit": "mg/l"}
    rows = [
        {**base, "label": f"series{label}", "time": str(t), "mean": str(t + 1)}
        for label in range(200)
        for t in range(100)
    ]
    (valid_study / "timecourses_Fig1.tsv").write_text(tsv("timecourses", *rows), encoding="utf-8")
    start = time.monotonic()
    report = validate_folder(valid_study, sf_vocabulary)
    assert time.monotonic() - start < 10
    assert codes(report) <= {"not_formatted"}


def test_max_issues(make_study, valid_files, tsv, sf_vocabulary):
    rows = [{**CMAX, "mean": "bad", "comment": str(i)} for i in range(30)]
    folder = make_study({**valid_files, "outputs_Tab2.tsv": tsv("outputs", *rows)})
    report = validate_folder(folder, sf_vocabulary, max_issues=5)
    assert len(report.issues) == 5
    assert report.truncated


def test_is_v2_folder(valid_study, tmp_path):
    assert is_v2_folder(valid_study)
    old = tmp_path / "old"
    old.mkdir()
    (old / "study.json").write_text('{"sid": "X", "groupset": {}}')
    assert not is_v2_folder(old)
    (old / "study.json").write_text("{")
    assert not is_v2_folder(old)
    assert not is_v2_folder(tmp_path / "missing")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_validation.py -q`
Expected: FAIL with `ImportError: cannot import name 'is_v2_folder'`

- [ ] **Step 3: Write the implementation**

`python/src/pkdb/studyformat/validation.py`:

```python
"""Validate a study format 2 folder: layout, format, rows, relationships, vocabulary."""

from pathlib import Path

from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.validation import ValidationIssue, ValidationReport
from pkdb.studyformat.formatter import planned_files
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.load import LoadedStudy, load_study
from pkdb.studyformat.relations import check_relations
from pkdb.studyformat.rows import check_rows
from pkdb.studyformat.tables import STUDY_JSON
from pkdb.studyformat.terms import check_terms

FORMAT_VERSION = 2


def is_v2_folder(folder: Path) -> bool:
    """Whether study.json declares study format 2."""
    try:
        data = load_json((Path(folder) / STUDY_JSON).read_bytes())
    except OSError, JsonFileError:
        return False
    return isinstance(data, dict) and data.get("format") == FORMAT_VERSION


def format_issues(study: LoadedStudy) -> list[ValidationIssue]:
    issues = []
    for name, text in planned_files(study).items():
        if text is None:
            issues.append(
                make_issue("not_formatted", f"{name} has no rows; run pkdb format to remove it", file=name)
            )
        elif (study.folder / name).read_bytes() != text.encode("utf-8"):
            issues.append(
                make_issue("not_formatted", f"{name} is not in canonical form; run pkdb format", file=name)
            )
    return issues


def acknowledged(issue: ValidationIssue, study: LoadedStudy) -> bool:
    if issue.severity != "warning" or study.review is None:
        return False
    for item in study.review.items:
        if item.acknowledges != issue.code:
            continue
        target = item.target
        if target is None or target.file is None:
            return True
        source = issue.source
        if source is None or source.file != target.file:
            continue
        if target.column and source.header != target.column:
            continue
        if target.rows:
            table = study.table(target.file)
            lines = {
                row.line
                for row in (table.rows if table else [])
                if all(row.cells.get(key) == value for key, value in target.rows.items())
            }
            if source.row not in lines:
                continue
        return True
    return False


def validate_folder(
    folder: Path, vocabulary: Vocabulary, *, max_issues: int = 1000
) -> ValidationReport:
    study = load_study(Path(folder))
    issues = [
        *study.issues,
        *format_issues(study),
        *check_rows(study),
        *check_relations(study),
        *check_terms(study, vocabulary),
    ]
    kept = [issue for issue in issues if not acknowledged(issue, study)]
    return ValidationReport(issues=kept).finalize(max_issues)
```

Replace `python/src/pkdb/studyformat/__init__.py` with:

```python
"""Study format 2: fixed table templates committed as canonical TSV files."""

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.validation import FORMAT_VERSION, is_v2_folder, validate_folder

__all__ = ["FORMAT_VERSION", "format_folder", "is_v2_folder", "validate_folder"]
```

`except OSError, JsonFileError:` is the Python 3.14 form of catching two exceptions without a name (PEP 758), as used elsewhere in this package; if `ruff format` rewrites it to the parenthesized form, keep ruff's output.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd python && uv run --locked pytest tests/studyformat -q`
Expected: PASS

- [ ] **Step 5: Whole suite, lint, type check, commit**

```bash
cd python && uv run --locked pytest -q && uv run --locked ruff format . && uv run --locked ruff check . && uv run --locked ty check
cd .. && git add python/src/pkdb/studyformat python/tests/studyformat
git commit -m "Validate study format 2 folders across all layers"
```

---

### Task 12: JSON Schema export and column reference

**Files:**
- Create: `python/src/pkdb/studyformat/export.py`
- Create: `docs/study-format.md` (generated)
- Modify: `zensical.toml` (navigation entry after "Local curation")
- Test: `python/tests/studyformat/test_studyformat_export.py`

**Interfaces:**
- Consumes: `TABLES`, `TableSpec`, `table_file` (Task 1); `Column`, `ColumnType` (Task 1); `parse_cell` (Task 3); `StudyMetadata`, `Review` (Task 4).
- Produces: `row_model(spec) -> type[BaseModel]`; `type_label(column) -> str`; `json_schemas() -> dict[str, dict]` with keys `study.schema.json`, `review.schema.json` and `<kind>.row.schema.json` for every table; `column_reference() -> str` (Markdown page).

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from pkdb.studyformat.export import column_reference, json_schemas
from pkdb.studyformat.tables import TABLES

DOCS = Path(__file__).resolve().parents[3] / "docs" / "study-format.md"


def test_schema_files():
    schemas = json_schemas()
    assert sorted(schemas) == sorted(
        ["study.schema.json", "review.schema.json"]
        + [f"{kind}.row.schema.json" for kind in TABLES]
    )
    assert "format" in schemas["study.schema.json"]["properties"]
    assert "items" in schemas["review.schema.json"]["properties"]


def test_row_schema_mirrors_the_table():
    schema = json_schemas()["outputs.row.schema.json"]
    assert list(schema["properties"]) == list(TABLES["outputs"].names)
    assert schema["x-pkdb-columns"] == list(TABLES["outputs"].names)
    assert schema["x-pkdb-file"] == "outputs_<source>.tsv"
    assert sorted(schema["required"]) == ["measurement", "subjects"]
    assert schema["properties"]["error_type"]["enum"] == ["sd", "se", "gsd"]
    assert schema["properties"]["mean"]["examples"] == [2.9]
    time = schema["properties"]["time"]
    assert {"type": "number"} in time["anyOf"] and {"const": "NR", "type": "string"} in time["anyOf"]
    assert schema["properties"]["interventions"]["anyOf"][0]["type"] == "array"


def test_column_reference_lists_every_column():
    text = column_reference()
    assert text.startswith("<!-- Generated by `pkdb schema docs`")
    for spec in TABLES.values():
        for column in spec.columns:
            assert f"| `{column.name}` |" in text
    assert "\u2014" not in text


def test_committed_column_reference_is_current():
    assert DOCS.read_text(encoding="utf-8") == column_reference()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_export.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkdb.studyformat.export'`

- [ ] **Step 3: Write the implementation**

```python
"""JSON Schema and the Markdown column reference, derived from the table declarations."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from pkdb.studyformat.cells import parse_cell
from pkdb.studyformat.columns import Column, ColumnType
from pkdb.studyformat.models import Review, StudyMetadata
from pkdb.studyformat.tables import TABLES, TableSpec, table_file

T = ColumnType
_TYPES: dict[ColumnType, Any] = {
    T.TEXT: str,
    T.NAME: str,
    T.NAMES: list[str],
    T.NUMBER: float,
    T.INTEGER: Annotated[int, Field(ge=0)],
    T.TIME: float,
    T.TIMES: list[float],
    T.UNIT: str,
    T.TERM: str,
    T.ENUM: str,
    T.SOURCE: str,
}
_LABELS = {
    T.TEXT: "text",
    T.NAME: "name",
    T.NAMES: "comma-separated names",
    T.NUMBER: "number",
    T.INTEGER: "whole number",
    T.TIME: "number",
    T.TIMES: "number or `;`-separated numbers",
    T.UNIT: "unit",
    T.TERM: "vocabulary term",
    T.ENUM: "choice",
    T.SOURCE: "source",
}


def _file(spec: TableSpec) -> str:
    return table_file(spec.kind, "<source>" if spec.per_source else None)


def _annotation(column: Column) -> Any:
    annotation = _TYPES[column.type]
    return annotation | Literal["NR"] if column.allows_nr else annotation


def _example(column: Column) -> list[Any] | None:
    if not column.example:
        return None
    value, _ = parse_cell(column, column.example)
    return [list(value) if isinstance(value, tuple) else value]


def row_model(spec: TableSpec) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for column in spec.columns:
        options = {
            "description": column.description,
            "examples": _example(column),
            "json_schema_extra": {"enum": list(column.choices)} if column.choices else None,
        }
        if column.name in spec.required_columns:
            fields[column.name] = (_annotation(column), Field(**options))
        else:
            fields[column.name] = (_annotation(column) | None, Field(default=None, **options))
    return create_model(
        f"{spec.kind.capitalize()}Row",
        __config__=ConfigDict(extra="forbid", title=f"Row of {_file(spec)}"),
        **fields,
    )


def json_schemas() -> dict[str, dict]:
    schemas = {
        "study.schema.json": StudyMetadata.model_json_schema(),
        "review.schema.json": Review.model_json_schema(),
    }
    for spec in TABLES.values():
        schema = row_model(spec).model_json_schema()
        schema["description"] = (
            f"{spec.description} Each line of the TSV file is one row; an empty cell is null."
        )
        schema["x-pkdb-file"] = _file(spec)
        schema["x-pkdb-columns"] = list(spec.names)
        schemas[f"{spec.kind}.row.schema.json"] = schema
    return schemas


def type_label(column: Column) -> str:
    if column.vocabulary:
        label = f"vocabulary: {column.vocabulary.replace('_', ' ')}"
    elif column.choices:
        label = "one of " + ", ".join(f"`{choice}`" for choice in column.choices)
    else:
        label = _LABELS[column.type]
    return f"{label} or `NR`" if column.allows_nr else label


def _required(spec: TableSpec, column: Column) -> str:
    if column.owned:
        return "written by `pkdb format`"
    return "yes" if column.name in spec.required_columns else ""


def column_reference() -> str:
    lines = [
        "<!-- Generated by `pkdb schema docs` from python/src/pkdb/studyformat. Do not edit this file. -->",
        "",
        "# Study format",
        "",
        "A study folder in study format 2 contains `study.json`, `reference.json`, `review.json`, the tab-separated tables below, the publication PDF and an image `<study>_<source>.png` for every paper table or figure the data come from. `pkdb format` writes all files in canonical form, `pkdb validate` checks them, and `pkdb schema export` writes the same definitions as JSON Schema.",
        "",
        "## Tables",
        "",
        "| File | Content | Required |",
        "|---|---|---|",
    ]
    for spec in TABLES.values():
        lines.append(f"| `{_file(spec)}` | {spec.description} | {'yes' if spec.required else ''} |")
    lines += [
        "",
        "## TSV encoding",
        "",
        "- UTF-8 without byte order mark, LF line endings and a final newline.",
        "- Tab separated without quoting. Cells contain no tabs or line breaks.",
        "- One header row with every template column in template order.",
        "- An empty cell means missing. `NR` (not reported) is allowed only in time columns.",
        "- Numbers use a decimal point and are written in their shortest form.",
        "- `pkdb format` sorts the rows and writes the `study` column and, in files named after a source, the `source` column.",
    ]
    for spec in TABLES.values():
        lines += [
            "",
            f"## `{_file(spec)}`",
            "",
            spec.description,
            "",
            "| Column | Type | Required | Description |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| `{column.name}` | {type_label(column)} | {_required(spec, column)} | {column.description} |"
            for column in spec.columns
        ]
    return "\n".join(lines) + "\n"
```

Generate the committed page from the repository root:

```bash
cd python && uv run --locked python -c "from pkdb.studyformat.export import column_reference; import pathlib; pathlib.Path('../docs/study-format.md').write_text(column_reference(), encoding='utf-8')"
```

In `zensical.toml`, insert after the line `  { "Local curation" = "local-curation.md" },`:

```toml
  { "Study format" = "study-format.md" },
```

- [ ] **Step 4: Run tests and the docs build**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_export.py -q`
Expected: PASS

Run: `cd .. && uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean 2>&1 | grep -iE "error|warn" ; echo done`
Expected: no error or warning lines, then `done`.

If the JSON Schema layout of `Literal["NR"]` or the integer constraint differs from the test (for example `{"const": "NR", "type": "string"}` versus `{"enum": ["NR"], "type": "string"}`), adjust the assertion to Pydantic's actual output for the `time` property only; the other assertions stay.

- [ ] **Step 5: Lint, format, type check, commit**

```bash
cd python && uv run --locked ruff format src/pkdb/studyformat tests/studyformat && uv run --locked ruff check src/pkdb/studyformat tests/studyformat && uv run --locked ty check
cd .. && git add python/src/pkdb/studyformat/export.py python/tests/studyformat/test_studyformat_export.py docs/study-format.md zensical.toml
git commit -m "Export study format 2 as JSON Schema and a column reference page"
```

---

### Task 13: Command line

**Files:**
- Create: `python/src/pkdb/studyformat_cli.py`
- Modify: `python/src/pkdb/cli.py` (register and dispatch `format` and `schema`; format 2 branch in the validate loop; refuse format 2 in `prepare` and `upload`)
- Modify: `docs/python-client.md` (new section "Study format 2 folders")
- Test: `python/tests/studyformat/test_studyformat_cli.py`

**Interfaces:**
- Consumes: `format_folder`, `is_v2_folder`, `validate_folder` (Tasks 7, 11); `json_schemas`, `column_reference` (Task 12); `pkdb.preparation.study_folders`; `pkdb.cache.atomic_json`, `atomic_text`; `pkdb.domain.vocabulary.vocabulary_hash`.
- Produces: `studyformat_cli.register(commands)`, `studyformat_cli.run(args) -> int`; commands `pkdb format FOLDER [--check] [--format human|json]`, `pkdb schema export --output DIR`, `pkdb schema docs --output FILE`. `pkdb validate` on a format 2 folder emits the usual result object with `study_format: 2`, `sid: "<substance>/<name>"`, `report`, `vocabulary_version`, `vocabulary_hash`.

- [ ] **Step 1: Write the failing test**

```python
import json

from pkdb.cli import main


def lines(capsys):
    return [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]


def test_format_command(make_study, valid_files, capsys):
    folder = make_study(valid_files)
    assert main(["format", str(folder), "--check", "--format", "json"]) == 1
    entry = lines(capsys)[0]
    assert entry["ok"] and "subjects.tsv" in {change["file"] for change in entry["changes"]}
    assert main(["format", str(folder), "--format", "json"]) == 0
    capsys.readouterr()
    assert main(["format", str(folder), "--check", "--format", "json"]) == 0
    assert lines(capsys)[0]["changes"] == []


def test_format_skips_format_1(tmp_path, capsys):
    folder = tmp_path / "Old"
    folder.mkdir()
    (folder / "study.json").write_text('{"sid": "X"}')
    assert main(["format", str(folder), "--format", "json"]) == 0
    assert "format 1" in lines(capsys)[0]["skipped"]


def test_format_reports_problems_for_people(make_study, valid_files, capsys):
    folder = make_study({**valid_files, "outputs_Tab2.tsv": "group\nall\n"})
    assert main(["format", str(folder), "--format", "human"]) == 1
    out = capsys.readouterr().out
    assert "caffeine/Example" in out
    assert "unknown_column" in out and "subjects" in out


def test_validate_format_2(valid_study, sf_vocabulary, tmp_path, capsys):
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    args = ["validate", str(valid_study), "--offline", "--vocabulary", str(lock), "--format", "json"]
    assert main(args) == 0
    result = lines(capsys)[-1]
    assert result["ok"] and result["study_format"] == 2
    assert result["sid"] == "caffeine/Example"
    assert result["report"]["issues"] == []


def test_validate_format_2_failure(valid_study, sf_vocabulary, tmp_path, capsys):
    (valid_study / "notes.csv").write_text("x\n")
    lock = tmp_path / "vocabulary.json"
    sf_vocabulary.save(lock)
    args = ["validate", str(valid_study), "--offline", "--vocabulary", str(lock), "--format", "json"]
    assert main(args) == 1
    result = lines(capsys)[-1]
    assert not result["ok"]
    assert [issue["code"] for issue in result["report"]["issues"]] == ["unknown_file"]


def test_prepare_and_upload_refuse_format_2(valid_study, capsys, monkeypatch):
    assert main(["prepare", str(valid_study), "--offline", "--format", "json"]) == 1
    assert "study format 2" in capsys.readouterr().err
    monkeypatch.setenv("PKDB_API_KEY", "test-key")
    args = ["upload", str(valid_study), "--endpoint", "http://127.0.0.1:9", "--format", "json"]
    assert main(args) == 1
    assert "study format 2" in capsys.readouterr().err


def test_schema_commands(tmp_path, capsys):
    assert main(["schema", "export", "--output", str(tmp_path / "schemas")]) == 0
    assert (tmp_path / "schemas" / "outputs.row.schema.json").is_file()
    assert main(["schema", "docs", "--output", str(tmp_path / "reference.md")]) == 0
    assert "# Study format" in (tmp_path / "reference.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_cli.py -q`
Expected: FAIL (argparse exits with `invalid choice: 'format'`)

- [ ] **Step 3: Write the implementation**

`python/src/pkdb/studyformat_cli.py`:

```python
"""Commands for study format 2 folders: format and schema."""

import json
import sys
from pathlib import Path


def register(commands) -> None:
    command = commands.add_parser(
        "format",
        help="Write study format 2 folders in canonical form",
        description="Write study format 2 folders in canonical form: sorted rows, canonical numbers and JSON, filled study and source columns.",
    )
    command.add_argument("folder", type=Path, help="Study folder or parent directory")
    command.add_argument(
        "--check",
        action="store_true",
        help="Only report files that need formatting; exit with 1 if any do",
    )
    command.add_argument(
        "--format",
        dest="output",
        choices=("human", "json"),
        help="Output format (default: human on a terminal, otherwise json)",
    )
    schema = commands.add_parser(
        "schema",
        help="Export the study format 2 schema",
        description="Export the study format 2 schema as JSON Schema or as the Markdown column reference.",
    )
    actions = schema.add_subparsers(dest="action", required=True)
    export = actions.add_parser(
        "export", help="Write JSON Schema files for study.json, review.json and every table"
    )
    export.add_argument("--output", type=Path, required=True, help="Directory for the schema files")
    docs = actions.add_parser("docs", help="Write the Markdown column reference")
    docs.add_argument("--output", type=Path, required=True, help="Markdown file to write")


def run(args) -> int:
    return _schema(args) if args.command == "schema" else _format(args)


def _schema(args) -> int:
    from pkdb.cache import atomic_json, atomic_text
    from pkdb.studyformat.export import column_reference, json_schemas

    if args.action == "export":
        schemas = json_schemas()
        for name, schema in schemas.items():
            atomic_json(args.output / name, schema)
        print(f"Wrote {len(schemas)} schema files to {args.output}")
    else:
        atomic_text(args.output, column_reference())
        print(f"Wrote {args.output}")
    return 0


def _label(folder: Path) -> str:
    return f"{folder.parent.name}/{folder.name}"


def _print_human(folder: Path, result, check: bool) -> None:
    written = [change.file for change in result.changes if change.action == "write"]
    removed = [change.file for change in result.changes if change.action == "delete"]
    parts = []
    if written:
        parts.append(("would rewrite " if check else "rewrote ") + ", ".join(written))
    if removed:
        parts.append(("would remove " if check else "removed ") + ", ".join(removed))
    print(f"{_label(folder)}: {'; '.join(parts) if parts else 'already formatted'}")
    for issue in result.issues:
        source = issue.source
        where = source.file if source else ""
        if source and source.row:
            where += f" line {source.row}"
        print(f"  {where}: {issue.message} [{issue.code}]")
        for suggestion in issue.suggestions:
            if suggestion.candidates:
                print(f"    Did you mean: {', '.join(map(str, suggestion.candidates))}")


def _format(args) -> int:
    from pkdb.preparation import study_folders
    from pkdb.studyformat import format_folder, is_v2_folder

    human = args.output == "human" or (args.output is None and sys.stdout.isatty())
    try:
        folders = study_folders(args.folder)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    failed = False
    for folder in folders:
        if not is_v2_folder(folder):
            message = "study format 1; convert it with pkdb migrate"
            if human:
                print(f"{_label(folder)}: skipped, {message}")
            else:
                print(json.dumps({"path": str(folder), "skipped": message}), flush=True)
            continue
        result = format_folder(folder, check=args.check)
        failed |= not result.ok or (args.check and bool(result.changes))
        if human:
            _print_human(folder, result, args.check)
        else:
            entry = {
                "path": str(folder),
                "ok": result.ok,
                "changes": [{"file": c.file, "action": c.action} for c in result.changes],
                "issues": [issue.model_dump(mode="json") for issue in result.issues],
            }
            print(json.dumps(entry, ensure_ascii=False), flush=True)
    return int(failed)
```

Changes in `python/src/pkdb/cli.py`:

1. Replace `from pkdb import import_cli, reference_cli` and the two `register` calls with:

```python
    from pkdb import import_cli, reference_cli, studyformat_cli

    reference_cli.register(commands)
    import_cli.register(commands)
    studyformat_cli.register(commands)
```

2. After `if args.command == "reference": return reference_cli.run(args, client=client)` add:

```python
    if args.command in {"format", "schema"}:
        return studyformat_cli.run(args)
```

3. Directly after `folders = study_folders(args.folder)` (inside the existing `try`) add:

```python
        if args.command in {"prepare", "upload"}:
            from pkdb.studyformat import is_v2_folder

            if format2 := [folder for folder in folders if is_v2_folder(folder)]:
                raise ValueError(
                    f"{len(format2)} folder(s) use study format 2, which pkdb {args.command} does not support yet; run pkdb validate instead"
                )
```

4. In the per-folder loop, wrap the existing body of the `try:` (from `if tables := sync_tsvs(folder):` to `result["ok"] = True`) in the `else` branch of:

```python
            from pkdb.studyformat import is_v2_folder, validate_folder

            if is_v2_folder(folder):
                from pkdb.domain.vocabulary import vocabulary_hash

                report = validate_folder(folder, snapshot)
                batch["vocabulary_hash"] = vocabulary_hash(snapshot)
                result.update(
                    study_format=2,
                    sid=f"{folder.parent.name}/{folder.name}",
                    report=report.model_dump(mode="json"),
                    vocabulary_version=snapshot.version,
                    vocabulary_hash=vocabulary_hash(snapshot),
                )
                result["ok"] = report.valid
                if not report.valid:
                    result["error"] = "Study validation failed"
            else:
                ...existing body unchanged...
```

Append to `docs/python-client.md` a section (each paragraph on one line):

```markdown
## Study format 2 folders

Study folders whose `study.json` contains `"format": 2` keep their data in fixed tab-separated tables; see [Study format](study-format.md). `pkdb format FOLDER` writes every file of such folders in canonical form, and `pkdb format FOLDER --check` only reports the files that would change. `pkdb validate FOLDER` checks layout, format, rows, relationships between tables and vocabulary terms, and reports every issue with file, row and column. `pkdb schema export --output DIR` writes JSON Schema files for `study.json`, `review.json` and every table, and `pkdb schema docs --output FILE` writes the column reference. `pkdb prepare` and `pkdb upload` do not accept study format 2 folders yet.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd python && uv run --locked pytest tests/studyformat/test_studyformat_cli.py -q`
Expected: PASS

- [ ] **Step 5: Whole suite, lint, type check, docs, commit**

```bash
cd python && uv run --locked pytest -q && uv run --locked ruff format . && uv run --locked ruff check . && uv run --locked ty check
cd .. && uvx --python 3.14 --with-requirements docs/requirements.txt zensical build --clean 2>&1 | grep -iE "error|warn"; echo done
git add python/src/pkdb/studyformat_cli.py python/src/pkdb/cli.py docs/python-client.md python/tests/studyformat/test_studyformat_cli.py
git commit -m "Add pkdb format and pkdb schema, validate study format 2 folders"
```
