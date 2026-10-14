import json
import sys
from dataclasses import replace

import numpy as np
import pytest
from digitize_fixtures import GOOD, png, project

from pkdb.cli import main
from pkdb.studyformat.colors import SERIES_COLORS
from pkdb.studyformat.digitize import png_size
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.plot import (
    _error_ranges,
    _error_segment,
    _linestyle,
    render_source,
)
from pkdb.studyformat.sources import (
    OverlayPoint,
    SourcePoint,
    SourceSeries,
    SourceView,
    source_view,
)

RED = (255, 0, 0)


def digitized(make_study, valid_files, width=100):
    """A study whose Fig1 is digitized on a red image of `width` x 100 pixels."""
    files = {
        **valid_files,
        "Example_Fig1.png": png(width, 100, bytes(RED)),
        "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
    }
    folder = make_study(files)
    assert format_folder(folder).ok
    return folder


def pixels(path):
    """The RGB values of a PNG from 0 to 255, by row and column."""
    from matplotlib.image import imread

    return np.rint(imread(path)[:, :, :3] * 255).astype(int)


def is_color(values, rgb, tolerance=0):
    """Which pixels have the color `rgb`."""
    return np.all(np.abs(values - np.array(rgb)) <= tolerance, axis=2)


def image_size(path):
    """Width and height of a PNG file."""
    size = png_size(path.read_bytes())
    assert size is not None
    return size


def color_box(path, rgb):
    """Left, top, width and height of the pixels of exactly the color `rgb`."""
    rows, columns = np.nonzero(is_color(pixels(path), rgb))
    left, top = int(columns.min()), int(rows.min())
    return left, top, int(columns.max()) - left + 1, int(rows.max()) - top + 1


def test_overlay_draws_the_image_at_its_pixels_with_the_view_pixels(
    make_study, valid_files, tmp_path
):
    study = load_study(digitized(make_study, valid_files, width=600))
    result = render_source(study, "Fig1", tmp_path / "out.png")
    width, height = image_size(result.path)
    # The image keeps its size and its pixels at the top, without blurred edges.
    assert color_box(result.path, RED) == (0, 0, 600, 100)
    assert width == 600 and height > 100
    # Only the marks cover the image, no legend.
    assert np.count_nonzero(~is_color(pixels(result.path)[:100], RED)) < 1000
    expected = tuple(
        (p.px, p.py) for p in source_view(study, "Fig1").overlay if p.role == "mapped"
    )
    assert expected and result.points == expected


def test_overlay_puts_the_series_and_the_mark_key_below_the_image(
    make_study, valid_files, tmp_path
):
    study = load_study(digitized(make_study, valid_files, width=600))
    result = render_source(study, "Fig1", tmp_path / "out.png")
    strip = pixels(result.path)[100:]
    [series] = source_view(study, "Fig1").series
    color = tuple(int(series.color[i : i + 2], 16) for i in (1, 3, 5))
    # The dot of the series and the black marks of the key.
    assert np.count_nonzero(is_color(strip, color, 2)) > 10
    assert np.count_nonzero(is_color(strip, (0, 0, 0), 2)) > 50


def test_overlay_of_a_narrow_image_widens_for_the_legends(
    make_study, valid_files, tmp_path
):
    study = load_study(digitized(make_study, valid_files))
    result = render_source(study, "Fig1", tmp_path / "out.png")
    width, height = image_size(result.path)
    left, top, image_width, image_height = color_box(result.path, RED)
    # The image keeps its pixels in the middle of the top.
    assert (top, image_width, image_height) == (0, 100, 100)
    assert width > 100 and left == (width - 100) // 2 and height > 100
    # The legends fit: the margins of the figure stay white.
    edges = pixels(result.path)[:, [0, -1]]
    assert is_color(edges[100:], (255, 255, 255)).all()


def test_side_by_side_without_digitization(valid_study, tmp_path):
    study = load_study(valid_study)
    for source in ("Fig1", "Fig2"):
        result = render_source(study, source, tmp_path / f"{source}.png")
        assert result.path.exists() and result.points == ()


def test_plot_command_writes_outside_the_study(
    make_study, valid_files, tmp_path, capsys
):
    folder = digitized(make_study, valid_files)
    out = tmp_path / "plots"
    args = ["plot", str(folder), "--out", str(out), "--format", "json"]
    assert main([*args, "--source", "Fig1"]) == 0
    entry = json.loads(capsys.readouterr().out)
    assert entry["plots"] == [
        {
            "source": "Fig1",
            "file": str(out / "Example_Fig1.plot.png"),
            "mode": "overlay",
            "unmatched": [],
        }
    ]
    assert not list(folder.glob("*.plot.png"))
    assert main(args) == 0
    entry = json.loads(capsys.readouterr().out)
    assert [p["source"] for p in entry["plots"]] == ["Fig1", "Fig2"]
    assert (out / "Example_Fig1.plot.png").exists()
    assert (out / "Example_Fig2.plot.png").exists()
    assert entry["plots"][1]["mode"] == "side_by_side"


def test_error_bar_dataset_shares_the_series_color_and_legend_entry(
    make_study, valid_files, tmp_path
):
    wpd = project(GOOD)
    wpd["datasetColl"].append(
        {
            "name": "drug_plasma;error_bar",
            "axesName": "XY",
            "data": [{"x": 10, "y": 90}],
        }
    )
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(wpd),
        }
    )
    assert format_folder(folder).ok
    study = load_study(folder)
    result = render_source(study, "Fig1", tmp_path / "out.png")
    assert result.legend == ("drug_plasma",)
    # Each drawn series once, in the color of the source view, which the curation app draws alike.
    assert result.colors == (
        ("drug_plasma", source_view(study, "Fig1").series[0].color),
    )


def test_render_source_reports_its_mode_without_pyplot(
    make_study, valid_files, tmp_path, monkeypatch
):
    import matplotlib

    def no_backend_switch(*args, **kwargs):
        raise AssertionError("render_source must not switch the global backend")

    # Importing pyplot now fails, so rendering cannot use its global state.
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    monkeypatch.setattr(matplotlib, "use", no_backend_switch)
    study = load_study(digitized(make_study, valid_files))
    overlay = render_source(study, "Fig1", tmp_path / "Fig1.png")
    side = render_source(study, "Fig2", tmp_path / "Fig2.png")
    assert (overlay.mode, side.mode) == ("overlay", "side_by_side")
    assert color_box(overlay.path, RED)[2:] == (100, 100)
    assert png_size(side.path.read_bytes()) == (1200, 500)


def test_plot_lists_series_without_dataset(make_study, valid_files, tmp_path, capsys):
    wpd = project(GOOD)
    wpd["datasetColl"][0]["name"] = "parent_plasma"
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(wpd),
        }
    )
    assert format_folder(folder).ok
    out = tmp_path / "plots"
    args = ["plot", str(folder), "--source", "Fig1", "--out", str(out)]
    assert main([*args, "--format", "json"]) == 0
    [plot] = json.loads(capsys.readouterr().out)["plots"]
    assert (plot["mode"], plot["unmatched"]) == ("overlay", ["drug_plasma"])
    assert main([*args, "--format", "human"]) == 0
    assert capsys.readouterr().out == (
        f"caffeine/Example: Fig1 (overlay) {out / 'Example_Fig1.plot.png'}\n"
        "  series without dataset: drug_plasma\n"
    )


def test_plot_default_sources_include_digitized_figures_without_rows(
    make_study, valid_files, tmp_path, capsys
):
    folder = make_study(
        {
            **valid_files,
            "Example_Fig3.png": png(100, 100),
            "Example_Fig3.wpd.json": json.dumps(project(GOOD)),
        }
    )
    assert format_folder(folder).ok
    out = tmp_path / "plots"
    assert main(["plot", str(folder), "--out", str(out), "--format", "human"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        f"caffeine/Example: Fig1 (side_by_side) {out / 'Example_Fig1.plot.png'}",
        "  series without dataset: drug_plasma",
        f"caffeine/Example: Fig2 (side_by_side) {out / 'Example_Fig2.plot.png'}",
        "  series without dataset: age_vs_cmax",
        f"caffeine/Example: Fig3 (overlay) {out / 'Example_Fig3.plot.png'}",
    ]


@pytest.mark.parametrize("inside", [".", "plots", "plots/deeper"])
def test_plot_refuses_an_output_folder_in_the_study(valid_study, capsys, inside):
    out = valid_study / inside
    assert main(["plot", str(valid_study), "--out", str(out)]) == 1
    assert "never into the study folder" in capsys.readouterr().err
    assert not (valid_study / "plots").exists()
    assert not list(valid_study.glob("*.plot.png"))


def test_plot_takes_the_series_colors_and_order_of_the_source_view(
    make_study, valid_files, tmp_path
):
    wpd = project(GOOD)
    wpd["datasetColl"].insert(
        0, {"name": "parent_plasma", "axesName": "XY", "data": [{"x": 50, "y": 50}]}
    )
    folder = make_study(
        {
            **valid_files,
            "Example_Fig1.png": png(100, 100),
            "Example_Fig1.wpd.json": json.dumps(wpd),
        }
    )
    assert format_folder(folder).ok
    study = load_study(folder)
    view = source_view(study, "Fig1")
    result = render_source(study, "Fig1", tmp_path / "out.png")
    assert result.legend == ("parent_plasma", "drug_plasma")
    assert dict(result.colors) == {s.name: s.color for s in view.series}
    assert [s.color for s in view.series] == list(SERIES_COLORS[:2])


def test_side_by_side_plots_the_points_of_the_source_view(valid_study, tmp_path):
    study = load_study(valid_study)
    view = source_view(study, "Fig1")
    result = render_source(study, "Fig1", tmp_path / "Fig1.png")
    assert result.mode == "side_by_side"
    assert result.legend == tuple(dict.fromkeys(p.series for p in view.points))
    assert dict(result.colors) == {s.name: s.color for s in view.series}


def test_side_by_side_colors_only_the_series_it_draws(
    make_study, valid_files, tmp_path
):
    wpd = project(GOOD)
    wpd["datasetColl"].append(
        {"name": "parent_plasma", "axesName": "XY", "data": [{"x": 50, "y": 50}]}
    )
    # A project without its image: the figure is drawn side by side, from the mapped rows.
    folder = make_study({**valid_files, "Example_Fig1.wpd.json": json.dumps(wpd)})
    study = load_study(folder)
    view = source_view(study, "Fig1")
    assert [s.name for s in view.series] == ["drug_plasma", "parent_plasma"]
    result = render_source(study, "Fig1", tmp_path / "Fig1.png")
    assert result.mode == "side_by_side"
    assert dict(result.colors) == {"drug_plasma": view.series[0].color}


def source_point(y, low, high):
    return SourcePoint(
        "drug_plasma",
        "timecourses",
        "timecourses_Fig1.tsv",
        1,
        1.0,
        y,
        low,
        high,
        "1",
        str(y),
    )


def test_side_by_side_draws_the_error_bars_of_the_source_view():
    # Down to the low end and up to the high end; 0 at a point without an error bar.
    rows = [source_point(4.0, 2.0, 8.0), source_point(5.0, None, None)]
    assert _error_ranges(rows) == [[2.0, 0.0], [4.0, 0.0]]
    assert _error_ranges([source_point(5.0, None, None)]) is None


def overlay_point(low, high):
    return OverlayPoint(
        series="drug_plasma",
        role="mapped",
        px=10.0,
        py=50.0,
        x=1.0,
        y=5.0,
        file="timecourses_Fig1.tsv",
        line=1,
        error_low_px=low,
        error_high_px=high,
        x_text="1",
        y_text="5",
    )


def test_overlay_draws_the_error_bar_of_a_mapped_row_from_its_low_to_its_high_end():
    assert _error_segment(overlay_point((10.0, 60.0), (10.0, 40.0)), 100) == (
        [10.0, 10.0],
        [60.0, 40.0],
    )
    # A low end without a pixel, off a log axis, reaches the bottom of the image (here 100).
    assert _error_segment(overlay_point(None, (10.0, 40.0)), 100) == (
        [10.0, 10.0],
        [100.0, 40.0],
    )
    # A high end without a pixel is the cross of the row.
    assert _error_segment(overlay_point((10.0, 60.0), None), 100) == (
        [10.0, 10.0],
        [60.0, 50.0],
    )
    assert _error_segment(overlay_point(None, None), 100) is None


def test_side_by_side_draws_timecourses_and_outputs_as_lines_and_scatters_as_points():
    assert [_linestyle(kind) for kind in ("timecourses", "outputs", "scatters")] == [
        "-",
        "-",
        "",
    ]


def test_plot_default_sources_include_figures_whose_outputs_have_a_time(
    make_study, valid_files, tsv, tmp_path, capsys
):
    output = {
        "subjects": "all",
        "interventions": "D1",
        "measurement": "concentration",
        "substance": "drug",
        "tissue": "plasma",
        "time_unit": "h",
        "unit": "mg/l",
    }
    folder = make_study(
        {
            **valid_files,
            "outputs_Fig3.tsv": tsv("outputs", {**output, "time": "1", "mean": "2"}),
            "Example_Fig3.png": png(100, 100),
            # Outputs without a time: nothing to plot.
            "outputs_Fig4.tsv": tsv(
                "outputs", {**output, "measurement": "cmax", "mean": "2"}
            ),
            "Example_Fig4.png": png(100, 100),
        }
    )
    assert format_folder(folder).ok
    out = tmp_path / "plots"
    assert main(["plot", str(folder), "--out", str(out), "--format", "human"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert (
        f"caffeine/Example: Fig3 (side_by_side) {out / 'Example_Fig3.plot.png'}"
        in lines
    )
    assert "  series without dataset: all · D1 · concentration · drug · plasma" in lines
    assert not any("Fig4" in line for line in lines)


TIMECOURSE = {
    "subjects": "all",
    "interventions": "D1",
    "measurement": "concentration",
    "substance": "drug",
    "tissue": "plasma",
    "time_unit": "h",
    "unit": "mg/l",
    "time": "1",
    "mean": "2",
}


def many_series(make_study, valid_files, tsv, count):
    """A figure Fig3 without a digitization, with `count` timecourse series of one point whose labels have commas."""
    rows = [{**TIMECOURSE, "label": f"CAF,CHL,{index}"} for index in range(count)]
    folder = make_study(
        {
            **valid_files,
            "timecourses_Fig3.tsv": tsv("timecourses", *rows),
            "Example_Fig3.png": png(100, 100),
        }
    )
    assert format_folder(folder).ok
    return folder


def test_side_by_side_lists_at_most_twenty_series_in_the_legend(
    make_study, valid_files, tsv, tmp_path
):
    study = load_study(many_series(make_study, valid_files, tsv, 45))
    result = render_source(study, "Fig3", tmp_path / "Fig3.png")
    assert result.mode == "side_by_side"
    assert result.legend == tuple(f"CAF,CHL,{index}" for index in range(20))
    # Every series is still drawn.
    assert len(result.colors) == 45


def test_plot_caps_the_series_without_dataset_and_keeps_the_names_apart(
    make_study, valid_files, tsv, tmp_path, capsys
):
    folder = many_series(make_study, valid_files, tsv, 25)
    out = tmp_path / "plots"
    args = ["plot", str(folder), "--source", "Fig3", "--out", str(out)]
    assert main([*args, "--format", "human"]) == 0
    line = capsys.readouterr().out.splitlines()[1]
    names = [f"CAF,CHL,{index}" for index in range(20)]
    assert line == f"  series without dataset: {'; '.join(names)}; and 5 more series"
    # JSON keeps the full list.
    assert main([*args, "--format", "json"]) == 0
    [plot] = json.loads(capsys.readouterr().out)["plots"]
    assert len(plot["unmatched"]) == 25


def test_the_axis_title_names_the_distinct_labels_of_its_series():
    from pkdb.studyformat.plot import axis_title

    assert axis_title(["time (h)", "time (h)", None]) == "time (h)"
    assert axis_title(["a (kg)", "b (%)", "a (kg)"]) == "a (kg) / b (%)"
    assert axis_title(list("abcde")) == "a / b / c and 2 more"
    assert axis_title([None]) == ""


def test_side_by_side_titles_the_y_axis_with_every_measurement_of_its_series(
    make_study, valid_files, tsv, tmp_path, monkeypatch
):
    from matplotlib.axes import Axes

    folder = make_study(valid_files)
    study = load_study(folder)
    view = source_view(study, "Fig1")
    series = tuple(
        SourceSeries(name, "#112233", "#445566", "time (wk)", label)
        for name, label in (("a", "weight (kg)"), ("b", "hba1c (percent)"))
    )
    points = tuple(
        SourcePoint(
            name, "outputs", "outputs_Fig1.tsv", 1, 1.0, 2.0, None, None, "1", "2"
        )
        for name in ("a", "b")
    )
    view = replace(view, series=series, points=points, unmatched=("a", "b"))
    titles = {}
    monkeypatch.setattr(
        Axes, "set_ylabel", lambda self, text, *a, **k: titles.update(y=text)
    )
    monkeypatch.setattr(
        Axes, "set_xlabel", lambda self, text, *a, **k: titles.update(x=text)
    )
    from pkdb.studyformat.plot import _side_by_side

    _side_by_side(study, view, tmp_path / "a.png")
    assert titles == {"x": "time (wk)", "y": "weight (kg) / hba1c (percent)"}


def test_a_figure_with_a_thousand_single_point_series_renders_fast(
    valid_study, tmp_path
):
    import time

    from pkdb.studyformat.plot import _side_by_side

    names = [f"CAF,CHL,{index}" for index in range(1300)]
    view = SourceView(
        "Fig5", None, None, None, None, (), (), tuple(names), "side_by_side",
        tuple(
            SourcePoint(name, "outputs", "outputs_Fig5.tsv", index + 2, 1.0 + index % 7, 2.0 + index % 11, 1.0, 4.0, "1", "2")
            for index, name in enumerate(names)
        ),
        tuple(SourceSeries(name, "#336699", "#99ccff", "time (h)", "y (mg)") for name in names),
        False,
        False,
    )  # fmt: skip
    started = time.perf_counter()
    result = _side_by_side(load_study(valid_study), view, tmp_path / "a.png")
    assert time.perf_counter() - started < 5
    assert len(result.legend) == 20 and len(result.colors) == 1300
