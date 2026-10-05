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
# Codes that stop a file from loading or formatting.
STRUCTURAL = frozenset(
    {
        "invalid_encoding",
        "missing_header",
        "unknown_column",
        "duplicate_column",
        "extra_cells",
        "invalid_json",
        "duplicate_key",
        "invalid_study_json",
        "invalid_review_json",
        "invalid_reference_json",
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
                "missing_header",
                "The first line must contain the column names",
                file=file,
                line=1,
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
                        file=file,
                        line=1,
                        column=index,
                        header=name,
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
                    file=file,
                    line=1,
                    column=index,
                    header=name,
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
                    file=file,
                    line=line.number,
                    column=extra[0],
                )
            )
    if issues:
        return None, issues
    rows = []
    for line in parsed.lines:
        cells, values = {}, {}
        for column in spec.columns:
            index = positions.get(column.name)
            raw = (
                line.cells[index]
                if index is not None and index < len(line.cells)
                else ""
            )
            text = canonical_cell(column, raw)
            value, problem = parse_cell(column, text)
            cells[column.name], values[column.name] = text, value
            if problem and not column.owned:
                issues.append(
                    make_issue(
                        problem.code,
                        problem.message,
                        file=file,
                        line=line.number,
                        column=index,
                        header=column.name,
                        hint=problem.hint,
                        actual=text,
                    )
                )
        if any(cells[column.name] for column in spec.columns if not column.owned):
            rows.append(Row(line.number, cells, values))
    return LoadedTable(file, spec, source, parsed.header, rows), issues


# Marks a JSON file that cannot be used: missing, or already reported.
_UNUSABLE = object()


def _read_json(study: LoadedStudy, name: str) -> object:
    # Symbolic links are reported by the layout and never followed.
    if name not in study.layout.files:
        return _UNUSABLE
    try:
        return load_json((study.folder / name).read_bytes())
    except JsonFileError as error:
        study.issues.append(make_issue(error.code, str(error), file=name))
        return _UNUSABLE


def _validate[M: BaseModel](
    study: LoadedStudy, name: str, model: type[M], code: str
) -> M | None:
    data = _read_json(study, name)
    if data is _UNUSABLE:
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
    if (
        _validate(study, REFERENCE_JSON, Reference, "invalid_reference_json")
        is not None
    ):
        reference = _read_json(study, REFERENCE_JSON)
        study.reference = reference if isinstance(reference, dict) else None
    return study
