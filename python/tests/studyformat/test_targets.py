import json

from digitize_fixtures import GOOD, png, project

from pkdb.schemas.review import ReviewTarget
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.targets import DigitizedSeries, TargetMatch, match_target


def digitized(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
        }
    )
    assert format_folder(folder).ok
    return load_study(folder)


def test_a_row_filter_matches_the_lines_of_its_rows(valid_study):
    study = load_study(valid_study)
    table = study.table("timecourses_Fig1.tsv")
    assert table is not None
    expected = tuple(row.line for row in table.rows if row.cells["time"] == "1")
    target = ReviewTarget(
        file="timecourses_Fig1.tsv", rows={"label": "drug_plasma", "time": "1"}
    )
    assert match_target(study, target).lines == expected
    nothing = ReviewTarget(file="timecourses_Fig1.tsv", rows={"label": "drug_feces"})
    assert match_target(study, nothing).lines == ()


def test_a_target_without_rows_or_of_another_file_has_no_lines(valid_study):
    study = load_study(valid_study)
    for target in (
        None,
        ReviewTarget(),
        ReviewTarget(file="timecourses_Fig1.tsv", column="mean"),
        ReviewTarget(file="study.json"),
    ):
        assert match_target(study, target).lines is None
        assert match_target(study, target).series is None
    # The rows of a data table are counted, also without a row filter.
    column = ReviewTarget(file="timecourses_Fig1.tsv", column="mean")
    assert match_target(study, column).total == 3
    assert match_target(study, ReviewTarget(file="study.json")).total is None


def test_a_series_of_a_digitized_figure_is_named(make_study, valid_files):
    study = digitized(make_study, valid_files)
    series = ReviewTarget(
        file="timecourses_Fig1.tsv", rows={"label": "drug_plasma", "time": "1"}
    )
    assert match_target(study, series).series == DigitizedSeries("Fig1", "drug_plasma")
    # Fig2 has no WebPlotDigitizer project, and a paper table no digitization at all.
    scatter = ReviewTarget(file="scatters_Fig2.tsv", rows={"name": "age_vs_cmax"})
    assert match_target(study, scatter).series is None
    table = ReviewTarget(file="outputs_Tab2.tsv", rows={"measurement": "cmax"})
    assert match_target(study, table).series is None


def test_a_scatter_series_is_named_by_its_name(make_study, valid_files):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig2.png": png(100, 100),
            "Example_Fig2.wpd.json": json.dumps(project([], extra=("age_vs_cmax",))),
        }
    )
    study = load_study(folder)
    target = ReviewTarget(file="scatters_Fig2.tsv", rows={"name": "age_vs_cmax"})
    assert match_target(study, target) == TargetMatch(
        (2, 3), DigitizedSeries("Fig2", "age_vs_cmax"), 2
    )
    # A scatter series is named by `name`, not by `label`.
    label = ReviewTarget(file="scatters_Fig2.tsv", rows={"label": "age_vs_cmax"})
    assert match_target(study, label) == TargetMatch((), None, 2)
