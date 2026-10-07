"""Render a figure source with matplotlib: the digitized overlay or image and data side by side.

The overlay uses image pixels, so its points equal those of `source_view`, which the curation app draws with Plotly.
Figures are drawn on their own Agg canvas without pyplot, so rendering changes no global matplotlib state and is
safe in the threads of the curation server.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pkdb.studyformat.colors import POINT_RING
from pkdb.studyformat.digitize import ERROR_BAR_SUFFIX
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import SourceView, source_view


@dataclass(frozen=True)
class PlotResult:
    """The written PNG, its mode, the pixels of the mapped points drawn in overlay mode and the series without dataset."""

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


def _save(figure, path: Path) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    FigureCanvasAgg(figure)
    figure.savefig(path, dpi=100)


def _overlay(study, view, path: Path) -> PlotResult:
    from matplotlib.figure import Figure
    from matplotlib.image import imread
    from matplotlib.lines import Line2D

    width, height = view.image_size
    figure = Figure(figsize=(width / 100, height / 100), dpi=100)
    axes = figure.add_axes((0, 0, 1, 1))
    axes.imshow(imread(study.folder / view.image), extent=(0, width, height, 0))
    axes.set_xlim(0, width)
    axes.set_ylim(height, 0)
    axes.axis("off")
    # The colors and their order of the source view, which the curation app draws alike.
    base = {series.name: series.color for series in view.series}
    drawn = {p.series.removesuffix(ERROR_BAR_SUFFIX) for p in view.overlay}
    series = [name for name in base if name in drawn]
    color = {
        p.series: base[p.series.removesuffix(ERROR_BAR_SUFFIX)] for p in view.overlay
    }
    mapped = []
    for point in view.overlay:
        if point.role == "raw":
            bar = point.series.endswith(ERROR_BAR_SUFFIX)
            axes.scatter(
                point.px,
                point.py,
                s=40 if bar else 16,
                marker="_" if bar else "o",
                color=color[point.series],
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
            color=color[point.series],
        )
        if point.error_px is not None:
            axes.plot(
                [point.px, point.error_px[0]],
                [point.py, point.error_px[1]],
                color=color[point.series],
            )
    handles = [
        Line2D([], [], marker="o", linestyle="", color=base[name], label=name)
        for name in series
    ]
    if handles:
        axes.legend(handles=handles, loc="best", framealpha=0.8, fontsize="small")
    _save(figure, path)
    return PlotResult(
        path,
        "overlay",
        tuple(mapped),
        tuple(series),
        tuple(sorted(color.items())),
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
        colors=tuple(sorted((entry.name, entry.color) for entry in view.series)),
        unmatched=view.unmatched,
    )
