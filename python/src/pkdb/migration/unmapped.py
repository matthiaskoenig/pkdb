"""Numbers of format 1 rows in statistic columns that `study.json` does not map.

Format 1 reads the statistics of a record only from the columns that its
template in `study.json` maps. A row whose numbers sit in other columns, such
as the median, min and max of a tmax row whose template maps only mean and sd,
or a `value` column where the template maps `mean`, parses as a record
without any value, which the converter drops (`rows.valueless`). The gate
refuses such a drop, because it would lose the numbers (`unmapped_value`).
"""

import math
from collections import defaultdict
from collections.abc import Collection, Iterator

from pkdb.importers.workbook import table_reader
from pkdb.schemas.source import SourceBundle, SourceLocation
from pkdb.schemas.study import CanonicalStudy, DataRecord, Observation, Subject
from pkdb.studyformat.text import format_number

# The statistic columns of format 1 sheets, compared without case: the
# statistics but the count, `value`, which format 1 reads as the mean, and
# `mean_pm`, the end of an error bar. Other columns, such as `count`,
# `comments` or `time`, hold no value of a row.
COLUMNS = frozenset(
    {
        "value",
        "mean",
        "median",
        "min",
        "max",
        "sd",
        "se",
        "cv",
        "gmean",
        "gsd",
        "gcv",
        "mean_pm",
    }
)
# The tables were read once by the format 1 parser, which applies the row limit.
MAX_ROWS = 1_000_000
Row = tuple[str, str | None, int]


def _number(cell: object) -> str | None:
    """A cell that holds a finite number, as text such as `2.5`; else None."""
    if isinstance(cell, bool) or not isinstance(cell, int | float | str):
        return None
    try:
        number = float(cell)
    except ValueError:
        return None
    return format_number(number) if math.isfinite(number) else None


def _locations(study: CanonicalStudy) -> Iterator[SourceLocation]:
    """The sources of every record of the parsed study."""
    records: list[Observation | Subject | DataRecord] = [
        *study.interventions,
        *study.measurements,
        *study.scatters,
    ]
    for subject in [*study.groups, *study.individuals]:
        records += [subject, *subject.characteristica]
    for record in records:
        if record.source is not None:
            yield record.source


def _row(source: SourceLocation | None) -> Row | None:
    if source is None or source.row is None:
        return None
    return source.file, source.sheet, source.row


def unmapped_values(
    bundle: SourceBundle, study: CanonicalStudy, dropped: Collection[str]
) -> dict[str, list[tuple[str, str]]]:
    """The unmapped statistic columns with a number of the rows of dropped records.

    `dropped` are the keys of the parsed records that the converter drops as
    rows without any value. For each that comes from a row of a format 1
    sheet, the result lists the statistic columns (`COLUMNS`) of that row,
    in the order of the sheet, that hold a number although no template of the
    row maps them, with the number. A column that the template of another
    record of the same row maps holds that record's data. A row without such
    a number is left out: it carries no data.
    """
    mapped: dict[Row, set[str]] = defaultdict(set)
    for source in _locations(study):
        if (row := _row(source)) is not None:
            mapped[row] |= source._mapped
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
    tables: dict[tuple[str, str | None], dict[int, dict]] = {}
    found: dict[str, list[tuple[str, str]]] = {}
    with table_reader() as read:
        for key, (file, sheet, number) in wanted.items():
            if (file, sheet) not in tables:
                tables[file, sheet] = {
                    location.row: cells
                    for cells, location in read(bundle.files[file], sheet, MAX_ROWS)
                    if location.row is not None
                }
            cells = tables[file, sheet].get(number, {})
            numbers = [
                (column, value)
                for column, cell in cells.items()
                if column.lower() in COLUMNS
                and column not in mapped[file, sheet, number]
                and (value := _number(cell)) is not None
            ]
            if numbers:
                found[key] = numbers
    return found
