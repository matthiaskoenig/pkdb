import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { OverlayPoint, SourcePoint, SourceSeries, SourceView, ValidationIssue } from "../../src/study-views/types";
import {
  dataRows,
  digitizedScales,
  drawsOnImage,
  FADED,
  axisTitle,
  capped,
  LEGEND_LIMIT,
  legendEntries,
  logAxes,
  logTicks,
  overlayTraces,
  plotTraces,
  PROBLEM_COLORS,
  plottedProblems,
  problemHover,
  plottedSeries,
  pointsOffScale,
  POINT_RING,
  rowAt,
  wrapText,
  type AxisScales,
  type OverlayTrace,
} from "../../src/curation-app/overlay";

const loader = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("../../src/features/plots/plotly", () => ({ loadPlotly: loader.load }));

const IMAGE_URL = "/local/studies/caffeine/Example/files/Example_Fig1.png";
const TIMECOURSES = "timecourses_Fig1.tsv";
const PROJECT = "Example_Fig1.wpd.json";

function point(changes: Partial<OverlayPoint> & Pick<OverlayPoint, "series" | "role">): OverlayPoint {
  return {
    px: 0,
    py: 0,
    x: 0,
    y: 0,
    file: PROJECT,
    line: null,
    error_low_px: null,
    error_high_px: null,
    x_text: String(changes.x ?? 0),
    y_text: String(changes.y ?? 0),
    error_bar_end: false,
    ...changes,
  };
}

function mapped(changes: Partial<SourcePoint> & Pick<SourcePoint, "series" | "line" | "x" | "y">): SourcePoint {
  return {
    kind: "timecourses",
    file: TIMECOURSES,
    error_low: null,
    error_high: null,
    x_text: String(changes.x),
    y_text: String(changes.y),
    ...changes,
  };
}

/** The series of the source view with colors that only the view knows. */
const SERIES: SourceSeries[] = [
  { name: "drug_plasma", color: "#1a2b3c", dark_color: "#4d5e6f", x_label: "time (h)", y_label: "concentration (mg/l)" },
  { name: "drug_urine", color: "#2b3c4d", dark_color: "#5e6f70", x_label: "time (h)", y_label: "amount (mg)" },
  { name: "drug_feces", color: "#3c4d5e", dark_color: "#6f7081", x_label: "time (h)", y_label: "amount (mg)" },
];

/** A digitized figure of 100 x 100 pixels with two series, an error bar and a series without dataset. */
function figure(changes: Partial<SourceView> = {}): SourceView {
  return {
    source: "Fig1",
    image: "Example_Fig1.png",
    image_url: IMAGE_URL,
    image_size: [100, 100],
    raw_grid: null,
    digitization: PROJECT,
    mapped: [],
    overlay: [
      point({ series: "drug_plasma", role: "raw", px: 10, py: 90, x: 0, y: 0.1 }),
      point({ series: "drug_plasma", role: "raw", px: 20, py: 50, x: 1, y: 5.000004, y_text: "5" }),
      point({ series: "drug_plasma", error_bar_end: true, role: "raw", px: 20, py: 40, x: 1, y: 6 }),
      point({ series: "drug_urine", role: "raw", px: 60, py: 31, x: 2, y: 7 }),
      point({
        series: "drug_plasma",
        role: "mapped",
        px: 20,
        py: 50,
        x: 1,
        y: 5,
        file: TIMECOURSES,
        line: 2,
        error_low_px: [20, 60],
        error_high_px: [20, 40],
        y_text: "5.00",
      }),
      point({ series: "drug_urine", role: "mapped", px: 60, py: 30, x: 2, y: 7, file: TIMECOURSES, line: 3 }),
    ],
    unmatched: ["drug_feces"],
    layout: "overlay",
    points: [
      mapped({ series: "drug_plasma", line: 2, x: 1, y: 5, error_low: 4, error_high: 6, y_text: "5.00" }),
      mapped({ series: "drug_urine", line: 3, x: 2, y: 7 }),
      mapped({ series: "drug_feces", line: 4, x: 0, y: 1, error_low: 0.5, error_high: 1.5 }),
      mapped({ series: "drug_feces", line: 6, x: 1, y: 3.25, error_low: 2.5, error_high: 4 }),
    ],
    series: SERIES,
    log_x: false,
    log_y: false,
    ...changes,
  };
}

function trace(traces: OverlayTrace[], meta: string): OverlayTrace {
  const found = traces.find((entry) => entry.meta === meta);
  if (!found) throw new Error(`No trace ${meta} in ${traces.map((entry) => entry.meta).join(", ")}`);
  return found;
}

/** A file of the repository next to this test; jsdom's URL is not Node's, so `fs` takes its path. */
function repositoryFile(relative: string): string {
  return readFileSync(fileURLToPath(new URL(relative, import.meta.url).href), "utf8");
}

const DARK = { surface: "#192b31", text: "#ffffff", muted: "#aaaaaa", grid: "#333333", primary: "#79d5d6" };

describe("overlayTraces", () => {
  it("keeps the overlay in the pixels of the image, without an axis type", () => {
    const { layout } = overlayTraces(figure({ log_x: true, log_y: true }));
    expect(layout.xaxis.type).toBeUndefined();
    expect(layout.yaxis.type).toBeUndefined();
    expect(layout.yaxis.range).toEqual([100, 0]);
  });

  it("draws on the image in pixel space with hidden, fixed axes", () => {
    const { layout } = overlayTraces(figure());
    expect(layout.images).toEqual([
      expect.objectContaining({
        source: IMAGE_URL,
        xref: "x",
        yref: "y",
        x: 0,
        y: 0,
        sizex: 100,
        sizey: 100,
        sizing: "stretch",
        layer: "below",
      }),
    ]);
    expect(layout.xaxis).toEqual(expect.objectContaining({ range: [0, 100], visible: false, fixedrange: true }));
    expect(layout.yaxis).toEqual(expect.objectContaining({ range: [100, 0], visible: false, fixedrange: true }));
    expect(layout.showlegend).toBe(false);
    expect(layout.dragmode).toBe(false);
  });

  it("draws one trace per series and role: small dots for raw points, thin crosses for mapped rows", () => {
    const { traces } = overlayTraces(figure());
    const raw = trace(traces, "raw drug_plasma");
    expect(raw).toEqual(expect.objectContaining({ mode: "markers", x: [10, 20], y: [90, 50] }));
    expect(raw.marker?.symbol).toBe("circle");
    // A ring with contrast against the paper.
    expect(raw.marker?.line).toEqual({ width: 1, color: POINT_RING });
    const crosses = trace(traces, "mapped drug_plasma");
    expect(crosses).toEqual(expect.objectContaining({ mode: "markers", x: [20], y: [50] }));
    expect(crosses.marker?.symbol).toBe("x-thin-open");
    expect(trace(traces, "mapped drug_urine")).toEqual(expect.objectContaining({ x: [60], y: [30] }));
    expect(trace(traces, "raw-bar drug_plasma")).toEqual(expect.objectContaining({ x: [20], y: [40] }));
    expect(traces.map((entry) => entry.meta)).not.toContain("mapped drug_feces");
  });

  it("leaves the uid of a trace to Plotly, which puts it into CSS selectors", () => {
    expect(overlayTraces(figure()).traces.some((entry) => "uid" in entry)).toBe(false);
    expect(plotTraces(figure()).traces.some((entry) => "uid" in entry)).toBe(false);
  });

  it("draws smaller marks on an image shown smaller than its size, down to 60 %", () => {
    const full = overlayTraces(figure()).traces;
    const half = overlayTraces(figure(), null, undefined, 0.5).traces;
    expect(trace(full, "raw drug_plasma").marker?.size).toBe(7);
    expect(trace(full, "mapped drug_plasma").marker?.size).toBe(11);
    expect(trace(half, "raw drug_plasma").marker?.size).toBeCloseTo(4.2);
    expect(trace(half, "mapped drug_plasma").marker?.size).toBeCloseTo(6.6);
    expect(trace(half, "mapped drug_plasma").marker?.line?.width).toBe(1.5);
    expect(trace(half, "error drug_plasma").line?.width).toBe(1.5);
  });

  it("draws digitized error bar ends as short horizontal bars, as pkdb plot does", () => {
    const full = overlayTraces(figure()).traces;
    expect(trace(full, "raw-bar drug_plasma").marker).toEqual({
      symbol: "line-ew-open",
      size: 9,
      color: "#1a2b3c",
      line: { width: 2, color: "#1a2b3c" },
    });
    const half = trace(overlayTraces(figure(), null, undefined, 0.5).traces, "raw-bar drug_plasma");
    expect(half.marker?.size).toBeCloseTo(5.4);
    expect(half.marker?.line).toEqual({ width: 1.5, color: "#1a2b3c" });
  });

  it("draws the error bars of mapped rows as segments from their low to their high end", () => {
    const { traces } = overlayTraces(figure());
    const bars = trace(traces, "error drug_plasma");
    expect(bars).toEqual(expect.objectContaining({ mode: "lines", x: [20, 20, null], y: [60, 40, null] }));
    expect(bars.hoverinfo).toBe("skip");
    expect(traces.map((entry) => entry.meta)).not.toContain("error drug_urine");
  });

  it("starts the error bar of a mapped row at its cross where an end has no pixel, off a log axis", () => {
    const view = figure({
      overlay: [
        point({ series: "drug_plasma", role: "mapped", px: 20, py: 50, x: 1, y: 5, file: TIMECOURSES, line: 2, error_high_px: [20, 40] }),
        point({ series: "drug_urine", role: "mapped", px: 60, py: 30, x: 2, y: 7, file: TIMECOURSES, line: 3, error_low_px: [60, 45] }),
      ],
    });
    const { traces } = overlayTraces(view);
    expect(trace(traces, "error drug_plasma")).toEqual(expect.objectContaining({ x: [20, 20, null], y: [100, 40, null] }));
    expect(trace(traces, "error drug_urine")).toEqual(expect.objectContaining({ x: [60, 60, null], y: [45, 30, null] }));
  });

  it("draws no bar when both ends are off a log axis of the digitization", () => {
    const view = figure({
      overlay: [point({ series: "drug_plasma", role: "mapped", px: 20, py: 50, x: 1, y: 5, file: TIMECOURSES, line: 2 })],
    });
    expect(overlayTraces(view).traces.some((t) => t.meta === "error drug_plasma")).toBe(false);
  });

  it("colors a series and its error bars alike, in the colors of the source view", () => {
    const { traces } = overlayTraces(figure());
    expect(trace(traces, "raw drug_plasma").marker?.color).toBe("#1a2b3c");
    expect(trace(traces, "mapped drug_plasma").marker?.line?.color).toBe("#1a2b3c");
    expect(trace(traces, "raw-bar drug_plasma").marker?.color).toBe("#1a2b3c");
    expect(trace(traces, "error drug_plasma").line?.color).toBe("#1a2b3c");
    expect(trace(traces, "raw drug_urine").marker?.color).toBe("#2b3c4d");
  });

  it("keeps the colors for paper in the dark theme, as the marks sit on the image", () => {
    const { layout, traces } = overlayTraces(figure(), null, { dark: true, colors: DARK, font: "Inter, sans-serif" });
    expect(trace(traces, "raw drug_plasma").marker?.color).toBe("#1a2b3c");
    expect(layout.hoverlabel).toEqual(
      expect.objectContaining({ bgcolor: "#192b31", font: expect.objectContaining({ color: "#ffffff" }) }),
    );
    expect(trace(traces, "mapped drug_plasma").hoverlabel).toEqual(
      expect.objectContaining({ bgcolor: "#192b31", bordercolor: "#1a2b3c" }),
    );
  });

  it("fades the other series when a series is emphasized, and draws it on top", () => {
    const plain = overlayTraces(figure()).traces;
    expect(plain.every((entry) => entry.opacity === 1)).toBe(true);
    const { traces } = overlayTraces(figure(), "drug_plasma");
    for (const meta of ["raw drug_plasma", "raw-bar drug_plasma", "mapped drug_plasma", "error drug_plasma"])
      expect(trace(traces, meta).opacity).toBe(1);
    for (const meta of ["raw drug_urine", "mapped drug_urine"]) expect(trace(traces, meta).opacity).toBe(0.2);
    expect(traces.at(-1)?.meta).toBe("mapped drug_plasma");
  });

  it("does not fade anything for a series that the overlay does not draw", () => {
    const { traces } = overlayTraces(figure(), "drug_feces");
    expect(traces.every((entry) => entry.opacity === 1)).toBe(true);
  });

  it("names the file, line, series and values as printed on hover", () => {
    const { traces } = overlayTraces(figure());
    const crosses = trace(traces, "mapped drug_plasma");
    expect(crosses.customdata).toEqual([[TIMECOURSES, 2, "drug_plasma", "1", "5.00", false]]);
    expect(crosses.hovertemplate).toBe(
      "%{customdata[0]} line %{customdata[1]}<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>",
    );
    const raw = trace(traces, "raw drug_plasma");
    expect(raw.customdata).toEqual([
      [PROJECT, null, "drug_plasma", "0", "0.1", false],
      [PROJECT, null, "drug_plasma", "1", "5", false],
    ]);
    expect(raw.hovertemplate).toBe(
      "%{customdata[0]}<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>",
    );
    // A digitized error bar end says so, and its customdata says so to a click.
    const bar = trace(traces, "raw-bar drug_plasma");
    expect(bar.customdata).toEqual([[PROJECT, null, "drug_plasma", "1", "6", true]]);
    expect(bar.hovertemplate).toBe(
      "%{customdata[0]}<br>%{customdata[2]} (error bar)<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>",
    );
  });

  it("escapes markup in names, which Plotly would read as tags", () => {
    const view = figure({ overlay: [point({ series: "a<b>&c", role: "raw", px: 1, py: 1 })] });
    expect(trace(overlayTraces(view).traces, "raw a<b>&c").customdata?.[0]?.[2]).toBe("a&lt;b&gt;&amp;c");
  });
});

describe("plotTraces", () => {
  const plain = figure({
    digitization: null,
    overlay: [],
    layout: "side_by_side",
    unmatched: ["drug_plasma", "drug_urine", "drug_feces"],
  });

  it("plots the points of each series in table units, with error bars from the low to the high end", () => {
    const { traces, layout } = plotTraces(plain);
    expect(traces.map((entry) => entry.meta)).toEqual(["plot drug_plasma", "plot drug_urine", "plot drug_feces"]);
    const feces = trace(traces, "plot drug_feces");
    expect(feces).toEqual(expect.objectContaining({ mode: "lines+markers", x: [0, 1], y: [1, 3.25] }));
    expect(feces.error_y).toEqual(
      expect.objectContaining({ type: "data", symmetric: false, array: [0.5, 0.75], arrayminus: [0.5, 0.75], visible: true }),
    );
    expect(trace(traces, "plot drug_urine").error_y).toBeUndefined();
    expect(feces.customdata).toEqual([
      [TIMECOURSES, 4, "drug_feces", "0", "1", false, ""],
      [TIMECOURSES, 6, "drug_feces", "1", "3.25", false, ""],
    ]);
    expect(trace(traces, "plot drug_plasma").customdata?.[0]?.[4]).toBe("5.00");
    expect(feces.marker?.color).toBe("#3c4d5e");
    // The axes of the first series, from the source view.
    expect(layout.xaxis).toEqual(expect.objectContaining({ title: { text: "time (h)", font: { size: 11 } }, fixedrange: true }));
    expect(layout.yaxis).toEqual(expect.objectContaining({ title: { text: "concentration (mg/l) / amount (mg)", font: { size: 11 } }, fixedrange: true }));
  });

  it("plots only the series without a dataset of a digitized figure, with their labels", () => {
    const { traces, layout } = plotTraces(figure());
    expect(traces.map((entry) => entry.meta)).toEqual(["plot drug_feces"]);
    expect(trace(traces, "plot drug_feces").marker?.color).toBe("#3c4d5e");
    expect(layout.yaxis.title).toEqual({ text: "amount (mg)", font: { size: 11 } });
  });

  it("uses the dark steps of the colors on the dark surface", () => {
    const { traces, layout } = plotTraces(plain, null, { dark: true, colors: DARK, font: "Inter, sans-serif" });
    expect(trace(traces, "plot drug_plasma").marker?.color).toBe("#4d5e6f");
    expect(layout.paper_bgcolor).toBe("#192b31");
    expect(layout.font).toEqual({ color: "#ffffff", family: "Inter, sans-serif" });
    expect(layout.hoverlabel.font.family).toBe("Inter, sans-serif");
  });

  it("fades the other series when a series is emphasized", () => {
    const { traces } = plotTraces(plain, "drug_urine");
    expect(trace(traces, "plot drug_urine").opacity).toBe(1);
    expect(trace(traces, "plot drug_plasma").opacity).toBe(0.2);
    expect(trace(traces, "plot drug_feces").opacity).toBe(0.2);
    expect(traces.at(-1)?.meta).toBe("plot drug_urine");
  });

  it("draws scatter series as points only", () => {
    const view = figure({
      source: "Fig2",
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: ["age_vs_cmax"],
      points: [
        mapped({ series: "age_vs_cmax", kind: "scatters", file: "scatters_Fig2.tsv", line: 2, x: 30, y: 2 }),
        mapped({ series: "age_vs_cmax", kind: "scatters", file: "scatters_Fig2.tsv", line: 3, x: 40, y: 3 }),
      ],
      series: [{ name: "age_vs_cmax", color: "#123456", dark_color: "#654321", x_label: "age (yr)", y_label: "cmax (mg/l)" }],
    });
    const { traces, layout } = plotTraces(view);
    expect(trace(traces, "plot age_vs_cmax")).toEqual(expect.objectContaining({ mode: "markers", x: [30, 40], y: [2, 3] }));
    expect(layout.xaxis.title).toEqual({ text: "age (yr)", font: { size: 11 } });
    expect(layout.yaxis.title).toEqual({ text: "cmax (mg/l)", font: { size: 11 } });
  });

  it("draws outputs series as lines and markers by time, rings their problems and selects their rows", () => {
    const name = "all · D150 · concentration · caffeine · plasma";
    const OUTPUTS = "outputs_Fig2.tsv";
    const view = figure({
      source: "Fig2",
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: [name],
      points: [
        mapped({ series: name, kind: "outputs", file: OUTPUTS, line: 2, x: 0.5, y: 2.1 }),
        mapped({ series: name, kind: "outputs", file: OUTPUTS, line: 3, x: 1, y: 3 }),
      ],
      series: [{ name, color: "#123456", dark_color: "#654321", x_label: "time (hr)", y_label: "concentration (mg/l)" }],
    });
    const problem: ValidationIssue = {
      code: "negative_value",
      severity: "warning",
      message: "m",
      source: { file: OUTPUTS, row: 3, header: "mean" },
    };
    const { traces, layout } = plotTraces(view, null, undefined, null, { rowProblems: plottedProblems(view, [problem]) });
    const outputs = trace(traces, `plot ${name}`);
    expect(outputs).toEqual(expect.objectContaining({ mode: "lines+markers", x: [0.5, 1], y: [2.1, 3] }));
    expect(layout.xaxis.title).toEqual({ text: "time (hr)", font: { size: 11 } });
    expect(trace(traces, "problem warning")).toEqual(expect.objectContaining({ x: [1], y: [3] }));
    expect(rowAt(view, { customdata: outputs.customdata![1] })).toEqual({ file: OUTPUTS, line: 3 });
  });

  it("draws asymmetric error bars, and none at a point without an error bar", () => {
    const view = figure({
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: [],
      points: [
        // A gmean of 4 with a gsd of 2: from 2 to 8.
        mapped({ series: "drug_plasma", line: 1, x: 1, y: 4, error_low: 2, error_high: 8 }),
        mapped({ series: "drug_plasma", line: 2, x: 2, y: 5 }),
        mapped({ series: "drug_urine", line: 3, x: 1, y: 7 }),
      ],
    });
    const { traces } = plotTraces(view);
    const bars = trace(traces, "plot drug_plasma").error_y;
    expect(bars).toEqual(expect.objectContaining({ type: "data", symmetric: false, visible: true, thickness: 1.5, width: 4 }));
    // Plotly reads null as 0 and draws a cap at the point; NaN draws nothing.
    expect(bars?.array).toEqual([4, Number.NaN]);
    expect(bars?.arrayminus).toEqual([2, Number.NaN]);
    expect(trace(traces, "plot drug_urine").error_y).toBeUndefined();
  });

  it("passes an error bar that reaches 0 or below on to a log axis, which cuts it, and spans the decades of its ends above 0", () => {
    const view = figure({
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: [],
      points: [
        mapped({ series: "drug_plasma", line: 1, x: 1, y: 1, error_low: -0.5, error_high: 2.5 }),
        mapped({ series: "drug_plasma", line: 2, x: 2, y: 2, error_low: 1, error_high: 20 }),
      ],
    });
    const { traces, layout } = plotTraces(view, null, undefined, null, { scales: { x: "linear", y: "log" } });
    const bars = trace(traces, "plot drug_plasma");
    // The point at 1 stays; Plotly draws its bar down to the bottom of the plot and leaves out the cap there.
    expect(bars.y).toEqual([1, 2]);
    expect(bars.error_y?.arrayminus).toEqual([1.5, 1]);
    expect(bars.error_y?.array).toEqual([1.5, 18]);
    // 1 to 20 spans 1.3 decades with the ends of the bars; the points alone, 1 and 2, span 0.3.
    expect(layout.yaxis.dtick).toBe("D2");
  });
});

/** The contrast ratio of two colors `#rrggbb` (WCAG 2). */
function contrast(first: string, second: string): number {
  const luminance = (color: string) => {
    const [red, green, blue] = [1, 3, 5].map((start) => {
      const value = Number.parseInt(color.slice(start, start + 2), 16) / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * red! + 0.7152 * green! + 0.0722 * blue!;
  };
  const [light, dark] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (light! + 0.05) / (dark! + 0.05);
}

describe("the selected row", () => {
  const plain = figure({
    digitization: null,
    overlay: [],
    layout: "side_by_side",
    unmatched: ["drug_plasma", "drug_urine", "drug_feces"],
  });

  it("rings the mapped point of the selected row on the overlay, last", () => {
    const { traces } = overlayTraces(figure(), "drug_urine", undefined, 1, { file: TIMECOURSES, line: 2 });
    const last = traces.at(-1)!;
    expect(last.meta).toBe("selected");
    expect(last.x).toEqual([20]);
    expect(last.y).toEqual([50]);
    expect(last.marker?.symbol).toBe("circle-open");
    expect(last.hoverinfo).toBe("skip");
    expect(last.showlegend).toBe(false);
  });

  it("draws the ring in amber on a dark outline, which keep 3:1 on the paper and on the dark surface", () => {
    const { traces } = overlayTraces(figure(), null, undefined, 1, { file: TIMECOURSES, line: 2 });
    const [outline, ring] = traces.slice(-2);
    expect(outline!.meta).toBe("selected outline");
    expect(outline!.marker).toEqual({ symbol: "circle-open", size: 16, color: POINT_RING, line: { width: 5.5, color: POINT_RING } });
    expect([outline!.x, outline!.y]).toEqual([ring!.x, ring!.y]);
    const amber = ring!.marker!.line!.color as string;
    expect(ring!.marker!.line!.width).toBe(2.5);
    // The outline on the white paper and on the plot of the light theme, the ring on the dark surface.
    expect(contrast(POINT_RING, "#ffffff")).toBeGreaterThanOrEqual(3);
    expect(contrast(amber, "#192b31")).toBeGreaterThanOrEqual(3);
    expect(contrast(amber, POINT_RING)).toBeGreaterThanOrEqual(3);
  });

  it("rings the plotted point of the selected row", () => {
    const { traces } = plotTraces(plain, null, undefined, { file: TIMECOURSES, line: 6 });
    const last = traces.at(-1)!;
    expect(last.meta).toBe("selected");
    expect(last.x).toEqual([1]);
    expect(last.y).toEqual([3.25]);
  });

  it("adds no trace for a row without a point or without a selection", () => {
    expect(overlayTraces(figure()).traces.some((entry) => entry.meta === "selected")).toBe(false);
    expect(plotTraces(plain).traces.some((entry) => entry.meta === "selected")).toBe(false);
    const other = plotTraces(plain, null, undefined, { file: "subjects.tsv", line: 2 });
    expect(other.traces.some((entry) => entry.meta === "selected")).toBe(false);
    const overlay = overlayTraces(figure(), null, undefined, 1, { file: TIMECOURSES, line: 99 });
    expect(overlay.traces.some((entry) => entry.meta === "selected")).toBe(false);
  });

  it("draws the plot compact", () => {
    const { layout } = plotTraces(plain);
    expect(layout.height).toBe(220);
    expect(layout.margin).toEqual({ l: 48, r: 8, t: 8, b: 36, pad: 2 });
    expect(layout.xaxis.tickfont).toEqual({ size: 11 });
  });

  it("draws linear axes by default and sets the log type on the chosen axes", () => {
    const linear = plotTraces(plain).layout;
    expect([linear.xaxis.type, linear.yaxis.type]).toEqual(["linear", "linear"]);
    const log = plotTraces(plain, null, undefined, null, { scales: { x: "linear", y: "log" } }).layout;
    expect([log.xaxis.type, log.yaxis.type]).toEqual(["linear", "log"]);
    // A log axis labels full values (0.5), not bare mantissas; a linear axis keeps the default.
    expect(log.yaxis).toEqual(expect.objectContaining({ tickformat: "~g", exponentformat: "none" }));
    expect(log.xaxis.tickformat).toBeUndefined();
    // The titles and the compact axes stay.
    expect(log.yaxis).toEqual(expect.objectContaining({ title: { text: "concentration (mg/l) / amount (mg)", font: { size: 11 } }, fixedrange: true }));
  });

  it("leaves out the points at 0 or below of a log axis, with their error bars, hover texts and ring", () => {
    const scales: AxisScales = { x: "log", y: "linear" };
    // Line 4 of drug_feces is at x 0 and selected.
    const { traces } = plotTraces(plain, null, undefined, { file: TIMECOURSES, line: 4 }, { scales });
    const feces = trace(traces, "plot drug_feces");
    expect(feces.x).toEqual([1]);
    expect(feces.y).toEqual([3.25]);
    expect(feces.error_y?.array).toEqual([0.75]);
    expect(feces.error_y?.arrayminus).toEqual([0.75]);
    expect(feces.customdata).toEqual([[TIMECOURSES, 6, "drug_feces", "1", "3.25", false, ""]]);
    expect(traces.some((entry) => entry.meta === "selected")).toBe(false);
    expect(pointsOffScale(plain, scales)).toBe(1);
    expect(pointsOffScale(plain, { x: "linear", y: "log" })).toBe(0);
  });

  it("counts a point once when both log axes leave it out", () => {
    const view = figure({
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: [],
      points: [
        mapped({ series: "drug_plasma", line: 1, x: 0, y: 0 }),
        mapped({ series: "drug_plasma", line: 2, x: -1, y: 2 }),
        mapped({ series: "drug_plasma", line: 3, x: 1, y: -0.5 }),
        mapped({ series: "drug_plasma", line: 4, x: 2, y: 3 }),
      ],
    });
    expect(pointsOffScale(view, { x: "linear", y: "linear" })).toBe(0);
    expect(pointsOffScale(view, { x: "log", y: "linear" })).toBe(2);
    expect(pointsOffScale(view, { x: "linear", y: "log" })).toBe(2);
    expect(pointsOffScale(view, { x: "log", y: "log" })).toBe(3);
    expect(trace(plotTraces(view, null, undefined, null, { scales: { x: "log", y: "log" } }).traces, "plot drug_plasma").x).toEqual([2]);
  });

  it("leaves out every point when all are at 0 or below and keeps the series", () => {
    const view = figure({
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: [],
      points: [mapped({ series: "drug_plasma", line: 1, x: 0, y: 0 }), mapped({ series: "drug_plasma", line: 2, x: 1, y: 0 })],
    });
    const { traces, layout } = plotTraces(view, null, undefined, null, { scales: { x: "linear", y: "log" } });
    expect(trace(traces, "plot drug_plasma")).toEqual(expect.objectContaining({ x: [], y: [], customdata: [] }));
    expect(layout.yaxis.title).toEqual({ text: "concentration (mg/l)", font: { size: 11 } });
    expect(pointsOffScale(view, { x: "linear", y: "log" })).toBe(2);
  });

  it("takes the default scales from the digitization, else linear", () => {
    expect(digitizedScales(plain)).toEqual({ x: "linear", y: "linear" });
    expect(digitizedScales({ ...plain, log_y: true })).toEqual({ x: "linear", y: "log" });
    expect(digitizedScales({ ...plain, log_x: true, log_y: true })).toEqual({ x: "log", y: "log" });
    expect(logAxes({ x: "log", y: "log" })).toEqual(["x", "y"]);
    expect(logAxes({ x: "linear", y: "log" })).toEqual(["y"]);
  });
});

describe("problems in the plot", () => {
  const plain = figure({
    digitization: null,
    overlay: [],
    layout: "side_by_side",
    unmatched: ["drug_plasma", "drug_urine", "drug_feces"],
  });
  const MESSAGE = "sd is 0.3677, but error_bar 0.5452 (se) with count 9 of enalapril implies sd 0.4934.";

  function problem(line: number, severity: ValidationIssue["severity"] = "warning", changes: Partial<ValidationIssue> = {}): ValidationIssue {
    return { code: "inconsistent_statistics", severity, message: MESSAGE, source: { file: TIMECOURSES, row: line, header: "sd" }, ...changes };
  }

  it("rings the points of rows with problems in the color of their worst severity, below the ring of the selected row", () => {
    const { traces } = plotTraces(plain, null, undefined, { file: TIMECOURSES, line: 6 }, {
      rowProblems: plottedProblems(plain, [
        problem(4),
        problem(6),
        problem(6, "error", { code: "missing_value", message: "mean is missing." }),
      ]),
    });
    expect(traces.map((entry) => entry.meta)).toEqual([
      "plot drug_plasma",
      "plot drug_urine",
      "plot drug_feces",
      "problem warning",
      "problem error",
      "selected outline",
      "selected",
    ]);
    const warning = trace(traces, "problem warning");
    expect([warning.x, warning.y]).toEqual([[0], [1]]);
    expect(warning.marker).toEqual({
      symbol: "circle-open",
      size: 28,
      color: PROBLEM_COLORS.light.warning,
      opacity: [1],
      line: { width: 2, color: PROBLEM_COLORS.light.warning, dash: "dash" },
    });
    // The ring takes no hover, so that the point below it shows its label and takes the click.
    expect(warning.hoverinfo).toBe("skip");
    expect(warning.showlegend).toBe(false);
    const error = trace(traces, "problem error");
    expect([error.x, error.y]).toEqual([[1], [3.25]]);
    expect(error.marker?.color).toBe(PROBLEM_COLORS.light.error);
    // The warning ring is dashed and the error ring solid: they differ by more than color.
    expect(error.marker?.line).toEqual({ width: 2, color: PROBLEM_COLORS.light.error });
  });

  it("draws the ring of a problem thin and outside the ring of the selected row, so that the two differ and both show", () => {
    const { traces } = plotTraces(plain, null, undefined, { file: TIMECOURSES, line: 4 }, { rowProblems: plottedProblems(plain, [problem(4)]) });
    const ring = trace(traces, "problem warning").marker!;
    const outline = trace(traces, "selected outline").marker!;
    const selected = trace(traces, "selected").marker!;
    // A ring of size s and width w covers the radii s/2 - w/2 to s/2 + w/2.
    expect(ring.size / 2 - ring.line!.width / 2).toBeGreaterThan(outline.size / 2 + outline.line!.width / 2);
    expect(ring.line!.width).toBeLessThan(selected.line!.width);
    expect([ring.symbol, selected.symbol]).toEqual(["circle-open", "circle-open"]);
  });

  it("rings in the colors of the dark theme, which keep 3:1 on the surface of each theme", () => {
    const dark = { dark: true, colors: DARK, font: "sans-serif" };
    expect(trace(plotTraces(plain, null, dark, null, { rowProblems: plottedProblems(plain, [problem(4)]) }).traces, "problem warning").marker?.color).toBe(
      PROBLEM_COLORS.dark.warning,
    );
    for (const severity of ["error", "warning"] as const) {
      expect(contrast(PROBLEM_COLORS.light[severity], "#ffffff")).toBeGreaterThanOrEqual(3);
      expect(contrast(PROBLEM_COLORS.dark[severity], "#192b31")).toBeGreaterThanOrEqual(3);
    }
  });

  it("fades the ring of a faded series with it", () => {
    const { traces } = plotTraces(plain, "drug_plasma", undefined, null, { rowProblems: plottedProblems(plain, [problem(4)]) });
    expect(trace(traces, "problem warning").marker?.opacity).toEqual([FADED]);
  });

  it("adds the problems of a row to the hover label of its point: severity, code and the message in lines", () => {
    const { traces } = plotTraces(plain, null, undefined, null, { rowProblems: plottedProblems(plain, [problem(4)]) });
    const feces = trace(traces, "plot drug_feces");
    expect(feces.hovertemplate).toBe(
      "%{customdata[0]} line %{customdata[1]}<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}%{customdata[6]}<extra></extra>",
    );
    expect(feces.customdata?.[0]?.[6]).toBe(
      "<br><br>Warning · inconsistent_statistics<br>sd is 0.3677, but error_bar 0.5452 (se) with count 9 of<br>enalapril implies sd 0.4934.",
    );
    expect(feces.customdata?.[1]?.[6]).toBe("");
  });

  it("lists at most five problems of a row in its hover label and counts the others", () => {
    const issues = Array.from({ length: 7 }, (_, index) => problem(4, "warning", { code: `code_${index}`, message: "Short." }));
    const text = problemHover(issues);
    expect(text.match(/Warning · code_/g)).toHaveLength(5);
    // Plotly sets a style attribute for a tag such as bold, which the content security policy blocks.
    expect(text.replaceAll("<br>", "")).not.toContain("<");
    expect(text.endsWith("<br>and 2 more")).toBe(true);
  });

  /** The lines of the problems in a hover label, after the blank line that starts them. */
  function hoverLines(text: string): string[] {
    expect(text.startsWith("<br><br>")).toBe(true);
    return text.slice("<br><br>".length).split("<br>");
  }

  it("keeps the problems of a row within eight lines of its hover label, so that the whole label fits the plot", () => {
    // A message of two lines each, as real messages wrap.
    const long = (index: number) =>
      `mean ${index} at 4 hr lies 61.3 pixels from the nearest point of dataset 'caf_plasma_100mg' in Demo2020_Fig1.wpd.json`;
    const issues = Array.from({ length: 7 }, (_, index) => problem(4, "warning", { code: `code_${index}`, message: long(index) }));
    expect(wrapText(long(0))).toHaveLength(2);
    const lines = hoverLines(problemHover(issues));
    expect(lines.length).toBeLessThanOrEqual(8);
    // The severity and the code of five problems, the message of the first as it fits, and the count of the others.
    expect(lines.filter((line) => line.startsWith("Warning · code_"))).toHaveLength(5);
    expect(lines.slice(0, 3)).toEqual(["Warning · code_0", ...wrapText(long(0))]);
    expect(lines.at(-1)).toBe("and 2 more");

    // Fewer problems leave room for more messages, in their order.
    const three = hoverLines(problemHover(issues.slice(0, 3)));
    expect(three.length).toBeLessThanOrEqual(8);
    expect(three.filter((line) => line.startsWith("mean "))).toEqual([wrapText(long(0))[0], wrapText(long(1))[0]]);
    expect(three.at(-1)).toBe("Warning · code_2");
  });

  it("aligns the lines of the hover label of the data plot to the left", () => {
    const { traces } = plotTraces(plain, null, undefined, null, { rowProblems: plottedProblems(plain, [problem(4)]) });
    expect(trace(traces, "plot drug_feces").hoverlabel?.align).toBe("left");
  });

  it("escapes markup in the problems, which Plotly would read as tags", () => {
    expect(problemHover([problem(4, "error", { code: "a<b>", message: "mean <none> & more" })])).toBe(
      "<br><br>Error · a&lt;b&gt;<br>mean &lt;none&gt; &amp; more",
    );
  });

  it("wraps a message at spaces into lines of at most 60 characters", () => {
    expect(wrapText(MESSAGE)).toEqual(["sd is 0.3677, but error_bar 0.5452 (se) with count 9 of", "enalapril implies sd 0.4934."]);
    expect(wrapText("a ".repeat(3) + "x".repeat(70))).toEqual(["a a a", "x".repeat(70)]);
  });

  it("rings nothing for problems of rows that the plot does not draw, of other files, or without a line", () => {
    const { traces } = plotTraces(plain, null, undefined, null, {
      rowProblems: plottedProblems(plain, [
        problem(99),
        { ...problem(4), source: { file: "outputs_Fig1.tsv", row: 4 } },
        { ...problem(4), source: { file: TIMECOURSES } },
        { ...problem(4), source: null },
      ]),
    });
    expect(traces.some((entry) => entry.meta.startsWith("problem"))).toBe(false);
  });

  it("selects the row of a ringed point on a click, as the point under the ring takes it", () => {
    const { traces } = plotTraces(plain, null, undefined, null, { rowProblems: plottedProblems(plain, [problem(4)]) });
    expect(rowAt(plain, { customdata: trace(traces, "plot drug_feces").customdata![0] })).toEqual({ file: TIMECOURSES, line: 4 });
  });

  it("keys and rings only the problems of the points that the log axes draw", () => {
    // Line 4 of drug_feces is at x 0, which a log x axis leaves out; line 6 is at x 1.
    const scales: AxisScales = { x: "log", y: "linear" };
    const problems = plottedProblems(plain, [problem(4), problem(6, "error")], scales);
    expect([...problems.keys()]).toEqual([`${TIMECOURSES}:6`]);
    expect([...plottedProblems(plain, [problem(4), problem(6, "error")]).keys()]).toEqual([`${TIMECOURSES}:4`, `${TIMECOURSES}:6`]);
    const { traces } = plotTraces(plain, null, undefined, null, { scales, rowProblems: plottedProblems(plain, [problem(4), problem(6)]) });
    // Even with the problems of all plotted rows, a ring needs a drawn point.
    const ring = trace(traces, "problem warning");
    expect([ring.x, ring.y]).toEqual([[1], [3.25]]);
  });

  it("rings nothing on the overlay of the image", () => {
    expect(overlayTraces(figure()).traces.some((entry) => entry.meta.startsWith("problem"))).toBe(false);
  });
});

describe("the ticks of a log axis", () => {
  /** A plot of drug_plasma at x 1, 2, 3 and so on, at the values `ys` with the error bar ends `ends`. */
  function plotOf(ys: number[], ends: ([number, number] | null)[] = []): SourceView {
    return figure({
      digitization: null,
      overlay: [],
      layout: "side_by_side",
      unmatched: [],
      points: ys.map((y, index) => {
        const [low, high] = ends[index] ?? [null, null];
        return mapped({ series: "drug_plasma", line: index + 1, x: index + 1, y, error_low: low, error_high: high });
      }),
    });
  }
  const LOG: AxisScales = { x: "log", y: "log" };

  it.each([
    [0, { nticks: 4 }],
    [0.5, { nticks: 4 }],
    [0.74, { nticks: 4 }],
    [0.75, { dtick: "D2" }],
    [1, { dtick: "D2" }],
    [1.3, { dtick: "D2" }],
    [2, { dtick: "D2" }],
    [2.5, { dtick: "D2" }],
    [2.6, { dtick: 1 }],
    [3, { dtick: 1 }],
    [4, { dtick: 1 }],
    [4.1, { dtick: 2 }],
    [5, { dtick: 2 }],
    [9, { dtick: 3 }],
  ])("ticks a log axis over %s decades with %o", (span, ticks) => {
    expect(logTicks(span)).toEqual(ticks);
  });

  it("chooses the ticks of each log axis by the span of its drawn values", () => {
    // y from 1 to 20 spans 1.3 decades, where Plotly would label every digit; x from 1 to 4, 0.6.
    const view = plotOf([1, 2, 5, 20]);
    const { layout } = plotTraces(view, null, undefined, null, { scales: LOG });
    expect(layout.yaxis).toEqual(expect.objectContaining({ dtick: "D2", tickformat: "~g", exponentformat: "none" }));
    expect(layout.yaxis.nticks).toBeUndefined();
    expect(layout.xaxis).toEqual(expect.objectContaining({ nticks: 4, tickformat: "~g", exponentformat: "none" }));
    expect(layout.xaxis.dtick).toBeUndefined();
    // A linear axis keeps the ticks of Plotly.
    const linear = plotTraces(view, null, undefined, null, { scales: { x: "linear", y: "linear" } }).layout;
    expect([linear.xaxis.dtick, linear.xaxis.nticks, linear.yaxis.dtick, linear.yaxis.nticks]).toEqual([
      undefined,
      undefined,
      undefined,
      undefined,
    ]);
  });

  it("counts the ends of the error bars above 0 and leaves out the points at 0 or below", () => {
    // 1 to 5 spans 0.7 decades; the point at 0 is not drawn on the log axis.
    expect(plotTraces(plotOf([1, 5, 0]), null, undefined, null, { scales: LOG }).layout.yaxis.nticks).toBe(4);
    // The error bar of 5 to 20 also reaches down to -10, which a log axis does not draw: 1 to 20.
    const { layout } = plotTraces(plotOf([1, 5, 0], [null, [-10, 20], [-1000, 1000]]), null, undefined, null, { scales: LOG });
    expect(layout.yaxis.dtick).toBe("D2");
    // Without values above 0, a log axis has nothing to span.
    expect(plotTraces(plotOf([0, -1]), null, undefined, null, { scales: LOG }).layout.yaxis).toEqual(
      expect.objectContaining({ nticks: 4 }),
    );
  });
});

describe("rowAt", () => {
  const PLASMA = [PROJECT, null, "drug_plasma", "1", "5"];

  it("selects the row of a mapped point", () => {
    expect(rowAt(figure(), { customdata: [TIMECOURSES, 2, "drug_plasma", "1", "5"], x: 20, y: 50 })).toEqual({
      file: TIMECOURSES,
      line: 2,
    });
  });

  it("selects the mapped row under a digitized point, which Plotly prefers on hover", () => {
    expect(rowAt(figure(), { customdata: PLASMA, x: 20, y: 50 })).toEqual({ file: TIMECOURSES, line: 2 });
    expect(rowAt(figure(), { customdata: [PROJECT, null, "drug_urine", "2", "7"], x: 60, y: 31 })).toEqual({
      file: TIMECOURSES,
      line: 3,
    });
  });

  it("selects nothing for a digitized point without a mapped row under it", () => {
    expect(rowAt(figure(), { customdata: PLASMA, x: 10, y: 90 })).toBeNull();
    // A mapped point of another series does not count.
    expect(rowAt(figure(), { customdata: [PROJECT, null, "drug_urine", "1", "5"], x: 20, y: 50 })).toBeNull();
    expect(rowAt(figure(), { customdata: "other", x: 20, y: 50 })).toBeNull();
    expect(rowAt(figure(), {})).toBeNull();
  });

  it("selects the mapped row whose error bar ends, at either end, at a clicked digitized error bar end", () => {
    const bar = trace(overlayTraces(figure()).traces, "raw-bar drug_plasma").customdata?.[0];
    expect(rowAt(figure(), { customdata: bar, x: 20, y: 40 })).toEqual({ file: TIMECOURSES, line: 2 });
    // Within the radius of a digitized point of the end of the error bar.
    expect(rowAt(figure(), { customdata: bar, x: 22, y: 41 })).toEqual({ file: TIMECOURSES, line: 2 });
    // The low end counts too: a figure may digitize the lower ends of its error bars.
    expect(rowAt(figure(), { customdata: bar, x: 20, y: 61 })).toEqual({ file: TIMECOURSES, line: 2 });
  });

  it("selects nothing for a digitized error bar end without a mapped error bar at it", () => {
    const bar = trace(overlayTraces(figure()).traces, "raw-bar drug_plasma").customdata?.[0];
    expect(rowAt(figure(), { customdata: bar, x: 20, y: 30 })).toBeNull();
    // The cross of the row does not count: the end of its error bar is 10 pixels away.
    expect(rowAt(figure(), { customdata: bar, x: 20, y: 50 })).toBeNull();
    // drug_urine has no error bar.
    expect(rowAt(figure(), { customdata: [PROJECT, null, "drug_urine", "2", "7", true], x: 60, y: 30 })).toBeNull();
  });

  it("reads names back from the escaped customdata", () => {
    const view = figure({
      overlay: [
        point({ series: "a<b>", role: "raw", px: 5, py: 5 }),
        point({ series: "a<b>", role: "mapped", px: 5, py: 6, file: TIMECOURSES, line: 7 }),
      ],
    });
    const raw = trace(overlayTraces(view).traces, "raw a<b>").customdata?.[0];
    expect(rowAt(view, { customdata: raw, x: 5, y: 5 })).toEqual({ file: TIMECOURSES, line: 7 });
  });
});

describe("the parts around the plot", () => {
  it("draws on the image when the source view says so and the image is known", () => {
    expect(drawsOnImage(figure())).toBe(true);
    expect(drawsOnImage(figure({ layout: "side_by_side" }))).toBe(false);
    expect(drawsOnImage(figure({ image: null, image_url: null, image_size: null }))).toBe(false);
  });

  it("plots every series of the points beside an image that the overlay does not draw on", () => {
    expect(plottedSeries(figure())).toEqual(["drug_feces"]);
    expect(plottedSeries(figure({ layout: "side_by_side" }))).toEqual(["drug_plasma", "drug_urine", "drug_feces"]);
  });

  it("lists the series of the legend with their colors", () => {
    expect(legendEntries(figure(), "overlay", false)).toEqual([
      { series: "drug_plasma", color: "#1a2b3c" },
      { series: "drug_urine", color: "#2b3c4d" },
    ]);
    expect(legendEntries(figure(), "overlay", true)[0]?.color).toBe("#1a2b3c");
    expect(legendEntries(figure(), "plot", true)).toEqual([{ series: "drug_feces", color: "#6f7081" }]);
  });

  it("tabulates the points of the overlay and of the plot as printed", () => {
    expect(dataRows(figure(), "overlay")).toEqual([
      { series: "drug_plasma", kind: "Digitized", x: "0", y: "0.1", file: PROJECT, line: null },
      { series: "drug_plasma", kind: "Digitized", x: "1", y: "5", file: PROJECT, line: null },
      { series: "drug_plasma", kind: "Digitized error bar", x: "1", y: "6", file: PROJECT, line: null },
      { series: "drug_urine", kind: "Digitized", x: "2", y: "7", file: PROJECT, line: null },
      { series: "drug_plasma", kind: "Mapped", x: "1", y: "5.00", file: TIMECOURSES, line: 2 },
      { series: "drug_urine", kind: "Mapped", x: "2", y: "7", file: TIMECOURSES, line: 3 },
    ]);
    expect(dataRows(figure(), "plot")).toEqual([
      { series: "drug_feces", kind: "Mapped", x: "0", y: "1", file: TIMECOURSES, line: 4 },
      { series: "drug_feces", kind: "Mapped", x: "1", y: "3.25", file: TIMECOURSES, line: 6 },
    ]);
  });

  it("rings digitized points as pkdb plot does", () => {
    const colors = repositoryFile("../../../python/src/pkdb/studyformat/colors.py");
    expect(colors).toContain(`POINT_RING = "${POINT_RING}"`);
  });
});

describe("loadNoncedPlotly", () => {
  /** The style element that the map library inside Plotly creates when Plotly is imported. */
  const MAP_STYLE = "9f215cf04c5486422605d13261cb87401f4e7763b6296af81e98efbc0130da53";

  beforeEach(() => {
    document.head.replaceChildren();
    vi.resetModules();
    loader.load.mockReset();
  });

  function withNonce(nonce: string): void {
    const meta = document.createElement("meta");
    meta.setAttribute("property", "csp-nonce");
    meta.nonce = nonce;
    document.head.append(meta);
  }

  it("creates Plotly's global style element with the nonce before the first import, once", async () => {
    withNonce("n0nce");
    const engine = { react: vi.fn() };
    let styleAtImport: Element | null = null;
    loader.load.mockImplementation(async () => {
      styleAtImport = document.getElementById("plotly.js-style-global");
      return engine;
    });
    const { loadNoncedPlotly } = await import("../../src/curation-app/plotly");
    await expect(loadNoncedPlotly()).resolves.toBe(engine);
    await loadNoncedPlotly();
    const styles = document.head.querySelectorAll("style#plotly\\.js-style-global");
    expect(styles).toHaveLength(1);
    expect(styleAtImport).toBe(styles[0]);
    expect(styles[0]?.getAttribute("nonce")).toBe("n0nce");
  });

  it("creates the style element of the map library, which Plotly would create without the nonce", async () => {
    withNonce("n0nce");
    loader.load.mockResolvedValue({});
    const { loadNoncedPlotly } = await import("../../src/curation-app/plotly");
    await loadNoncedPlotly();
    await loadNoncedPlotly();
    expect(document.head.querySelectorAll(`style[id="${MAP_STYLE}"]`)).toHaveLength(1);
    expect(document.getElementById(MAP_STYLE)?.getAttribute("nonce")).toBe("n0nce");
  });

  it("keeps an existing global style element", async () => {
    const existing = document.createElement("style");
    existing.id = "plotly.js-style-global";
    document.head.append(existing);
    loader.load.mockResolvedValue({});
    const { loadNoncedPlotly } = await import("../../src/curation-app/plotly");
    await loadNoncedPlotly();
    expect(document.head.querySelectorAll("style#plotly\\.js-style-global")).toHaveLength(1);
    expect(document.getElementById("plotly.js-style-global")).toBe(existing);
  });

  it("knows every style element that the bundled Plotly creates", async () => {
    // A new version of Plotly may create another one, which the CSP would refuse.
    const bundle = repositoryFile("../../node_modules/plotly.js-dist-min/plotly.min.js");
    expect(bundle.match(/createElement\("style"\)/g)).toHaveLength(2);
    // Style attributes, which the CSP refuses, are set only by traces that the app does not draw:
    // the two fills of a color bar, the CSS test of image traces, and the fast rendering and the
    // flipped axes of heatmap and image traces.
    expect(bundle.match(/\.attr\("style"/g)).toHaveLength(5);
    expect(bundle).toContain('"plotly.js-style-"+');
    const { PLOTLY_STYLES } = await import("../../src/curation-app/plotly");
    for (const id of PLOTLY_STYLES.slice(1)) expect(bundle).toContain(`document.getElementById("${id}")`);
  });

  it("imports again after a failed import", async () => {
    loader.load.mockRejectedValueOnce(new TypeError("Failed to fetch dynamically imported module")).mockResolvedValue({});
    const { loadNoncedPlotly, plotlyImport } = await import("../../src/curation-app/plotly");
    await expect(loadNoncedPlotly()).rejects.toThrow("Failed to fetch");
    expect(plotlyImport.state).toBe("failed");
    await expect(loadNoncedPlotly()).resolves.toEqual({});
    expect(loader.load).toHaveBeenCalledTimes(2);
    expect(plotlyImport.state).toBe("loaded");
  });

  it("knows an import that failed again after a retry, which a browser keeps until a reload", async () => {
    loader.load.mockRejectedValue(new TypeError("Failed to fetch dynamically imported module"));
    const { loadNoncedPlotly, plotlyImport, retryPlotly } = await import("../../src/curation-app/plotly");
    // Two plots that import at once fail once.
    await Promise.allSettled([loadNoncedPlotly(), loadNoncedPlotly()]);
    expect(plotlyImport.state).toBe("failed");
    expect(plotlyImport.attempt).toBe(0);
    retryPlotly();
    expect(plotlyImport.attempt).toBe(1);
    await expect(loadNoncedPlotly()).rejects.toThrow("Failed to fetch");
    expect(plotlyImport.state).toBe("failed again");
  });
});

describe("many series", () => {
  const names = Array.from({ length: 45 }, (_, index) => `s${index}`);

  it("caps a list at the limit and counts the rest", () => {
    expect(LEGEND_LIMIT).toBe(20);
    expect(capped(names)).toEqual({ shown: names.slice(0, 20), more: 25 });
    expect(capped(names.slice(0, 20))).toEqual({ shown: names.slice(0, 20), more: 0 });
    expect(capped(["a"], 3)).toEqual({ shown: ["a"], more: 0 });
  });

  it("titles an axis with the shared title, else the distinct ones, at most three", () => {
    expect(axisTitle(["time (h)", "time (h)", null], "x")).toBe("time (h)");
    expect(axisTitle(["a (kg)", "b (%)", "a (kg)"], "y")).toBe("a (kg) / b (%)");
    expect(axisTitle(["a", "b", "c", "d", "e"], "y")).toBe("a / b / c and 2 more");
    expect(axisTitle([null], "y")).toBe("y");
    expect(axisTitle([], "x")).toBe("x");
  });

  it("titles the axes of a plot of series with different measurements by all of them", () => {
    const view = {
      ...figure(),
      series: [
        { name: "w", color: "#111111", dark_color: "#222222", x_label: "time (wk)", y_label: "weight change (kg)" },
        { name: "h", color: "#333333", dark_color: "#444444", x_label: "time (wk)", y_label: "hba1c (percent)" },
      ],
      points: [mapped({ series: "w", line: 1, x: 1, y: 1 }), mapped({ series: "h", line: 2, x: 1, y: 2 })],
      unmatched: ["w", "h"],
      overlay: [],
    } as SourceView;
    const layout = plotTraces(view).layout;
    expect(layout.xaxis.title).toEqual({ text: "time (wk)", font: { size: 11 } });
    expect(layout.yaxis.title).toEqual({ text: "weight change (kg) / hba1c (percent)", font: { size: 11 } });
  });
});
