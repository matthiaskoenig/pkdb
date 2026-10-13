"""Line numbers of study format 2 tables, as curators count them (#938).

In a table with a header, `<kind>[_<source>].tsv`, the header is line 0 and the
first entry line 1, so line n is row n + 1 of its sheet. A raw table
`<study>_<source>.tsv` has no header and starts at line 1, which is row 1. An
issue keeps the address of its cell in the workbook.
"""

from copy import deepcopy

import pytest

from pkdb.schemas.source import SourceLocation
from pkdb.studyformat import read_study
from pkdb.studyformat.issues import make_issue, table_place
from pkdb.studyformat.load import load_study, load_table
from pkdb.studyformat.raw import load_raw
from pkdb.studyformat.tables import TABLES, has_header, table_line, workbook_row
from pkdb.studyformat.validation import format_issues

OUTPUTS = TABLES["outputs"]


def test_the_header_is_line_0_and_the_first_entry_line_1():
    data = b"subjects\tmean\tcount\nall\t2,5\t1.5\n\nS1\t3\t2\n"
    table, issues = load_table(
        "outputs_Tab1.tsv", data, OUTPUTS, "Tab1", study="Example"
    )
    assert table is not None
    # A blank line is skipped but keeps its number.
    assert [row.line for row in table.rows] == [1, 3]
    # The cell is the address in the workbook: line 1 is row 2 of the sheet.
    assert [
        (issue.code, issue.source.row, issue.source.cell)
        for issue in issues
        if issue.source
    ] == [("invalid_integer", 1, "C2"), ("invalid_number", 1, "B2")]


def test_a_problem_of_the_header_is_at_line_0_and_row_1():
    data = b"subjects\tmeen\nall\t1\n"
    table, issues = load_table(
        "outputs_Tab1.tsv", data, OUTPUTS, "Tab1", study="Example"
    )
    assert table is None
    [issue] = issues
    assert issue.source is not None
    assert (issue.code, issue.source.row, issue.source.cell) == (
        "unknown_column",
        0,
        "B1",
    )


def test_a_raw_table_starts_at_line_1_and_row_1():
    raw, issues = load_raw(
        "Example_Tab2.tsv", [b"Sex\tAge\n", b"\n", b"M\t30\n"], "Tab2"
    )
    assert issues == [] and raw is not None
    assert [row.line for row in raw.rows] == [1, 3]
    issue = make_issue(
        "cell_too_long", "Too long.", file="Example_Tab2.tsv", line=3, column=1
    )
    assert issue.source is not None
    assert (issue.source.row, issue.source.cell) == (3, "B3")


def test_a_record_points_to_its_line_and_its_workbook_cell(valid_study):
    study = read_study(load_study(valid_study))
    records = {record.key: record for record in study.measurements}
    source = records["outputs_Tab2.tsv:1"].source
    assert source is not None and source.row == 1
    assert source.for_header("mean").cell == "N2"


@pytest.mark.parametrize(
    ("file", "header", "row", "line"),
    [
        # Line 1 of the file is row `row` of its sheet; physical line 1 is line `line`.
        ("outputs_Tab2.tsv", True, 2, 0),
        ("subjects.tsv", True, 2, 0),
        ("Example_Tab2.tsv", False, 1, 1),
        ("Example.xlsx", False, 1, 1),
        ("study.json", False, 1, 1),
    ],
)
def test_lines_rows_and_physical_lines(file, header, row, line):
    assert has_header(file) is header
    assert workbook_row(file, 1) == row
    assert table_line(file, 1) == line


def test_a_row_offset_moves_the_cell_of_a_header_and_keeps_line_0():
    location = SourceLocation(file="outputs_Tab2.tsv", sheet="outputs_Tab2", row=0)
    location._columns = {"mean": "N"}
    location._row_offset = 1
    header = location.for_header("mean")
    assert (header.row, header.cell) == (0, "N1")
    assert deepcopy(location).for_header("mean").cell == "N1"
    assert location.model_copy(update={"row": 4}).for_header("mean").cell == "N5"
    # Without an offset the row is the row of the sheet, as study format 1 reads it.
    sheet = SourceLocation(file="Example.xlsx", sheet="Tab1", row=7)
    sheet._columns = {"mean": "C"}
    assert sheet.for_header("mean").cell == "C7"


def test_a_file_out_of_canonical_form_names_the_line_that_differs(valid_study):
    path = valid_study / "outputs_Tab2.tsv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[1] = lines[1].replace("\t2.5\t", "\t2.50\t")
    path.write_text("".join(lines), encoding="utf-8", newline="")
    [issue] = [
        issue
        for issue in format_issues(load_study(valid_study))
        if issue.source and issue.source.file == "outputs_Tab2.tsv"
    ]
    assert issue.source is not None
    assert (issue.code, issue.source.row) == ("not_formatted", 1)
    assert "first difference in line 1" in issue.message


def test_the_place_in_a_table_names_line_column_and_workbook_cell():
    assert table_place(96, "error_bar", "Y97") == [
        "line 96",
        "error_bar",
        "workbook cell Y97",
    ]
    assert table_place(0, "meen", "B1") == ["line 0", "meen", "workbook cell B1"]
    assert table_place(3, None, None) == ["line 3"]
    assert table_place(None, None, None) == []
