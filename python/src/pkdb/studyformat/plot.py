"""Render a figure source with matplotlib: the digitized overlay or image and data side by side.

The overlay uses image pixels, so its points equal those of `source_view`, which the curation app draws with Plotly.
The image keeps its pixels at the top of the PNG, with the series and the key of the marks in a strip below it.
Figures are drawn on their own Agg canvas without pyplot, so rendering changes no global matplotlib state and is
safe in the threads of the curation server.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pkdb.studyformat.colors import POINT_RING
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import OverlayPoint, SourcePoint, SourceView, source_view


@dataclass(frozen=True)
class PlotResult:
    """The written PNG and its mode, with what the plot draws.

    `points` are the mapped points drawn in overlay mode, in image pixels; the image starts at the top of the
    PNG, centered when the legends are wider. `legend` holds the series of the legend, `colors` the color of each
    drawn series once, and `unmatched` the series without a dataset.
    """

    path: Path
    mode: Literal["overlay", "side_by_side"]
    points: tuple[tuple[float, float], ...] = ()
    legend: tuple[str, ...] = ()
    colors: tuple[tuple[str, str], ...] = ()
    unmatched: tuple[str, ...] = ()


def render_source(study: LoadedStudy, source: str, path: Path) -> PlotResult:
    """Write the plot of a figure source to `path`; raises KeyError for an unknown source."""
    view = source_view(study, source)
    if view.layout == "overlay":
        return _overlay(study, view, path)
    return _side_by_side(study, view, path)


# The most series that a legend lists; the figure still draws every series.
LEGEND_LIMIT = 20
DPI = 100
# The space in pixels around and between the legends below the image of an overlay.
STRIP_PAD = 8


def _save(figure, path: Path) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    FigureCanvasAgg(figure)
    figure.savefig(path, dpi=DPI)


def _key():
    """The marks of the overlay in black, named as in the key of the curation app."""
    from matplotlib.lines import Line2D

    def mark(label: str, **style) -> Line2D:
        return Line2D([], [], linestyle="", color="black", label=label, **style)

    # Marker sizes in points are the square roots of the areas that the overlay scatters.
    return [
        mark("Digitized point", marker="o", markersize=4),
        mark(
            "Digitized error bar", marker="_", markersize=40**0.5, markeredgewidth=1.5
        ),
        mark("Mapped row", marker="x", markersize=60**0.5, markeredgewidth=2),
        mark(
            "Error bar of a mapped row", marker="|", markersize=10, markeredgewidth=1.5
        ),
    ]


def _legend_strip(figure, renderer, width: int, height: int, rows: list[list]) -> None:
    """Size the figure to the image of `width` x `height` pixels at the top and a legend per row of handles below it.

    A legend takes as many columns as fit the width of the image. A legend wider than the image in one column widens
    the figure; the image then stays at its pixels in the middle.
    """
    legends = []
    for handles in filter(None, rows):
        for columns in range(len(handles), 0, -1):
            legend = figure.legend(
                handles=handles,
                loc="upper center",
                ncols=columns,
                frameon=False,
                fontsize="small",
                borderaxespad=0,
            )
            box = legend.get_window_extent(renderer)
            if box.width <= width - 2 * STRIP_PAD or columns == 1:
                break
            legend.remove()
        legends.append((legend, math.ceil(box.width), math.ceil(box.height)))
    total_width = max(
        width, *(legend_width + 2 * STRIP_PAD for _, legend_width, _ in legends)
    )
    strip = STRIP_PAD + sum(
        legend_height + STRIP_PAD for _, _, legend_height in legends
    )
    total_height = height + strip
    figure.set_size_inches(total_width / DPI, total_height / DPI)
    left = (total_width - width) // 2
    figure.axes[0].set_position(
        (
            left / total_width,
            strip / total_height,
            width / total_width,
            height / total_height,
        )
    )
    top = strip - STRIP_PAD
    for legend, _, legend_height in legends:
        legend.set_bbox_to_anchor((0.5, top / total_height))
        top -= legend_height + STRIP_PAD


def _error_segment(
    point: OverlayPoint, height: float
) -> tuple[list[float], list[float]] | None:
    """The x and the y pixels of the error bar of a mapped point, from its low to its high end.

    An end without a pixel is at or below 0 on a log axis of the digitization. A low end then
    reaches the bottom of the image (`height`), as the data plot cuts the bar at its axis. A
    high end, and so the whole bar, is the point itself; None without an error bar.
    """
    if point.error_low_px is None and point.error_high_px is None:
        return None
    cross = (point.px, point.py)
    low = point.error_low_px or (
        cross if point.error_high_px is None else (point.px, height)
    )
    high = point.error_high_px or cross
    return [low[0], high[0]], [low[1], high[1]]


def _error_ranges(rows: list[SourcePoint]) -> list[list[float]] | None:
    """The distances from each point down to the low and up to the high end of its error bar,
    as matplotlib takes them: 0 without an error bar, None when no point has one."""
    if all(p.error_low is None and p.error_high is None for p in rows):
        return None
    below = [0.0 if p.error_low is None else max(0.0, p.y - p.error_low) for p in rows]
    above = [
        0.0 if p.error_high is None else max(0.0, p.error_high - p.y) for p in rows
    ]
    return [below, above]


def _image(path: Path):
    """The pixels of an image as RGB(A): matplotlib would color a grayscale image with a colormap."""
    import numpy as np
    from matplotlib.image import imread

    pixels = imread(path)
    return np.dstack([pixels] * 3) if pixels.ndim == 2 else pixels


def _overlay(study, view, path: Path) -> PlotResult:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    width, height = view.image_size
    figure = Figure(figsize=(width / DPI, height / DPI), dpi=DPI)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_axes((0, 0, 1, 1))
    axes.imshow(_image(study.folder / view.image), extent=(0, width, height, 0))
    axes.set_xlim(0, width)
    axes.set_ylim(height, 0)
    axes.axis("off")
    # The colors and their order of the source view, which the curation app draws alike.
    base = {series.name: series.color for series in view.series}
    drawn = {p.series for p in view.overlay}
    series = [name for name in base if name in drawn]
    mapped = []
    for point in view.overlay:
        if point.role == "raw":
            bar = point.error_bar_end
            axes.scatter(
                point.px,
                point.py,
                s=40 if bar else 16,
                marker="_" if bar else "o",
                color=base[point.series],
                edgecolors=None if bar else POINT_RING,
                linewidths=None if bar else 0.75,
            )
            continue
        mapped.append((point.px, point.py))
        axes.scatter(
            point.px,
            point.py,
            s=60,
            marker="x",
            linewidths=2,
            color=base[point.series],
        )
        if (segment := _error_segment(point, height)) is not None:
            axes.plot(*segment, color=base[point.series])
    names, more = capped(series)
    handles = [
        Line2D([], [], marker="o", linestyle="", color=base[name], label=name)
        for name in names
    ]
    if more:
        handles.append(_more_series(more))
    _legend_strip(figure, canvas.get_renderer(), width, height, [handles, _key()])
    _save(figure, path)
    return PlotResult(
        path,
        "overlay",
        tuple(mapped),
        tuple(names),
        tuple(sorted((name, base[name]) for name in drawn)),
        view.unmatched,
    )


def _linestyle(kind: str) -> Literal["-", ""]:
    """Timecourse and outputs series as lines through their points by time, scatters as points."""
    return "" if kind == "scatters" else "-"


def capped[T](items: Sequence[T], limit: int = LEGEND_LIMIT) -> tuple[list[T], int]:
    """The first `limit` items and how many more there are."""
    return list(items[:limit]), max(0, len(items) - limit)


def axis_title(labels: Iterable[str | None]) -> str:
    """The title of an axis for the labels of its series: the one that all share, else the
    distinct ones (at most three, then "and N more") joined with " / "; empty without a label."""
    shown, more = capped(list(dict.fromkeys(label for label in labels if label)), 3)
    return " / ".join(shown) + (f" and {more} more" if more else "")


def _more_series(count: int):
    """An empty legend entry that counts the series beyond the limit."""
    from matplotlib.lines import Line2D

    return Line2D([], [], linestyle="", label=f"and {count} more series")


def _side_by_side(study: LoadedStudy, view: SourceView, path: Path) -> PlotResult:
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    series: dict[str, list] = {}
    for point in view.points:
        series.setdefault(point.series, []).append(point)
    styles = {entry.name: entry for entry in view.series}
    figure = Figure(figsize=(12, 5))
    left, right = figure.subplots(1, 2)
    if view.image and view.image_size:
        left.imshow(_image(study.folder / view.image))
    left.axis("off")
    # A series of one point is no line: all of them are drawn by two calls, so that a figure with a
    # series per individual stays fast.
    singles = [rows[0] for rows in series.values() if len(rows) == 1]
    for name, rows in series.items():
        if len(rows) == 1:
            continue
        right.errorbar(
            [p.x for p in rows],
            [p.y for p in rows],
            yerr=_error_ranges(rows),
            marker="o",
            linestyle=_linestyle(rows[0].kind),
            color=styles[name].color,
        )
    if singles:
        colors = [styles[p.series].color for p in singles]
        right.scatter([p.x for p in singles], [p.y for p in singles], color=colors)
        bars = [
            p for p in singles if p.error_low is not None or p.error_high is not None
        ]
        right.vlines(
            [p.x for p in bars],
            [p.y if p.error_low is None else p.error_low for p in bars],
            [p.y if p.error_high is None else p.error_high for p in bars],
            colors=[styles[p.series].color for p in bars],
        )
    if series:
        right.set_xlabel(axis_title(styles[name].x_label for name in series))
        right.set_ylabel(axis_title(styles[name].y_label for name in series))
        names, more = capped(list(series))
        handles = [
            Line2D(
                [],
                [],
                marker="o",
                color=styles[name].color,
                linestyle=_linestyle(series[name][0].kind),
                label=name,
            )
            for name in names
        ]
        if more:
            handles.append(_more_series(more))
        # The default "best" place weighs every point, which is slow for many.
        right.legend(handles=handles, loc="best" if not more else "upper right")
    figure.tight_layout()
    _save(figure, path)
    return PlotResult(
        path,
        "side_by_side",
        legend=tuple(capped(list(series))[0]),
        colors=tuple(sorted((name, styles[name].color) for name in series)),
        unmatched=view.unmatched,
    )
