"""Error bars that format 1 workbooks compute as ABS(X - mean)."""

import re
from collections import defaultdict
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_to_tuple

from pkdb.schemas.study import CanonicalStudy, Observation

CELL = r"\$?([A-Z]{1,3})\$?([0-9]+)"
ABS = re.compile(rf"=\s*ABS\(\s*{CELL}\s*-\s*{CELL}\s*\)\s*", re.IGNORECASE)
SPREADS = ("sd", "se")


def _records(study: CanonicalStudy) -> list[Observation]:
    records: list[Observation] = [*study.interventions, *study.measurements]
    for subject in [*study.groups, *study.individuals]:
        records.extend(subject.characteristica)
    return records


def _cells(
    workbook: Path, wanted: dict[str, set[str]], *, data_only: bool
) -> dict[tuple[str, str], object]:
    """The wanted cells by sheet and coordinate: formulas, or the values saved with them.

    Each sheet is read once up to its last wanted row, since a read-only sheet
    reads from its start for every single cell that is looked up.
    """
    book = openpyxl.load_workbook(workbook, read_only=True, data_only=data_only)
    found: dict[tuple[str, str], object] = {}
    try:
        for name, coordinates in wanted.items():
            if name not in book.sheetnames:
                continue
            sheet = book[name]
            # Some writers save wrong sheet dimensions, which would cut rows short.
            sheet.reset_dimensions()
            last = max(coordinate_to_tuple(coordinate)[0] for coordinate in coordinates)
            rows = sheet.iter_rows(min_row=1, max_row=last, values_only=True)
            for row, values in enumerate(rows, 1):
                for column, value in enumerate(values, 1):
                    coordinate = f"{get_column_letter(column)}{row}"
                    if coordinate in coordinates:
                        found[name, coordinate] = value
    finally:
        book.close()
    return found


def error_bars(workbook: Path, study: CanonicalStudy) -> dict[str, tuple[float, str]]:
    """Record key to (error bar, `sd` or `se`) for spreads computed as ABS(X - mean)."""
    # (record key, sheet, sd or se, its cell, the mean cell of the same row)
    spreads = []
    for record in _records(study):
        source = record.source
        if source is None or source.sheet is None:
            continue
        mean = source.for_field("mean").cell
        for kind in SPREADS:
            # A field without a cell of its own is located at its row, without a cell.
            cell = source.for_field(kind).cell
            if mean is not None and cell is not None:
                spreads.append((record.key, source.sheet, kind, cell, mean))
    wanted = defaultdict(set)
    for _, sheet, _, cell, _ in spreads:
        wanted[sheet].add(cell)
    formulas = _cells(workbook, wanted, data_only=False)
    bars = []
    for key, sheet, kind, cell, mean in spreads:
        formula = formulas.get((sheet, cell))
        match = ABS.fullmatch(formula) if isinstance(formula, str) else None
        if match is None:
            continue
        first = f"{match[1]}{match[2]}".upper()
        second = f"{match[3]}{match[4]}".upper()
        other = second if first == mean else first if second == mean else None
        if other is not None and other != mean:
            bars.append((key, sheet, kind, other))
    wanted = defaultdict(set)
    for _, sheet, _, other in bars:
        wanted[sheet].add(other)
    values = _cells(workbook, wanted, data_only=True)
    found = {}
    for key, sheet, kind, other in bars:
        bar = values.get((sheet, other))
        # Format 2 refuses negative error bars of concentrations; the saved
        # spread says the same.
        if isinstance(bar, (int, float)) and not isinstance(bar, bool) and bar >= 0:
            found[key] = (float(bar), kind)
    return found
