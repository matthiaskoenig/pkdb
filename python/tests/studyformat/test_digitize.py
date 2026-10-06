import json
from pathlib import Path

import pytest
from digitize_fixtures import GOOD
from digitize_fixtures import project as fixture_project

from pkdb.studyformat.digitize import (
    Axes,
    CalibrationPoint,
    DigitizationError,
    canonical_digitization,
    load_digitization,
    parse_digitization_file,
    parse_project,
    png_size,
)
from pkdb.studyformat.jsonio import dump_json

ORACLE = json.loads(
    (Path(__file__).parent / "data/wpd/calibration_oracle.json").read_text()
)


def _axes(entry: dict) -> Axes:
    return Axes(
        entry["name"],
        entry["isLogX"],
        entry["isLogY"],
        entry["noRotation"],
        tuple(
            CalibrationPoint(p["px"], p["py"], float(p["dx"]), float(p["dy"]))
            for p in entry["calibrationPoints"]
        ),
    )


@pytest.mark.parametrize("case", ORACLE["cases"], ids=lambda case: case["name"])
def test_calibration_matches_webplotdigitizer(case):
    axes = _axes(case["axes"])
    for pixel, value, back in zip(
        case["pixels"], case["values"], case["back"], strict=True
    ):
        assert axes.pixel_to_data(*pixel) == pytest.approx(value, rel=1e-9, abs=1e-9)
        assert axes.data_to_pixel(*value) == pytest.approx(back, rel=1e-9, abs=1e-6)


def project(**overrides) -> dict:
    base = {
        "version": [4, 2],
        "axesColl": [
            ORACLE["cases"][0]["axes"]
            | {
                "calibrationPoints": [
                    {**p, "dx": str(p["dx"]), "dy": str(p["dy"])}
                    for p in ORACLE["cases"][0]["axes"]["calibrationPoints"]
                ]
            }
        ],
        "datasetColl": [
            {
                "name": "drug_plasma",
                "axesName": "XY",
                "colorRGB": [200, 0, 0, 255],
                "metadataKeys": [],
                "data": [{"x": 105.6686, "y": 528.8291, "value": [9, 9]}],
                "autoDetectionData": {"fgColor": [0, 0, 255], "mask": "x"},
            }
        ],
        "measurementColl": [],
    }
    return base | overrides


def test_parse_digitization_file():
    assert parse_digitization_file("Example_Fig1.wpd.json", "Example") == "Fig1"
    assert parse_digitization_file("Example_Tab1.wpd.json", "Example") is None
    assert parse_digitization_file("Other_Fig1.wpd.json", "Example") is None


def test_canonical_form_recomputes_values_and_drops_detection_data():
    data = dump_json(project()).encode()
    loaded, issues = load_digitization("Example_Fig1.wpd.json", data, "Fig1")
    assert issues == []
    assert loaded is not None
    text = canonical_digitization(loaded)
    written = json.loads(text)
    point = written["datasetColl"][0]["data"][0]
    assert point["value"] == [0, 0]
    assert written["datasetColl"][0]["autoDetectionData"] is None
    assert written["axesColl"][0]["calibrationPoints"][1]["dx"] == "20"
    again, _ = load_digitization("Example_Fig1.wpd.json", text.encode(), "Fig1")
    assert again is not None
    assert canonical_digitization(again) == text


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"version": [3, 0]}, "digitization_unsupported"),
        (
            {"axesColl": [{"name": "B", "type": "BarAxes", "calibrationPoints": []}]},
            "digitization_unsupported",
        ),
        (
            {"measurementColl": [{"type": "Distance", "name": "d", "data": []}]},
            "digitization_unsupported",
        ),
        (
            {"datasetColl": [{"name": "s", "axesName": "missing", "data": []}]},
            "digitization_invalid",
        ),
        ({"axesColl": []}, "digitization_invalid"),
        (
            {"datasetColl": [{"name": "s", "axesName": ["XY"], "data": []}]},
            "digitization_invalid",
        ),
        (
            {"datasetColl": [{"name": "s", "axesName": {"a": 1}, "data": []}]},
            "digitization_invalid",
        ),
        ({"datasetColl": [{"name": "s", "data": []}]}, "digitization_invalid"),
        ({"datasetColl": ["s"]}, "digitization_invalid"),
        ({"axesColl": ["XY"]}, "digitization_invalid"),
    ],
)
def test_unsupported_and_invalid_projects(change, code):
    with pytest.raises(DigitizationError) as error:
        parse_project(project(**change))
    assert error.value.code == code


def test_date_calibration_is_unsupported():
    data = project()
    data["axesColl"][0]["calibrationPoints"][0]["dx"] = "2020/01/31"
    with pytest.raises(DigitizationError) as error:
        parse_project(data)
    assert error.value.code == "digitization_unsupported"


def test_coinciding_calibration_points_are_invalid():
    data = project()
    data["axesColl"][0]["calibrationPoints"][1] = data["axesColl"][0][
        "calibrationPoints"
    ][0]
    with pytest.raises(DigitizationError) as error:
        parse_project(data)
    assert error.value.code == "digitization_invalid"


def test_png_size():
    header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (900).to_bytes(4)
        + (600).to_bytes(4)
    )
    assert png_size(header + b"\x08\x06\x00\x00\x00") == (900, 600)
    assert png_size(b"png") is None


def test_layout_loader_and_formatter(make_study, valid_files):
    from pkdb.studyformat.formatter import format_folder
    from pkdb.studyformat.load import load_study

    folder = make_study({**valid_files, "Example_Fig1.wpd.json": json.dumps(project())})
    assert format_folder(folder).ok
    study = load_study(folder)
    digitization = study.digitization("Fig1")
    assert digitization is not None
    assert digitization.datasets[0].name == "drug_plasma"
    assert (
        json.loads((folder / "Example_Fig1.wpd.json").read_text())["datasetColl"][0][
            "autoDetectionData"
        ]
        is None
    )


def _steep_log_project() -> dict:
    """A log y axis with Y1 and Y2 0.05 pixels apart: 20 decades per pixel."""
    data = fixture_project(GOOD)
    axes = data["axesColl"][0]
    axes["isLogY"] = True
    axes["calibrationPoints"][2] |= {"py": 100, "dy": "1"}
    axes["calibrationPoints"][3] |= {"py": 99.95, "dy": "10"}
    return data


def test_point_values_that_overflow_a_log_axis_are_invalid():
    data = dump_json(_steep_log_project()).encode()
    loaded, issues = load_digitization("Example_Fig1.wpd.json", data, "Fig1")
    assert loaded is None
    assert [issue.code for issue in issues] == ["digitization_invalid"]
    assert "drug_plasma" in issues[0].message


@pytest.mark.parametrize("value", ["1e999", "-1e999"])
def test_calibration_values_must_be_finite(value):
    data = project()
    data["axesColl"][0]["calibrationPoints"][1]["dx"] = value
    with pytest.raises(DigitizationError, match="finite") as error:
        parse_project(data)
    assert error.value.code == "digitization_invalid"
