"""Source views: per paper table, figure or text passage, the image, the raw extraction and the mapped rows.

A digitized figure also gets overlay points in image pixels: the digitized points
and the mapped rows drawn at their pixel, so a curator can see where they differ.
The mapped rows of timecourse and scatter tables, and the outputs rows with a time of a figure
whose x axis is time (`over_time`), are also points in the units of their tables, for a plot beside the image. The series of a figure have
one order and one color each, which `pkdb plot` and the curation app share.
"""

from dataclasses import dataclass
from typing import Literal

from pkdb.studyformat.colors import series_color
from pkdb.studyformat.digitize import (
    ERROR_BAR_SUFFIX,
    VALUE_DIGITS,
    Axes,
    DigitizationError,
    LoadedDigitization,
    MappedPoint,
    dataset_series,
    digitization_file,
    mapped_points,
    outputs_series,
    png_size,
)
from pkdb.studyformat.load import LoadedStudy, LoadedTable
from pkdb.studyformat.raw import raw_file, raw_grid
from pkdb.studyformat.tables import SOURCE_PATTERN, TEXT_SOURCE, image_file
from pkdb.studyformat.text import format_number, natural_key

# The kind of a plotted point: timecourse and outputs rows over time, scatter rows as points.
PointKind = Literal["timecourses", "scatters", "outputs"]
# The tables whose mapped rows a figure plots, by kind.
_PLOTTED_KINDS: dict[str, PointKind] = {
    "timecourses": "timecourses",
    "scatters": "scatters",
    "outputs": "outputs",
}

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

    `series` is the timecourse label or scatter name of the point; `error_bar_end` marks a
    digitized end of an error bar, from the dataset `<series>;error_bar`. `error_low_px` and
    `error_high_px` are the pixels of the ends of the error bar of a mapped row; None without
    that end, and for an end at or below 0 on a log axis. `x_text` and `y_text` are the values
    as printed: the cells of a mapped row, and the six significant digits of the canonical
    project for a digitized point.
    """

    series: str
    role: Literal["raw", "mapped"]
    px: float
    py: float
    x: float
    y: float
    file: str
    line: int | None
    error_low_px: tuple[float, float] | None
    error_high_px: tuple[float, float] | None
    x_text: str
    y_text: str
    error_bar_end: bool = False


@dataclass(frozen=True)
class SourcePoint:
    """A mapped row of a timecourse or scatter table, or an outputs row with a time (`over_time`), in the units of its table.

    `error_low` and `error_high` are the ends of the error bar of a timecourse row or an outputs row around `y`
    (`digitize.error_ends`): the first statistic that fits, the one that `error_type` names
    first (as reported or as the digitized `error_bar` gives it), then around a `gmean` `gsd`,
    `sd`, `se`, and around a `mean` or `median` `sd`, `se`; a negative `sd` or `se` or a `gsd`
    below 1 is skipped and the next statistic is tried; a row with no valid statistic has no bar,
    and an `error_bar` without `error_type` is mirrored. None without a bar. `x_text` and `y_text`
    are the cells as printed.
    """

    series: str
    kind: PointKind
    file: str
    line: int
    x: float
    y: float
    error_low: float | None
    error_high: float | None
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
    overlay draws on; otherwise the image and a plot of the points go side by side. `log_x` and
    `log_y` say whether the digitization draws that axis on a log scale, the default of the plot
    of the curation app; False without a digitization.
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
    log_x: bool
    log_y: bool


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


def has_source(study: LoadedStudy, source: str) -> bool:
    """Whether the study has the source."""
    return source in _all_sources(study)


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


def _end_pixel(axes: Axes, x: float, end: float | None) -> tuple[float, float] | None:
    """The pixel of an end of an error bar; None without the end and off a log axis."""
    return None if end is None else _pixel(axes, x, end)


def _value_text(value: float) -> str:
    """A digitized value with the significant digits of the canonical project."""
    return format_number(float(f"{value:.{VALUE_DIGITS}g}"))


def over_time(points: list[tuple[PointKind, MappedPoint]]) -> bool:
    """Whether the x axis of a figure is time: it has timecourse rows or an outputs series at two or more times.

    Only then are its outputs rows with a time plotted at their time. An outputs series at one
    time, such as the change of a measurement at the end of the treatment per dose or per
    exposure quartile, is a point over an x that the outputs do not name.
    """
    times: dict[str, set[float]] = {}
    for kind, point in points:
        if kind == "timecourses":
            return True
        if kind == "outputs" and not point.dataset.endswith(ERROR_BAR_SUFFIX):
            times.setdefault(point.dataset, set()).add(point.x)
    return any(len(values) > 1 for values in times.values())


def figure_points(
    study: LoadedStudy, source: str
) -> list[tuple[PointKind, MappedPoint]]:
    """The mapped rows of the timecourse, scatter and outputs tables of a figure as dataset points.

    The outputs rows with a time are points only when the x axis of the figure is time (`over_time`).
    """
    points = [
        (kind, point)
        for table in study.tables
        if table.source == source and (kind := _PLOTTED_KINDS.get(table.kind))
        for point in mapped_points(table)
    ]
    if over_time(points):
        return points
    return [(kind, point) for kind, point in points if kind != "outputs"]


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
            series, bar = dataset_series(dataset.name)
            for px, py in dataset.points:
                x, y = axes.pixel_to_data(px, py)
                overlay.append(
                    OverlayPoint(
                        series,
                        "raw",
                        px,
                        py,
                        x,
                        y,
                        digitization.file,
                        None,
                        None,
                        None,
                        _value_text(x),
                        _value_text(y),
                        bar,
                    )
                )
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
                _end_pixel(axes, point.x, point.error_low),
                _end_pixel(axes, point.x, point.error_high),
                point.x_text,
                point.y_text,
            )
        )
    return tuple(overlay), tuple(unmatched)


def _source_points(
    rows: list[tuple[PointKind, MappedPoint]],
) -> tuple[SourcePoint, ...]:
    """The mapped rows as points in table units, each with the ends of its error bar."""
    return tuple(
        SourcePoint(
            point.dataset,
            kind,
            point.file,
            point.line,
            point.x,
            point.y,
            point.error_low,
            point.error_high,
            point.x_text,
            point.y_text,
        )
        for kind, point in rows
        if not point.dataset.endswith(ERROR_BAR_SUFFIX)
    )


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
        if table.source != source or table.kind not in _PLOTTED_KINDS:
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
            elif table.kind == "outputs" and (name := outputs_series(row)):
                labels.setdefault(
                    name,
                    (
                        _label("time", cells.get("time_unit", "")),
                        _label(cells.get("measurement", ""), cells.get("unit", "")),
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
            *(p.series for p in overlay),
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


def _log_scales(digitization: LoadedDigitization | None) -> tuple[bool, bool]:
    """Whether the digitization draws x and y on log scales.

    An axis is log when it is log on every axes that a dataset uses, or on every axes of a
    project without datasets. A log axis of negative values counts as linear, as a plot draws
    a log axis of values above 0 only.
    """
    if digitization is None or not digitization.axes:
        return False, False
    used = {dataset.axes for dataset in digitization.datasets}
    chosen = [
        entry for name, entry in digitization.axes.items() if name in used
    ] or list(digitization.axes.values())
    return (
        all(entry.log_x and not entry.negative_x for entry in chosen),
        all(entry.log_y and not entry.negative_y for entry in chosen),
    )


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
    mapped_rows = figure_points(study, source)
    overlay, unmatched = _overlay(study, source, [p for _, p in mapped_rows])
    points = _source_points(mapped_rows)
    log_x, log_y = _log_scales(digitization)
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
        log_x=log_x,
        log_y=log_y,
    )
