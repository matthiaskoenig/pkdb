"""Draw the images, PDFs and WebPlotDigitizer project of the curation app test fixture.

The text files of the fixture (study.json, review.json, reference.json and the tables) are the
data. This script draws Figure 1 of caffeine/Demo2020 from its timecourse rows, digitizes the
image exactly as WebPlotDigitizer would on it (calibration on the axis ticks, points on the
markers, with a little click noise), and draws the paper tables and placeholder PDFs, so the
data, the images and the project agree. Run it after changing the data of a figure or table:

    uv run --project python python tools/curation_testing/make_fixture.py

One point is placed wrongly on purpose: the row of the 100 mg series at 4 h says 1.24 mg/l
while the figure shows 1.42 mg/l, and that point is not digitized, so validation reports one
`digitized_mismatch` at the row. The fixture is synthetic: it describes no real publication.
"""

import random
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.load import load_study

FIXTURE = Path(__file__).resolve().parent / "fixture"
DEMO = FIXTURE / "caffeine" / "Demo2020"
DRAFT = FIXTURE / "caffeine" / "Draft2021"

WIDTH, HEIGHT, DPI = 900, 600, 100
X_LIMITS, Y_LIMITS = (-0.6, 25.0), (0.0, 6.0)
X_CALIBRATION, Y_CALIBRATION = (0.0, 24.0), (0.0, 6.0)
SERIES = {
    "caf_plasma_100mg": {
        "legend": "100 mg",
        "marker": "o",
        "face": "black",
        "line": "-",
    },
    "caf_plasma_200mg": {
        "legend": "200 mg",
        "marker": "s",
        "face": "white",
        "line": "--",
    },
}
# Where the figure draws the misplaced row, which is therefore not digitized.
FIGURE_VALUES = {("caf_plasma_100mg", 4.0): 1.42}
# Clicks in WebPlotDigitizer land within about half a pixel of a marker.
CLICK_NOISE = 0.5
# PNG and PDF files without the version of matplotlib or a date, so that they only change
# with the drawing.
PNG_METADATA = {"Software": None}
PDF_METADATA = {"Creator": None, "Producer": None, "CreationDate": None}

# The points of each series as the figure draws them: time, mean and error bar end.
Series = dict[str, list[tuple[float, float, float | None]]]


def timecourse_series(folder: Path) -> Series:
    """The points of each series of Figure 1 as the figure draws them."""
    table = load_study(folder).table("timecourses_Fig1.tsv")
    assert table is not None, "timecourses_Fig1.tsv is missing"
    series: Series = {name: [] for name in SERIES}
    for row in table.rows:
        label, time, mean = row.cells["label"], row.values["time"], row.values["mean"]
        bar = row.values.get("error_bar")
        assert isinstance(time, float) and isinstance(mean, float)
        mean = FIGURE_VALUES.get((label, time), mean)
        series[label].append((time, mean, bar if isinstance(bar, float) else None))
    return series


def draw_figure(series: Series, path: Path) -> Figure:
    """Draw Figure 1 as a journal prints it; the figure gives the pixels of data points."""
    figure = Figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    axes = figure.add_axes((0.11, 0.12, 0.85, 0.82))
    for label, points in series.items():
        style = SERIES[label]
        times = [time for time, _, _ in points]
        means = [mean for _, mean, _ in points]
        upper = [(bar - mean) if bar is not None else 0.0 for _, mean, bar in points]
        axes.errorbar(
            times,
            means,
            yerr=[[0.0] * len(points), upper],
            color="black",
            linestyle=style["line"],
            linewidth=1.2,
            marker=style["marker"],
            markersize=7,
            markerfacecolor=style["face"],
            markeredgecolor="black",
            capsize=4,
            elinewidth=1,
            label=style["legend"],
        )
    axes.set_xlim(*X_LIMITS)
    axes.set_ylim(*Y_LIMITS)
    axes.set_xticks(range(0, 25, 4))
    axes.set_yticks(range(0, 7))
    axes.set_xlabel("Time [h]", fontsize=13)
    axes.set_ylabel("Caffeine in plasma [mg/l]", fontsize=13)
    axes.tick_params(labelsize=12)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    axes.legend(frameon=False, fontsize=12, title="Dose", title_fontsize=12)
    figure.savefig(path, dpi=DPI, metadata=PNG_METADATA)
    return figure


def pixel(figure: Figure, x: float, y: float) -> tuple[float, float]:
    """The image pixel of a data point: origin at the top-left corner, y pointing down."""
    axes = figure.axes[0]
    display_x, display_y = axes.transData.transform((x, y))
    return round(float(display_x), 2), round(HEIGHT - float(display_y), 2)


def calibration_point(figure: Figure, x: float, y: float, dx: float, dy: float) -> dict:
    """A click on an axis tick at data point (x, y) with the values `dx` and `dy` entered."""
    px, py = pixel(figure, x, y)
    return {"px": px, "py": py, "dx": f"{dx:g}", "dy": f"{dy:g}", "dz": None}


def digitization(figure: Figure, series: Series) -> dict:
    """The WebPlotDigitizer 4 project of Figure 1, digitized on its image."""
    clicks = random.Random(2020)

    def offset() -> float:
        return clicks.uniform(-CLICK_NOISE, CLICK_NOISE)

    def click(x: float, y: float) -> dict:
        px, py = pixel(figure, x, y)
        return {
            "x": round(px + offset(), 2),
            "y": round(py + offset(), 2),
            "value": [x, y],
        }

    # The x axis is drawn at the lowest y and the y axis at the lowest x. WebPlotDigitizer
    # stores 0 for the value that a point of the other axis does not use.
    x_axis_y, y_axis_x = Y_LIMITS[0], X_LIMITS[0]
    (x1, x2), (y1, y2) = X_CALIBRATION, Y_CALIBRATION
    datasets = []
    colors = {
        "caf_plasma_100mg": [200, 0, 0, 255],
        "caf_plasma_200mg": [0, 0, 200, 255],
    }
    for label, points in series.items():
        means = [
            click(t, mean) for t, mean, _ in points if (label, t) not in FIGURE_VALUES
        ]
        bars = [click(t, bar) for t, _, bar in points if bar is not None]
        for name, data in ((label, means), (f"{label};error_bar", bars)):
            datasets.append(
                {
                    "name": name,
                    "axesName": "XY",
                    "colorRGB": colors[label],
                    "metadataKeys": [],
                    "data": data,
                    "autoDetectionData": None,
                }
            )
    return {
        "version": [4, 2],
        "axesColl": [
            {
                "name": "XY",
                "type": "XYAxes",
                "isLogX": False,
                "isLogY": False,
                "noRotation": False,
                "calibrationPoints": [
                    calibration_point(figure, x1, x_axis_y, x1, 0),
                    calibration_point(figure, x2, x_axis_y, x2, 0),
                    calibration_point(figure, y_axis_x, y1, 0, y1),
                    calibration_point(figure, y_axis_x, y2, 0, y2),
                ],
            }
        ],
        "datasetColl": datasets,
        "measurementColl": [],
    }


def draw_table(path: Path, caption: str, rows: list[list[str]], note: str) -> None:
    """Draw a paper table: the caption, rules above and below the header and at the end, a note."""
    columns = max(len(row) for row in rows)
    height = 1.3 + 0.42 * len(rows)
    figure = Figure(figsize=(WIDTH / DPI, height), dpi=DPI)
    figure.text(
        0.04, 1 - 0.45 / height, caption, fontsize=13, weight="bold", va="center"
    )
    starts = [0.04, *(0.5 + 0.24 * index for index in range(columns - 1))]
    top = 1 - 0.85 / height
    step = 0.42 / height

    def rule(y: float, width: float = 1.0) -> None:
        figure.add_artist(Line2D([0.03, 0.97], [y, y], linewidth=width, color="black"))

    rule(top)
    for index, row in enumerate(rows):
        y = top - step * (index + 0.5)
        for column, cell in enumerate(row):
            figure.text(starts[column], y, cell, fontsize=12, va="center")
    rule(top - step, 0.6)
    bottom = top - step * len(rows)
    rule(bottom)
    figure.text(
        0.04, bottom - 0.3 / height, note, fontsize=11, style="italic", va="center"
    )
    figure.savefig(path, dpi=DPI, metadata=PNG_METADATA)


def draw_pdf(path: Path, study: str, title: str) -> None:
    """A one-page placeholder for the publication PDF."""
    figure = Figure(figsize=(8.27, 11.69))
    figure.text(0.1, 0.9, title, fontsize=15, weight="bold", wrap=True)
    figure.text(
        0.1,
        0.84,
        f"{study} is a synthetic test study of the PK-DB curation app.\n"
        "This page stands in for the publication PDF. Its values are made up.",
        fontsize=12,
    )
    figure.savefig(path, metadata=PDF_METADATA)


def raw_rows(path: Path) -> list[list[str]]:
    return [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    series = timecourse_series(DEMO)
    figure = draw_figure(series, DEMO / "Demo2020_Fig1.png")
    (DEMO / "Demo2020_Fig1.wpd.json").write_text(
        dump_json(digitization(figure, series)), encoding="utf-8"
    )

    # The raw table holds the cells as printed; its last row is the note below the table.
    printed = [
        [cell for cell in row if cell] for row in raw_rows(DEMO / "Demo2020_Tab2.tsv")
    ]
    draw_table(
        DEMO / "Demo2020_Tab2.png",
        "Table 2. Pharmacokinetic parameters of caffeine",
        printed[:-1],
        printed[-1][0],
    )
    draw_table(
        DRAFT / "Draft2021_Tab1.png",
        "Table 1. Caffeine after a 150 mg tablet",
        [
            ["Parameter", "150 mg"],
            ["Cmax (mg/l)", "3.1 ± 0.6"],
            ["tmax (h)", "1.1 ± 0.4"],
        ],
        "Mean ± SD of 8 subjects.",
    )
    reference = {
        DEMO: "Caffeine in plasma after two oral doses",
        DRAFT: "Caffeine tablets in a draft study",
    }
    for folder, title in reference.items():
        draw_pdf(folder / f"{folder.name}.pdf", folder.name, title)
    for folder in (DEMO, DRAFT):
        result = format_folder(folder)
        assert result.ok, result.issues


if __name__ == "__main__":
    main()
