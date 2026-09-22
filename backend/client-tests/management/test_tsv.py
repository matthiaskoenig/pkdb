"""Test TSV creation from a complete temporary workbook."""

from pathlib import Path

from openpyxl import Workbook
from pkdb_data.management.tsv import build_tsvs


def test_build_tsvs(tmp_path: Path) -> None:
    """Build the expected TSV without changing source fixtures."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Tab1"
    sheet.append(["Instructions"])
    sheet.append(["study", "time", "concentration"])
    sheet.append(["Example", 0, 2])
    sheet.append(["Example", 1, 1])
    path = tmp_path / "Example.xlsx"
    workbook.save(path)
    assert build_tsvs(path_xlsx=path)
    assert (tmp_path / ".Example_Tab1.tsv").read_text() == (
        "study\ttime\tconcentration\nExample\t0\t2\nExample\t1\t1\n"
    )
