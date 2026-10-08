/**
 * The Plotly traces of a figure source: the overlay of the digitized points and the mapped rows
 * on the image of the figure, in the pixels of the image, and the data plot of mapped rows that
 * have no digitized dataset.
 *
 * Everything that the library knows comes from the source view (`source_view` of
 * python/src/pkdb/studyformat/sources.py), which `pkdb plot` draws too: the pixels, the points
 * in table units, the values as printed, and the series in one order with their colors and axis
 * labels. This module only lays them out for Plotly.
 */
import type { OverlayPoint, SourceSeries, SourceView } from "./api/types";
import { plotColors, type PlotColors } from "../features/plots/theme";

/**
 * The ring around a digitized point, which has contrast against the paper of the figure. The
 * same as `POINT_RING` of python/src/pkdb/studyformat/colors.py, which a test compares.
 */
export const POINT_RING = "#1f1f1f";

/** The color of a series that the source view does not list, which does not happen in a valid view. */
const UNKNOWN_COLOR = "#757575";

/** The opacity of the series beside an emphasized series. */
export const FADED = 0.2;

export type OverlayMode = "overlay" | "plot";

/** The colors and the fonts of the page around the plot, so that the hover labels and axes read like the page. */
export interface PlotTheme {
  dark: boolean;
  colors: PlotColors;
  /** The font family of the page, as the browser computes it from base.css. */
  font: string;
}

const LIGHT: PlotTheme = { dark: false, colors: plotColors({}), font: "sans-serif" };

/** The font family of the page; `sans-serif` without styles, as in tests. */
export function pageFont(): string {
  return getComputedStyle(document.documentElement).fontFamily || "sans-serif";
}

/** What the hover label and a click read of a point: file, TSV line (null for a digitized point), series, x and y. */
export type Customdata = [file: string, line: number | null, series: string, x: string, y: string];

interface HoverLabel {
  bgcolor: string;
  bordercolor: string;
  font: { color: string; family: string; size: number };
}

export interface OverlayTrace {
  type: "scatter";
  /**
   * `<marks> <series>`, such as `mapped caf_plasma_D150`, which names the trace for tests and
   * debugging: `raw`, `raw-bar` (digitized error bar ends), `mapped`, `error` (error bars of
   * mapped rows) or `plot`. Not a `uid`: Plotly puts uids into CSS selectors, which a series
   * name would break.
   */
  meta: string;
  name: string;
  mode: "markers" | "lines" | "lines+markers";
  x: (number | null)[];
  y: (number | null)[];
  opacity: number;
  showlegend: false;
  marker?: { symbol: string; size: number; color: string; line?: { width: number; color: string } };
  line?: { color: string; width: number };
  error_y?: { type: "data"; array: (number | null)[]; visible: true; color: string; thickness: number; width: number };
  customdata?: Customdata[];
  hovertemplate?: string;
  hoverinfo?: "skip";
  hoverlabel?: HoverLabel;
}

export interface OverlayAxis {
  range?: [number, number];
  autorange?: false;
  visible: boolean;
  fixedrange: true;
  title?: { text: string };
  automargin?: true;
  gridcolor?: string;
  linecolor?: string;
  zerolinecolor?: string;
}

export interface LayoutImage {
  source: string;
  xref: "x";
  yref: "y";
  x: number;
  y: number;
  sizex: number;
  sizey: number;
  sizing: "stretch";
  layer: "below";
  xanchor: "left";
  yanchor: "top";
}

export interface OverlayLayout {
  autosize: true;
  height?: number;
  xaxis: OverlayAxis;
  yaxis: OverlayAxis;
  images?: LayoutImage[];
  margin: { l: number; r: number; t: number; b: number; pad: number };
  showlegend: false;
  hovermode: "closest";
  dragmode: false;
  paper_bgcolor: string;
  plot_bgcolor: string;
  font: { color: string; family: string };
  hoverlabel: HoverLabel;
}

export interface OverlayPlot {
  traces: OverlayTrace[];
  layout: OverlayLayout;
}

/** Whether the overlay draws on the image of the figure: the source view says so. */
export function drawsOnImage(view: SourceView): boolean {
  return view.layout === "overlay" && view.image_url !== null && view.image_size !== null;
}

function unique(values: readonly string[]): string[] {
  return [...new Set(values)];
}

/**
 * The series that the data plot draws: those without a dataset beside the overlay, and every
 * series of the points when the image and the plot go side by side.
 */
export function plottedSeries(view: SourceView): string[] {
  return drawsOnImage(view) ? [...view.unmatched] : unique(view.points.map((point) => point.series));
}

function plottedPoints(view: SourceView) {
  const series = new Set(plottedSeries(view));
  return view.points.filter((point) => series.has(point.series));
}

/** The series of the source view by name. */
function seriesStyles(view: SourceView): Map<string, SourceSeries> {
  return new Map(view.series.map((series) => [series.name, series]));
}

/** The color of a series and of its error bars: its light step on paper, else the step of the theme. */
function colorOf(styles: Map<string, SourceSeries>, series: string, dark: boolean): string {
  const style = styles.get(series);
  return (dark ? style?.dark_color : style?.color) ?? UNKNOWN_COLOR;
}

/** Plotly reads tags and entities in hover text; names from the files are text. */
function escapeMarkup(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function customdata(point: { file: string; line: number | null; series: string; x_text: string; y_text: string }): Customdata {
  return [escapeMarkup(point.file), point.line, escapeMarkup(point.series), escapeMarkup(point.x_text), escapeMarkup(point.y_text)];
}

const VALUES = "<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>";
/** The hover text of a mapped row: `<file> line <line>`, the series, x and y. */
const MAPPED_HOVER = `%{customdata[0]} line %{customdata[1]}${VALUES}`;
/** The hover text of a digitized point, which has no line. */
const RAW_HOVER = `%{customdata[0]}${VALUES}`;

function hoverLabel(theme: PlotTheme, border: string): HoverLabel {
  const { colors } = theme;
  return { bgcolor: colors.surface, bordercolor: border, font: { color: colors.text, family: theme.font, size: 13 } };
}

/** The opacity of each series: emphasized or not faded, the others faded. */
function opacities(drawn: readonly string[], highlight: string | null | undefined): (series: string) => number {
  const active = highlight != null && drawn.includes(highlight);
  return (series) => (active && series !== highlight ? FADED : 1);
}

/** The emphasized traces last, so that they are drawn on top. */
function emphasizedLast(traces: OverlayTrace[]): OverlayTrace[] {
  return [...traces.filter((trace) => trace.opacity !== 1), ...traces.filter((trace) => trace.opacity === 1)];
}

function baseLayout(theme: PlotTheme): Omit<OverlayLayout, "xaxis" | "yaxis" | "margin"> {
  return {
    autosize: true,
    showlegend: false,
    hovermode: "closest",
    dragmode: false,
    paper_bgcolor: "rgba(0, 0, 0, 0)",
    plot_bgcolor: "rgba(0, 0, 0, 0)",
    font: { color: theme.colors.text, family: theme.font },
    hoverlabel: hoverLabel(theme, theme.colors.grid),
  };
}

/** The smallest scale of the marks of the overlay, so that they stay visible on a small image. */
export const MIN_MARK_SCALE = 0.6;

/**
 * The marker traces of the overlay in drawing order: the role and the error bar flag of their
 * points, and the prefix of their meta.
 */
const MARKS: readonly (readonly [role: OverlayPoint["role"], errorBarEnd: boolean, prefix: string])[] = [
  ["raw", false, "raw"],
  ["raw", true, "raw-bar"],
  ["mapped", false, "mapped"],
];

/**
 * The overlay of a digitized figure in the pixels of its image: the image below, a trace per
 * series and kind of mark (small dots for digitized points and digitized error bar ends, thin
 * crosses for mapped rows), and the error bars of mapped rows as segments to their digitized
 * end. With `highlight`, the other series fade. `scale` is the size at which the image is
 * shown: the marks shrink with it, down to `MIN_MARK_SCALE`, so that they do not hide the
 * printed symbols of a small image.
 */
export function overlayTraces(
  view: SourceView,
  highlight: string | null = null,
  theme: PlotTheme = LIGHT,
  scale = 1,
): OverlayPlot {
  const [width, height] = view.image_size ?? [0, 0];
  const marks = Math.min(1, Math.max(MIN_MARK_SCALE, scale));
  const stroke = marks < 0.8 ? 1.5 : 2;
  const styles = seriesStyles(view);
  const series = unique(view.overlay.map((point) => point.series));
  const opacity = opacities(series, highlight);
  // The marks sit on the image of the paper, which keeps its colors in the dark theme.
  const color = (name: string) => colorOf(styles, name, false);
  const traces: OverlayTrace[] = [];

  for (const name of series) {
    const bars = view.overlay.flatMap((point) =>
      point.series === name && point.role === "mapped" && point.error_px ? [{ ...point, end: point.error_px }] : [],
    );
    if (!bars.length) continue;
    traces.push({
      type: "scatter",
      meta: `error ${name}`,
      name,
      mode: "lines",
      x: bars.flatMap((point) => [point.px, point.end[0], null]),
      y: bars.flatMap((point) => [point.py, point.end[1], null]),
      opacity: opacity(name),
      showlegend: false,
      line: { color: color(name), width: stroke },
      hoverinfo: "skip",
    });
  }
  for (const [role, end, prefix] of MARKS) {
    for (const name of series) {
      const points = view.overlay.filter(
        (point) => point.series === name && point.role === role && point.error_bar_end === end,
      );
      if (!points.length) continue;
      const marker =
        role === "raw"
          ? // A dark ring keeps a dot apart from the paper and from a mark of another color below it.
            { symbol: "circle", size: 7 * marks, color: color(name), line: { width: 1, color: POINT_RING } }
          : { symbol: "x-thin-open", size: 11 * marks, color: color(name), line: { width: stroke, color: color(name) } };
      traces.push({
        type: "scatter",
        meta: `${prefix} ${name}`,
        name,
        mode: "markers",
        x: points.map((point) => point.px),
        y: points.map((point) => point.py),
        opacity: opacity(name),
        showlegend: false,
        marker,
        // The hover text names a digitized error bar end with its series.
        customdata: points.map((point) => customdata(end ? { ...point, series: `${point.series} (error bar)` } : point)),
        hovertemplate: role === "raw" ? RAW_HOVER : MAPPED_HOVER,
        hoverlabel: hoverLabel(theme, color(name)),
      });
    }
  }
  const hidden = { visible: false, fixedrange: true, autorange: false } as const;
  return {
    traces: emphasizedLast(traces),
    layout: {
      ...baseLayout(theme),
      xaxis: { ...hidden, range: [0, width] },
      // Pixels count down from the top of the image.
      yaxis: { ...hidden, range: [height, 0] },
      images: view.image_url
        ? [
            {
              source: view.image_url,
              xref: "x",
              yref: "y",
              x: 0,
              y: 0,
              sizex: width,
              sizey: height,
              sizing: "stretch",
              layer: "below",
              xanchor: "left",
              yanchor: "top",
            },
          ]
        : [],
      margin: { l: 0, r: 0, t: 0, b: 0, pad: 0 },
    },
  };
}

/**
 * The data plot of the mapped rows of `plottedSeries` in the units of their tables: timecourses
 * as lines with error bars to the error bar end, scatters as points. With `highlight`, the other
 * series fade.
 */
export function plotTraces(view: SourceView, highlight: string | null = null, theme: PlotTheme = LIGHT): OverlayPlot {
  const styles = seriesStyles(view);
  const points = plottedPoints(view);
  const series = unique(points.map((point) => point.series));
  const opacity = opacities(series, highlight);
  const traces = series.map((name): OverlayTrace => {
    const rows = points.filter((point) => point.series === name);
    const color = colorOf(styles, name, theme.dark);
    const errors = rows.map((point) => (point.error_bar === null ? null : Math.abs(point.error_bar - point.y)));
    return {
      type: "scatter",
      meta: `plot ${name}`,
      name,
      mode: rows[0]?.kind === "scatters" ? "markers" : "lines+markers",
      x: rows.map((point) => point.x),
      y: rows.map((point) => point.y),
      opacity: opacity(name),
      showlegend: false,
      marker: { symbol: "circle", size: 8, color },
      line: { color, width: 2 },
      ...(errors.some((error) => error !== null)
        ? { error_y: { type: "data", array: errors, visible: true, color, thickness: 1.5, width: 4 } as const }
        : {}),
      customdata: rows.map(customdata),
      hovertemplate: MAPPED_HOVER,
      hoverlabel: hoverLabel(theme, color),
    };
  });
  // The axes of the first series, as `pkdb plot` labels them.
  const first = styles.get(series[0] ?? "");
  const [xTitle, yTitle] = [first?.x_label ?? "x", first?.y_label ?? "y"];
  const axis = (text: string): OverlayAxis => ({
    title: { text },
    visible: true,
    fixedrange: true,
    automargin: true,
    gridcolor: theme.colors.grid,
    linecolor: theme.colors.grid,
    zerolinecolor: theme.colors.grid,
  });
  return {
    traces: emphasizedLast(traces),
    layout: {
      ...baseLayout(theme),
      height: 360,
      paper_bgcolor: theme.colors.surface,
      plot_bgcolor: theme.colors.surface,
      xaxis: axis(xTitle),
      yaxis: axis(yTitle),
      margin: { l: 64, r: 16, t: 16, b: 56, pad: 4 },
    },
  };
}

/** The series of the legend with the colors of their marks. */
export function legendEntries(view: SourceView, mode: OverlayMode, dark: boolean): { series: string; color: string }[] {
  const styles = seriesStyles(view);
  const series =
    mode === "overlay" ? unique(view.overlay.map((point) => point.series)) : plottedSeries(view);
  // The overlay marks sit on the image, which keeps its light colors.
  return series.map((name) => ({ series: name, color: colorOf(styles, name, mode === "plot" && dark) }));
}

/** A point of the data table of the plot. */
export interface DataRow {
  series: string;
  kind: "Digitized" | "Digitized error bar" | "Mapped";
  x: string;
  y: string;
  file: string;
  line: number | null;
}

/** The points of the overlay or of the data plot, for the data table. */
export function dataRows(view: SourceView, mode: OverlayMode): DataRow[] {
  if (mode === "overlay")
    return view.overlay.map((point) => ({
      series: point.series,
      kind: point.role === "mapped" ? "Mapped" : point.error_bar_end ? "Digitized error bar" : "Digitized",
      x: point.x_text,
      y: point.y_text,
      file: point.file,
      line: point.line,
    }));
  return plottedPoints(view).map((point) => ({
    series: point.series,
    kind: "Mapped",
    x: point.x_text,
    y: point.y_text,
    file: point.file,
    line: point.line,
  }));
}

function unescapeMarkup(text: string): string {
  return text.replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
}

/**
 * How close, in image pixels, a mapped row must lie to a clicked digitized point for the click
 * to select it: within the radius of the dot at the size of the image.
 */
const CLICK_PIXELS = 3;

/** A point of a Plotly hover or click event: its customdata and its position in the plot. */
export interface EventPoint {
  customdata?: unknown;
  x?: unknown;
  y?: unknown;
}

/**
 * The row that a click on a point selects: the row of a mapped point, or the mapped row of its
 * series under a digitized point (`CLICK_PIXELS`). Plotly prefers the small dot of a digitized
 * point to the cross of the mapped row below it, so the dot stands for its row.
 */
export function rowAt(view: SourceView, point: EventPoint): { file: string; line: number } | null {
  if (!Array.isArray(point.customdata)) return null;
  const [file, line, series]: unknown[] = point.customdata;
  if (typeof file === "string" && typeof line === "number") return { file: unescapeMarkup(file), line };
  const { x, y } = point;
  if (typeof series !== "string" || typeof x !== "number" || typeof y !== "number") return null;
  const name = unescapeMarkup(series);
  let best: { file: string; line: number; distance: number } | null = null;
  for (const mapped of view.overlay) {
    if (mapped.role !== "mapped" || mapped.series !== name || mapped.line === null) continue;
    const distance = Math.hypot(mapped.px - x, mapped.py - y);
    if (distance <= CLICK_PIXELS && (best === null || distance < best.distance))
      best = { file: mapped.file, line: mapped.line, distance };
  }
  return best && { file: best.file, line: best.line };
}
