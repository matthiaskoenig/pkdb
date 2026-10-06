"""Render a figure source with matplotlib: the digitized overlay or image and data side by side.

The overlay uses image pixels, so its points equal those of `source_view`, which the curation app draws with Plotly.
Figures are drawn on their own Agg canvas without pyplot, so rendering changes no global matplotlib state and is
safe in the threads of the curation server.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pkdb.studyformat.digitize import ERROR_BAR_SUFFIX, mapped_points
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import source_view

COLORS = ("#0e9aa7", "#e8710a", "#7b5ea7", "#2e7d32", "#c2185b", "#5d4037")


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
    if view.digitization and view.image and view.image_size:
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
    series = list(
        dict.fromkeys(p.series.removesuffix(ERROR_BAR_SUFFIX) for p in view.overlay)
    )
    base = {name: COLORS[i % len(COLORS)] for i, name in enumerate(series)}
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
                s=40 if bar else 12,
                marker="_" if bar else "o",
                color=color[point.series],
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


def _units(study: LoadedStudy, view) -> dict[str, tuple[str, str]]:
    """Per series name the axis units: time and value of timecourses, x and y of scatters."""
    units: dict[str, tuple[str, str]] = {}
    for table in study.tables:
        if table.source != view.source:
            continue
        for row in table.rows:
            cells = row.cells
            if table.kind == "timecourses" and cells.get("label"):
                units.setdefault(
                    cells["label"], (cells.get("time_unit", ""), cells.get("unit", ""))
                )
            elif table.kind == "scatters" and cells.get("name"):
                units.setdefault(
                    cells["name"], (cells.get("x_unit", ""), cells.get("y_unit", ""))
                )
    return units


def _side_by_side(study, view, path: Path) -> PlotResult:
    from matplotlib.figure import Figure

    points = [
        point
        for table in study.tables
        if table.source == view.source and table.kind in ("timecourses", "scatters")
        for point in mapped_points(table)
    ]
    bars = {
        (p.file, p.line, p.dataset): p.y
        for p in points
        if p.dataset.endswith(ERROR_BAR_SUFFIX)
    }
    series: dict[str, list] = {}
    for point in points:
        if not point.dataset.endswith(ERROR_BAR_SUFFIX):
            series.setdefault(point.dataset, []).append(point)
    units = _units(study, view)
    figure = Figure(figsize=(12, 5))
    left, right = figure.subplots(1, 2)
    if view.image and view.image_size:
        from matplotlib.image import imread

        left.imshow(imread(study.folder / view.image))
    left.axis("off")
    for i, (name, rows) in enumerate(series.items()):
        error = [
            abs(bars[key] - p.y)
            if (key := (p.file, p.line, name + ERROR_BAR_SUFFIX)) in bars
            else 0.0
            for p in rows
        ]
        right.errorbar(
            [p.x for p in rows],
            [p.y for p in rows],
            yerr=error if any(error) else None,
            marker="o",
            linestyle="-" if rows[0].column != "y_mean" else "",
            color=COLORS[i % len(COLORS)],
            label=name,
        )
    if units:
        x_unit, y_unit = next(iter(units.values()))
        right.set_xlabel(x_unit)
        right.set_ylabel(y_unit)
    if series:
        right.legend()
    figure.tight_layout()
    _save(figure, path)
    return PlotResult(path, "side_by_side", unmatched=view.unmatched)
