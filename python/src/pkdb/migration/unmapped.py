"""Numbers of format 1 rows in columns that `study.json` does not map.

Format 1 reads the statistics of a record only from the columns that its
template in `study.json` maps; the converter writes nothing else of the row.
A number in another column is lost: the median, min and max of a tmax row
whose template maps only mean and sd, a `cv` column next to a mapped mean, the
digitized end of an error bar whose spread is not mapped, a baseline, or a
whole measurement that no template reads. When every record of the row is
left without a value, the converter drops the row too (`rows.valueless`). The
gate refuses both, a dropped and a converted row with such a number
(`unmapped_value`).

A number that a kept record of the row holds is not lost: a column that its
template maps, a column that the workbook formula of such a mapped cell reads,
such as the `mean + se` column of an error bar `ABS(X - mean)`, a column that a
formula computes from these alone, such as an sd computed from that se and the
count, and a copy of a statistic of the record, such as a `value` column that
repeats the mapped `mean` or a `mean_pm` column that is the mean plus the sd.
"""

import math
from collections import defaultdict
from collections.abc import Collection
from pathlib import Path
from typing import NamedTuple

from pkdb.importers.workbook import table_reader
from pkdb.migration.formulas import references, sheet_formulas
from pkdb.schemas.source import SourceBundle, SourceLocation
from pkdb.schemas.study import CanonicalStudy, DataRecord, Observation, Subject
from pkdb.studyformat.text import format_number

# Every unmapped column with a number is a value of its row, compared without
# case, except these columns: they count the subjects, place the row in time or
# name it. A list of statistic names missed values under names such as
# `geomean`, `geometric_mean`, `ci_low` or `q25`.
NON_VALUE_COLUMNS = frozenset(
    {
        "count",
        "group_count",
        "groupcount",
        "individual_count",
        "n",
        "subjects",
        "day",
        "tstart",
        "tend",
        "t_start",
        "t_end",
        "traw",
        "study",
        "group",
        "individual",
        "subject",
        "name",
        "id",
        "label",
    }
)
# Columns whose name starts with `time` place the row in time, such as `time`,
# `time_start`, `time_end`, `timeraw` or the digitized `time_dig` of a rounded
# `time`, and so do `day`, `tstart`, `tend` and `traw`.
TIME_COLUMNS = "time"
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
    return (
        name not in NON_VALUE_COLUMNS
        and not name.startswith(TIME_COLUMNS)
        and not any(text in name for text in TEXT_COLUMNS)
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


Cell = tuple[int, str]


def _held(
    formulas: dict[Cell, str], seeds: set[Cell], plain: set[str], sheet: str
) -> set[Cell]:
    """The cells of a sheet whose numbers the records that are kept hold.

    `seeds` are the cells that the templates of the kept records map and
    `plain` the letters of the columns that hold no value, such as the count.
    The kept records hold the seeds; the cells of the same row that the
    workbook formulas of held cells read, at any depth, such as the
    `mean + se` column of an error bar `ABS(X - mean)` or an index that a
    name is made of; and the cells whose formulas compute a number only from
    held cells and plain cells of any rows of the sheet, such as an sd
    computed from that se and the count, or a change computed from the mean
    and the mean of the baseline row. A cell of another row that a formula
    reads is held only by the records of that row, as the sum of the cvs of
    three rows holds none of them. A formula that reads other sheets, whole
    columns or names computes no number of the sheet alone.
    """
    read = {cell: references(formula, sheet) for cell, formula in formulas.items()}
    held = set(seeds)
    pending = list(seeds)
    while pending:
        number, _ = cell = pending.pop()
        if (cells := read.get(cell)) is None:
            continue
        for other in cells.cells - held:
            if other[0] == number:
                held.add(other)
                pending.append(other)
    computed = True
    while computed:
        computed = False
        for cell, cells in read.items():
            if (
                cell not in held
                and not cells.outside
                and cells.cells & held
                and all(other in held or other[1] in plain for other in cells.cells)
            ):
                held.add(cell)
                computed = True
    return held


class RowNumbers(NamedTuple):
    """The numbers of a format 1 row that the conversion would lose.

    `row` is the file, sheet and row number; `dropped` the keys of the records
    of the row that the converter drops as rows without any value; `kept` the
    records of the row that it converts; `numbers` the columns with their
    numbers, in the order of the sheet.
    """

    row: Row
    dropped: list[str]
    kept: Records
    numbers: list[tuple[str, str]]


def _copies(records: Records) -> set[float]:
    """The statistics of the kept records of a row, which a copy repeats.

    These are the statistics, such as the `mean` that a `value` column
    repeats, and the ends of the error bars: the central value plus or minus
    the spread, such as the `mean_pm` column that a curator digitized for an
    sd that is typed in. Times and counts are no statistics, so a `max` that
    happens to equal the time of the row is no copy. A copy is exact: with a
    tolerance for the rounding of the numbers as written, a max of 12 would be
    the end of the error bar 10 +- 2.4 too.
    """
    copies: set[float] = set()
    for record in records:
        statistics = getattr(record, "statistics", None)
        if statistics is None:
            continue
        values = statistics.model_dump(exclude={"count", "error_type"})
        copies |= {float(value) for value in values.values() if value is not None}
        centers = [statistics.mean, statistics.median, statistics.gmean]
        spreads = [statistics.sd, statistics.se, statistics.error_bar]
        for center in centers:
            for spread in spreads:
                if center is not None and spread is not None:
                    copies |= {center + spread, center - spread}
    return copies


def _copy(value: str, copies: set[float]) -> bool:
    """Whether a number repeats a number that a kept record of the row holds."""
    number = float(value)
    return any(math.isclose(number, copy, rel_tol=1e-9) for copy in copies)


def unmapped_values(
    bundle: SourceBundle, study: CanonicalStudy, dropped: Collection[str]
) -> list[RowNumbers]:
    """The rows of format 1 sheets with numbers in columns that no template of the row maps.

    Each record of the study that comes from a row of a format 1 sheet places
    that row, whether the converter keeps the record or drops it as a row
    without any value (`dropped`, by key). The result lists, for each such row
    in the order of the files, sheets and rows, the columns of the row that can
    hold a value (all but `NON_VALUE_COLUMNS` and comments) that hold a number
    although no template of the row maps them, with the number. A column that
    the template of a record of the row maps holds that record's data. A
    column whose number a kept record of the row holds through a workbook
    formula (see `_held`) or repeats (see `_copies`), such as a `value` column
    that is a copy of the mapped `mean`, is no loss either. A row without such
    a number is left out: the conversion loses nothing of it.
    """
    mapped: dict[Row, set[str]] = defaultdict(set)
    kept: dict[Row, set[str]] = defaultdict(set)
    kept_records: dict[Row, Records] = defaultdict(list)
    for record in _records(study):
        if (row := _row(record.source)) is None:
            continue
        assert record.source is not None
        mapped[row] |= record.source._mapped
        if getattr(record, "key", None) not in dropped:
            kept[row] |= record.source._mapped
            kept_records[row].append(record)
    records: list[Observation] = [*study.measurements]
    for subject in [*study.groups, *study.individuals]:
        records += subject.characteristica
    dropped_keys: dict[Row, list[str]] = defaultdict(list)
    for record in records:
        if record.key in dropped and (row := _row(record.source)) is not None:
            dropped_keys[row].append(record.key)
    rows = sorted(
        (row for row in mapped if row[0] in bundle.files),
        key=lambda row: (row[0], row[1] or "", row[2]),
    )
    tables: dict[tuple[str, str | None], dict[int, tuple[dict, dict[str, str]]]] = {}
    candidates: dict[Row, list[tuple[str, str]]] = {}
    with table_reader() as read:
        for row in rows:
            file, sheet, number = row
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
                and column not in mapped[row]
                and (value := _number(cell)) is not None
            ]
            if numbers:
                candidates[row] = numbers
    held = _held_headers(bundle, tables, kept, set(candidates))
    found: list[RowNumbers] = []
    for row, numbers in candidates.items():
        copies = _copies(kept_records[row])
        numbers = [
            (column, value)
            for column, value in numbers
            if column not in held.get(row, ()) and not _copy(value, copies)
        ]
        if numbers:
            found.append(RowNumbers(row, dropped_keys[row], kept_records[row], numbers))
    return found


def _held_headers(
    bundle: SourceBundle,
    tables: dict[tuple[str, str | None], dict[int, tuple[dict, dict[str, str]]]],
    kept: dict[Row, set[str]],
    rows: set[Row],
) -> dict[Row, set[str]]:
    """The headers of the wanted rows whose numbers the kept records hold through formulas.

    Only the sheets of workbooks have formulas (see `_held`); a hidden table
    holds the saved values alone.
    """
    sheets: dict[str, set[str]] = defaultdict(set)
    for file, sheet, _ in rows:
        if sheet is not None and Path(file).suffix.lower() == ".xlsx":
            sheets[file].add(sheet)
    found: dict[Row, set[str]] = {}
    for file, names in sheets.items():
        for sheet, formulas in sheet_formulas(bundle.files[file], names).items():
            table = tables[file, sheet]
            columns: dict[str, str] = {}
            for _, letters in table.values():
                columns |= letters
            headers = {letter: header for header, letter in columns.items()}
            seeds = {
                (number, columns[header])
                for (f, s, number), mapped in kept.items()
                if f == file and s == sheet
                for header in mapped
                if header in columns
            }
            plain = {
                letter
                for letter, header in headers.items()
                if not _value_column(header)
            }
            for number, letter in _held(formulas, seeds, plain, sheet):
                if (row := (file, sheet, number)) in rows and letter in headers:
                    found.setdefault(row, set()).add(headers[letter])
    return found
