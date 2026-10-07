"""Source views: per paper table, figure or text passage, the image, the raw extraction and the mapped rows.

A digitized figure also gets overlay points in image pixels: the digitized points
and the mapped rows drawn at their pixel, so a curator can see where they differ.
The mapped rows of timecourse and scatter tables are also points in the units of
their tables, for a plot beside the image. The series of a figure have one order
and one color each, which `pkdb plot` and the curation app share.
"""

from dataclasses import dataclass
from typing import Literal

from pkdb.studyformat.colors import series_color
from pkdb.studyformat.digitize import (
    ERROR_BAR_SUFFIX,
    VALUE_DIGITS,
    Axes,
    DigitizationError,
    MappedPoint,
    digitization_file,
    mapped_points,
    png_size,
)
from pkdb.studyformat.load import LoadedStudy, LoadedTable
from pkdb.studyformat.raw import raw_file, raw_grid
from pkdb.studyformat.tables import SOURCE_PATTERN, TEXT_SOURCE, image_file
from pkdb.studyformat.text import format_number, natural_key

_DIGITIZED_KINDS = ("timecourses", "scatters")

SourceKind = Literal["table", "figure", "text"]


def source_kind(source: str) -> SourceKind:
    """A paper table `Tab…`, a figure `Fig…` or the text."""
    if source == TEXT_SOURCE:
        return "text"
    return "table" if source.startswith("Tab") else "figure"


@dataclass(frozen=True)
class SourceSummary:
    """A source of a study with its image, raw extraction, contributing tables and missing files.

    `missing_image` and `missing_raw` name the image and the raw extraction that the source
    lacks: `<name>_<source>.png`, and `<name>_<source>.tsv` of a paper table or the
    WebPlotDigitizer project `<name>_<source>.wpd.json` of a figure. The text has neither.
    """

    source: str
    kind: SourceKind
    image: str | None
    raw: str | None
    raw_kind: Literal["table", "digitization"] | None
    tables: tuple[str, ...]
    missing_image: str | None
    missing_raw: str | None


@dataclass(frozen=True)
class MappedTable:
    """The rows of a table that belong to a source: TSV line and cells in header order.

    A shared table (subjects, interventions, characteristica) names the source of each row; the
    rows of any other table all belong to its source.
    """

    file: str
    kind: str
    header: tuple[str, ...]
    rows: tuple[tuple[int, tuple[str, ...]], ...]
    shared: bool


@dataclass(frozen=True)
class OverlayPoint:
    """A digitized (raw) or mapped point of a figure at an image pixel.

    `x_text` and `y_text` are the values as printed: the cells of a mapped row, and the six
    significant digits of the canonical project for a digitized point.
    """

    series: str
    role: Literal["raw", "mapped"]
    px: float
    py: float
    x: float
    y: float
    file: str
    line: int | None
    error_px: tuple[float, float] | None
    x_text: str
    y_text: str


@dataclass(frozen=True)
class SourcePoint:
    """A mapped row of a timecourse or scatter table in the units of its table.

    `error_bar` is the end of the error bar of a timecourse row; `x_text` and `y_text` are the
    cells as printed.
    """

    series: str
    kind: Literal["timecourses", "scatters"]
    file: str
    line: int
    x: float
    y: float
    error_bar: float | None
    x_text: str
    y_text: str


@dataclass(frozen=True)
class SourceSeries:
    """A series of a figure in the order of its colors, with the axis labels of its table."""

    name: str
    color: str
    dark_color: str
    x_label: str | None
    y_label: str | None


@dataclass(frozen=True)
class SourceView:
    """Everything the curation app and `pkdb plot` show of one source.

    `layout` is `overlay` when the figure has a digitization on an image of known size, which the
    overlay draws on; otherwise the image and a plot of the points go side by side.
    """

    source: str
    image: str | None
    image_size: tuple[int, int] | None
    raw_grid: tuple[tuple[str, ...], ...] | None
    digitization: str | None
    mapped: tuple[MappedTable, ...]
    overlay: tuple[OverlayPoint, ...]
    unmatched: tuple[str, ...]
    layout: Literal["overlay", "side_by_side"]
    points: tuple[SourcePoint, ...]
    series: tuple[SourceSeries, ...]


def _sources_of(table: LoadedTable) -> set[str]:
    if table.source is not None:
        return {table.source}
    return {source for row in table.rows if (source := row.cells.get("source"))}


def _image(study: LoadedStudy, source: str) -> str | None:
    name = image_file(study.name, source)
    return name if source != TEXT_SOURCE and name in study.layout.files else None


def _contributing(study: LoadedStudy, source: str) -> list[LoadedTable]:
    return [table for table in study.tables if source in _sources_of(table)]


def _all_sources(study: LoadedStudy) -> list[str]:
    sources: set[str] = set()
    for table in study.tables:
        sources |= _sources_of(table)
    sources |= {raw.source for raw in study.raw_tables}
    sources |= {digitization.source for digitization in study.digitizations}
    prefix = f"{study.name}_"
    for name in study.layout.files:
        if name.startswith(prefix) and name.endswith(".png"):
            source = name[len(prefix) : -len(".png")]
            if SOURCE_PATTERN.fullmatch(source):
                sources.add(source)
    return sorted(sources, key=natural_key)


def _expected_raw(study: LoadedStudy, source: str) -> str | None:
    """The raw extraction of a source: a raw table of a paper table, a project of a figure."""
    kind = source_kind(source)
    if kind == "table":
        return raw_file(study.name, source)
    return digitization_file(study.name, source) if kind == "figure" else None


def study_sources(study: LoadedStudy) -> list[SourceSummary]:
    """Every source of a study in natural order."""
    summaries = []
    for source in _all_sources(study):
        raw = study.raw(raw_file(study.name, source))
        digitization = study.digitization(source)
        image = _image(study, source)
        found = raw.file if raw else digitization.file if digitization else None
        kind = source_kind(source)
        summaries.append(
            SourceSummary(
                source=source,
                kind=kind,
                image=image,
                raw=found,
                raw_kind="table" if raw else "digitization" if digitization else None,
                tables=tuple(table.file for table in _contributing(study, source)),
                missing_image=None
                if image or kind == "text"
                else image_file(study.name, source),
                missing_raw=None if found else _expected_raw(study, source),
            )
        )
    return summaries


def _mapped_table(table: LoadedTable, source: str) -> MappedTable:
    header = table.spec.names
    return MappedTable(
        table.file,
        table.kind,
        header,
        tuple(
            (row.line, tuple(row.cells.get(name, "") for name in header))
            for row in table.rows
            if table.source == source or row.cells.get("source") == source
        ),
        table.source is None,
    )


def _pixel(axes: Axes, x: float, y: float) -> tuple[float, float] | None:
    """The pixel of a data point rounded to the digits of the digitization, None off a log axis."""
    try:
        px, py = axes.data_to_pixel(x, y)
    except DigitizationError:
        return None
    return round(px, VALUE_DIGITS), round(py, VALUE_DIGITS)


def _value_text(value: float) -> str:
    """A digitized value with the significant digits of the canonical project."""
    return format_number(float(f"{value:.{VALUE_DIGITS}g}"))


def _figure_points(
    study: LoadedStudy, source: str
) -> list[tuple[Literal["timecourses", "scatters"], MappedPoint]]:
    """The mapped rows of the timecourse and scatter tables of a figure as dataset points."""
    return [
        ("scatters" if table.kind == "scatters" else "timecourses", point)
        for table in study.tables
        if table.source == source and table.kind in _DIGITIZED_KINDS
        for point in mapped_points(table)
    ]


def _error_bars(points: list[MappedPoint]) -> dict[tuple[str, int, str], MappedPoint]:
    """The error bar ends of mapped rows by file, line and `<series>;error_bar`."""
    return {
        (p.file, p.line, p.dataset): p
        for p in points
        if p.dataset.endswith(ERROR_BAR_SUFFIX)
    }


def _overlay(
    study: LoadedStudy, source: str, points: list[MappedPoint]
) -> tuple[tuple[OverlayPoint, ...], tuple[str, ...]]:
    """The overlay points of a digitized figure and the series without a dataset."""
    digitization = study.digitization(source)
    datasets = {d.name: d for d in digitization.datasets} if digitization else {}
    unmatched: dict[str, None] = {}
    overlay: list[OverlayPoint] = []
    if digitization:
        for dataset in digitization.datasets:
            axes = digitization.axes[dataset.axes]
            for px, py in dataset.points:
                x, y = axes.pixel_to_data(px, py)
                overlay.append(
                    OverlayPoint(
                        dataset.name,
                        "raw",
                        px,
                        py,
                        x,
                        y,
                        digitization.file,
                        None,
                        None,
                        _value_text(x),
                        _value_text(y),
                    )
                )
    bars = _error_bars(points)
    for point in points:
        if point.dataset.endswith(ERROR_BAR_SUFFIX):
            continue
        dataset = datasets.get(point.dataset)
        if dataset is None or digitization is None:
            unmatched.setdefault(point.dataset)
            continue
        axes = digitization.axes[dataset.axes]
        if (pixel := _pixel(axes, point.x, point.y)) is None:
            continue
        px, py = pixel
        error_px = None
        bar = bars.get((point.file, point.line, point.dataset + ERROR_BAR_SUFFIX))
        if bar is not None:
            error_px = _pixel(axes, bar.x, bar.y)
        overlay.append(
            OverlayPoint(
                point.dataset,
                "mapped",
                px,
                py,
                point.x,
                point.y,
                point.file,
                point.line,
                error_px,
                point.x_text,
                point.y_text,
            )
        )
    return tuple(overlay), tuple(unmatched)


def _source_points(
    figure_points: list[tuple[Literal["timecourses", "scatters"], MappedPoint]],
) -> tuple[SourcePoint, ...]:
    """The mapped rows as points in table units, each with the end of its error bar."""
    bars = _error_bars([point for _, point in figure_points])
    result = []
    for kind, point in figure_points:
        if point.dataset.endswith(ERROR_BAR_SUFFIX):
            continue
        bar = bars.get((point.file, point.line, point.dataset + ERROR_BAR_SUFFIX))
        result.append(
            SourcePoint(
                point.dataset,
                kind,
                point.file,
                point.line,
                point.x,
                point.y,
                bar.y if bar else None,
                point.x_text,
                point.y_text,
            )
        )
    return tuple(result)


def _label(name: str, unit: str) -> str | None:
    """`time (h)`, `concentration (mg/l)`: an axis as far as its table names it."""
    if name and unit:
        return f"{name} ({unit})"
    return name or unit or None


def _labels(
    study: LoadedStudy, source: str
) -> dict[str, tuple[str | None, str | None]]:
    """Per series of a figure the x and y axis labels from its first row."""
    labels: dict[str, tuple[str | None, str | None]] = {}
    for table in study.tables:
        if table.source != source or table.kind not in _DIGITIZED_KINDS:
            continue
        for row in table.rows:
            cells = row.cells
            if table.kind == "timecourses" and cells.get("label"):
                labels.setdefault(
                    cells["label"],
                    (
                        _label("time", cells.get("time_unit", "")),
                        _label(cells.get("measurement", ""), cells.get("unit", "")),
                    ),
                )
            elif table.kind == "scatters" and cells.get("name"):
                labels.setdefault(
                    cells["name"],
                    (
                        _label(cells.get("x_measurement", ""), cells.get("x_unit", "")),
                        _label(cells.get("y_measurement", ""), cells.get("y_unit", "")),
                    ),
                )
    return labels


def _series(
    study: LoadedStudy,
    source: str,
    overlay: tuple[OverlayPoint, ...],
    unmatched: tuple[str, ...],
    points: tuple[SourcePoint, ...],
) -> tuple[SourceSeries, ...]:
    """The series in the order of their colors: the overlay first, then those without a dataset, then the rest."""
    names = dict.fromkeys(
        [
            *(p.series.removesuffix(ERROR_BAR_SUFFIX) for p in overlay),
            *unmatched,
            *(p.series for p in points),
        ]
    )
    labels = _labels(study, source)
    result = []
    for index, name in enumerate(names):
        color, dark = series_color(index)
        x_label, y_label = labels.get(name, (None, None))
        result.append(SourceSeries(name, color, dark, x_label, y_label))
    return tuple(result)


def source_view(study: LoadedStudy, source: str) -> SourceView:
    """The view of one source; raises KeyError for a source the study does not have."""
    if source not in _all_sources(study):
        raise KeyError(source)
    image = _image(study, source)
    image_size = None
    if image is not None:
        with (study.folder / image).open("rb") as stream:
            image_size = png_size(stream.read(24))
    raw = study.raw(raw_file(study.name, source))
    digitization = study.digitization(source)
    figure_points = _figure_points(study, source)
    overlay, unmatched = _overlay(study, source, [p for _, p in figure_points])
    points = _source_points(figure_points)
    return SourceView(
        source=source,
        image=image,
        image_size=image_size,
        raw_grid=tuple(raw_grid(raw)) if raw else None,
        digitization=digitization.file if digitization else None,
        mapped=tuple(_mapped_table(t, source) for t in _contributing(study, source)),
        overlay=overlay,
        unmatched=unmatched,
        layout="overlay" if digitization and image and image_size else "side_by_side",
        points=points,
        series=_series(study, source, overlay, unmatched, points),
    )
