"""Outputs rows with a time as points of series over time, as the plot of a figure draws them."""

from pkdb.studyformat.digitize import mapped_points, outputs_series
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study

OUTPUT = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "concentration",
    "substance": "drug",
    "tissue": "plasma",
    "time_unit": "h",
    "unit": "mg/l",
}
SERIES = "all · D1 · concentration · drug · plasma"


def outputs_table(make_study, valid_files, tsv, *rows):
    """outputs_Fig1.tsv of a study with `rows`, after pkdb format."""
    folder = make_study({**valid_files, "outputs_Fig1.tsv": tsv("outputs", *rows)})
    assert format_folder(folder).ok
    table = load_study(folder).table("outputs_Fig1.tsv")
    assert table is not None
    return table


def test_outputs_rows_with_a_time_are_points_of_their_series(
    make_study, valid_files, tsv
):
    table = outputs_table(
        make_study,
        valid_files,
        tsv,
        {**OUTPUT, "time": "1", "mean": "2"},
        {**OUTPUT, "time": "2", "median": "3", "error_bar": "4", "error_type": "sd"},
        # Without a time, with time NR or without a central value: not plotted.
        {**OUTPUT, "measurement": "cmax", "mean": "5"},
        {**OUTPUT, "time": "NR", "mean": "1"},
        {**OUTPUT, "time": "3", "sd": "1"},
    )
    points = mapped_points(table)
    assert [(p.dataset, p.x, p.y, p.column, p.x_text, p.y_text) for p in points] == [
        (SERIES, 1.0, 2.0, "mean", "1", "2"),
        (SERIES, 2.0, 3.0, "median", "2", "3"),
        (f"{SERIES};error_bar", 2.0, 4.0, "error_bar", "2", "4"),
    ]
    assert {p.file for p in points} == {"outputs_Fig1.tsv"}
    # The lines of the rows, as pkdb format sorted them: cmax first.
    assert [p.line for p in points] == [2, 3, 3]


def test_outputs_points_get_the_error_ends_of_their_row(make_study, valid_files, tsv):
    table = outputs_table(
        make_study,
        valid_files,
        tsv,
        {**OUTPUT, "time": "1", "mean": "10", "sd": "2"},
        {**OUTPUT, "time": "2", "mean": "10"},
    )
    assert [(p.x, p.error_low, p.error_high) for p in mapped_points(table)] == [
        (1.0, 8.0, 12.0),
        (2.0, None, None),
    ]


def test_the_series_of_an_outputs_row_leaves_out_its_empty_parts(
    make_study, valid_files, tsv
):
    table = outputs_table(
        make_study,
        valid_files,
        tsv,
        {**OUTPUT, "interventions": "", "time": "1", "mean": "2"},
        {**OUTPUT, "tissue": "", "time": "1", "mean": "3"},
    )
    assert [outputs_series(row) for row in table.rows] == [
        "all · concentration · drug · plasma",
        "all · D1 · concentration · drug",
    ]
    assert [p.dataset for p in mapped_points(table)] == [
        "all · concentration · drug · plasma",
        "all · D1 · concentration · drug",
    ]


def test_the_points_of_an_outputs_series_are_sorted_by_time(
    make_study, valid_files, tsv
):
    # pkdb format sorts method before time: the rows read A at 0 h, A at 2 h, B at 1 h.
    table = outputs_table(
        make_study,
        valid_files,
        tsv,
        {**OUTPUT, "method": "B", "time": "1", "mean": "2"},
        {**OUTPUT, "method": "A", "time": "2", "mean": "3"},
        {**OUTPUT, "method": "A", "time": "0", "mean": "1"},
    )
    assert [
        (row.line, row.cells["method"], row.cells["time"]) for row in table.rows
    ] == [
        (1, "A", "0"),
        (2, "A", "2"),
        (3, "B", "1"),
    ]
    assert [(p.dataset, p.x, p.line) for p in mapped_points(table)] == [
        (SERIES, 0.0, 1),
        (SERIES, 1.0, 3),
        (SERIES, 2.0, 2),
    ]


def test_timecourse_points_keep_the_order_of_their_rows(valid_study):
    table = load_study(valid_study).table("timecourses_Fig1.tsv")
    assert table is not None
    assert [(p.dataset, p.line) for p in mapped_points(table)] == [
        ("drug_plasma", 1),
        ("drug_plasma", 2),
        ("drug_plasma", 3),
    ]
