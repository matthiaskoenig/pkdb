import json

from digitize_fixtures import GOOD, png, project

from pkdb.studyformat.colors import SERIES_COLORS, SERIES_DARK_COLORS
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.sources import source_view, study_sources


def test_study_sources_lists_every_source(valid_study):
    (valid_study / "Example_Tab2.tsv").write_text("cmax\t2.5 ± 0.5\n")
    summaries = {s.source: s for s in study_sources(load_study(valid_study))}
    assert list(summaries) == ["Fig1", "Fig2", "Tab1", "Tab2", "TabA", "Text"]
    assert (
        summaries["Tab2"].raw == "Example_Tab2.tsv"
        and summaries["Tab2"].raw_kind == "table"
    )
    assert summaries["Tab1"].tables == ("subjects.tsv", "characteristica.tsv")
    assert summaries["Text"].image is None


def test_table_source_view(valid_study):
    (valid_study / "Example_Tab2.tsv").write_text("cmax\t2.5 ± 0.5\n")
    view = source_view(load_study(valid_study), "Tab2")
    assert view.raw_grid == (("cmax", "2.5 ± 0.5"),)
    assert [table.file for table in view.mapped] == ["outputs_Tab2.tsv"]
    assert view.overlay == ()


def test_figure_overlay_in_pixels(make_study, valid_files):
    files = {
        **valid_files,
        "Example_Fig1.png": png(100, 100),
        "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
    }
    folder = make_study(files)
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    assert view.image_size == (100, 100)
    mapped = [(p.px, p.py) for p in view.overlay if p.role == "mapped"]
    raw = [(p.px, p.py) for p in view.overlay if p.role == "raw"]
    assert mapped == [(0.0, 100.0), (10.0, 80.0), (20.0, 90.0)] == raw
    assert {p.line for p in view.overlay if p.role == "mapped"} == {2, 3, 4}
    assert view.unmatched == ()


def test_figure_without_digitization_lists_unmatched_series(valid_study):
    view = source_view(load_study(valid_study), "Fig1")
    assert view.digitization is None and view.unmatched == ("drug_plasma",)


def test_unknown_source_raises(valid_study):
    import pytest

    with pytest.raises(KeyError):
        source_view(load_study(valid_study), "Tab9")


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


def with_error_bars(make_study, valid_files, tsv, **extra):
    rows = [
        {**TIMECOURSE, "time": "0", "mean": "0"},
        {
            **TIMECOURSE,
            "time": "1",
            "mean": "2.50",
            "error_bar": "3",
            "error_type": "sd",
        },
        {**TIMECOURSE, "time": "NR", "mean": "1"},
        {**TIMECOURSE, "label": "drug_urine", "time": "2", "median": "4"},
    ]
    folder = make_study(
        {**valid_files, "timecourses_Fig1.tsv": tsv("timecourses", *rows), **extra}
    )
    assert format_folder(folder).ok
    return folder


def test_points_are_the_mapped_rows_in_the_units_of_their_table(
    make_study, valid_files, tsv
):
    view = source_view(
        load_study(with_error_bars(make_study, valid_files, tsv)), "Fig1"
    )
    assert [(p.series, p.line, p.x, p.y, p.error_bar) for p in view.points] == [
        ("drug_plasma", 2, 0.0, 0.0, None),
        ("drug_plasma", 3, 1.0, 2.5, 3.0),
        ("drug_urine", 5, 2.0, 4.0, None),
    ]
    # The hover shows the cells as printed, after pkdb format.
    assert [(p.x_text, p.y_text) for p in view.points] == [
        ("0", "0"),
        ("1", "2.5"),
        ("2", "4"),
    ]
    assert {(p.kind, p.file) for p in view.points} == {
        ("timecourses", "timecourses_Fig1.tsv")
    }


def test_points_of_scatters_are_named_by_name(valid_study):
    view = source_view(load_study(valid_study), "Fig2")
    assert [(p.series, p.kind, p.x, p.y, p.x_text) for p in view.points] == [
        ("age_vs_cmax", "scatters", 30.0, 2.0, "30"),
        ("age_vs_cmax", "scatters", 40.0, 3.0, "40"),
    ]


def test_series_have_one_order_colors_and_axis_labels(make_study, valid_files, tsv):
    wpd = project(GOOD)
    wpd["datasetColl"].append(
        {"name": "parent_plasma", "axesName": "XY", "data": [{"x": 5, "y": 5}]}
    )
    folder = with_error_bars(
        make_study,
        valid_files,
        tsv,
        **{"Example_Fig1.png": png(100, 100), "Example_Fig1.wpd.json": json.dumps(wpd)},
    )
    view = source_view(load_study(folder), "Fig1")
    # The datasets of the overlay first, then the series without a dataset.
    assert [s.name for s in view.series] == [
        "drug_plasma",
        "parent_plasma",
        "drug_urine",
    ]
    assert [(s.color, s.dark_color) for s in view.series] == list(
        zip(SERIES_COLORS, SERIES_DARK_COLORS)
    )[:3]
    plasma, parent, urine = view.series
    assert (plasma.x_label, plasma.y_label) == ("time (h)", "concentration (mg/l)")
    # A dataset without rows has no units.
    assert (parent.x_label, parent.y_label) == (None, None)
    assert urine.y_label == "concentration (mg/l)"
    assert view.unmatched == ("drug_urine",) and view.layout == "overlay"


def test_scatter_series_take_the_labels_of_their_axes(valid_study):
    [series] = source_view(load_study(valid_study), "Fig2").series
    assert (series.name, series.x_label, series.y_label) == (
        "age_vs_cmax",
        "age (yr)",
        "cmax (mg/l)",
    )


def test_series_colors_repeat_after_the_palette(valid_study):
    assert len(SERIES_COLORS) == len(SERIES_DARK_COLORS) == 8
    assert len(set(SERIES_COLORS)) == 8


def test_error_bar_ends_belong_to_their_series(make_study, valid_files, tsv):
    wpd = project(GOOD)
    wpd["datasetColl"].append(
        {
            "name": "drug_plasma;error_bar",
            "axesName": "XY",
            "data": [{"x": 10, "y": 50}],
        }
    )
    folder = with_error_bars(
        make_study,
        valid_files,
        tsv,
        **{"Example_Fig1.png": png(100, 100), "Example_Fig1.wpd.json": json.dumps(wpd)},
    )
    view = source_view(load_study(folder), "Fig1")
    raw = [(p.series, p.error_bar_end) for p in view.overlay if p.role == "raw"]
    assert raw == [("drug_plasma", False)] * 3 + [("drug_plasma", True)]
    assert not any(p.error_bar_end for p in view.overlay if p.role == "mapped")
    assert [s.name for s in view.series] == ["drug_plasma", "drug_urine"]


def test_overlay_points_carry_their_values_as_text(make_study, valid_files, tsv):
    folder = with_error_bars(
        make_study,
        valid_files,
        tsv,
        **{
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(project([(0, 100), (10, 75.12345678)])),
        },
    )
    view = source_view(load_study(folder), "Fig1")
    raw = [(p.x_text, p.y_text) for p in view.overlay if p.role == "raw"]
    mapped = [(p.x_text, p.y_text) for p in view.overlay if p.role == "mapped"]
    # Digitized values with the six significant digits of the canonical project.
    assert raw == [("0", "0"), ("1", "2.48765")]
    assert mapped == [("0", "0"), ("1", "2.5")]


def test_layout_is_side_by_side_without_a_calibrated_image(valid_study):
    assert source_view(load_study(valid_study), "Fig1").layout == "side_by_side"


def test_summaries_name_the_kind_and_the_missing_files(valid_study):
    summaries = {s.source: s for s in study_sources(load_study(valid_study))}
    assert {name: s.kind for name, s in summaries.items()} == {
        "Fig1": "figure",
        "Fig2": "figure",
        "Tab1": "table",
        "Tab2": "table",
        "TabA": "table",
        "Text": "text",
    }
    assert (summaries["Tab2"].missing_image, summaries["Tab2"].missing_raw) == (
        None,
        "Example_Tab2.tsv",
    )
    assert summaries["Fig2"].missing_raw == "Example_Fig2.wpd.json"
    assert (summaries["Text"].missing_image, summaries["Text"].missing_raw) == (
        None,
        None,
    )
    (valid_study / "Example_Fig1.png").unlink()
    fig1 = next(s for s in study_sources(load_study(valid_study)) if s.source == "Fig1")
    assert fig1.missing_image == "Example_Fig1.png"


def test_mapped_tables_say_whether_other_sources_share_them(valid_study):
    view = source_view(load_study(valid_study), "Tab1")
    assert {table.file: table.shared for table in view.mapped} == {
        "subjects.tsv": True,
        "characteristica.tsv": True,
    }
    assert [
        table.shared for table in source_view(load_study(valid_study), "Tab2").mapped
    ] == [False]
