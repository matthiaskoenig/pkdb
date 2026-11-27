"""Draw the images, PDFs and WebPlotDigitizer project of the curation app test fixture.

The text files of the fixture (study.json, review.json, reference.json and the tables) are the
data. This script draws Figure 1 of caffeine/Demo2020 from its timecourse rows, digitizes the
image exactly as WebPlotDigitizer would on it (calibration on the axis ticks, points on the
markers, with a little click noise), and draws the paper tables and placeholder PDFs, so the
data, the images and the project agree. The figure and the tables are charts of sbmlsim-core,
drawn into PNG files by its renderer, and the PDFs are written with fpdf2. Run it after
changing the data of a figure or table:

    uv run --project python --with fpdf2 python tools/curation_testing/make_fixture.py

One point is placed wrongly on purpose: the row of the 100 mg series at 4 h says 1.24 mg/l
while the figure shows 1.42 mg/l, and that point is not digitized, so validation reports one
`digitized_mismatch` at the row. The fixture is synthetic: it describes no real publication.
"""

import math
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF
from sbmlsim_core.chart import Chart, ChartAxis

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.load import load_study

FIXTURE = Path(__file__).resolve().parent / "fixture"
DEMO = FIXTURE / "caffeine" / "Demo2020"
DRAFT = FIXTURE / "caffeine" / "Draft2021"

WIDTH, HEIGHT, DPI = 900, 600, 100
# A chart is laid out in points of 1/72 inch and drawn at DPI pixels per inch.
SCALE = DPI / 72
X_LIMITS, Y_LIMITS = (-0.6, 25.0), (0.0, 6.0)
X_TICKS, Y_TICKS = list(range(0, 25, 4)), list(range(7))
X_CALIBRATION, Y_CALIBRATION = (0.0, 24.0), (0.0, 6.0)
FONTS = {"label": 13, "tick": 12, "legend": 12}
SERIES = {
    "caf_plasma_100mg": {
        "legend": "100 mg",
        "marker": "circle",
        "face": "black",
        "line": "solid",
    },
    "caf_plasma_200mg": {
        "legend": "200 mg",
        "marker": "square",
        "face": "white",
        "line": "dashed",
    },
}
# Where the figure draws the misplaced row, which is therefore not digitized.
FIGURE_VALUES = {("caf_plasma_100mg", 4.0): 1.42}
# Clicks in WebPlotDigitizer land within about half a pixel of a marker.
CLICK_NOISE = 0.5
SVG = "{http://www.w3.org/2000/svg}"
# The creation date of the PDFs, the year of the synthetic Demo2020.
PDF_DATE = datetime(2020, 1, 1, tzinfo=UTC)

# The points of each series as the figure draws them: time, mean and error bar end.
Series = dict[str, list[tuple[float, float, float | None]]]


@dataclass(frozen=True)
class Frame:
    """Where a chart draws the values of its plot: the image pixel of a data point."""

    x0: float
    x_slope: float
    y0: float
    y_slope: float

    def pixel(self, x: float, y: float) -> tuple[float, float]:
        """The image pixel of a data point: origin at the top-left corner, y pointing down."""
        return (
            round(self.x0 + self.x_slope * x, 2),
            round(self.y0 + self.y_slope * y, 2),
        )


def plot_svg(root: ET.Element) -> ET.Element:
    """The element of the one plot of the SVG of a chart, placed at its x and y in points."""
    return next(e for e in root.iter(f"{SVG}svg") if e.get("class") == "sbmlsim-plot")


def tick_marks(axis: ET.Element, coordinate: int) -> list[float]:
    """The positions of the tick marks of an axis of the SVG of a chart, in points."""
    positions = []
    for group in axis.iter(f"{SVG}g"):
        if group.get("class") == "charton-tick":
            for path in group.iter(f"{SVG}path"):
                start = path.get("d", "").split("L")[0].removeprefix("M")
                positions.append(float(start.split()[coordinate]))
    return positions


def frame(chart: Chart) -> Frame:
    """The frame of the one plot of a chart, from the tick marks its renderer draws.

    The renderer places the tick marks at the values of `X_TICKS` and `Y_TICKS`, so a line
    through the first and the last mark of an axis maps a value to its point, and every mark
    in between checks the line. The PNG is the SVG drawn at `SCALE` pixels per point.
    """
    root = ET.fromstring(chart.svg())
    plot = plot_svg(root)
    lines = {}
    for coordinate, (name, ticks) in enumerate((("x", X_TICKS), ("y", Y_TICKS))):
        axis = next(
            e
            for e in plot.iter(f"{SVG}g")
            if e.get("data-axis") == name and "charton-axis" in e.get("class", "")
        )
        # a y axis points down in the image
        marks = sorted(tick_marks(axis, coordinate), reverse=name == "y")
        assert len(marks) == len(ticks), (name, marks)
        slope = (marks[-1] - marks[0]) / (ticks[-1] - ticks[0])
        start = marks[0] - slope * ticks[0]
        for tick, mark in zip(ticks, marks, strict=True):
            assert math.isclose(start + slope * tick, mark, abs_tol=0.02), (name, tick)
        offset = float(plot.get(name, 0))
        lines[name] = ((offset + start) * SCALE, slope * SCALE)
    (x0, x_slope), (y0, y_slope) = lines["x"], lines["y"]
    return Frame(x0, x_slope, y0, y_slope)


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


def draw_figure(series: Series, path: Path) -> Frame:
    """Draw Figure 1 as a journal prints it; the frame gives the pixels of data points."""
    chart = Chart(WIDTH / SCALE, HEIGHT / SCALE, fonts=FONTS, dpi=DPI)
    plot = chart.plot(
        x=ChartAxis(label="Time [h]", min=X_LIMITS[0], max=X_LIMITS[1], ticks=X_TICKS),
        y=ChartAxis(
            label="Caffeine in plasma [mg/l]",
            min=Y_LIMITS[0],
            max=Y_LIMITS[1],
            ticks=Y_TICKS,
        ),
        legend_title="Dose",
        legend_frame=False,
    )
    for label, points in series.items():
        style = SERIES[label]
        plot.curve(
            [time for time, _, _ in points],
            [mean for _, mean, _ in points],
            # the bars point up only: no lower side, none where a row has no error bar
            yerr=(
                [math.nan] * len(points),
                [
                    bar - mean if bar is not None else math.nan
                    for _, mean, bar in points
                ],
            ),
            color="black",
            line=style["line"],
            width=1.2,
            marker=style["marker"],
            size=7,
            marker_fill=style["face"],
            marker_edge="black",
            # the whole width of a cap, twice the `capsize` of matplotlib
            error_cap=8,
            error_width=1,
            label=style["legend"],
        )
    chart.save(path)
    return frame(chart)


def calibration_point(frame: Frame, x: float, y: float, dx: float, dy: float) -> dict:
    """A click on an axis tick at data point (x, y) with the values `dx` and `dy` entered."""
    px, py = frame.pixel(x, y)
    return {"px": px, "py": py, "dx": f"{dx:g}", "dy": f"{dy:g}", "dz": None}


def digitization(frame: Frame, series: Series) -> dict:
    """The WebPlotDigitizer 4 project of Figure 1, digitized on its image."""
    clicks = random.Random(2020)

    def offset() -> float:
        return clicks.uniform(-CLICK_NOISE, CLICK_NOISE)

    def click(x: float, y: float) -> dict:
        px, py = frame.pixel(x, y)
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
                    calibration_point(frame, x1, x_axis_y, x1, 0),
                    calibration_point(frame, x2, x_axis_y, x2, 0),
                    calibration_point(frame, y_axis_x, y1, 0, y1),
                    calibration_point(frame, y_axis_x, y2, 0, y2),
                ],
            }
        ],
        "datasetColl": datasets,
        "measurementColl": [],
    }


class Page:
    """A chart of one plot without axes, which places text and rules on the whole image.

    A position is given as matplotlib gives one in a figure, by fractions of the image from
    its left and its bottom; `axes` maps it onto the fractions of the panel of the plot,
    which the renderer insets into the image, and the elements are not clipped to it.
    """

    def __init__(self, width: float, height: float) -> None:
        def hidden() -> ChartAxis:
            return ChartAxis(
                min=0.0,
                max=1.0,
                label_visible=False,
                ticks_visible=False,
                tick_marks_visible=False,
                line_visible=False,
            )

        self.width, self.height = width, height
        self.chart = Chart(width, height, dpi=DPI)
        self.plot = self.chart.plot(x=hidden(), y=hidden(), legend=False)
        root = ET.fromstring(self.chart.svg())
        rect = root.find(f"{SVG}defs/{SVG}clipPath/{SVG}rect")
        assert rect is not None
        plot = plot_svg(root)
        self.left = float(plot.get("x", 0)) + float(rect.get("x", 0))
        self.top = float(plot.get("y", 0)) + float(rect.get("y", 0))
        self.panel_width = float(rect.get("width", 0))
        self.panel_height = float(rect.get("height", 0))

    def axes(self, x: float, y: float) -> tuple[float, float]:
        """The fractions of the panel of a position given by fractions of the image."""
        return (
            (x * self.width - self.left) / self.panel_width,
            (self.top + self.panel_height - (1 - y) * self.height) / self.panel_height,
        )

    def text(
        self, x: float, y: float, value: str, size: float, bold: bool = False
    ) -> None:
        """A text which starts at x and is centred on y."""
        ax, ay = self.axes(x, y)
        self.plot.text(
            ax,
            ay,
            value,
            size=size,
            weight="bold" if bold else "normal",
            baseline="center",
            coordinates="axes",
            clip=False,
        )

    def rule(self, y: float, width: float = 1.0) -> None:
        """A rule across the table at y."""
        (left, ay), (right, _) = self.axes(0.03, y), self.axes(0.97, y)
        self.plot.curve(
            [left, right],
            [ay, ay],
            color="black",
            width=width,
            coordinates="axes",
            clip=False,
        )


def draw_table(path: Path, caption: str, rows: list[list[str]], note: str) -> None:
    """Draw a paper table: the caption, rules above and below the header and at the end, a note."""
    columns = max(len(row) for row in rows)
    height = 1.3 + 0.42 * len(rows)
    page = Page(WIDTH / SCALE, height * 72)
    page.text(0.04, 1 - 0.45 / height, caption, 13, bold=True)
    starts = [0.04, *(0.5 + 0.24 * index for index in range(columns - 1))]
    top = 1 - 0.85 / height
    step = 0.42 / height
    page.rule(top)
    for index, row in enumerate(rows):
        y = top - step * (index + 0.5)
        for column, cell in enumerate(row):
            page.text(starts[column], y, cell, 12)
    page.rule(top - step, 0.6)
    bottom = top - step * len(rows)
    page.rule(bottom)
    page.text(0.04, bottom - 0.3 / height, note, 11)
    page.chart.save(path)


def draw_pdf(path: Path, study: str, title: str) -> None:
    """A one-page A4 placeholder for the publication PDF, with a fixed date and no producer."""
    pdf = FPDF(format="A4")
    # a fixed date and no version of fpdf2, so that the file only changes with its text
    pdf.set_creation_date(PDF_DATE)
    pdf.producer = ""
    pdf.set_margins(21, 25)
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=15)
    pdf.multi_cell(0, 7, title)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0,
        6,
        f"{study} is a synthetic test study of the PK-DB curation app.\n"
        "This page stands in for the publication PDF. Its values are made up.",
    )
    pdf.output(str(path))


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
