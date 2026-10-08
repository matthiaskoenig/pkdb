"""Change one cell of a study workbook and save it, as a curator would in a spreadsheet program.

    uv run --project python python tools/curation_testing/edit_workbook.py <workbook> <sheet> <cell> <value>

`cell` is an A1 reference such as O6. A value that reads as a number is written as a number,
any other value as text.
"""

import sys
from pathlib import Path

import openpyxl


def typed(value: str) -> int | float | str:
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: edit_workbook.py <workbook> <sheet> <cell> <value>")
    workbook, sheet, cell, value = (
        Path(sys.argv[1]),
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
    )
    book = openpyxl.load_workbook(workbook)
    book[sheet][cell].value = typed(value)
    book.save(workbook)


if __name__ == "__main__":
    main()
