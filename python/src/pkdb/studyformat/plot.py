"""Render a figure source with matplotlib: the digitized overlay or image and data side by side.

The overlay uses image pixels, so its points equal those of `source_view`, which the curation app draws with Plotly.
"""

from dataclasses import dataclass
from pathlib import Path

from pkdb.studyformat.digitize import ERROR_BAR_SUFFIX, mapped_points
from pkdb.studyformat.load import LoadedStudy
from pkdb.studyformat.sources import source_view

COLORS = ("#0e9aa7", "#e8710a", "#7b5ea7", "#2e7d32", "#c2185b", "#5d4037")


@dataclass(frozen=True)
class PlotResult:
    """The written PNG and the pixels of the mapped points drawn in overlay mode."""

    path: Path
    points: tuple[tuple[float, float], ...]


def render_source(study: LoadedStudy, source: str, path: Path) -> PlotResult:
    """Write the plot of a figure source to `path`; raises KeyError for an unknown source."""
    view = source_view(study, source)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if view.digitization and view.image and view.image_size:
        return _overlay(plt, study, view, path)
    return _side_by_side(plt, study, view, path)


def _overlay(plt, study, view, path: Path) -> PlotResult:
    from matplotlib.image import imread

    width, height = view.image_size
    figure = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    try:
        axes = figure.add_axes((0, 0, 1, 1))
        axes.imshow(imread(study.folder / view.image), extent=(0, width, height, 0))
        axes.set_xlim(0, width)
        axes.set_ylim(height, 0)
        axes.axis("off")
        series = list(dict.fromkeys(p.series for p in view.overlay))
        color = {name: COLORS[i % len(COLORS)] for i, name in enumerate(series)}
        mapped = []
        for point in view.overlay:
            if point.role == "raw":
                axes.scatter(point.px, point.py, s=12, color=color[point.series])
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
            plt.Line2D([], [], marker="o", linestyle="", color=color[name], label=name)
            for name in series
        ]
        if handles:
            axes.legend(handles=handles, loc="upper left")
        figure.savefig(path, dpi=100)
    finally:
        plt.close(figure)
    return PlotResult(path, tuple(mapped))


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


def _side_by_side(plt, study, view, path: Path) -> PlotResult:
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
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 5))
    try:
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
        figure.savefig(path, dpi=100)
    finally:
        plt.close(figure)
    return PlotResult(path, ())
