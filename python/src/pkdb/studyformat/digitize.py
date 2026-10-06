"""WebPlotDigitizer projects: the raw extraction of a figure.

`<study>_<source>.wpd.json` is a WebPlotDigitizer 4 project digitized on the
figure image `<study>_<source>.png`; pixels have their origin at the top-left
corner with y pointing down. The calibration is a port of WebPlotDigitizer's
XYAxes (javascript/core/axes/xy.js, commit 3a3ecb1).
"""

import math
import re
from copy import deepcopy
from dataclasses import dataclass, field

from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue
from pkdb.studyformat.jsonio import JsonFileError, dump_json, load_json
from pkdb.studyformat.text import NUMBER_PATTERN

DIGITIZATION_SUFFIX = ".wpd.json"
FIGURE_SOURCE = re.compile(r"Fig[A-Za-z0-9_-]+")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
VALUE_DIGITS = 6


class DigitizationError(ValueError):
    """A project that cannot be used: `digitization_invalid` or `digitization_unsupported`."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _invalid(message: str) -> DigitizationError:
    return DigitizationError("digitization_invalid", message)


def _unsupported(message: str) -> DigitizationError:
    return DigitizationError("digitization_unsupported", message)


def digitization_file(study: str, source: str) -> str:
    """File name `<study>_<source>.wpd.json` of the digitization of a figure."""
    return f"{study}_{source}{DIGITIZATION_SUFFIX}"


def parse_digitization_file(name: str, study: str) -> str | None:
    """The source of a digitization file name of a study, or None."""
    prefix = f"{study}_"
    if not name.startswith(prefix) or not name.endswith(DIGITIZATION_SUFFIX):
        return None
    source = name[len(prefix) : -len(DIGITIZATION_SUFFIX)]
    return source if FIGURE_SOURCE.fullmatch(source) else None


@dataclass(frozen=True)
class CalibrationPoint:
    """A calibration point: its pixel and the axis value given for it."""

    px: float
    py: float
    dx: float
    dy: float


def _inverse(m: list[float]) -> list[float]:
    determinant = m[0] * m[3] - m[1] * m[2]
    if determinant == 0 or not math.isfinite(determinant):
        raise _invalid("The calibration points do not span both axes")
    return [
        m[3] / determinant,
        -m[1] / determinant,
        -m[2] / determinant,
        m[0] / determinant,
    ]


def _product(a: list[float], b: list[float]) -> list[float]:
    return [
        a[0] * b[0] + a[1] * b[2],
        a[0] * b[1] + a[1] * b[3],
        a[2] * b[0] + a[3] * b[2],
        a[2] * b[1] + a[3] * b[3],
    ]


class Axes:
    """The XY calibration of one axes of a project."""

    def __init__(
        self,
        name: str,
        log_x: bool,
        log_y: bool,
        no_rotation: bool,
        points: tuple[CalibrationPoint, ...],
    ):
        if len(points) != 4:
            raise _invalid(f"Axes {name!r} needs 4 calibration points X1, X2, Y1, Y2")
        self.name, self.log_x, self.log_y, self.no_rotation = (
            name,
            log_x,
            log_y,
            no_rotation,
        )
        self.points = points
        p1, p2, p3, p4 = points
        xmin, xmax, ymin, ymax = p1.dx, p2.dx, p3.dy, p4.dy
        self.negative_x = log_x and xmin < 0 and xmax < 0
        self.negative_y = log_y and ymin < 0 and ymax < 0
        if log_x:
            xmin, xmax = (
                self._log(xmin, self.negative_x),
                self._log(xmax, self.negative_x),
            )
        if log_y:
            ymin, ymax = (
                self._log(ymin, self.negative_y),
                self._log(ymax, self.negative_y),
            )
        data = [xmin - xmax, 0.0, 0.0, ymin - ymax]
        pixels = [p1.px - p2.px, p3.px - p4.px, p1.py - p2.py, p3.py - p4.py]
        a = _product(data, _inverse(pixels))
        if no_rotation:
            if abs(a[0] * a[3]) > abs(a[1] * a[2]):
                a = [
                    self._ratio(xmax - xmin, p2.px - p1.px),
                    0.0,
                    0.0,
                    self._ratio(ymax - ymin, p4.py - p3.py),
                ]
            else:
                a = [
                    0.0,
                    self._ratio(xmax - xmin, p2.py - p1.py),
                    self._ratio(ymax - ymin, p4.px - p3.px),
                    0.0,
                ]
        self.matrix = a
        self.inverse = _inverse(a)
        self.offset = (
            xmin - a[0] * p1.px - a[1] * p1.py,
            ymin - a[2] * p3.px - a[3] * p3.py,
        )

    @staticmethod
    def _log(value: float, negative: bool) -> float:
        value = -value if negative else value
        if value <= 0:
            raise _invalid(
                "A log axis needs positive calibration values, or all negative"
            )
        return math.log10(value)

    @staticmethod
    def _ratio(numerator: float, denominator: float) -> float:
        if denominator == 0:
            raise _invalid("The calibration points do not span both axes")
        return numerator / denominator

    def pixel_to_data(self, px: float, py: float) -> tuple[float, float]:
        a, (c0, c1) = self.matrix, self.offset
        x = a[0] * px + a[1] * py + c0
        y = a[2] * px + a[3] * py + c1
        if self.log_x:
            x = -(10**x) if self.negative_x else 10**x
        if self.log_y:
            y = -(10**y) if self.negative_y else 10**y
        return x, y

    def data_to_pixel(self, x: float, y: float) -> tuple[float, float]:
        if self.log_x:
            x = self._log(x, self.negative_x)
        if self.log_y:
            y = self._log(y, self.negative_y)
        m, (c0, c1) = self.inverse, self.offset
        dx, dy = x - c0, y - c1
        return m[0] * dx + m[1] * dy, m[2] * dx + m[3] * dy


@dataclass(frozen=True)
class Dataset:
    """A digitized dataset: its name, axes and pixel points."""

    name: str
    axes: str
    points: tuple[tuple[float, float], ...]


@dataclass
class LoadedDigitization:
    """A loaded project: the JSON as read, its axes by name and its datasets."""

    file: str
    source: str
    data: dict
    axes: dict[str, Axes] = field(default_factory=dict)
    datasets: list[Dataset] = field(default_factory=list)


def _number(value: object, what: str) -> float:
    if isinstance(value, bool):
        raise _invalid(f"{what} is not a number")
    if isinstance(value, int | float) and math.isfinite(value):
        return float(value)
    if isinstance(value, str) and NUMBER_PATTERN.fullmatch(value.strip()):
        return float(value)
    if isinstance(value, str):
        raise _unsupported(f"{what} {value!r} is not a number; dates are not supported")
    raise _invalid(f"{what} is not a number")


def parse_project(data: object) -> tuple[dict[str, Axes], list[Dataset]]:
    """The axes and datasets of a WebPlotDigitizer 4 project; DigitizationError otherwise."""
    if not isinstance(data, dict):
        raise _invalid("The project is not a JSON object")
    version = data.get("version")
    if not (isinstance(version, list) and version and version[0] == 4):
        raise _unsupported(
            f"WebPlotDigitizer project version {version!r}; version 4 is supported"
        )
    if data.get("measurementColl"):
        raise _unsupported("Measurements (distances, angles, areas) are not supported")
    axes_entries = data.get("axesColl")
    if not isinstance(axes_entries, list) or not axes_entries:
        raise _invalid("The project has no calibrated axes")
    axes: dict[str, Axes] = {}
    for entry in axes_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise _invalid("An axes entry has no name")
        if entry.get("type") != "XYAxes":
            raise _unsupported(
                f"Axes {entry['name']!r} of type {entry.get('type')!r}; only XY axes are supported"
            )
        points = entry.get("calibrationPoints")
        if (
            not isinstance(points, list)
            or len(points) != 4
            or not all(isinstance(p, dict) for p in points)
        ):
            raise _invalid(
                f"Axes {entry['name']!r} needs 4 calibration points X1, X2, Y1, Y2"
            )
        axes[entry["name"]] = Axes(
            entry["name"],
            entry.get("isLogX") is True,
            entry.get("isLogY") is True,
            entry.get("noRotation") is True,
            tuple(
                CalibrationPoint(
                    _number(point.get("px"), "A calibration pixel"),
                    _number(point.get("py"), "A calibration pixel"),
                    _number(point.get("dx"), "A calibration value"),
                    _number(point.get("dy"), "A calibration value"),
                )
                for point in points
            ),
        )
    datasets: list[Dataset] = []
    for entry in data.get("datasetColl") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise _invalid("A dataset has no name")
        name, axes_name = entry["name"], entry.get("axesName")
        if not isinstance(axes_name, str) or axes_name not in axes:
            raise _invalid(f"Dataset {name!r} refers to unknown axes {axes_name!r}")
        points = entry.get("data") or []
        if not isinstance(points, list) or not all(isinstance(p, dict) for p in points):
            raise _invalid(f"Dataset {name!r} has invalid points")
        datasets.append(
            Dataset(
                name,
                axes_name,
                tuple(
                    (_number(p.get("x"), "A pixel"), _number(p.get("y"), "A pixel"))
                    for p in points
                ),
            )
        )
    return axes, datasets


def load_digitization(
    file: str, data: bytes, source: str
) -> tuple[LoadedDigitization | None, list[ValidationIssue]]:
    """Read a project; None and the issue when it cannot be used."""
    try:
        value = load_json(data)
        axes, datasets = parse_project(value)
        assert isinstance(value, dict)  # parse_project accepts objects only
    except JsonFileError as error:
        return None, [make_issue("digitization_invalid", str(error), file=file)]
    except DigitizationError as error:
        return None, [make_issue(error.code, error.message, file=file)]
    return LoadedDigitization(file, source, value, axes, datasets), []


def _rounded(value: float) -> float | int:
    rounded = float(f"{value:.{VALUE_DIGITS}g}")
    return int(rounded) if rounded.is_integer() and abs(rounded) < 1e15 else rounded


def canonical_digitization(digitization: LoadedDigitization) -> str:
    """Canonical text: the project with its key order, no detection data and recomputed values."""
    data = deepcopy(digitization.data)
    for entry in data.get("datasetColl") or []:
        if "autoDetectionData" in entry:
            entry["autoDetectionData"] = None
        axes = digitization.axes[entry["axesName"]]
        for point in entry.get("data") or []:
            x, y = axes.pixel_to_data(float(point["x"]), float(point["y"]))
            point["value"] = [_rounded(x), _rounded(y)]
    return dump_json(data)


def png_size(data: bytes) -> tuple[int, int] | None:
    """Width and height of a PNG image from its header, or None for another file."""
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20]), int.from_bytes(data[20:24])
