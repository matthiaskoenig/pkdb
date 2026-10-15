import pytest
from migration_fixtures import Formula, v1_study

from pkdb.importers.folder import load_folder, parse_bundle
from pkdb.migration.formulas import error_bars, references


def study_with(root, spread, *, column="sd", upper=3.25):
    """A format 1 output whose `column` cell B3 holds `spread`.

    Row 1 holds notes and row 2 the header, so mean is A3 and upper C3.
    """
    output = {
        "source": "Tab2",
        "output_type": "output",
        "group": "all",
        "measurement_type": "cmax",
        "substance": "drug",
        "tissue": "plasma",
        "mean": "col==mean",
        column: f"col=={column}",
        "unit": "mg/l",
    }
    study = {
        "sid": "Example",
        "name": "Example",
        "reference": "123",
        "creator": "curator",
        "groupset": {"groups": [{"name": "all", "count": 4}]},
        "outputset": {"outputs": [output]},
    }
    sheets = {"Tab2": [["mean", column, "upper"], [2.5, spread, upper]]}
    folder = v1_study(root, study, sheets, ())
    return folder / "Example.xlsx", parse_bundle(load_folder(folder))


def test_abs_of_a_difference_with_the_mean_is_an_error_bar(tmp_path):
    workbook, study = study_with(tmp_path, Formula("=ABS(C3-A3)", 0.75))
    [record] = study.measurements
    # The importer reads the saved value of the formula.
    assert record.statistics.sd == 0.75
    assert error_bars(workbook, study) == {record.key: (3.25, "sd")}


@pytest.mark.parametrize("formula", ["= ABS( A3 - C3 )", "=abs($A$3-$C3)"])
def test_operands_in_either_order_spaces_and_dollars_are_accepted(tmp_path, formula):
    workbook, study = study_with(tmp_path, Formula(formula, 0.75), column="se")
    [record] = study.measurements
    assert error_bars(workbook, study) == {record.key: (3.25, "se")}


@pytest.mark.parametrize(
    ("formula", "value"),
    [
        ("=C3-A3", 0.75),
        ("=ABS(C3-B4)", 3.25),
        ("=ABS(C3-A3)/2", 0.375),
        ("=0.75", 0.75),
        ("=ABS(Tab1!C3-A3)", 0.75),
    ],
)
def test_other_formulas_are_no_error_bars(tmp_path, formula, value):
    workbook, study = study_with(tmp_path, Formula(formula, value))
    assert error_bars(workbook, study) == {}


def test_an_error_bar_below_zero_keeps_the_spread(tmp_path):
    # The other cell is the lower end of the error bar, below zero.
    workbook, study = study_with(tmp_path, Formula("=ABS(C3-A3)", 2.75), upper=-0.25)
    assert error_bars(workbook, study) == {}


def test_a_spread_without_a_formula_is_no_error_bar(tmp_path):
    workbook, study = study_with(tmp_path, 0.75)
    assert error_bars(workbook, study) == {}


@pytest.mark.parametrize(
    ("formula", "cells", "outside"),
    [
        ("=ABS($E3-F$4)", {(3, "E"), (4, "F")}, False),
        ("=AVERAGE(B3:C4)", {(3, "B"), (3, "C"), (4, "B"), (4, "C")}, False),
        ("='Tab2'!B3*2", {(3, "B")}, False),
        ("=Fig1!B3+B3", {(3, "B")}, True),
        ("=SUM(B:B)", set(), True),
        ("=SUM(B1:B20000)", set(), True),
        ("=dose*B3", {(3, "B")}, True),
    ],
    ids=["cells", "range", "own sheet", "other sheet", "column", "large", "name"],
)
def test_references_are_the_cells_of_the_sheet_that_a_formula_reads(
    formula, cells, outside
):
    read = references(formula, "Tab2")
    assert (set(read.cells), read.outside) == (cells, outside)
