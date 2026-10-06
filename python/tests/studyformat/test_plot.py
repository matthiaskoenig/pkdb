import json

from digitize_fixtures import GOOD, png, project

from pkdb.cli import main
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
