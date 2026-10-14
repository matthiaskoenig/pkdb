"""The error bars of the plotted points: which statistic of a row draws them, around which value."""

import pytest

from pkdb.studyformat.digitize import error_ends, mapped_points
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study

CELLS = ("mean", "median", "gmean", "sd", "se", "gsd", "error_bar", "error_type")


def ends(column: str, **values: object) -> tuple[float, float] | None:
    """The error bar of a row with `values` (the other statistics empty) around `column`."""
    return error_ends({name: values.get(name) for name in CELLS}, column)


@pytest.mark.parametrize(
    ("column", "values", "expected"),
    [
        pytest.param("mean", {"mean": 2.0, "sd": 0.5}, (1.5, 2.5), id="sd"),
        pytest.param("mean", {"mean": 2.0, "se": 0.25}, (1.75, 2.25), id="se"),
        pytest.param(
            "mean", {"mean": 2.0, "sd": 0.5, "se": 0.25}, (1.5, 2.5), id="sd_before_se"
        ),
        pytest.param(
            "mean",
            {"mean": 2.0, "sd": 0.5, "se": 0.25, "error_bar": 2.25, "error_type": "se"},
            (1.75, 2.25),
            id="reported_statistic_of_error_type_first",
        ),
        pytest.param(
            "mean",
            {"mean": 2.5, "error_bar": 3.0, "error_type": "sd"},
            (2.0, 3.0),
            id="digitized_sd_is_mirrored_around_the_mean",
        ),
        pytest.param(
            "mean",
            {"mean": 2.5, "sd": 1.0, "error_bar": 3.0, "error_type": "se"},
            (2.0, 3.0),
            id="digitized_se_before_a_reported_sd",
        ),
        pytest.param(
            "gmean", {"gmean": 4.0, "gsd": 2.0}, (2.0, 8.0), id="gsd_around_a_gmean"
        ),
        pytest.param(
            "gmean",
            {"gmean": 4.0, "error_bar": 8.0, "error_type": "gsd"},
            (2.0, 8.0),
            id="digitized_gsd_upper_end",
        ),
        pytest.param(
            "gmean",
            {"gmean": 4.0, "error_bar": 2.0, "error_type": "gsd"},
            (2.0, 8.0),
            id="digitized_gsd_lower_end",
        ),
        pytest.param(
            "mean",
            {"mean": 3.0, "gmean": 4.0, "gsd": 2.0, "sd": 1.0},
            (2.0, 4.0),
            id="gsd_around_a_mean_falls_through_to_sd",
        ),
        pytest.param(
            "mean",
            {"mean": 3.0, "gmean": 4.0, "error_bar": 6.0, "error_type": "gsd"},
            None,
            id="digitized_gsd_around_a_mean_gives_no_bar",
        ),
        pytest.param(
            "gmean",
            {"gmean": 4.0, "error_bar": -1.0, "error_type": "gsd"},
            None,
            id="digitized_gsd_below_0_gives_no_bar",
        ),
        pytest.param(
            "gmean",
            {"gmean": 4.0, "gsd": 0.5, "error_bar": 8.0, "error_type": "gsd"},
            None,
            id="invalid_reported_gsd_is_not_mirrored",
        ),
        pytest.param(
            "median", {"median": 4.0, "sd": 1.0}, (3.0, 5.0), id="median_with_sd"
        ),
        pytest.param(
            "median",
            {"median": 4.0, "error_bar": 5.0, "error_type": "sd"},
            (3.0, 5.0),
            id="digitized_sd_without_a_mean_is_mirrored_around_the_median",
        ),
        pytest.param(
            "mean",
            {"mean": 2.0, "error_bar": 2.5},
            (1.5, 2.5),
            id="error_bar_without_error_type_is_mirrored",
        ),
        pytest.param(
            "mean",
            {"mean": 2.0, "sd": -0.5},
            None,
            id="negative_sd_gives_no_bar",
        ),
        pytest.param(
            "mean",
            {"mean": 2.0, "sd": -0.5, "se": 0.25},
            (1.75, 2.25),
            id="negative_sd_falls_through",
        ),
        pytest.param(
            "gmean", {"gmean": 4.0, "gsd": 0.5}, None, id="gsd_below_1_does_not_fit"
        ),
        pytest.param(
            "gmean",
            {"gmean": 0.0, "gsd": 2.0, "sd": 1.0},
            (-1.0, 1.0),
            id="gmean_at_0_has_no_gsd_bar",
        ),
        pytest.param(
            "gmean",
            {"gmean": 4.0, "gsd": 2.0, "sd": 1.0},
            (2.0, 8.0),
            id="gsd_before_sd_around_a_gmean",
        ),
        pytest.param("mean", {"mean": 2.0}, None, id="no_statistic"),
        pytest.param(
            "gmean", {"gmean": 4.0, "gsd": 0.0}, None, id="gsd_of_0_does_not_fit"
        ),
        pytest.param(
            "mean",
            {"mean": 1e308, "sd": 1e308, "se": 1.0},
            (1e308 - 1.0, 1e308 + 1.0),
            id="overflowing_sd_falls_through",
        ),
    ],
)
def test_error_ends(column, values, expected):
    found = ends(column, **values)
    if expected is None:
        assert found is None
    else:
        assert found == pytest.approx(expected)


def test_an_overflowing_error_bar_without_another_statistic_is_none():
    assert ends("mean", mean=1e308, sd=1e308) is None


TIMECOURSE = {
    "label": "drug_plasma",
    "subjects": "all",
    "interventions": "D1",
    "measurement": "concentration",
    "substance": "drug",
    "tissue": "plasma",
    "time_unit": "h",
    "unit": "mg/l",
}


def test_timecourse_points_carry_the_ends_of_their_error_bars(
    make_study, valid_files, tsv
):
    rows = [
        {**TIMECOURSE, "time": "0", "mean": "2", "sd": "0.5"},
        {
            **TIMECOURSE,
            "time": "1",
            "mean": "2.5",
            "error_bar": "3",
            "error_type": "sd",
        },
        {**TIMECOURSE, "time": "2", "mean": "1"},
    ]
    folder = make_study(
        {**valid_files, "timecourses_Fig1.tsv": tsv("timecourses", *rows)}
    )
    assert format_folder(folder).ok
    table = load_study(folder).table("timecourses_Fig1.tsv")
    assert table is not None
    assert [
        (p.dataset, p.line, p.error_low, p.error_high) for p in mapped_points(table)
    ] == [
        ("drug_plasma", 1, 1.5, 2.5),
        ("drug_plasma", 2, 2.0, 3.0),
        # The digitized end itself, which the checks compare with the dataset of the error bars.
        ("drug_plasma;error_bar", 2, None, None),
        ("drug_plasma", 3, None, None),
    ]


def test_scatter_points_have_no_error_bars(valid_study):
    table = load_study(valid_study).table("scatters_Fig2.tsv")
    assert table is not None
    assert {(p.error_low, p.error_high) for p in mapped_points(table)} == {(None, None)}
