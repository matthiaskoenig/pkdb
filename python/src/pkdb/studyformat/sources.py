"""Source views: per paper table, figure or text passage, the image, the raw extraction and the mapped rows.

A digitized figure also gets overlay points in image pixels: the digitized points
and the mapped rows drawn at their pixel, so a curator can see where they differ.
"""

from dataclasses import dataclass
from typing import Literal

from pkdb.studyformat.digitize import (
    ERROR_BAR_SUFFIX,
    VALUE_DIGITS,
    Axes,
    DigitizationError,
    mapped_points,
    png_size,
)
from pkdb.studyformat.load import LoadedStudy, LoadedTable
from pkdb.studyformat.raw import raw_file, raw_grid
from pkdb.studyformat.tables import SOURCE_PATTERN, TEXT_SOURCE, image_file
from pkdb.studyformat.text import natural_key

_DIGITIZED_KINDS = ("timecourses", "scatters")


@dataclass(frozen=True)
class SourceSummary:
    """A source of a study with its image, raw extraction and contributing tables."""

    source: str
    image: str | None
    raw: str | None
    raw_kind: Literal["table", "digitization"] | None
    tables: tuple[str, ...]


@dataclass(frozen=True)
class MappedTable:
    """The rows of a table that belong to a source: TSV line and cells in header order."""

    file: str
    kind: str
    header: tuple[str, ...]
    rows: tuple[tuple[int, tuple[str, ...]], ...]


@dataclass(frozen=True)
class OverlayPoint:
    """A digitized (raw) or mapped point of a figure at an image pixel."""

    series: str
    role: Literal["raw", "mapped"]
    px: float
    py: float
    x: float
    y: float
    file: str
    line: int | None
    error_px: tuple[float, float] | None


@dataclass(frozen=True)
class SourceView:
    """Everything the curation app and `pkdb plot` show of one source."""

    source: str
    image: str | None
    image_size: tuple[int, int] | None
    raw_grid: tuple[tuple[str, ...], ...] | None
    digitization: str | None
    mapped: tuple[MappedTable, ...]
    overlay: tuple[OverlayPoint, ...]
    unmatched: tuple[str, ...]


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


def study_sources(study: LoadedStudy) -> list[SourceSummary]:
    """Every source of a study in natural order."""
    summaries = []
    for source in _all_sources(study):
        raw = study.raw(raw_file(study.name, source))
        digitization = study.digitization(source)
        summaries.append(
            SourceSummary(
                source=source,
                image=_image(study, source),
                raw=raw.file if raw else digitization.file if digitization else None,
                raw_kind="table" if raw else "digitization" if digitization else None,
                tables=tuple(table.file for table in _contributing(study, source)),
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
    )


def _pixel(axes: Axes, x: float, y: float) -> tuple[float, float] | None:
    """The pixel of a data point rounded to the digits of the digitization, None off a log axis."""
    try:
        px, py = axes.data_to_pixel(x, y)
    except DigitizationError:
        return None
    return round(px, VALUE_DIGITS), round(py, VALUE_DIGITS)


def _overlay(
    study: LoadedStudy, source: str
) -> tuple[tuple[OverlayPoint, ...], tuple[str, ...]]:
    """The overlay points of a digitized figure and the series without a dataset."""
    points = [
        point
        for table in study.tables
        if table.source == source and table.kind in _DIGITIZED_KINDS
        for point in mapped_points(table)
    ]
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
                        dataset.name, "raw", px, py, x, y, digitization.file, None, None
                    )
                )
    bars = {
        (p.file, p.line, p.dataset): p
        for p in points
        if p.dataset.endswith(ERROR_BAR_SUFFIX)
    }
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
            )
        )
    return tuple(overlay), tuple(unmatched)


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
    overlay, unmatched = _overlay(study, source)
    return SourceView(
        source=source,
        image=image,
        image_size=image_size,
        raw_grid=tuple(raw_grid(raw)) if raw else None,
        digitization=digitization.file if digitization else None,
        mapped=tuple(_mapped_table(t, source) for t in _contributing(study, source)),
        overlay=overlay,
        unmatched=unmatched,
    )
