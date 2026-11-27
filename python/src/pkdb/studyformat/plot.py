"""Render a figure source as a chart of sbmlsim-core: the digitized overlay, or the image and the data side by side.

The overlay uses image pixels, so its points equal those of `source_view`, which the curation app draws with Plotly.
The chart of an overlay draws the image at its pixels at the top in the middle, with the series and the key of the marks
in legends below it; it is wider than the image by the room the renderer keeps around a panel, or by legends wider than
the image. A chart is written by the suffix of its path, SVG or PNG (`.png`, a pixel per pixel of an overlay). The charts of `sbmlsim_core.chart` hold no global state, so rendering is safe in the
threads of the curation server.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sbmlsim_core import figure_geometry
from sbmlsim_core.chart import Chart, ChartAxis, ChartPlot

from pkdb.studyformat.colors import POINT_RING
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import OverlayPoint, SourcePoint, SourceView, source_view


@dataclass(frozen=True)
class PlotResult:
    """The written chart and its mode, with what the plot draws.

    `chart` is the drawn chart, written to `path` by its suffix. `points` are the mapped points drawn in overlay
    mode, in image pixels; the image starts at the top of the chart, centered when the legends are wider. `legend`
    holds the series of the legend, `colors` the color of each drawn series once, and `unmatched` the series without
    a dataset.
    """

    path: Path
    mode: Literal["overlay", "side_by_side"]
    chart: Chart
    points: tuple[tuple[float, float], ...] = ()
    legend: tuple[str, ...] = ()
    colors: tuple[tuple[str, str], ...] = ()
    unmatched: tuple[str, ...] = ()


def render_source(study: LoadedStudy, source: str, path: Path) -> PlotResult:
    """Write the plot of a figure source to `path`, SVG or by its suffix PNG; raises KeyError for an unknown source."""
    view = source_view(study, source)
    if view.layout == "overlay":
        return _overlay(study, view, path)
    return _side_by_side(study, view, path)


# The most series that a legend lists; the figure still draws every series.
LEGEND_LIMIT = 20
# The pixels of a point of the marks of an overlay, which is drawn in image pixels at 100 per inch.
PT = 100 / 72
# The edge width of the crosses of the mapped rows, 2 points: the renderer strokes an x at 1.5 times its edge width.
CROSS_WIDTH = 2 * PT / 1.5
# The font size of the legends below an overlay in pixels.
STRIP_FONT = 25 / 3 * PT
# The side by side chart in pixels, 12 x 5 inches, written as PNG at 100 per inch: 1200 x 500 pixels.
SIDE_WIDTH, SIDE_HEIGHT, SIDE_DPI = 864, 360, 100
# The space in pixels between a legend below an overlay and the edges of the chart.
STRIP_PAD = 8
# The legend groups of the key of the marks of an overlay, and of the series beyond the limit.
KEY = ("digitized_point", "digitized_error_bar", "mapped_row", "mapped_error_bar")
MORE = "more_series"


def _hidden(low: float, high: float, reverse: bool = False) -> ChartAxis:
    """An axis from `low` to `high` without line, ticks or label, as for an image."""
    return ChartAxis(
        min=low,
        max=high,
        reverse=reverse,
        label_visible=False,
        ticks_visible=False,
        line_visible=False,
    )


def _key(plot: ChartPlot) -> None:
    """The marks of the overlay in black, named as in the key of the curation app."""
    plot.curve(
        [], [], line="none", marker="circle", size=4 * PT, color="black",
        label="Digitized point", legend=KEY[0],
    )  # fmt: skip
    plot.curve(
        [], [], xerr=[], line="none", error_width=1.5 * PT, color="black",
        label="Digitized error bar", legend=KEY[1],
    )  # fmt: skip
    plot.curve(
        [], [], line="none", marker="x", size=60**0.5 * PT, marker_edge_width=CROSS_WIDTH,
        color="black", label="Mapped row", legend=KEY[2],
    )  # fmt: skip
    plot.curve(
        [], [], yerr=[], line="none", error_width=1.5 * PT, color="black",
        label="Error bar of a mapped row", legend=KEY[3],
    )  # fmt: skip


def _more_series(plot: ChartPlot, count: int) -> None:
    """An empty legend entry that counts the series beyond the limit."""
    plot.curve([], [], line="none", label=f"and {count} more series", legend=MORE)


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


def _error_ranges(rows: list[SourcePoint]) -> tuple[list[float], list[float]] | None:
    """The distances from each point down to the low and up to the high end of its error bar,
    the errors of two sides of a curve: 0 without an error bar, None when no point has one."""
    if all(p.error_low is None and p.error_high is None for p in rows):
        return None
    below = [0.0 if p.error_low is None else max(0.0, p.y - p.error_low) for p in rows]
    above = [
        0.0 if p.error_high is None else max(0.0, p.error_high - p.y) for p in rows
    ]
    return below, above


def _overlay(study: LoadedStudy, view: SourceView, path: Path) -> PlotResult:
    assert view.image is not None and view.image_size is not None
    width, height = view.image_size
    # The colors and their order of the source view, which the curation app draws alike.
    base = {series.name: series.color for series in view.series}
    drawn = {p.series for p in view.overlay}
    series = [name for name in base if name in drawn]
    names, _ = capped(series)
    chart = _overlay_chart(study, view, base, series, (width, height), (0, width))
    # The room of the renderer around the panel, and the widest entry of the legends below it.
    geometry = figure_geometry(chart.to_json())
    panel = geometry["plots"][0]["rect"]
    left = panel["x"]
    right = chart.width - left - panel["width"]
    above = chart.height - panel["height"]
    legends = max(entry["rect"]["width"] for entry in geometry["legend_entries"])
    # The image at its pixels in the middle, the legends inside the chart; an even margin
    # keeps the image on whole pixels.
    total = max(width + 2 * max(left, right), legends + 2 * STRIP_PAD)
    total = width + 2 * math.ceil((total - width) / 2)
    low = left - (total - width) / 2
    chart = _overlay_chart(
        study,
        view,
        base,
        series,
        (total, height + above),
        (low, low + total - left - right),
    )
    chart.save(path)
    return PlotResult(
        path,
        "overlay",
        chart,
        tuple((p.px, p.py) for p in view.overlay if p.role != "raw"),
        tuple(names),
        tuple(sorted((name, base[name]) for name in drawn)),
        view.unmatched,
    )


def _overlay_chart(
    study: LoadedStudy,
    view: SourceView,
    base: dict[str, str],
    series: list[str],
    size: tuple[float, float],
    x_range: tuple[float, float],
) -> Chart:
    """The chart of an overlay of `size` pixels whose x axis spans `x_range` image pixels."""
    assert view.image is not None and view.image_size is not None
    width, height = view.image_size
    names, more = capped(series)
    groups = [*names, *([MORE] if more else [])]
    strip = {"position": "bottom", "frame": False, "size": STRIP_FONT}
    # The PNG has a pixel per pixel of the chart.
    chart = Chart(
        *size,
        legends=[{"groups": groups, **strip}, {"groups": list(KEY), **strip}],
        dpi=72,
        thinning=None,
    )
    plot = chart.plot(x=_hidden(*x_range), y=_hidden(0, height, reverse=True))
    plot.image((study.folder / view.image).read_bytes(), (0, width, height, 0))
    segments: list[tuple[str, list[float], list[float]]] = []
    for name in series:
        points = [p for p in view.overlay if p.series == name]
        color = base[name]
        dots = [p for p in points if p.role == "raw" and not p.error_bar_end]
        ends = [p for p in points if p.role == "raw" and p.error_bar_end]
        crosses = [p for p in points if p.role != "raw"]
        if dots:
            plot.curve(
                [p.px for p in dots], [p.py for p in dots], line="none",
                marker="circle", size=4 * PT, color=color, marker_edge=POINT_RING,
                marker_edge_width=0.75 * PT,
            )  # fmt: skip
        if ends:
            # A short horizontal bar at each end, 40**0.5 points wide.
            plot.curve(
                [p.px for p in ends], [p.py for p in ends],
                xerr=[40**0.5 / 2 * PT] * len(ends), line="none",
                error_width=1.5 * PT, color=color,
            )  # fmt: skip
        if crosses:
            plot.curve(
                [p.px for p in crosses], [p.py for p in crosses], line="none",
                marker="x", size=60**0.5 * PT, marker_edge_width=CROSS_WIDTH, color=color,
            )  # fmt: skip
        xs: list[float] = []
        ys: list[float] = []
        for point in crosses:
            if (segment := _error_segment(point, height)) is not None:
                xs.extend([*segment[0], math.nan])
                ys.extend([*segment[1], math.nan])
        if xs:
            segments.append((color, xs, ys))
    # The error bars of the mapped rows over all marks, a gap after each.
    for color, xs, ys in segments:
        plot.curve(xs, ys, width=1.5 * PT, color=color)
    for name in names:
        plot.curve(
            [], [], line="none", marker="circle", size=6 * PT, color=base[name],
            label=name, legend=name,
        )  # fmt: skip
    if more:
        _more_series(plot, more)
    _key(plot)
    return chart


def _linestyle(kind: str) -> Literal["solid", "none"]:
    """Timecourse and outputs series as lines through their points by time, scatters as points."""
    return "none" if kind == "scatters" else "solid"


def capped[T](items: Sequence[T], limit: int = LEGEND_LIMIT) -> tuple[list[T], int]:
    """The first `limit` items and how many more there are."""
    return list(items[:limit]), max(0, len(items) - limit)


def axis_title(labels: Iterable[str | None]) -> str:
    """The title of an axis for the labels of its series: the one that all share, else the
    distinct ones (at most three, then "and N more") joined with " / "; empty without a label."""
    shown, more = capped(list(dict.fromkeys(label for label in labels if label)), 3)
    return " / ".join(shown) + (f" and {more} more" if more else "")


def _side_by_side(study: LoadedStudy, view: SourceView, path: Path) -> PlotResult:
    series: dict[str, list[SourcePoint]] = {}
    for point in view.points:
        series.setdefault(point.series, []).append(point)
    styles = {entry.name: entry for entry in view.series}
    names, more = capped(list(series))
    # The PNG is 1200 x 500 pixels.
    chart = Chart(SIDE_WIDTH, SIDE_HEIGHT, columns=2, dpi=SIDE_DPI, thinning=None)
    if view.image and view.image_size:
        width, height = view.image_size
        figure = chart.plot(
            0,
            0,
            x=_hidden(0, width),
            y=_hidden(0, height, reverse=True),
            aspect="equal",
            legend=False,
        )
        figure.image((study.folder / view.image).read_bytes(), (0, width, height, 0))
    else:
        chart.plot(0, 0, x=_hidden(0, 1), y=_hidden(0, 1), legend=False)
    x_label = axis_title(styles[name].x_label for name in series)
    y_label = axis_title(styles[name].y_label for name in series)
    # The default "best" place weighs every point, which is slow for many.
    data = chart.plot(
        0,
        1,
        x=ChartAxis(label=x_label or None, label_visible=bool(x_label)),
        y=ChartAxis(label=y_label or None, label_visible=bool(y_label)),
        legend=bool(series),
        legend_loc="best" if not more else "upper right",
        frame_color="black",
        frame_width=0.8,
    )
    # A series of one point is no line: those of a color are drawn by one curve, so that a figure with a
    # series per individual stays fast.
    singles: dict[str, list[SourcePoint]] = {}
    for name, rows in series.items():
        if len(rows) == 1:
            singles.setdefault(styles[name].color, []).append(rows[0])
            continue
        data.curve(
            [p.x for p in rows], [p.y for p in rows], yerr=_error_ranges(rows),
            error_width=1.5, line=_linestyle(rows[0].kind), width=1.5,
            marker="circle", size=6, color=styles[name].color,
        )  # fmt: skip
    for color, rows in singles.items():
        data.curve(
            [p.x for p in rows], [p.y for p in rows], yerr=_error_ranges(rows),
            error_width=1.5, line="none", marker="circle", size=6, color=color,
        )  # fmt: skip
    for name in names:
        data.curve(
            [], [], line=_linestyle(series[name][0].kind), width=1.5,
            marker="circle", size=6, color=styles[name].color, label=name, legend=name,
        )  # fmt: skip
    if more:
        _more_series(data, more)
    chart.save(path)
    return PlotResult(
        path,
        "side_by_side",
        chart,
        legend=tuple(names),
        colors=tuple(sorted((name, styles[name].color) for name in series)),
        unmatched=view.unmatched,
    )
