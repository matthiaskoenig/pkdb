"""Read legacy workbooks without generating or changing source TSV files."""

import csv
from pathlib import Path

import openpyxl
import pandas as pd

from pkdb.importers.expressions import clean
from pkdb.schemas.source import SourceLocation
from pkdb.schemas.validation import StudyValidationError, fail


def read_table(
    path: Path, sheet: str | None, max_rows: int
) -> list[tuple[dict, SourceLocation]]:
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    location = SourceLocation(file=path.name, sheet=sheet)
    try:
        if path.suffix.lower() == ".xlsx":
            if sheet is None:
                fail("missing_sheet", "Workbook sheet is required", location)
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            try:
                headers = next(
                    workbook[sheet].iter_rows(min_row=2, max_row=2, values_only=True),
                    (),
                )
            finally:
                workbook.close()
        else:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                headers = next(csv.reader(handle, delimiter="\t"), [])
        named = [
            header.strip()
            for header in headers
            if isinstance(header, str) and header.strip()
        ]
        if len(named) != len(set(named)):
            fail("duplicate_column", "Column headers must be unique", location)
        if path.suffix.lower() == ".xlsx":
            if sheet is None:
                fail("missing_sheet", "Workbook sheet is required")
            frame = pd.read_excel(
                path, sheet_name=sheet, skiprows=[0], comment="#", nrows=max_rows + 1
            )
            first_row = 3
        else:
            frame = pd.read_csv(
                path,
                sep="\t",
                nrows=max_rows + 1,
                keep_default_na=False,
                na_values=["na", "NA", "nan", "NAN"],
            )
            first_row = 2
    except StudyValidationError:
        raise
    except (ValueError, KeyError, OSError) as error:
        fail("invalid_table", str(error), SourceLocation(file=path.name, sheet=sheet))
    if len(frame) > max_rows:
        fail("row_limit", "Source table exceeds configured row limit")
    frame = frame.loc[
        :, [c for c in frame.columns if not str(c).startswith("Unnamed:")]
    ]
    if any(not isinstance(column, str) for column in frame.columns):
        fail("invalid_header", "Column headers must be strings")
    frame.columns = frame.columns.str.strip()
    if frame.columns.duplicated().any():
        fail("duplicate_column", "Column headers must be unique")
    return [
        (
            dict(zip(frame.columns, (clean(value) for value in row))),
            SourceLocation(file=path.name, sheet=sheet, row=index + first_row),
        )
        for index, row in enumerate(frame.itertuples(index=False, name=None))
        if not all(pd.isna(value) for value in row)
    ]
