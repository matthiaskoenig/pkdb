import pytest
from migration_fixtures import (
    IMAGES,
    SHEETS,
    SPLIT_HEADER,
    SPLIT_OUTPUT,
    SPLIT_ROW,
    STUDY,
    Formula,
    v1_study,
)

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.unmapped import unmapped_values


def dropped(found):
    """The unmapped numbers of the rows with dropped records, by record key."""
    return {key: row.numbers for row in found for key in row.dropped}


def converted(found):
    """The unmapped numbers of the rows whose records are all kept, by sheet row."""
    return {row.row[1:]: row.numbers for row in found if not row.dropped}


GROUP = {
    "source": "Tab1",
    "image": "Tab1",
    "name": "col==group",
    "count": "col==count",
    "characteristica": [
        {"measurement_type": "col==measurement", "mean": "col==mean", "unit": "yr"}
    ],
}
TAB1 = [
    ["group", "count", "measurement", "mean", "Median", "comments"],
    ["all", 2, "age", 35, "NA", "NA"],
    ["all", 2, "age", "NA", 40, 7],
]


def test_each_characteristic_of_a_subject_keeps_its_row(tmp_path):
    study = {**STUDY, "groupset": {"groups": [GROUP]}}
    v1 = v1_study(tmp_path, study, {**SHEETS, "Tab1": TAB1}, IMAGES)
    [group] = parse_bundle(load_folder(v1)).groups
    sources = [record.source for record in group.characteristica]
    assert group.source is not None and None not in sources
    assert [(s.sheet, s.row) for s in sources if s] == [("Tab1", 3), ("Tab1", 4)]
    # The headers that the template maps, those of characteristica included.
    assert group.source._mapped == {"group", "count", "measurement", "mean"}
    assert all(s and s._mapped == group.source._mapped for s in sources)


def test_numbers_of_unmapped_statistic_columns_are_found_in_hidden_tables(tmp_path):
    # A hidden table holds text: `40` is a number, in a column of any case;
    # comments hold no value.
    study = {**STUDY, "groupset": {"groups": [GROUP]}}
    v1 = v1_study(tmp_path, study, {**SHEETS, "Tab1": TAB1}, IMAGES, workbook=False)
    parsed = parse_bundle(load_folder(v1))
    keys = [record.key for record in parsed.groups[0].characteristica]
    assert dropped(unmapped_values(load_folder(v1), parsed, keys)) == {
        keys[1]: [("Median", "40")]
    }


def test_numbers_of_any_unmapped_column_but_counts_times_and_comments_are_found(
    tmp_path,
):
    # Statistics have many names in format 1 sheets, such as a geometric mean,
    # a confidence limit or a quartile. Counts, times, names and comments hold
    # no value of the row.
    tab1 = [
        ["group", "count", "measurement", "mean", "geomean", "CI_low", "q25"],
        ["all", 2, "age", 35, "NA", "NA", "NA"],
        ["all", 2, "age", "NA", 40, 38, 36],
    ]
    tab1 = [[*row, "n", "time", "Notes"] for row in tab1]
    tab1[1:] = [[*row[:-3], 2, 1, 5] for row in tab1[1:]]
    study = {**STUDY, "groupset": {"groups": [GROUP]}}
    v1 = v1_study(tmp_path, study, {**SHEETS, "Tab1": tab1}, IMAGES, workbook=False)
    parsed = parse_bundle(load_folder(v1))
    keys = [record.key for record in parsed.groups[0].characteristica]
    assert dropped(unmapped_values(load_folder(v1), parsed, keys)) == {
        keys[1]: [("geomean", "40"), ("CI_low", "38"), ("q25", "36")]
    }


def _split_study(tmp_path, header, row, *, workbook=True):
    """The dropped cmax record of the split Tab2 row, with its unmapped numbers."""
    study = {**STUDY, "outputset": {"outputs": [SPLIT_OUTPUT]}}
    sheets = {**SHEETS, "Tab2": [header, row]}
    v1 = v1_study(tmp_path, study, sheets, IMAGES, workbook=workbook)
    parsed = parse_bundle(load_folder(v1))
    [cmax] = [r.key for r in parsed.measurements if r.measurement_type == "cmax"]
    return dropped(unmapped_values(load_folder(v1), parsed, [cmax])), cmax


def test_columns_that_feed_a_kept_record_of_the_row_are_no_unmapped_values(tmp_path):
    # The AUC record keeps auc_pm through its error bar and auc_sd is computed
    # from its se and the count, so the dropped cmax record loses no number.
    found, _ = _split_study(tmp_path, SPLIT_HEADER, SPLIT_ROW)
    assert found == {}


@pytest.mark.parametrize(
    ("change", "lost"),
    [
        # A number in a column that no formula of a kept cell reads.
        ({"extra": 7}, [("extra", "7")]),
        # A formula that also reads an unmapped number computes data of its own.
        (
            {"extra": 7, "auc_sd": Formula("=G3*SQRT(B3)+I3", 7.2121)},
            [("auc_sd", "7.2121"), ("extra", "7")],
        ),
        # A formula that reads another row computes no number of this row alone.
        ({"auc_sd": Formula("=G2*SQRT(B3)", 0.5)}, [("auc_sd", "0.5")]),
        # A constant is a number of its own.
        ({"auc_sd": Formula("=0.5", 0.5)}, [("auc_sd", "0.5")]),
        # A formula of a kept cell that reads another sheet does not read auc_pm,
        # which is no end of the error bar 3.5 +- 0.2 either; the sd is still
        # computed from the kept se.
        ({"auc_se": Formula("=ABS($E3-Fig1!F3)", 0.2)}, [("auc_pm", "3.65")]),
    ],
    ids=["unread column", "own data", "other row", "constant", "other sheet"],
)
def test_numbers_that_no_kept_record_of_the_row_holds_are_found(tmp_path, change, lost):
    header, row = [*SPLIT_HEADER], [*SPLIT_ROW]
    for column, cell in change.items():
        if column in header:
            row[header.index(column)] = cell
        else:
            header.append(column)
            row.append(cell)
    found, cmax = _split_study(tmp_path, header, row)
    assert found == {cmax: lost}


def test_hidden_tables_have_no_formulas_that_feed_a_kept_record(tmp_path):
    # A hidden table holds the saved values only, so the check cannot know that
    # the sd is computed; auc_pm is the end of the error bar 3.5 + 0.15.
    found, cmax = _split_study(tmp_path, SPLIT_HEADER, SPLIT_ROW, workbook=False)
    assert found == {cmax: [("auc_sd", "0.2121")]}


CMAX = {
    "source": "Tab2",
    "image": "Tab2",
    "output_type": "output",
    "group": "col==group",
    "interventions": ["D1"],
    "measurement_type": "cmax",
    "substance": "drug",
    "tissue": "plasma",
    "mean": "col==mean",
    "sd": "col==sd",
    "unit": "mg/l",
}


def _converted(tmp_path, header, *rows, output=CMAX, workbook=True):
    """The unmapped numbers of the converted rows of Tab2, by sheet and row."""
    study = {**STUDY, "outputset": {"outputs": [output]}}
    sheets = {**SHEETS, "Tab2": [header, *rows]}
    v1 = v1_study(tmp_path, study, sheets, IMAGES, workbook=workbook)
    parsed = parse_bundle(load_folder(v1))
    return converted(unmapped_values(load_folder(v1), parsed, []))


@pytest.mark.parametrize("workbook", [True, False], ids=["workbook", "hidden tables"])
def test_numbers_of_unmapped_columns_of_converted_rows_are_found(tmp_path, workbook):
    # The cmax rows convert with their mean and sd, so the cv, the range and the
    # median that study.json does not map would be lost.
    header = ["group", "mean", "sd", "cv", "min", "max", "median"]
    rows = [
        ["all", 2.5, 0.5, 20, "NA", "NA", "NA"],
        ["all", 3, 1, "NA", 1.5, 6, 2.8],
        ["all", 4, 1, "NA", "NA", "NA", "NA"],
    ]
    first = 3 if workbook else 2
    sheet = "Tab2" if workbook else None
    assert _converted(tmp_path, header, *rows, workbook=workbook) == {
        (sheet, first): [("cv", "20")],
        (sheet, first + 1): [("min", "1.5"), ("max", "6"), ("median", "2.8")],
    }


def test_copies_of_the_statistics_of_a_kept_record_are_no_unmapped_values(tmp_path):
    # A value column that repeats the mean and the digitized ends of the error
    # bar, the mean plus or minus the sd, hold no number of their own. A max
    # that equals the time of the row is no copy: times are no statistics.
    output = {**CMAX, "time": "col==time", "time_unit": "h"}
    header = ["group", "time", "mean", "sd", "value", "mean_pm", "max"]
    rows = [
        ["all", 1, 2.5, 0.5, 2.5, 3, "NA"],
        ["all", 2, 3.2, 0.4, "NA", 2.8, 2],
    ]
    assert _converted(tmp_path, header, *rows, output=output) == {
        ("Tab2", 4): [("max", "2")]
    }


def test_counts_and_times_are_no_unmapped_values(tmp_path):
    # Columns that count the subjects or place the row in time, such as the
    # start of a collection interval or a digitized time, hold no value.
    header = ["group", "mean", "sd", "subjects", "individual_count", "tstart"]
    header += ["time_start", "time_dig", "Time_end", "day"]
    rows = [["all", 2.5, 0.5, 8, 1, 0, 0, 1.02, 2, 3]]
    assert _converted(tmp_path, header, *rows) == {}


def test_numbers_that_a_formula_of_a_kept_cell_reads_are_held(tmp_path):
    # The name of the group is made of the index, and the sd is computed from
    # the cv, which the sd and the mean determine: the record holds both.
    header = ["idx", "group", "mean", "sd", "cv"]
    rows = [
        [
            1,
            Formula('="all"&IF(A3>1,A3,"")', "all"),
            2.5,
            Formula("=E3/100*C3", 0.5),
            20,
        ]
    ]
    assert _converted(tmp_path, header, *rows) == {}


def test_numbers_computed_from_kept_cells_of_other_rows_are_held(tmp_path):
    # The change of the second row is computed from its mean and the mean of
    # the baseline row; the change of the baseline row is typed in, so it is a
    # number of its own.
    header = ["group", "mean", "sd", "change"]
    rows = [
        ["all", 2.5, 0.5, 0.1],
        ["all", 3, 0.5, Formula("=B4-B$3", 0.5)],
    ]
    assert _converted(tmp_path, header, *rows) == {("Tab2", 3): [("change", "0.1")]}


def test_a_formula_holds_no_numbers_of_other_rows(tmp_path):
    # The mean of the last row averages the cvs of the rows above: it holds none
    # of them, and an error bar computed from the end of the row above is no
    # error bar of this row.
    header = ["group", "mean", "sd", "cv", "mean_pm"]
    rows = [
        ["all", 2.5, 0.5, 20, 3.1],
        ["all", 3, Formula("=ABS(E3-B4)", 0.1), 30, 3.6],
        ["all", Formula("=AVERAGE(D3:D4)", 25), 1, "NA", "NA"],
    ]
    assert _converted(tmp_path, header, *rows) == {
        ("Tab2", 3): [("cv", "20"), ("mean_pm", "3.1")],
        ("Tab2", 4): [("cv", "30"), ("mean_pm", "3.6")],
    }
