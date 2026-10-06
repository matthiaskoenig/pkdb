"""WebPlotDigitizer projects: the raw extraction of a figure.

`<study>_<source>.wpd.json` is a WebPlotDigitizer 4 project digitized on the
figure image `<study>_<source>.png`; pixels have their origin at the top-left
corner with y pointing down. The calibration is a port of WebPlotDigitizer's
XYAxes (javascript/core/axes/xy.js, commit 3a3ecb1).
"""

import math
import re
import tarfile
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from pkdb.cache import atomic_bytes, atomic_text
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.issues import make_issue, row_issue
from pkdb.studyformat.jsonio import JsonFileError, dump_json, load_json
from pkdb.studyformat.tables import STUDY_JSON, image_file
from pkdb.studyformat.text import NUMBER_PATTERN

if TYPE_CHECKING:
    from pkdb.studyformat.load import LoadedStudy, LoadedTable, Row

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
        if math.isfinite(number := float(value)):
            return number
        raise _invalid(f"{what} {value!r} is not a finite number")
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
    for dataset in datasets:
        _check_values(dataset, axes[dataset.axes])
    return axes, datasets


def _check_values(dataset: Dataset, axes: Axes) -> None:
    """Refuse a dataset with a point whose axis values are not finite numbers.

    A steep log axis turns pixels into values beyond the float range, which the
    canonical form, the source views and the plots could not use.
    """
    for px, py in dataset.points:
        try:
            values = axes.pixel_to_data(px, py)
        except OverflowError:
            values = (math.inf, math.inf)
        if not all(math.isfinite(value) for value in values):
            raise _invalid(
                f"The point ({px:g}, {py:g}) of dataset {dataset.name!r} has no finite "
                f"value on axes {axes.name!r}; check the calibration points"
            )


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


ERROR_BAR_SUFFIX = ";error_bar"
MISMATCH_PIXELS = 2.0
CENTRAL = ("mean", "median", "gmean")
PROJECT_MEMBER = "wpd.json"


@dataclass(frozen=True)
class MappedPoint:
    """A mapped row as a point of a dataset, in axis units."""

    dataset: str
    file: str
    line: int
    column: str
    x: float
    y: float


def central_column(row: Row) -> str | None:
    """The column of the central value of a timecourse row: mean, median or gmean."""
    return next(
        (name for name in CENTRAL if isinstance(row.values.get(name), float)), None
    )


def mapped_points(table: LoadedTable) -> list[MappedPoint]:
    """The rows of a timecourse or scatter table as dataset points."""
    points: list[MappedPoint] = []
    for row in table.rows:
        values = row.values
        if table.kind == "timecourses":
            time, label = values.get("time"), row.cells.get("label", "")
            column = central_column(row)
            if not isinstance(time, float) or column is None or not label:
                continue
            value = values[column]
            assert isinstance(value, float)
            points.append(MappedPoint(label, table.file, row.line, column, time, value))
            if isinstance(bar := values.get("error_bar"), float):
                points.append(
                    MappedPoint(
                        label + ERROR_BAR_SUFFIX,
                        table.file,
                        row.line,
                        "error_bar",
                        time,
                        bar,
                    )
                )
        elif table.kind == "scatters":
            x, y = values.get("x_mean"), values.get("y_mean")
            name = row.cells.get("name", "")
            if isinstance(x, float) and isinstance(y, float) and name:
                points.append(MappedPoint(name, table.file, row.line, "y_mean", x, y))
    return points


def _outside_image(
    digitization: LoadedDigitization, size: tuple[int, int]
) -> ValidationIssue | None:
    """The `digitization_outside_image` issue when a calibration or dataset pixel is off the image."""
    width, height = size
    pixels = [(p.px, p.py) for axes in digitization.axes.values() for p in axes.points]
    pixels += [point for dataset in digitization.datasets for point in dataset.points]
    for px, py in pixels:
        if not (0 <= px <= width and 0 <= py <= height):
            return make_issue(
                "digitization_outside_image",
                f"The pixel ({px:g}, {py:g}) lies outside the {width} x {height} image",
                file=digitization.file,
            )
    return None


def _header_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as stream:
        return png_size(stream.read(24))


def _pixel(axes: Axes, x: float, y: float) -> tuple[float, float] | None:
    try:
        return axes.data_to_pixel(x, y)
    except DigitizationError:
        return None


def check_digitizations(study: LoadedStudy) -> Iterator[ValidationIssue]:
    """Compare each digitization with its image and the mapped rows of its source."""
    for digitization in study.digitizations:
        image = image_file(study.name, digitization.source)
        if image not in study.layout.files:
            continue
        size = _header_size(study.folder / image)
        if size is None:
            yield make_issue(
                "digitization_invalid",
                f"{image} is not a PNG image",
                file=digitization.file,
            )
            continue
        if issue := _outside_image(digitization, size):
            yield issue
        points = [
            point
            for table in study.tables
            if table.source == digitization.source
            for point in mapped_points(table)
        ]
        tables = {table.file: table for table in study.tables}
        datasets = {dataset.name: dataset for dataset in digitization.datasets}
        mapped = {point.dataset for point in points}
        for dataset in digitization.datasets:
            if dataset.name not in mapped:
                yield make_issue(
                    "unknown_dataset",
                    f"The dataset {dataset.name!r} matches no mapped row of source {digitization.source}",
                    file=digitization.file,
                )
        matched: dict[str, set[int]] = {name: set() for name in datasets}
        for point in points:
            dataset = datasets.get(point.dataset)
            if dataset is None or not dataset.points:
                continue
            pixel = _pixel(digitization.axes[dataset.axes], point.x, point.y)
            if pixel is None:
                continue
            distances = [math.dist(pixel, other) for other in dataset.points]
            nearest = min(distances)
            for index, distance in enumerate(distances):
                if distance <= MISMATCH_PIXELS:
                    matched[dataset.name].add(index)
            if nearest <= MISMATCH_PIXELS:
                continue
            table = tables[point.file]
            row = next(row for row in table.rows if row.line == point.line)
            value = row.values[point.column]
            assert isinstance(value, float)
            unit = row.cells.get(
                "time_unit" if table.kind == "timecourses" else "x_unit"
            )
            at = f"{point.x:g} {unit}" if unit else f"{point.x:g}"
            yield row_issue(
                table,
                row,
                "digitized_mismatch",
                f"{point.column} {value:g} at {at} lies {nearest:.1f} pixels from the nearest point of dataset {dataset.name!r} in {digitization.file}",
                point.column,
            )
        for dataset in digitization.datasets:
            if dataset.name not in mapped:
                continue
            unmatched = len(dataset.points) - len(matched[dataset.name])
            if unmatched:
                points, have = (
                    ("point", "has") if unmatched == 1 else ("points", "have")
                )
                yield make_issue(
                    "digitized_mismatch",
                    f"{unmatched} {points} of dataset {dataset.name!r} {have} no mapped row within {MISMATCH_PIXELS:g} pixels",
                    file=digitization.file,
                )


@dataclass(frozen=True)
class ImportResult:
    """The outcome of importing a project: the file written and the issues that stopped it."""

    file: str
    wrote_image: bool
    issues: list[ValidationIssue]


def _read_archive(path: Path) -> tuple[bytes, bytes | None]:
    """The project JSON and the single PNG image (or None) of a WebPlotDigitizer .tar file."""
    projects: list[bytes] = []
    images: list[bytes] = []
    with tarfile.open(path, "r:") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name.rsplit("/", 1)[-1]
            if name == PROJECT_MEMBER or name.lower().endswith(".png"):
                stream = tar.extractfile(member)
                assert stream is not None
                (projects if name == PROJECT_MEMBER else images).append(stream.read())
    if len(projects) != 1:
        raise ValueError(f"The archive needs exactly one {PROJECT_MEMBER} member")
    return projects[0], images[0] if len(images) == 1 else None


def import_project(folder: Path, source: str, path: Path) -> ImportResult:
    """Import a WebPlotDigitizer project (JSON or .tar) as the digitization of a figure.

    Raises ValueError for a source or study that cannot take it. Nothing is
    written when the project has an error.
    """
    if not FIGURE_SOURCE.fullmatch(source):
        raise ValueError(f"{source!r} is not a figure source such as Fig1")
    if not (folder / STUDY_JSON).is_file():
        raise ValueError(f"{folder} is not a study folder: it has no {STUDY_JSON}")
    study = folder.name
    file = digitization_file(study, source)
    image_name = image_file(study, source)
    if path.suffix == ".tar":
        try:
            content, archive_image = _read_archive(path)
        except tarfile.TarError as error:
            return ImportResult(
                file,
                False,
                [make_issue("digitization_invalid", f"Not a tar archive: {error}")],
            )
        except ValueError as error:
            return ImportResult(
                file, False, [make_issue("digitization_invalid", str(error))]
            )
    else:
        content, archive_image = path.read_bytes(), None
    existing = folder / image_name
    image = existing.read_bytes() if existing.is_file() else archive_image
    write_image = not existing.is_file() and archive_image is not None
    loaded, issues = load_digitization(file, content, source)
    if loaded is None:
        return ImportResult(file, False, issues)
    if image is None:
        return ImportResult(
            file,
            False,
            [make_issue("missing_image", f"{image_name} is missing", file=file)],
        )
    size = png_size(image)
    if size is None:
        return ImportResult(
            file,
            False,
            [
                make_issue(
                    "digitization_invalid",
                    f"{image_name} is not a PNG image",
                    file=file,
                )
            ],
        )
    if archive_image is not None and not write_image:
        digitized = png_size(archive_image)
        if digitized != size:
            on = (
                f"an image of {digitized[0]}x{digitized[1]}"
                if digitized
                else "an image that is not a PNG image"
            )
            return ImportResult(
                file,
                False,
                [
                    make_issue(
                        "digitization_invalid",
                        f"The project was digitized on {on}, the study image "
                        f"{image_name} is {size[0]}x{size[1]}",
                        file=file,
                    )
                ],
            )
    if issue := _outside_image(loaded, size):
        return ImportResult(file, False, [issue])
    if write_image:
        atomic_bytes(existing, image)
    atomic_text(folder / file, canonical_digitization(loaded))
    return ImportResult(file, write_image, [])
