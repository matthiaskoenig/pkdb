"""Line numbers of study format 2 tables, as curators count them (#938).

In a table with a header, `<kind>[_<source>].tsv`, the header is line 0 and the
first entry line 1, so line n is row n + 1 of its sheet. A raw table
`<study>_<source>.tsv` has no header and starts at line 1, which is row 1. An
issue keeps the address of its cell in the workbook.
"""

import pytest

from pkdb.studyformat import read_study
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.load import load_study, load_table
from pkdb.studyformat.raw import load_raw
from pkdb.studyformat.tables import TABLES

OUTPUTS = TABLES["outputs"]
# Strict: a test that passes before its task removes the mark fails.
NUMBERED_FROM_THE_HEADER = pytest.mark.xfail(
    strict=True, reason="#938: the header of a table is still line 1"
)


@NUMBERED_FROM_THE_HEADER
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


@NUMBERED_FROM_THE_HEADER
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


@NUMBERED_FROM_THE_HEADER
def test_a_record_points_to_its_line_and_its_workbook_cell(valid_study):
    study = read_study(load_study(valid_study))
    records = {record.key: record for record in study.measurements}
    source = records["outputs_Tab2.tsv:1"].source
    assert source is not None and source.row == 1
    assert source.for_header("mean").cell == "N2"
