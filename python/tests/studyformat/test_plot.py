import json
import sys

import pytest
from digitize_fixtures import GOOD, png, project

from pkdb.cli import main
from pkdb.studyformat.colors import SERIES_COLORS
from pkdb.studyformat.digitize import png_size
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.load import load_study
from pkdb.studyformat.plot import render_source
from pkdb.studyformat.sources import source_view


def digitized(make_study, valid_files):
    files = {
        **valid_files,
        "Example_Fig1.png": png(100, 100),
        "Example_Fig1.wpd.json": json.dumps(project(GOOD)),
    }
    folder = make_study(files)
    assert format_folder(folder).ok
    return folder


def test_overlay_has_the_image_size_and_the_view_pixels(
    make_study, valid_files, tmp_path
):
    study = load_study(digitized(make_study, valid_files))
    result = render_source(study, "Fig1", tmp_path / "out.png")
    assert png_size(result.path.read_bytes()) == (100, 100)
    expected = tuple(
        (p.px, p.py) for p in source_view(study, "Fig1").overlay if p.role == "mapped"
    )
    assert expected and result.points == expected


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
    result = render_source(load_study(folder), "Fig1", tmp_path / "out.png")
    colors = dict(result.colors)
    assert result.legend == ("drug_plasma",)
    assert colors["drug_plasma;error_bar"] == colors["drug_plasma"]
    assert png_size(result.path.read_bytes()) == (100, 100)


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
    assert png_size(overlay.path.read_bytes()) == (100, 100)
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
