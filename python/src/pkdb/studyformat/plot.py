"""Render a figure source with matplotlib: the digitized overlay or image and data side by side.

The overlay uses image pixels, so its points equal those of `source_view`, which the curation app draws with Plotly.
The image keeps its pixels at the top of the PNG, with the series and the key of the marks in a strip below it.
Figures are drawn on their own Agg canvas without pyplot, so rendering changes no global matplotlib state and is
safe in the threads of the curation server.
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pkdb.studyformat.colors import POINT_RING
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import SourceView, source_view


@dataclass(frozen=True)
class PlotResult:
    """The written PNG and its mode, with what the plot draws.

    `points` are the pixels of the mapped points drawn in overlay mode, `legend` the series of the
    legend, `colors` the color of each drawn series once, and `unmatched` the series without a dataset.
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


def _overlay(study, view, path: Path) -> PlotResult:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.image import imread
    from matplotlib.lines import Line2D

    width, height = view.image_size
    figure = Figure(figsize=(width / DPI, height / DPI), dpi=DPI)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_axes((0, 0, 1, 1))
    axes.imshow(imread(study.folder / view.image), extent=(0, width, height, 0))
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
        if point.error_px is not None:
            axes.plot(
                [point.px, point.error_px[0]],
                [point.py, point.error_px[1]],
                color=base[point.series],
            )
    handles = [
        Line2D([], [], marker="o", linestyle="", color=base[name], label=name)
        for name in series
    ]
    _legend_strip(figure, canvas.get_renderer(), width, height, [handles, _key()])
    _save(figure, path)
    return PlotResult(
        path,
        "overlay",
        tuple(mapped),
        tuple(series),
        tuple(sorted((name, base[name]) for name in drawn)),
        view.unmatched,
    )


def _side_by_side(study: LoadedStudy, view: SourceView, path: Path) -> PlotResult:
    from matplotlib.figure import Figure

    series: dict[str, list] = {}
    for point in view.points:
        series.setdefault(point.series, []).append(point)
    styles = {entry.name: entry for entry in view.series}
    figure = Figure(figsize=(12, 5))
    left, right = figure.subplots(1, 2)
    if view.image and view.image_size:
        from matplotlib.image import imread

        left.imshow(imread(study.folder / view.image))
    left.axis("off")
    for name, rows in series.items():
        error = [
            abs(p.error_bar - p.y) if p.error_bar is not None else 0.0 for p in rows
        ]
        right.errorbar(
            [p.x for p in rows],
            [p.y for p in rows],
            yerr=error if any(error) else None,
            marker="o",
            linestyle="-" if rows[0].kind == "timecourses" else "",
            color=styles[name].color,
            label=name,
        )
    if series:
        first = styles[next(iter(series))]
        right.set_xlabel(first.x_label or "")
        right.set_ylabel(first.y_label or "")
        right.legend()
    figure.tight_layout()
    _save(figure, path)
    return PlotResult(
        path,
        "side_by_side",
        legend=tuple(series),
        colors=tuple(sorted((name, styles[name].color) for name in series)),
        unmatched=view.unmatched,
    )
