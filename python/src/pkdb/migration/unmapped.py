"""Numbers of format 1 rows in columns that `study.json` does not map.

Format 1 reads the statistics of a record only from the columns that its
template in `study.json` maps. A row whose numbers sit in other columns, such
as the median, min and max of a tmax row whose template maps only mean and sd,
a `geomean` column or a `value` column where the template maps `mean`, parses as a record
without any value, which the converter drops (`rows.valueless`). The gate
refuses such a drop, because it would lose the numbers (`unmapped_value`).

A number that another record of the same row keeps is not lost: a column
that its template maps, a column that the workbook formula of such a mapped
cell reads, such as the `mean + se` column of an error bar `ABS(X - mean)`,
and a column that a formula computes from these alone, such as an sd
computed from that se and the count.
"""

import math
from collections import defaultdict
from collections.abc import Collection
from pathlib import Path

from pkdb.importers.workbook import table_reader
from pkdb.migration.formulas import references, row_formulas
from pkdb.schemas.source import SourceBundle, SourceLocation
from pkdb.schemas.study import CanonicalStudy, DataRecord, Observation, Subject
from pkdb.studyformat.text import format_number

# Every unmapped column with a number on a dropped row is a value of that row,
# compared without case, except these columns: they count the subjects, place
# the row in time or name it. A list of statistic names missed values under
# names such as `geomean`, `geometric_mean`, `ci_low` or `q25`.
NON_VALUE_COLUMNS = frozenset(
    {
        "count",
        "group_count",
        "groupcount",
        "n",
        "time",
        "time_end",
        "time_raw",
        "timeraw",
        "study",
        "group",
        "individual",
        "subject",
        "name",
        "id",
        "label",
    }
)
# Comment and note columns, such as `comments` or `notes`, hold no value.
TEXT_COLUMNS = ("comment", "note")
# The tables were read once by the format 1 parser, which applies the row limit.
MAX_ROWS = 1_000_000
Row = tuple[str, str | None, int]
Records = list[Observation | Subject | DataRecord]


def _number(cell: object) -> str | None:
    """A cell that holds a finite number, as text such as `2.5`; else None."""
    if isinstance(cell, bool) or not isinstance(cell, int | float | str):
        return None
    try:
        number = float(cell)
    except ValueError:
        return None
    return format_number(number) if math.isfinite(number) else None


def _value_column(column: str) -> bool:
    """Whether a format 1 column can hold a value of its row."""
    name = column.strip().lower()
    return name not in NON_VALUE_COLUMNS and not any(
        text in name for text in TEXT_COLUMNS
    )


def _records(study: CanonicalStudy) -> Records:
    """Every record of the parsed study."""
    records: Records = [*study.interventions, *study.measurements, *study.scatters]
    for subject in [*study.groups, *study.individuals]:
        records += [subject, *subject.characteristica]
    return records


def _row(source: SourceLocation | None) -> Row | None:
    if source is None or source.row is None:
        return None
    return source.file, source.sheet, source.row


def _kept(
    cells: dict,
    columns: dict[str, str],
    formulas: dict[str, str],
    kept: set[str],
    place: tuple[str, int],
) -> set[str]:
    """The headers of the row whose numbers the records that are kept hold.

    These are the `kept` headers, those that a template of a kept record of
    the row maps, with a number; the headers whose cells the formulas of these
    read, at any depth; and the headers whose formulas compute a number only
    from such cells and the cells of columns that hold no value, such as the
    count. A formula that reads other rows or sheets computes no number of
    the row alone.
    """
    sheet, row = place
    headers = {letter: header for header, letter in columns.items()}
    letters = {
        columns[header]
        for header in kept
        if header in columns and _number(cells.get(header)) is not None
    }
    pending = list(letters)
    while pending:
        formula = formulas.get(pending.pop())
        if formula is None:
            continue
        for letter in references(formula, sheet, row).columns - letters:
            letters.add(letter)
            pending.append(letter)
    plain = {letter for letter, header in headers.items() if not _value_column(header)}
    computed = True
    while computed:
        computed = False
        for letter, formula in formulas.items():
            if letter in letters or letter not in headers:
                continue
            read = references(formula, sheet, row)
            if (
                not read.outside
                and read.columns & letters
                and read.columns <= letters | plain
            ):
                letters.add(letter)
                computed = True
    return {headers[letter] for letter in letters if letter in headers}


def unmapped_values(
    bundle: SourceBundle, study: CanonicalStudy, dropped: Collection[str]
) -> dict[str, list[tuple[str, str]]]:
    """The unmapped statistic columns with a number of the rows of dropped records.

    `dropped` are the keys of the parsed records that the converter drops as
    rows without any value. For each that comes from a row of a format 1
    sheet, the result lists the columns of that row that can hold a value (all
    but `NON_VALUE_COLUMNS` and comments), in the order of the sheet, that hold
    a number although no template of the
    row maps them, with the number. A column that the template of another
    record of the same row maps holds that record's data, and so does a
    column whose number a kept record of the row holds through a workbook
    formula (see `_kept`). A row without such a number is left out: it
    carries no data.
    """
    mapped: dict[Row, set[str]] = defaultdict(set)
    kept: dict[Row, set[str]] = defaultdict(set)
    for record in _records(study):
        source = record.source
        if source is None or (row := _row(source)) is None:
            continue
        mapped[row] |= source._mapped
        if getattr(record, "key", None) not in dropped:
            kept[row] |= source._mapped
    records: list[Observation] = [*study.measurements]
    for subject in [*study.groups, *study.individuals]:
        records += subject.characteristica
    wanted = {
        record.key: row
        for record in records
        if record.key in dropped
        and (row := _row(record.source)) is not None
        and row[0] in bundle.files
    }
    tables: dict[tuple[str, str | None], dict[int, tuple[dict, dict[str, str]]]] = {}
    candidates: dict[str, list[tuple[str, str]]] = {}
    with table_reader() as read:
        for key, (file, sheet, number) in wanted.items():
            if (file, sheet) not in tables:
                tables[file, sheet] = {
                    location.row: (cells, location._columns)
                    for cells, location in read(bundle.files[file], sheet, MAX_ROWS)
                    if location.row is not None
                }
            cells, _ = tables[file, sheet].get(number, ({}, {}))
            numbers = [
                (column, value)
                for column, cell in cells.items()
                if _value_column(column)
                and column not in mapped[file, sheet, number]
                and (value := _number(cell)) is not None
            ]
            if numbers:
                candidates[key] = numbers
    formulas = _formulas(bundle, {wanted[key] for key in candidates})
    found: dict[str, list[tuple[str, str]]] = {}
    for key, numbers in candidates.items():
        file, sheet, number = row = wanted[key]
        if sheet is not None and (row_formula := formulas.get(row)):
            cells, columns = tables[file, sheet][number]
            held = _kept(cells, columns, row_formula, kept[row], (sheet, number))
            numbers = [
                (column, value) for column, value in numbers if column not in held
            ]
        if numbers:
            found[key] = numbers
    return found


def _formulas(bundle: SourceBundle, rows: set[Row]) -> dict[Row, dict[str, str]]:
    """The formulas of the rows of workbooks, by column letter."""
    wanted: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for file, sheet, number in rows:
        if sheet is not None and Path(file).suffix.lower() == ".xlsx":
            wanted[file][sheet].add(number)
    found: dict[Row, dict[str, str]] = {}
    for file, sheets in wanted.items():
        for (sheet, number), formulas in row_formulas(
            bundle.files[file], sheets
        ).items():
            found[file, sheet, number] = formulas
    return found
