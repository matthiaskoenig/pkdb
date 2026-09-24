"""Read tables with one-based physical coordinates, including blank/comment rows."""

import csv
from pathlib import Path
from zipfile import BadZipFile

import openpyxl
from openpyxl.utils import get_column_letter

from pkdb.importers.expressions import clean
from pkdb.schemas.source import SourceLocation
from pkdb.schemas.validation import StudyValidationError, fail


def read_table(
    path: Path, sheet: str | None, max_rows: int
) -> list[tuple[dict, SourceLocation]]:
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    location = SourceLocation(file=path.name, sheet=sheet)
    workbook = None
    handle = None
    try:
        if path.suffix.lower() == ".xlsx":
            if sheet is None:
                fail("missing_sheet", "Workbook sheet is required", location)
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            if sheet not in workbook.sheetnames:
                fail(
                    "missing_sheet",
                    "Referenced sheet is absent from the workbook",
                    location,
                    category="reference",
                    stage="read",
                    field="sheet",
                    actual=sheet,
                    expected={"available_sheets": workbook.sheetnames},
                )
            worksheet = workbook[sheet]
            # Excel can retain a million-row used range after deleted formatting.
            # Read actual XML cells without padding to stale worksheet dimensions.
            worksheet.reset_dimensions()
            iterator = worksheet.iter_rows(min_row=2, values_only=True)
            first_row = 3
        else:
            handle = path.open(newline="", encoding="utf-8-sig")
            iterator = iter(csv.reader(handle, delimiter="\t"))
            first_row = 2
        headers = next(iterator, ())
        columns = {}
        for index, header in enumerate(headers):
            if header is None or header == "":
                continue
            if not isinstance(header, str):
                fail("invalid_header", "Column headers must be strings", location)
            header = header.strip()
            if not header:
                continue
            if header in columns:
                fail("duplicate_column", "Column headers must be unique", location)
            columns[header] = index
        rows = []
        for physical_row, raw in enumerate(iterator, first_row):
            values = []
            commented = False
            for value in raw:
                if (
                    path.suffix.lower() == ".xlsx"
                    and isinstance(value, str)
                    and "#" in value
                ):
                    value = value.split("#", 1)[0]
                    commented = True
                    values.append(clean(value) or None)
                elif commented:
                    values.append(None)
                else:
                    values.append(clean(value))
            if not any(value is not None and value != "" for value in values):
                continue
            if len(rows) >= max_rows:
                fail(
                    "row_limit",
                    "Source table exceeds configured row limit",
                    location,
                    category="limit",
                    stage="read",
                    expected={"maximum_rows": max_rows},
                )
            source = SourceLocation(file=path.name, sheet=sheet, row=physical_row)
            source._columns.update(
                {
                    header: get_column_letter(index + 1)
                    for header, index in columns.items()
                }
            )
            rows.append(
                (
                    {
                        header: values[index] if index < len(values) else None
                        for header, index in columns.items()
                    },
                    source,
                )
            )
        return rows
    except StudyValidationError:
        raise
    except ValueError, KeyError, OSError, BadZipFile:
        fail(
            "invalid_table",
            "Cannot read the source table. Check its format and encoding and that the workbook is not corrupted.",
            location,
            category="parsing",
            stage="read",
        )
    finally:
        if workbook is not None:
            workbook.close()
        if handle is not None:
            handle.close()
