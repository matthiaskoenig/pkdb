import json

import pytest
from digitize_fixtures import GOOD, png, project

from pkdb.studyformat.colors import SERIES_COLORS, SERIES_DARK_COLORS
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.plot import _error_ranges
from pkdb.studyformat.sources import source_view, study_sources


def test_study_sources_lists_every_source(valid_study):
    (valid_study / "Example_Tab2.tsv").write_text(
        "cmax\t2.5 ± 0.5\n", encoding="utf-8", newline=""
    )
    summaries = {s.source: s for s in study_sources(load_study(valid_study))}
    assert list(summaries) == ["Fig1", "Fig2", "Tab1", "Tab2", "TabA", "Text"]
    assert (
        summaries["Tab2"].raw == "Example_Tab2.tsv"
        and summaries["Tab2"].raw_kind == "table"
    )
    assert summaries["Tab1"].tables == ("subjects.tsv", "characteristica.tsv")
    assert summaries["Text"].image is None


def test_table_source_view(valid_study):
    (valid_study / "Example_Tab2.tsv").write_text(
        "cmax\t2.5 ± 0.5\n", encoding="utf-8", newline=""
    )
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
    assert {p.line for p in view.overlay if p.role == "mapped"} == {1, 2, 3}
    assert view.unmatched == ()


def test_figure_without_digitization_lists_unmatched_series(valid_study):
    view = source_view(load_study(valid_study), "Fig1")
    assert view.digitization is None and view.unmatched == ("drug_plasma",)


def test_unknown_source_raises(valid_study):
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
    assert [
        (p.series, p.line, p.x, p.y, p.error_low, p.error_high) for p in view.points
    ] == [
        ("drug_plasma", 1, 0.0, 0.0, None, None),
        # The digitized end of an error bar of type sd, mirrored around the mean.
        ("drug_plasma", 2, 1.0, 2.5, 2.0, 3.0),
        ("drug_urine", 4, 2.0, 4.0, None, None),
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


def test_a_paper_table_whose_raw_table_is_its_source_lacks_no_image(valid_study):
    (valid_study / "Example_Tab2.png").unlink()
    tab2 = next(s for s in study_sources(load_study(valid_study)) if s.source == "Tab2")
    assert (tab2.image, tab2.missing_image) == (None, "Example_Tab2.png")
    (valid_study / "Example_Tab2.tsv").write_text("cmax\t2.5\n", encoding="utf-8")
    tab2 = next(s for s in study_sources(load_study(valid_study)) if s.source == "Tab2")
    assert (tab2.image, tab2.raw, tab2.missing_image, tab2.missing_raw) == (
        None,
        "Example_Tab2.tsv",
        None,
        None,
    )
    view = source_view(load_study(valid_study), "Tab2")
    assert (view.image, view.image_size, view.raw_grid) == (
        None,
        None,
        (("cmax", "2.5"),),
    )


def test_mapped_tables_say_whether_other_sources_share_them(valid_study):
    view = source_view(load_study(valid_study), "Tab1")
    assert {table.file: table.shared for table in view.mapped} == {
        "subjects.tsv": True,
        "characteristica.tsv": True,
    }
    assert [
        table.shared for table in source_view(load_study(valid_study), "Tab2").mapped
    ] == [False]


def scaled_project(*, log_x=False, log_y=False, low="1", high="100"):
    """The project of `project(GOOD)` on axes from `low` to `high`, log where asked."""
    data = project(GOOD)
    axes = data["axesColl"][0]
    axes["isLogX"], axes["isLogY"] = log_x, log_y
    axes["calibrationPoints"] = [
        {"px": 0, "py": 100, "dx": low, "dy": low, "dz": None},
        {"px": 100, "py": 100, "dx": high, "dy": low, "dz": None},
        {"px": 0, "py": 100, "dx": low, "dy": low, "dz": None},
        {"px": 0, "py": 0, "dx": low, "dy": high, "dz": None},
    ]
    return data


def figure_view(make_study, valid_files, data):
    """The view of Fig1 of a study whose project is `data`."""
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(data),
        }
    )
    assert format_folder(folder).ok
    return source_view(load_study(folder), "Fig1")


def test_scales_are_linear_without_a_digitization(valid_study):
    view = source_view(load_study(valid_study), "Fig1")
    assert (view.log_x, view.log_y) == (False, False)


@pytest.mark.parametrize(
    ("log_x", "log_y", "low", "high", "expected"),
    [
        (False, False, "1", "100", (False, False)),
        (False, True, "1", "100", (False, True)),
        (True, True, "1", "100", (True, True)),
        # A plot draws a log axis of values above 0 only: negative values stay linear.
        (False, True, "-100", "-1", (False, False)),
    ],
)
def test_scales_follow_the_log_axes_of_the_digitization(
    make_study, valid_files, log_x, log_y, low, high, expected
):
    data = scaled_project(log_x=log_x, log_y=log_y, low=low, high=high)
    view = figure_view(make_study, valid_files, data)
    assert (view.log_x, view.log_y) == expected


def inset(data, **changes):
    """Add the axes `Inset`, a copy of the first axes with `changes`, to the project `data`."""
    data["axesColl"].append({**data["axesColl"][0], "name": "Inset", **changes})


def log_y_on_the_axes_of_a_dataset_only(data):
    inset(data, isLogY=False)
    data["datasetColl"].append(
        {"name": "drug_urine", "axesName": "Inset", "data": [{"x": 50, "y": 50}]}
    )


def without_datasets(data):
    inset(data, isLogX=True)
    data["datasetColl"] = []


def log_on_every_axes(data):
    inset(data)
    data["datasetColl"].append(
        {"name": "drug_urine", "axesName": "Inset", "data": [{"x": 50, "y": 50}]}
    )


@pytest.mark.parametrize(
    ("log_x", "change", "expected"),
    [
        # An axis is log only when it is log on every axes that a dataset uses.
        (False, log_y_on_the_axes_of_a_dataset_only, (False, False)),
        # A project without datasets counts all its axes: y is log on both, x on the inset only.
        (False, without_datasets, (False, True)),
        (True, log_on_every_axes, (True, True)),
    ],
)
def test_the_scales_of_several_axes(make_study, valid_files, log_x, change, expected):
    data = scaled_project(log_x=log_x, log_y=True)
    change(data)
    view = figure_view(make_study, valid_files, data)
    assert (view.log_x, view.log_y) == expected


def test_points_carry_the_error_bars_of_their_statistics(make_study, valid_files, tsv):
    rows = [
        {**TIMECOURSE, "time": "0", "mean": "2", "sd": "0.5"},
        {**TIMECOURSE, "time": "1", "mean": "2", "se": "0.25"},
        {**TIMECOURSE, "label": "drug_gmean", "time": "1", "gmean": "4", "gsd": "2"},
    ]
    folder = make_study(
        {**valid_files, "timecourses_Fig1.tsv": tsv("timecourses", *rows)}
    )
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    assert [(p.series, p.y, p.error_low, p.error_high) for p in view.points] == [
        ("drug_gmean", 4.0, 2.0, 8.0),
        ("drug_plasma", 2.0, 1.5, 2.5),
        ("drug_plasma", 2.0, 1.75, 2.25),
    ]


def test_mapped_overlay_points_carry_the_pixels_of_their_error_bar_ends(
    make_study, valid_files, tsv
):
    folder = with_error_bars(
        make_study,
        valid_files,
        tsv,
        **{
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
        },
    )
    view = source_view(load_study(folder), "Fig1")
    mapped = {p.line: p for p in view.overlay if p.role == "mapped"}
    # 2.5 at 1 h is pixel (10, 75); its bar from 2 to 3 goes from pixel 80 up to pixel 70.
    assert (mapped[2].px, mapped[2].py) == (10.0, 75.0)
    assert (mapped[2].error_low_px, mapped[2].error_high_px) == (
        (10.0, 80.0),
        (10.0, 70.0),
    )
    assert (mapped[1].error_low_px, mapped[1].error_high_px) == (None, None)
    assert all(
        (p.error_low_px, p.error_high_px) == (None, None)
        for p in view.overlay
        if p.role == "raw"
    )


def test_an_error_bar_end_off_a_log_axis_has_no_pixel(make_study, valid_files, tsv):
    # 2 ± 3 on a log y axis from 1 to 100: the low end -1 has no pixel.
    rows = [{**TIMECOURSE, "time": "1", "mean": "2", "sd": "3"}]
    folder = make_study(
        {
            **valid_files,
            "timecourses_Fig1.tsv": tsv("timecourses", *rows),
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(scaled_project(log_y=True)),
        }
    )
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    assert [(p.error_low, p.error_high) for p in view.points] == [(-1.0, 5.0)]
    [mapped] = [p for p in view.overlay if p.role == "mapped"]
    assert mapped.error_low_px is None
    assert mapped.error_high_px is not None and mapped.error_high_px[1] < mapped.py


OUTPUT = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "concentration",
    "substance": "drug",
    "tissue": "plasma",
    "time_unit": "h",
    "unit": "mg/l",
}
OUTPUT_SERIES = "all · D1 · concentration · drug · plasma"


def test_outputs_with_a_time_are_plotted_as_series_by_time(
    make_study, valid_files, tsv
):
    rows = [
        {**OUTPUT, "time": "2", "mean": "3"},
        {**OUTPUT, "time": "1", "mean": "2"},
        {**OUTPUT, "measurement": "cmax", "mean": "5"},
    ]
    folder = make_study({**valid_files, "outputs_Fig1.tsv": tsv("outputs", *rows)})
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    outputs = [p for p in view.points if p.kind == "outputs"]
    assert [(p.series, p.file, p.line, p.x, p.y) for p in outputs] == [
        (OUTPUT_SERIES, "outputs_Fig1.tsv", 2, 1.0, 2.0),
        (OUTPUT_SERIES, "outputs_Fig1.tsv", 3, 2.0, 3.0),
    ]
    # Without a digitization, every series is plotted beside the image.
    assert view.layout == "side_by_side"
    assert set(view.unmatched) == {"drug_plasma", OUTPUT_SERIES}
    series = {entry.name: entry for entry in view.series}
    assert (series[OUTPUT_SERIES].x_label, series[OUTPUT_SERIES].y_label) == (
        "time (h)",
        "concentration (mg/l)",
    )


def test_outputs_rows_of_one_series_at_the_same_time_are_ordered_by_line(
    make_study, valid_files, tsv
):
    # The canonical order puts `calculation` before `time`, so the two rows at 1 h are not adjacent.
    rows = [
        {**OUTPUT, "calculation": "a", "time": "1", "mean": "4"},
        {**OUTPUT, "calculation": "b", "time": "2", "mean": "5"},
        {**OUTPUT, "calculation": "c", "time": "1", "mean": "3"},
    ]
    folder = make_study({**valid_files, "outputs_Fig1.tsv": tsv("outputs", *rows)})
    format_folder(folder)
    outputs = [
        p for p in source_view(load_study(folder), "Fig1").points if p.kind == "outputs"
    ]
    assert [(p.x, p.line) for p in outputs] == [(1.0, 1), (1.0, 3), (2.0, 2)]


def test_an_outputs_row_with_an_sd_has_an_error_bar(make_study, valid_files, tsv):
    folder = make_study(
        {
            **valid_files,
            "outputs_Fig1.tsv": tsv(
                "outputs", {**OUTPUT, "time": "1", "mean": "2", "sd": "0.5"}
            ),
        }
    )
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    (point,) = [p for p in view.points if p.kind == "outputs"]
    assert (point.error_low, point.error_high) == (1.5, 2.5)
    assert _error_ranges([point]) == [[0.5], [0.5]]


def test_an_outputs_series_with_a_dataset_is_drawn_on_the_image(
    make_study, valid_files, tsv
):
    data = project(GOOD)
    data["datasetColl"].append(
        {"name": OUTPUT_SERIES, "axesName": "XY", "data": [{"x": 10, "y": 80}]}
    )
    folder = make_study(
        {
            **valid_files,
            "outputs_Fig1.tsv": tsv("outputs", {**OUTPUT, "time": "1", "mean": "2"}),
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(data),
        }
    )
    assert format_folder(folder).ok
    view = source_view(load_study(folder), "Fig1")
    assert view.layout == "overlay"
    assert [
        (p.px, p.py, p.file, p.line)
        for p in view.overlay
        if p.role == "mapped" and p.series == OUTPUT_SERIES
    ] == [(10.0, 80.0, "outputs_Fig1.tsv", 1)]
    assert OUTPUT_SERIES not in view.unmatched
