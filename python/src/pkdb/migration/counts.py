"""Counts of format 1 outputs that only their tables hold.

Format 1 reads the statistics of an output from the columns that its template
in `study.json` maps, and no template maps `count`: the format 1 server
counted every output with its group. Curators kept the number of subjects of
a row in a `count` column all the same, and the formulas of their workbooks
derive an sd or se from it. Format 2 holds that number as the count of the
output.
"""

import math
from collections.abc import Mapping
from typing import NamedTuple

from pkdb.importers.folder import SourceBundle
from pkdb.importers.workbook import table_reader
from pkdb.migration.model import Decision
from pkdb.migration.rows import scatter_outputs
from pkdb.migration.sources import sheet_of
from pkdb.schemas.study import CanonicalStudy

COLUMN = "count"
# The tables were read once by the format 1 parser, which applies the row limit.
MAX_ROWS = 1_000_000


class TableCounts(NamedTuple):
    """The counts of the `count` columns by record key.

    `written` are the counts that differ from the count of the record's group,
    `above` those that exceed it, which the converter does not write.
    """

    written: Mapping[str, int]
    above: Mapping[str, int]
    invalid: list[Decision]


def _whole(cell: object) -> int | None:
    """The count of a cell, such as 12 of `12` or 12.0; None for any other cell."""
    try:
        number = float(str(cell))
    except ValueError:
        return None
    if not math.isfinite(number) or not number.is_integer() or number < 0:
        return None
    return int(number)


def table_counts(bundle: SourceBundle, study: CanonicalStudy) -> TableCounts:
    """The counts of the table rows of group outputs whose template maps no count.

    An individual counts 1, whatever its row says: curators copied the count
    of the group into the rows of its individuals. A scatter point has no
    count in format 2.
    """
    groups = {group.name: group.count for group in study.groups}
    points = scatter_outputs(study)
    tables: dict[tuple[str, str | None], dict[int, dict]] = {}
    written: dict[str, int] = {}
    above: dict[str, int] = {}
    invalid: dict[tuple[str | None, int], Decision] = {}
    with table_reader() as read:
        for record in study.measurements:
            source = record.source
            if (
                record.group is None
                or record.label in points
                or record.statistics.count is not None
                or source is None
                or source.row is None
                or source.file not in bundle.files
            ):
                continue
            table = (source.file, source.sheet)
            if table not in tables:
                tables[table] = {
                    location.row: row
                    for row, location in read(
                        bundle.files[source.file], source.sheet, MAX_ROWS
                    )
                    if location.row is not None
                }
            # The reader cleans the cells: an NA cell is None, an empty one too
            # in a workbook, and an empty string in a TSV.
            cell = tables[table].get(source.row, {}).get(COLUMN)
            if cell is None or cell == "":
                continue
            count = _whole(cell)
            group = groups.get(record.group)
            if count is None:
                sheet = sheet_of(source, study.metadata.name)
                invalid[sheet, source.row] = Decision(
                    kind="table_count_invalid",
                    detail=f"{sheet} row {source.row}: count {cell!r} is no whole number",
                )
            elif group is not None and count > group:
                above[record.key] = count
            elif count != group:
                written[record.key] = count
    return TableCounts(written, above, list(invalid.values()))
