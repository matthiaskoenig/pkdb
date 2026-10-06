"""Read a study format 2 folder into typed tables without judging the content."""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from difflib import get_close_matches
from io import BytesIO
from pathlib import Path

from pydantic import BaseModel, ValidationError

from pkdb.schemas.validation import ValidationIssue, fail
from pkdb.studyformat.cells import canonical_cell, parse_cell
from pkdb.studyformat.digitize import LoadedDigitization, load_digitization
from pkdb.studyformat.issues import LISTED, IssueCap, make_issue
from pkdb.studyformat.jsonio import JsonFileError, load_json
from pkdb.studyformat.layout import Layout, scan_folder
from pkdb.studyformat.models import ReferenceSnapshot, Review, StudyMetadata
from pkdb.studyformat.raw import LoadedRaw, load_raw
from pkdb.studyformat.tables import (
    REFERENCE_JSON,
    REVIEW_JSON,
    STUDY_JSON,
    TABLES,
    TableSpec,
)
from pkdb.studyformat.text import TooManyCells, TsvError, TsvLine, read_tsv

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
        "merge_conflict",
        "missing_header",
        "unknown_column",
        "duplicate_column",
        "extra_cells",
        "too_many_columns",
        "stray_text",
        "invalid_json",
        "duplicate_key",
        "invalid_study_json",
        "invalid_review_json",
        "invalid_reference_json",
        "digitization_invalid",
        "digitization_unsupported",
    }
)


@dataclass(frozen=True)
class Row:
    """One data line of a table: its line number and the cell texts and typed values."""

    line: int
    cells: dict[str, str]
    values: dict[str, object]


@dataclass
class LoadedTable:
    """A table file read into rows, with its header and source."""

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

    def matching_lines(self, filters: Mapping[str, str]) -> frozenset[int]:
        """Lines of the rows that have every cell value of a review target's `rows`."""
        return frozenset(
            row.line
            for row in self.rows
            if all(row.cells.get(key) == value for key, value in filters.items())
        )


@dataclass
class LoadedStudy:
    """A study folder read into typed tables, JSON files and the issues found."""

    layout: Layout
    tables: list[LoadedTable] = field(default_factory=list)
    raw_tables: list[LoadedRaw] = field(default_factory=list)
    digitizations: list[LoadedDigitization] = field(default_factory=list)
    # Table kinds that cannot be used: the file failed to load, or a required
    # table is missing. Nothing refers into them.
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

    def raw(self, file: str) -> LoadedRaw | None:
        return next((raw for raw in self.raw_tables if raw.file == file), None)

    def digitization(self, source: str) -> LoadedDigitization | None:
        return next((d for d in self.digitizations if d.source == source), None)

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


@dataclass
class RowLimit:
    """Counts the data lines of a study's tables against the upload row limit.

    Reading stops at the first line beyond the limit, so memory stays bounded
    by the limit and not by the size of the files.
    """

    maximum: int | None = None
    lines: int = 0

    def count(self) -> None:
        self.lines += 1
        if self.maximum is not None and self.lines > self.maximum:
            fail("row_limit", f"The study tables have more than {self.maximum} rows")


def _header_issues(
    file: str, header: tuple[str, ...], spec: TableSpec, filled: set[int]
) -> tuple[dict[str, int], list[ValidationIssue]]:
    # Column positions and the issues of the header. An unnamed column is
    # ignored unless a line has a value in it (`filled`). A header of very many
    # columns lists the first of them and counts the rest.
    issues = []
    cap = IssueCap()
    positions: dict[str, int] = {}
    for index, name in enumerate(header):
        if name in spec.names:
            if name not in positions:
                positions[name] = index
            elif cap.admit("duplicate_column"):
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
        elif (name != "" or index in filled) and cap.admit("unknown_column"):
            issues.append(
                make_issue(
                    "unknown_column",
                    f"Unknown column {name!r}",
                    file=file,
                    line=1,
                    column=index,
                    header=name,
                    candidates=_candidates(name, spec),
                )
            )
    kinds = {"duplicate_column": "repeat a column", "unknown_column": "are unknown"}
    issues.extend(
        make_issue(
            code, f"{total:,} header columns {kinds[code]}; {LISTED}", file=file, line=1
        )
        for code, total in cap.beyond()
    )
    return positions, issues


def load_table(
    file: str,
    data: bytes | Iterable[bytes],
    spec: TableSpec,
    source: str | None,
    *,
    study: str,
    limit: RowLimit | None = None,
) -> tuple[LoadedTable | None, list[ValidationIssue]]:
    """Read one table; `study` and `source` are the values of the owned columns.

    `data` is the content of the file, or its lines as a binary file yields
    them. The file is read one line at a time; `limit` counts its data lines
    and stops reading at the first line beyond the row limit.
    """
    lines = read_tsv(BytesIO(data) if isinstance(data, bytes) else data)
    owned = {"study": study, "source": source or ""}
    conflict: int | None = None
    header: tuple[str, ...] = ()
    unnamed: set[int] = set()
    filled: set[int] = set()
    positions: dict[str, int] = {}
    broken: list[ValidationIssue] = []
    extra: list[ValidationIssue] = []
    rows: list[Row] = []
    issues: list[ValidationIssue] = []
    stray: list[ValidationIssue] = []
    try:
        for line in lines:
            if line.number == 1:
                header = line.cells
                unnamed = {index for index, name in enumerate(header) if name == ""}
                positions, broken = _header_issues(file, header, spec, set())
            elif limit is not None:
                limit.count()
            if line.conflict and conflict is None:
                conflict = line.number
            if line.number == 1 or conflict is not None or not any(header):
                # Only the encoding and the row limit still matter.
                continue
            if unnamed:
                # Linear in the cells of the line, however many columns are unnamed.
                filled.update(
                    index
                    for index, cell in enumerate(line.cells)
                    if cell and index in unnamed
                )
            surplus = [
                index
                for index in range(len(header), len(line.cells))
                if line.cells[index]
            ]
            if surplus:
                extra.append(
                    make_issue(
                        "extra_cells",
                        f"Row has values beyond the {len(header)} header columns",
                        file=file,
                        line=line.number,
                        column=surplus[0],
                    )
                )
            if broken or extra:
                # The table cannot load; its cells are not judged.
                continue
            row, problems, unexpected = _read_row(file, line, spec, positions, owned)
            issues.extend(problems)
            if row is not None:
                rows.append(row)
            elif unexpected is not None:
                stray.append(unexpected)
    except TooManyCells as error:
        return None, [
            make_issue("too_many_columns", str(error), file=file, line=error.number)
        ]
    except TsvError as error:
        return None, [make_issue("invalid_encoding", str(error), file=file)]
    if conflict is not None:
        return None, [
            make_issue(
                "merge_conflict",
                f"Line {conflict} is a git conflict marker; resolve the git conflict and remove the markers",
                file=file,
                line=conflict,
            )
        ]
    if not any(header):
        return None, [
            make_issue(
                "missing_header",
                "The first line must contain the column names",
                file=file,
                line=1,
            )
        ]
    _, structure = _header_issues(file, header, spec, filled)
    if structure or extra:
        return None, [*structure, *extra]
    if stray:
        return None, stray
    return LoadedTable(file, spec, source, header, rows), issues


def _read_row(
    file: str,
    line: TsvLine,
    spec: TableSpec,
    positions: Mapping[str, int],
    owned: Mapping[str, str],
) -> tuple[Row | None, list[ValidationIssue], ValidationIssue | None]:
    # The row with the issues of its cells, or no row for an empty line and
    # the stray_text issue when an owned column has text it should not have.
    cells, values, issues = {}, {}, []
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
                    file=file,
                    line=line.number,
                    column=index,
                    header=column.name,
                    hint=problem.hint,
                    actual=text,
                )
            )
    if any(cells[column.name] for column in spec.columns if not column.owned):
        return Row(line.number, cells, values), issues, None
    # A row with the values `pkdb format` writes and nothing else is empty;
    # other text only in owned columns would be lost when formatting.
    unexpected = [
        column.name
        for column in spec.columns
        if column.owned and cells[column.name] not in ("", owned[column.name])
    ]
    if not unexpected:
        return None, issues, None
    name = unexpected[0]
    return (
        None,
        issues,
        make_issue(
            "stray_text",
            f"Line {line.number} has text only in the {name} column, which pkdb format writes; this is often a broken multi-line cell or a leftover of a merge",
            file=file,
            line=line.number,
            column=positions[name],
            header=name,
            actual=cells[name],
        ),
    )


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


def validation_issues(
    error: ValidationError, file: str, code: str
) -> list[ValidationIssue]:
    """Extract validation issues from a Pydantic ValidationError.

    Returns a list of ValidationIssue objects from the error details,
    respecting the issue cap as today.
    """
    issues = []
    cap = IssueCap()
    for detail in error.errors(include_url=False):
        if not cap.admit(code):
            continue
        path = ".".join(str(part) for part in detail["loc"])
        issues.append(
            make_issue(
                code,
                f"{path or file}: {detail['msg']}",
                file=file,
                field=path or None,
            )
        )
    issues.extend(
        make_issue(
            code, f"{total:,} entries of {file} are invalid; {LISTED}", file=file
        )
        for code, total in cap.beyond()
    )
    return issues


def _validate[M: BaseModel](
    study: LoadedStudy, name: str, model: type[M], code: str
) -> M | None:
    data = _read_json(study, name)
    if data is _UNUSABLE:
        return None
    try:
        return model.model_validate(data)
    except ValidationError as error:
        study.issues.extend(validation_issues(error, name, code))
        return None


def load_study(
    folder: Path, *, max_rows: int | None = None, max_files: int | None = None
) -> LoadedStudy:
    """Read a study folder into typed tables and JSON files; problems become issues.

    Upload limits fail with `file_limit` when the study has more than
    `max_files` files besides study.json and reference.json, and with
    `row_limit` as soon as its tables have more than `max_rows` data lines.
    """
    study = LoadedStudy(layout=(layout := scan_folder(Path(folder))))
    study.issues.extend(layout.issues)
    files = layout.files - {STUDY_JSON, REFERENCE_JSON}
    if max_files is not None and len(files) > max_files:
        fail("file_limit", f"The study has more than {max_files} files")
    limit = RowLimit(max_rows)
    for table_file in layout.tables:
        with (layout.folder / table_file.name).open("rb") as stream:
            table, issues = load_table(
                table_file.name,
                stream,
                table_file.spec,
                table_file.source,
                study=layout.study,
                limit=limit,
            )
        study.issues.extend(issues)
        if table is None:
            study.broken.add(table_file.spec.kind)
        else:
            study.tables.append(table)
    for raw_file in layout.raw_tables:
        with (layout.folder / raw_file.name).open("rb") as stream:
            raw, issues = load_raw(raw_file.name, stream, raw_file.source, limit=limit)
        study.issues.extend(issues)
        if raw is not None:
            study.raw_tables.append(raw)
    for digitization_file in layout.digitizations:
        loaded, issues = load_digitization(
            digitization_file.name,
            (layout.folder / digitization_file.name).read_bytes(),
            digitization_file.source,
        )
        study.issues.extend(issues)
        if loaded is not None:
            study.digitizations.append(loaded)
    present = {table_file.spec.kind for table_file in layout.tables}
    study.broken.update(
        spec.kind
        for spec in TABLES.values()
        if spec.required and spec.kind not in present
    )
    study.metadata = _validate(study, STUDY_JSON, StudyMetadata, "invalid_study_json")
    study.review = _validate(study, REVIEW_JSON, Review, "invalid_review_json")
    if (
        _validate(study, REFERENCE_JSON, ReferenceSnapshot, "invalid_reference_json")
        is not None
    ):
        reference = _read_json(study, REFERENCE_JSON)
        study.reference = reference if isinstance(reference, dict) else None
    return study
