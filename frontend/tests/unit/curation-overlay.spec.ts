import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MappedTable, OverlayPoint, SourceView } from "../../src/curation-app/api/types";
import {
  baseSeries,
  dataRows,
  isCalibrated,
  legendEntries,
  mappedPoints,
  overlayTraces,
  plotTraces,
  plottedSeries,
  rowAt,
  SERIES_COLORS,
  type OverlayTrace,
} from "../../src/curation-app/overlay";

const loader = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("../../src/features/plots/plotly", () => ({ loadPlotly: loader.load }));

const IMAGE_URL = "/local/studies/caffeine/Example/files/Example_Fig1.png";
const TIMECOURSES = "timecourses_Fig1.tsv";
const PROJECT = "Example_Fig1.wpd.json";

function point(changes: Partial<OverlayPoint> & Pick<OverlayPoint, "series" | "role">): OverlayPoint {
  return { px: 0, py: 0, x: 0, y: 0, file: PROJECT, line: null, error_px: null, ...changes };
}

const HEADER = ["study", "source", "label", "time", "time_unit", "measurement", "mean", "median", "unit", "error_bar"];
const timecourses: MappedTable = {
  file: TIMECOURSES,
  kind: "timecourses",
  header: HEADER,
  rows: [
    [2, ["Example", "Fig1", "drug_plasma", "1", "h", "concentration", "5", "", "mg/l", "6"]],
    [3, ["Example", "Fig1", "drug_urine", "2", "h", "concentration", "7", "", "mg/l", ""]],
    [4, ["Example", "Fig1", "drug_feces", "0", "h", "concentration", "1", "", "mg/l", "1.5"]],
    // Not reported: not a point, as in the library.
    [5, ["Example", "Fig1", "drug_feces", "NR", "h", "concentration", "2", "", "mg/l", ""]],
    // The median when there is no mean.
    [6, ["Example", "Fig1", "drug_feces", "1", "h", "concentration", "", "3.25", "mg/l", "2.5"]],
  ],
};

/** A digitized figure of 100 x 100 pixels with two series, an error bar and a series without dataset. */
function figure(changes: Partial<SourceView> = {}): SourceView {
  return {
    source: "Fig1",
    image: "Example_Fig1.png",
    image_url: IMAGE_URL,
    image_size: [100, 100],
    raw_grid: null,
    digitization: PROJECT,
    mapped: [timecourses],
    overlay: [
      point({ series: "drug_plasma", role: "raw", px: 10, py: 90, x: 0, y: 0.1 }),
      point({ series: "drug_plasma", role: "raw", px: 20, py: 50, x: 1, y: 5.000004 }),
      point({ series: "drug_plasma;error_bar", role: "raw", px: 20, py: 40, x: 1, y: 6 }),
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
      }),
      point({ series: "drug_urine", role: "mapped", px: 60, py: 30, x: 2, y: 7, file: TIMECOURSES, line: 3 }),
    ],
    unmatched: ["drug_feces"],
    ...changes,
  };
}

function trace(traces: OverlayTrace[], meta: string): OverlayTrace {
  const found = traces.find((entry) => entry.meta === meta);
  if (!found) throw new Error(`No trace ${meta} in ${traces.map((entry) => entry.meta).join(", ")}`);
  return found;
}

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
    const mapped = trace(traces, "mapped drug_plasma");
    expect(mapped).toEqual(expect.objectContaining({ mode: "markers", x: [20], y: [50] }));
    expect(mapped.marker?.symbol).toBe("x-thin-open");
    expect(trace(traces, "mapped drug_urine")).toEqual(expect.objectContaining({ x: [60], y: [30] }));
    expect(trace(traces, "raw drug_plasma;error_bar")).toEqual(expect.objectContaining({ x: [20], y: [40] }));
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

  it("draws the error bars of mapped rows as segments that end at error_px", () => {
    const { traces } = overlayTraces(figure());
    const bars = trace(traces, "error drug_plasma");
    expect(bars).toEqual(expect.objectContaining({ mode: "lines", x: [20, 20, null], y: [50, 40, null] }));
    expect(bars.hoverinfo).toBe("skip");
    expect(traces.map((entry) => entry.meta)).not.toContain("error drug_urine");
  });

  it("colors a series and its error bars alike, in the fixed order of the series", () => {
    const { traces } = overlayTraces(figure());
    const plasma = SERIES_COLORS.light[0];
    const urine = SERIES_COLORS.light[1];
    expect(trace(traces, "raw drug_plasma").marker?.color).toBe(plasma);
    expect(trace(traces, "mapped drug_plasma").marker?.line?.color).toBe(plasma);
    expect(trace(traces, "raw drug_plasma;error_bar").marker?.color).toBe(plasma);
    expect(trace(traces, "error drug_plasma").line?.color).toBe(plasma);
    expect(trace(traces, "raw drug_urine").marker?.color).toBe(urine);
  });

  it("fades the other series when a series is emphasized", () => {
    const plain = overlayTraces(figure()).traces;
    expect(plain.every((entry) => entry.opacity === 1)).toBe(true);
    const { traces } = overlayTraces(figure(), "drug_plasma");
    for (const meta of ["raw drug_plasma", "raw drug_plasma;error_bar", "mapped drug_plasma", "error drug_plasma"])
      expect(trace(traces, meta).opacity).toBe(1);
    for (const meta of ["raw drug_urine", "mapped drug_urine"]) expect(trace(traces, meta).opacity).toBe(0.2);
  });

  it("does not fade anything for a series that the overlay does not draw", () => {
    const { traces } = overlayTraces(figure(), "drug_feces");
    expect(traces.every((entry) => entry.opacity === 1)).toBe(true);
  });

  it("names the file, line, series and values of a point on hover", () => {
    const { traces } = overlayTraces(figure());
    const mapped = trace(traces, "mapped drug_plasma");
    expect(mapped.customdata).toEqual([[TIMECOURSES, 2, "drug_plasma", "1", "5"]]);
    expect(mapped.hovertemplate).toBe(
      "%{customdata[0]} line %{customdata[1]}<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>",
    );
    const raw = trace(traces, "raw drug_plasma");
    // Digitized values have six significant digits, as in the canonical project.
    expect(raw.customdata).toEqual([
      [PROJECT, null, "drug_plasma", "0", "0.1"],
      [PROJECT, null, "drug_plasma", "1", "5"],
    ]);
    expect(raw.hovertemplate).toBe(
      "%{customdata[0]}<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>",
    );
  });

  it("escapes markup in names, which Plotly would read as tags", () => {
    const view = figure({ overlay: [point({ series: "a<b>&c", role: "raw", px: 1, py: 1 })] });
    expect(trace(overlayTraces(view).traces, "raw a<b>&c").customdata?.[0]?.[2]).toBe("a&lt;b&gt;&amp;c");
  });

  it("reads the hover label in the theme colors", () => {
    const colors = { surface: "#192b31", text: "#ffffff", muted: "#aaaaaa", grid: "#333333", primary: "#79d5d6" };
    const { layout, traces } = overlayTraces(figure(), null, { dark: true, colors });
    expect(layout.hoverlabel).toEqual(
      expect.objectContaining({ bgcolor: "#192b31", font: expect.objectContaining({ color: "#ffffff" }) }),
    );
    expect(trace(traces, "mapped drug_plasma").hoverlabel).toEqual(
      expect.objectContaining({ bgcolor: "#192b31", bordercolor: SERIES_COLORS.light[0] }),
    );
    // The marks sit on the image, which keeps its colors in the dark theme.
    expect(trace(traces, "raw drug_plasma").marker?.color).toBe(SERIES_COLORS.light[0]);
  });
});

describe("mappedPoints", () => {
  it("reads timecourse rows as the library does: time and the central value, and the error bar end", () => {
    expect(mappedPoints(timecourses)).toEqual([
      { series: "drug_plasma", kind: "timecourses", file: TIMECOURSES, line: 2, x: 1, y: 5, error: 6 },
      { series: "drug_urine", kind: "timecourses", file: TIMECOURSES, line: 3, x: 2, y: 7, error: null },
      { series: "drug_feces", kind: "timecourses", file: TIMECOURSES, line: 4, x: 0, y: 1, error: 1.5 },
      { series: "drug_feces", kind: "timecourses", file: TIMECOURSES, line: 6, x: 1, y: 3.25, error: 2.5 },
    ]);
  });

  it("reads scatter rows by name with x_mean and y_mean", () => {
    const scatters: MappedTable = {
      file: "scatters_Fig2.tsv",
      kind: "scatters",
      header: ["study", "source", "name", "x_mean", "x_unit", "y_mean", "y_unit"],
      rows: [
        [2, ["Example", "Fig2", "age_vs_cmax", "30", "yr", "2", "mg/l"]],
        [3, ["Example", "Fig2", "age_vs_cmax", "40", "yr", "1,5", "mg/l"]],
        [4, ["Example", "Fig2", "", "50", "yr", "3", "mg/l"]],
      ],
    };
    expect(mappedPoints(scatters)).toEqual([
      { series: "age_vs_cmax", kind: "scatters", file: "scatters_Fig2.tsv", line: 2, x: 30, y: 2, error: null },
    ]);
  });

  it("has no points for other tables", () => {
    expect(mappedPoints({ file: "outputs_Fig1.tsv", kind: "outputs", header: ["mean"], rows: [[2, ["1"]]] })).toEqual([]);
  });
});

describe("plotTraces", () => {
  const plain = figure({ digitization: null, overlay: [], unmatched: ["drug_plasma", "drug_urine", "drug_feces"] });

  it("plots the mapped rows of each series in data units, with error bars to the error bar end", () => {
    const { traces, layout } = plotTraces(plain);
    expect(traces.map((entry) => entry.meta)).toEqual(["plot drug_plasma", "plot drug_urine", "plot drug_feces"]);
    const feces = trace(traces, "plot drug_feces");
    expect(feces).toEqual(expect.objectContaining({ mode: "lines+markers", x: [0, 1], y: [1, 3.25] }));
    expect(feces.error_y).toEqual(expect.objectContaining({ type: "data", array: [0.5, 0.75], visible: true }));
    expect(trace(traces, "plot drug_urine").error_y).toBeUndefined();
    expect(feces.customdata).toEqual([
      [TIMECOURSES, 4, "drug_feces", "0", "1"],
      [TIMECOURSES, 6, "drug_feces", "1", "3.25"],
    ]);
    expect(feces.marker?.color).toBe(SERIES_COLORS.light[2]);
    expect(layout.xaxis).toEqual(expect.objectContaining({ title: { text: "time (h)" }, fixedrange: true }));
    expect(layout.yaxis).toEqual(expect.objectContaining({ title: { text: "concentration (mg/l)" }, fixedrange: true }));
  });

  it("plots only the series without a dataset of a digitized figure, in the colors of the overlay", () => {
    const { traces } = plotTraces(figure());
    expect(traces.map((entry) => entry.meta)).toEqual(["plot drug_feces"]);
    expect(trace(traces, "plot drug_feces").marker?.color).toBe(SERIES_COLORS.light[2]);
  });

  it("uses the dark steps of the palette on the dark surface", () => {
    const colors = { surface: "#192b31", text: "#ffffff", muted: "#aaaaaa", grid: "#333333", primary: "#79d5d6" };
    const { traces, layout } = plotTraces(plain, null, { dark: true, colors });
    expect(trace(traces, "plot drug_plasma").marker?.color).toBe(SERIES_COLORS.dark[0]);
    expect(layout.paper_bgcolor).toBe("#192b31");
    expect(layout.font).toEqual(expect.objectContaining({ color: "#ffffff" }));
  });

  it("fades the other series when a series is emphasized", () => {
    const { traces } = plotTraces(plain, "drug_urine");
    expect(trace(traces, "plot drug_urine").opacity).toBe(1);
    expect(trace(traces, "plot drug_plasma").opacity).toBe(0.2);
    expect(trace(traces, "plot drug_feces").opacity).toBe(0.2);
    // The emphasized series is drawn on top.
    expect(traces.at(-1)?.meta).toBe("plot drug_urine");
  });

  it("draws scatter series as points only", () => {
    const view = figure({
      source: "Fig2",
      digitization: null,
      overlay: [],
      unmatched: ["age_vs_cmax"],
      mapped: [
        {
          file: "scatters_Fig2.tsv",
          kind: "scatters",
          header: ["name", "x_measurement", "x_mean", "x_unit", "y_measurement", "y_mean", "y_unit"],
          rows: [
            [2, ["age_vs_cmax", "age", "30", "yr", "cmax", "2", "mg/l"]],
            [3, ["age_vs_cmax", "age", "40", "yr", "cmax", "3", "mg/l"]],
          ],
        },
      ],
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

  it("selects the mapped row of a digitized point within 2 pixels, which Plotly prefers on hover", () => {
    expect(rowAt(figure(), { customdata: PLASMA, x: 20, y: 50 })).toEqual({ file: TIMECOURSES, line: 2 });
    expect(rowAt(figure(), { customdata: [PROJECT, null, "drug_urine", "2", "7"], x: 60, y: 31 })).toEqual({
      file: TIMECOURSES,
      line: 3,
    });
  });

  it("selects nothing for a digitized point without a mapped row nearby", () => {
    expect(rowAt(figure(), { customdata: PLASMA, x: 10, y: 90 })).toBeNull();
    // A mapped point of another series does not count.
    expect(rowAt(figure(), { customdata: [PROJECT, null, "drug_urine", "1", "5"], x: 20, y: 50 })).toBeNull();
    expect(rowAt(figure(), { customdata: "other", x: 20, y: 50 })).toBeNull();
    expect(rowAt(figure(), {})).toBeNull();
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
  it("names a series without its error bar suffix", () => {
    expect(baseSeries("drug_plasma;error_bar")).toBe("drug_plasma");
    expect(baseSeries("drug_plasma")).toBe("drug_plasma");
  });

  it("knows a figure that the overlay can draw on: a digitization on an image of known size", () => {
    expect(isCalibrated(figure())).toBe(true);
    expect(isCalibrated(figure({ digitization: null }))).toBe(false);
    expect(isCalibrated(figure({ image: null, image_url: null, image_size: null }))).toBe(false);
    expect(isCalibrated(figure({ image_size: null }))).toBe(false);
  });

  it("plots every series of a figure that the overlay cannot draw", () => {
    expect(plottedSeries(figure())).toEqual(["drug_feces"]);
    expect(plottedSeries(figure({ image_size: null }))).toEqual(["drug_plasma", "drug_urine", "drug_feces"]);
  });

  it("lists the series of the legend with their colors", () => {
    expect(legendEntries(figure(), "overlay", false)).toEqual([
      { series: "drug_plasma", color: SERIES_COLORS.light[0] },
      { series: "drug_urine", color: SERIES_COLORS.light[1] },
    ]);
    expect(legendEntries(figure(), "plot", true)).toEqual([{ series: "drug_feces", color: SERIES_COLORS.dark[2] }]);
  });

  it("tabulates the points of the overlay and of the plot", () => {
    expect(dataRows(figure(), "overlay")).toEqual([
      { series: "drug_plasma", kind: "Digitized", x: "0", y: "0.1", file: PROJECT, line: null },
      { series: "drug_plasma", kind: "Digitized", x: "1", y: "5", file: PROJECT, line: null },
      { series: "drug_plasma;error_bar", kind: "Digitized", x: "1", y: "6", file: PROJECT, line: null },
      { series: "drug_urine", kind: "Digitized", x: "2", y: "7", file: PROJECT, line: null },
      { series: "drug_plasma", kind: "Mapped", x: "1", y: "5", file: TIMECOURSES, line: 2 },
      { series: "drug_urine", kind: "Mapped", x: "2", y: "7", file: TIMECOURSES, line: 3 },
    ]);
    expect(dataRows(figure(), "plot")).toEqual([
      { series: "drug_feces", kind: "Mapped", x: "0", y: "1", file: TIMECOURSES, line: 4 },
      { series: "drug_feces", kind: "Mapped", x: "1", y: "3.25", file: TIMECOURSES, line: 6 },
    ]);
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
