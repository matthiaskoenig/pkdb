"""Read the study workbook back into canonical TSV tables (spec 10.2, 10.3 and 10.6)."""

import re
import warnings
from collections.abc import Callable, Iterable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import date, time, timedelta
from io import BytesIO
from pathlib import Path

import openpyxl
from openpyxl.styles.numbers import is_date_format
from openpyxl.workbook import Workbook

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.formatter import subject_order, table_rows
from pkdb.studyformat.issues import LISTED, IssueCap, column_letter, make_issue
from pkdb.studyformat.load import STRUCTURAL, LoadedTable, RowLimit, load_table
from pkdb.studyformat.tables import TableSpec, parse_table_file, table_file
from pkdb.studyformat.text import format_number, render_tsv
from pkdb.studyformat.workbook.base import (
    BASE_SHEET,
    BaseError,
    WorkbookBase,
    parse_base,
)

SUBJECTS = "subjects"
# The texts of the error values of Excel and LibreOffice.
ERROR_VALUES = frozenset(
    {
        "#NULL!",
        "#DIV/0!",
        "#VALUE!",
        "#REF!",
        "#NAME?",
        "#NUM!",
        "#N/A",
        "#GETTING_DATA",
    }
)
# The error value of a date-formatted number that openpyxl cannot convert.
OUTSIDE_CALENDAR = "#VALUE!"
LINE_BREAK = re.compile(r"[\t\n\r]")
LINE_BREAKS = {"\t": "tab", "\n": "line break", "\r": "carriage return"}
DATE_HINT = (
    "The spreadsheet converted this cell to a date; format the column as text "
    "and enter the value again."
)
CELL_ISSUES = {
    "cell_line_break": "contain a tab or a line break",
    "cell_date": "hold a date or a time",
    "cell_percent": "are formatted as percentages",
    "cell_error": "hold an error value",
    "formula_without_value": "hold a formula without a saved value",
    "formula_value": "hold formulas that are stored as their values",
    "value_outside_table": "have values outside the header columns",
}
SHEET_HINT = (
    "Rename the sheet to subjects, interventions, characteristica or "
    "<kind>_<source>, such as outputs_Tab2, or start its name with _ to keep it as "
    "a scratch sheet."
)

# The code, message and hint of an issue at a cell.
type Problem = tuple[str, str, str | None]
# Reports a problem at a sheet row and a 0-based column, with the column header.
type Report = Callable[[Problem, int, int, str | None], None]


@dataclass(frozen=True)
class SheetTable:
    """A data sheet as the canonical TSV text of its table file.

    `rows[i]` is the sheet row of canonical line `i + 1`; `rows[0]` is 1, the header.
    """

    file: str
    text: str
    rows: tuple[int, ...]


@dataclass(frozen=True)
class WorkbookContent:
    """The tables of a workbook, its data sheets in workbook order, its base and issues.

    An optional table without rows is left out of `tables`, as if absent, but its
    sheet is listed in `sheets`. `base` is None when `_base` is missing or invalid.
    """

    tables: dict[str, SheetTable]
    sheets: tuple[str, ...]
    base: WorkbookBase | None
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


class _Unreadable(Exception):
    """openpyxl cannot read the workbook or one of its sheets."""


def _load(data: bytes, *, data_only: bool) -> Workbook:
    try:
        return openpyxl.load_workbook(
            BytesIO(data), read_only=True, data_only=data_only
        )
    except Exception as error:
        # openpyxl raises many kinds of errors for a damaged or foreign file.
        raise _Unreadable(str(error)) from error


def _rows(sheet, *, values_only: bool = False) -> Iterator[tuple]:
    """The rows of a read-only sheet, ignoring the stored dimension.

    A row missing in the file is an empty tuple, so the n-th row is sheet row n.
    """
    sheet.reset_dimensions()
    try:
        yield from sheet.iter_rows(values_only=values_only)
    except Exception as error:
        raise _Unreadable(
            f"the sheet {sheet.title!r} cannot be read: {error}"
        ) from error


def _value_text(cell) -> tuple[str, Problem | None]:
    """Text of a cell value, and the problem of a value the spreadsheet converted."""
    value = cell.value
    if value is None:
        return "", None
    if cell.data_type == "e":
        if value == OUTSIDE_CALENDAR and is_date_format(cell.number_format):
            # openpyxl reads a date serial beyond the calendar as this error.
            return "", (
                "cell_date",
                "The cell is formatted as a date, and its value is outside the "
                "calendar",
                DATE_HINT,
            )
        return str(value), _error_value(str(value))
    if isinstance(value, str):
        if value.strip() in ERROR_VALUES:
            return value, _error_value(value.strip())
        if (match := LINE_BREAK.search(value)) is not None:
            name = LINE_BREAKS[match.group()]
            return LINE_BREAK.sub(" ", value), (
                "cell_line_break",
                f"The cell contains a {name}; a table cell holds a single line",
                f"Remove the {name} from the cell.",
            )
        return value, None
    if isinstance(value, bool):
        return ("TRUE" if value else "FALSE"), None
    if isinstance(value, int | float):
        text = str(value) if isinstance(value, int) else format_number(value)
        if "%" in (cell.number_format or ""):
            return text, (
                "cell_percent",
                f"The cell is formatted as a percentage and holds {text}",
                "20% is stored as 0.2; enter 20.",
            )
        return text, None
    if isinstance(value, date | time | timedelta):
        return str(value), (
            "cell_date",
            f"The cell holds the date or time {value}",
            DATE_HINT,
        )
    return str(value), None


def _error_value(value: str) -> Problem:
    return (
        "cell_error",
        f"The cell holds the error value {value}",
        "Correct the formula or enter the value instead.",
    )


def _formula_source(value: object) -> str:
    # A formula is text such as `=B2*2`; an array formula keeps it in `text`.
    text = value if isinstance(value, str) else getattr(value, "text", None)
    return f" {text}" if isinstance(text, str) else ""


def _cell_text(formula, value) -> tuple[str, Problem | None]:
    """Text of a cell, from the cells of the formula and the value pass."""
    if formula.data_type != "f":
        return _value_text(value)
    source = _formula_source(formula.value)
    # A formula whose value is empty text keeps an empty cached value of type
    # str; a formula that no spreadsheet application computed has none.
    if value.value is None and value.data_type != "str":
        return "", (
            "formula_without_value",
            f"The formula{source} has no saved value",
            "Save the workbook in Excel or LibreOffice.",
        )
    text, problem = _value_text(value)
    if problem is not None:
        return text, problem
    stored = f"its value {text}" if text else "an empty cell"
    return text, ("formula_value", f"The formula{source} is stored as {stored}", None)


def _outside(index: int) -> Problem:
    return (
        "value_outside_table",
        f"The value is outside the table: column {column_letter(index)} has no header",
        "Move the value into a column of the table, or into a scratch sheet whose "
        "name starts with _.",
    )


def _lines(rows: Iterable[tuple[tuple, tuple]], report: Report) -> Iterator[bytes]:
    """TSV lines of a sheet, one per sheet row, so that line numbers are sheet rows.

    The header is row 1 without trailing empty cells. A value in a column past
    the header is reported. Empty rows become empty lines, which `load_table`
    skips; trailing empty rows are left out.
    """
    header: list[str] | None = None
    empty = 0
    for number, (formulas, values) in enumerate(rows, start=1):
        cells: list[str] = []
        problems: list[tuple[int, Problem]] = []
        for index, (formula, value) in enumerate(zip(formulas, values, strict=True)):
            if value.value is None and formula.data_type != "f":
                cells.append("")
                continue
            text, problem = _cell_text(formula, value)
            cells.append(text)
            if problem is not None:
                problems.append((index, problem))
        if header is None:
            while cells and not cells[-1].strip():
                cells.pop()
            header = cells
        # Without a header, `load_table` reports the missing header instead.
        width = len(header) or len(cells)
        for index, problem in problems:
            if index < width:
                report(problem, number, index, header[index] if header else None)
        for index in range(width, len(cells)):
            if cells[index].strip():
                report(_outside(index), number, index, None)
        del cells[width:]
        if number > 1 and not any(cell.strip() for cell in cells):
            empty += 1
            continue
        for _ in range(empty):
            yield b"\n"
        empty = 0
        yield ("\t".join(cells) + "\n").encode("utf-8")


def _read_sheet(
    workbooks: tuple[Workbook, Workbook],
    name: str,
    parsed: tuple[TableSpec, str | None],
    study_name: str,
    limit: RowLimit,
) -> tuple[LoadedTable | None, list[ValidationIssue]]:
    """Load a data sheet as a table; its cell issues and the structural issues."""
    file = f"{name}.tsv"
    spec, source = parsed
    formulas, values = (workbook[name] for workbook in workbooks)
    issues: list[ValidationIssue] = []
    cap = IssueCap()

    def report(problem: Problem, number: int, index: int, header: str | None) -> None:
        code, message, hint = problem
        if cap.admit(code):
            issues.append(
                make_issue(
                    code,
                    message,
                    file=file,
                    line=number,
                    column=index,
                    header=header or None,
                    hint=hint,
                )
            )

    rows = zip(_rows(formulas), _rows(values), strict=True)
    table, found = load_table(
        file,
        _lines(rows, report),
        spec,
        source,
        study=study_name,
        limit=limit,
    )
    issues.extend(
        make_issue(code, f"{total:,} cells {CELL_ISSUES[code]}; {LISTED}", file=file)
        for code, total in cap.beyond()
    )
    # The content is judged by validation, as when formatting.
    issues.extend(issue for issue in found if issue.code in STRUCTURAL)
    return table, issues


def _read_base(
    values: Workbook, workbook: str
) -> tuple[WorkbookBase | None, list[ValidationIssue]]:
    if BASE_SHEET not in values.sheetnames:
        return None, [
            make_issue(
                "workbook_base_missing",
                f"The workbook has no {BASE_SHEET} sheet, so changes in both the "
                "workbook and the tables cannot be merged",
                file=workbook,
            )
        ]
    try:
        return parse_base(_rows(values[BASE_SHEET], values_only=True)), []
    except BaseError as error:
        return None, [make_issue(error.code, error.message, file=workbook)]


def _sheet_table(
    table: LoadedTable | None, study_name: str, order: dict[str, int]
) -> SheetTable | None:
    """The canonical text of a loaded table, or None for no table or no rows."""
    rows = None if table is None else table_rows(table, study_name, order)
    if table is None or rows is None:
        return None
    return SheetTable(
        table.file,
        render_tsv(table.spec.names, [cells for _, cells in rows]),
        (1, *(line for line, _ in rows)),
    )


def _read(
    workbooks: tuple[Workbook, Workbook],
    workbook: str,
    study_name: str,
    limit: RowLimit,
) -> WorkbookContent:
    values = workbooks[1]
    issues: list[ValidationIssue] = []
    worksheets = {sheet.title for sheet in values.worksheets}
    data: dict[str, tuple[TableSpec, str | None]] = {}
    for name in values.sheetnames:
        if name.startswith("_"):
            # `_lists`, `_base` and scratch sheets.
            continue
        parsed = parse_table_file(f"{name}.tsv")
        if parsed is None or name not in worksheets:
            issues.append(
                make_issue(
                    "unknown_sheet",
                    f"The sheet {name!r} is not a table of the study",
                    file=f"{name}.tsv",
                    hint=SHEET_HINT,
                )
            )
        else:
            data[name] = parsed
    if SUBJECTS not in data:
        issues.append(
            make_issue(
                "missing_sheet",
                f"The workbook has no {SUBJECTS} sheet",
                file=table_file(SUBJECTS),
                hint=f"Add the {SUBJECTS} sheet again; every study needs it.",
            )
        )
    base, found = _read_base(values, workbook)
    issues.extend(found)
    read: dict[str, tuple[SheetTable | None, list[ValidationIssue]]] = {}
    order: dict[str, int] = {}
    # The subjects come first: their order sorts the rows of every table.
    for name in sorted(data, key=lambda name: name != SUBJECTS):
        table, found = _read_sheet(workbooks, name, data[name], study_name, limit)
        if name == SUBJECTS:
            order = subject_order(table)
        read[name] = _sheet_table(table, study_name, order), found
    tables: dict[str, SheetTable] = {}
    for name in data:
        sheet, found = read[name]
        if sheet is not None:
            tables[sheet.file] = sheet
        issues.extend(found)
    return WorkbookContent(tables, tuple(data), base, issues)


def read_workbook(
    path: Path, study_name: str, *, max_rows: int | None = None
) -> WorkbookContent:
    """Read the data sheets of a workbook into the canonical text of their tables.

    Formula cells are read as the value the spreadsheet application saved. The
    file is read once, and both passes of openpyxl, with formulas and with
    values, read these bytes, so a save in between cannot mix two versions.
    `max_rows` limits the data rows of all sheets together; more raise
    StudyValidationError `row_limit`, as `load_study` does.
    """
    path = Path(path)
    with warnings.catch_warnings(), ExitStack() as stack:
        # openpyxl warns about parts of Excel files it does not support and
        # about dates beyond the calendar; the reader reports what matters.
        warnings.filterwarnings("ignore", module="openpyxl")
        try:
            data = path.read_bytes()
            formulas = _load(data, data_only=False)
            stack.callback(formulas.close)
            values = _load(data, data_only=True)
            stack.callback(values.close)
            return _read((formulas, values), path.name, study_name, RowLimit(max_rows))
        except (_Unreadable, OSError) as error:
            return WorkbookContent(
                {},
                (),
                None,
                [
                    make_issue(
                        "workbook_unreadable",
                        f"{path.name} cannot be read: {error}",
                        file=path.name,
                    )
                ],
            )
