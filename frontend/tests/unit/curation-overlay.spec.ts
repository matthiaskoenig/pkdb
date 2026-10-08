import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { OverlayPoint, SourcePoint, SourceSeries, SourceView } from "../../src/curation-app/api/types";
import {
  dataRows,
  drawsOnImage,
  legendEntries,
  overlayTraces,
  plotTraces,
  plottedSeries,
  POINT_RING,
  rowAt,
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
    error_px: null,
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
    error_bar: null,
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
        error_px: [20, 40],
        y_text: "5.00",
      }),
      point({ series: "drug_urine", role: "mapped", px: 60, py: 30, x: 2, y: 7, file: TIMECOURSES, line: 3 }),
    ],
    unmatched: ["drug_feces"],
    layout: "overlay",
    points: [
      mapped({ series: "drug_plasma", line: 2, x: 1, y: 5, error_bar: 6, y_text: "5.00" }),
      mapped({ series: "drug_urine", line: 3, x: 2, y: 7 }),
      mapped({ series: "drug_feces", line: 4, x: 0, y: 1, error_bar: 1.5 }),
      mapped({ series: "drug_feces", line: 6, x: 1, y: 3.25, error_bar: 2.5 }),
    ],
    series: SERIES,
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

  it("draws the error bars of mapped rows as segments that end at error_px", () => {
    const { traces } = overlayTraces(figure());
    const bars = trace(traces, "error drug_plasma");
    expect(bars).toEqual(expect.objectContaining({ mode: "lines", x: [20, 20, null], y: [50, 40, null] }));
    expect(bars.hoverinfo).toBe("skip");
    expect(traces.map((entry) => entry.meta)).not.toContain("error drug_urine");
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

  it("plots the points of each series in table units, with error bars to the error bar end", () => {
    const { traces, layout } = plotTraces(plain);
    expect(traces.map((entry) => entry.meta)).toEqual(["plot drug_plasma", "plot drug_urine", "plot drug_feces"]);
    const feces = trace(traces, "plot drug_feces");
    expect(feces).toEqual(expect.objectContaining({ mode: "lines+markers", x: [0, 1], y: [1, 3.25] }));
    expect(feces.error_y).toEqual(expect.objectContaining({ type: "data", array: [0.5, 0.75], visible: true }));
    expect(trace(traces, "plot drug_urine").error_y).toBeUndefined();
    expect(feces.customdata).toEqual([
      [TIMECOURSES, 4, "drug_feces", "0", "1", false],
      [TIMECOURSES, 6, "drug_feces", "1", "3.25", false],
    ]);
    expect(trace(traces, "plot drug_plasma").customdata?.[0]?.[4]).toBe("5.00");
    expect(feces.marker?.color).toBe("#3c4d5e");
    // The axes of the first series, from the source view.
    expect(layout.xaxis).toEqual(expect.objectContaining({ title: { text: "time (h)" }, fixedrange: true }));
    expect(layout.yaxis).toEqual(expect.objectContaining({ title: { text: "concentration (mg/l)" }, fixedrange: true }));
  });

  it("plots only the series without a dataset of a digitized figure, with their labels", () => {
    const { traces, layout } = plotTraces(figure());
    expect(traces.map((entry) => entry.meta)).toEqual(["plot drug_feces"]);
    expect(trace(traces, "plot drug_feces").marker?.color).toBe("#3c4d5e");
    expect(layout.yaxis.title).toEqual({ text: "amount (mg)" });
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
    expect(layout.xaxis.title).toEqual({ text: "age (yr)" });
    expect(layout.yaxis.title).toEqual({ text: "cmax (mg/l)" });
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

  it("selects the mapped row whose error bar ends at a clicked digitized error bar end", () => {
    const bar = trace(overlayTraces(figure()).traces, "raw-bar drug_plasma").customdata?.[0];
    expect(rowAt(figure(), { customdata: bar, x: 20, y: 40 })).toEqual({ file: TIMECOURSES, line: 2 });
    // Within the radius of a digitized point of the end of the error bar.
    expect(rowAt(figure(), { customdata: bar, x: 22, y: 41 })).toEqual({ file: TIMECOURSES, line: 2 });
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
