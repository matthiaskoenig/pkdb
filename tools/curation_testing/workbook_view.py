"""Print the sheet and the cell that a workbook opens at, such as timecourses_Fig1!O6.

    uv run --project python python tools/curation_testing/workbook_view.py <workbook>

The sheet is the active sheet, and the cell the active cell of its active pane, as a
spreadsheet program shows them when it opens the workbook.
"""

import sys
from pathlib import Path

import openpyxl


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: workbook_view.py <workbook>")
    sheet = openpyxl.load_workbook(Path(sys.argv[1])).active
    if sheet is None:
        raise SystemExit("The workbook has no active sheet")
    view = sheet.sheet_view
    pane = view.pane.activePane if view.pane is not None else "topLeft"
    cells = {
        (selection.pane or "topLeft"): selection.activeCell
        for selection in view.selection
    }
    print(f"{sheet.title}!{cells.get(pane, 'A1')}")


if __name__ == "__main__":
    main()
