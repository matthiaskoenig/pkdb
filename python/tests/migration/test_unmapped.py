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
    assert unmapped_values(load_folder(v1), parsed, keys) == {
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
    assert unmapped_values(load_folder(v1), parsed, keys) == {
        keys[1]: [("geomean", "40"), ("CI_low", "38"), ("q25", "36")]
    }


def _split_study(tmp_path, header, row, *, workbook=True):
    """The dropped cmax record of the split Tab2 row, with its unmapped numbers."""
    study = {**STUDY, "outputset": {"outputs": [SPLIT_OUTPUT]}}
    sheets = {**SHEETS, "Tab2": [header, row]}
    v1 = v1_study(tmp_path, study, sheets, IMAGES, workbook=workbook)
    parsed = parse_bundle(load_folder(v1))
    [cmax] = [r.key for r in parsed.measurements if r.measurement_type == "cmax"]
    return unmapped_values(load_folder(v1), parsed, [cmax]), cmax


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
        # A formula of a kept cell that reads another sheet does not read auc_pm;
        # the sd is still computed from the kept se.
        ({"auc_se": Formula("=ABS($E3-Fig1!F3)", 0.15)}, [("auc_pm", "3.65")]),
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
    # A hidden table holds the saved values only, so the check cannot know them.
    found, cmax = _split_study(tmp_path, SPLIT_HEADER, SPLIT_ROW, workbook=False)
    assert found == {cmax: [("auc_pm", "3.65"), ("auc_sd", "0.2121")]}
