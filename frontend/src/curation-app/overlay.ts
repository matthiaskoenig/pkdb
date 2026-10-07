/**
 * The Plotly traces of a figure source: the overlay of the digitized points and the mapped rows
 * on the image of the figure, in the pixels of the image, and the data plot of mapped rows that
 * have no digitized dataset.
 *
 * The overlay mirrors `pkdb plot` (python/src/pkdb/studyformat/plot.py): the points of
 * `source_view` in image pixels, the series in the order of the overlay, a series and its
 * `;error_bar` dataset in one color.
 */
import type { MappedTable, SourceView } from "./api/types";
import { plotColors, type PlotColors } from "../features/plots/theme";

/** The suffix of the dataset with the ends of the error bars of a series. */
export const ERROR_BAR_SUFFIX = ";error_bar";

/**
 * The categorical colors of the series in a fixed order, validated for color vision deficiency
 * on the light and the dark surface. The overlay always uses the light steps, because its marks
 * sit on the image of the paper. Past eight series the colors repeat; the legend, the hover
 * label and the data table name each series.
 */
export const SERIES_COLORS = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
} as const;

/** The opacity of the series beside an emphasized series. */
export const FADED = 0.2;

/** The fonts of the app (base.css), so that the hover labels and axes read like the page. */
const FONT = 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

export type OverlayMode = "overlay" | "plot";

/** The colors of the page theme around the plot. */
export interface PlotTheme {
  dark: boolean;
  colors: PlotColors;
}

const LIGHT: PlotTheme = { dark: false, colors: plotColors({}) };

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
   * `<role> <series>`, such as `mapped caf_plasma_D150`, which names the trace for tests and
   * debugging. Not a `uid`: Plotly puts uids into CSS selectors, which a series name would break.
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

/** A series without its `;error_bar` suffix. */
export function baseSeries(series: string): string {
  return series.endsWith(ERROR_BAR_SUFFIX) ? series.slice(0, -ERROR_BAR_SUFFIX.length) : series;
}

/** Whether the overlay can draw on the figure: a digitization on an image of known size. */
export function isCalibrated(
  view: SourceView,
): view is SourceView & { digitization: string; image_url: string; image_size: [number, number] } {
  return view.digitization !== null && view.image_url !== null && view.image_size !== null;
}

// Mapped rows as points, as `mapped_points` of the library reads them

/** A decimal number written with a decimal point, as `parse_number` of the library reads it. */
const NUMBER = /^[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/;
const CENTRAL = ["mean", "median", "gmean"] as const;

function parseNumber(text: string | undefined): number | null {
  if (text === undefined || !NUMBER.test(text)) return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

/** A mapped row of a timecourse or scatter table as a point of its series, in the units of its table. */
export interface MappedPoint {
  series: string;
  kind: "timecourses" | "scatters";
  file: string;
  line: number;
  x: number;
  y: number;
  /** The end of the error bar of a timecourse row. */
  error: number | null;
}

/** The rows of a timecourse or scatter table as points; none for other tables. */
export function mappedPoints(table: MappedTable): MappedPoint[] {
  const cell = (cells: string[], name: string) => {
    const index = table.header.indexOf(name);
    return index < 0 ? undefined : cells[index];
  };
  const points: MappedPoint[] = [];
  for (const [line, cells] of table.rows) {
    if (table.kind === "timecourses") {
      const series = cell(cells, "label") ?? "";
      const x = parseNumber(cell(cells, "time"));
      const y = CENTRAL.map((name) => parseNumber(cell(cells, name))).find((value) => value !== null) ?? null;
      if (series && x !== null && y !== null)
        points.push({
          series,
          kind: "timecourses",
          file: table.file,
          line,
          x,
          y,
          error: parseNumber(cell(cells, "error_bar")),
        });
    } else if (table.kind === "scatters") {
      const series = cell(cells, "name") ?? "";
      const x = parseNumber(cell(cells, "x_mean"));
      const y = parseNumber(cell(cells, "y_mean"));
      if (series && x !== null && y !== null)
        points.push({ series, kind: "scatters", file: table.file, line, x, y, error: null });
    }
  }
  return points;
}

function allMappedPoints(view: SourceView): MappedPoint[] {
  return view.mapped.flatMap(mappedPoints);
}

/**
 * The series that the data plot draws: those without a dataset beside the overlay, and every
 * series of the mapped rows when the overlay cannot draw on the figure.
 */
export function plottedSeries(view: SourceView): string[] {
  if (isCalibrated(view)) return [...view.unmatched];
  return unique(allMappedPoints(view).map((point) => point.series));
}

function plottedPoints(view: SourceView): MappedPoint[] {
  const series = new Set(plottedSeries(view));
  return allMappedPoints(view).filter((point) => series.has(point.series));
}

// Colors, text and the parts around the plot

function unique(values: readonly string[]): string[] {
  return [...new Set(values)];
}

/** The series of the source in the order of their colors: the overlay first, then the others. */
function colorOrder(view: SourceView): string[] {
  return unique([
    ...view.overlay.map((point) => baseSeries(point.series)),
    ...view.unmatched,
    ...allMappedPoints(view).map((point) => point.series),
  ]);
}

function colorOf(order: readonly string[], series: string, dark: boolean): string {
  const palette = dark ? SERIES_COLORS.dark : SERIES_COLORS.light;
  const index = Math.max(order.indexOf(baseSeries(series)), 0);
  return palette[index % palette.length]!;
}

/** A value with the six significant digits of a canonical digitization. */
export function formatValue(value: number): string {
  return String(Number(value.toPrecision(6)));
}

/** Plotly reads tags and entities in hover text; names from the files are text. */
function escapeMarkup(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function customdata(file: string, line: number | null, series: string, x: number, y: number): Customdata {
  return [escapeMarkup(file), line, escapeMarkup(series), formatValue(x), formatValue(y)];
}

const VALUES = "<br>%{customdata[2]}<br>x %{customdata[3]} · y %{customdata[4]}<extra></extra>";
/** The hover text of a mapped row: `<file> line <line>`, the series, x and y. */
const MAPPED_HOVER = `%{customdata[0]} line %{customdata[1]}${VALUES}`;
/** The hover text of a digitized point, which has no line. */
const RAW_HOVER = `%{customdata[0]}${VALUES}`;

function hoverLabel(colors: PlotColors, border: string): HoverLabel {
  return { bgcolor: colors.surface, bordercolor: border, font: { color: colors.text, family: FONT, size: 13 } };
}

/** The opacity of each series: emphasized or not faded, the others faded. */
function opacities(drawn: readonly string[], highlight: string | null | undefined): (series: string) => number {
  const active = highlight != null && drawn.some((series) => baseSeries(series) === highlight);
  return (series) => (active && baseSeries(series) !== highlight ? FADED : 1);
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
    font: { color: theme.colors.text, family: FONT },
    hoverlabel: hoverLabel(theme.colors, theme.colors.grid),
  };
}

/** The smallest scale of the marks of the overlay, so that they stay visible on a small image. */
export const MIN_MARK_SCALE = 0.6;

/**
 * The overlay of a digitized figure in the pixels of its image: the image below, a trace per
 * series and role (small dots for digitized points, thin crosses for mapped rows), and the error
 * bars of mapped rows as segments to their digitized end. With `highlight`, the other series
 * fade. `scale` is the size at which the image is shown: the marks shrink with it, down to
 * `MIN_MARK_SCALE`, so that they do not hide the printed symbols of a small image.
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
  const order = colorOrder(view);
  const series = unique(view.overlay.map((point) => point.series));
  const opacity = opacities(series, highlight);
  const color = (name: string) => colorOf(order, name, false);
  const traces: OverlayTrace[] = [];

  for (const name of series.filter((entry) => !entry.endsWith(ERROR_BAR_SUFFIX))) {
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
  for (const role of ["raw", "mapped"] as const) {
    for (const name of series) {
      const points = view.overlay.filter((point) => point.series === name && point.role === role);
      if (!points.length) continue;
      const marker =
        role === "raw"
          ? // A ring in the color of the paper keeps a dot apart from the printed symbol below it.
            { symbol: "circle", size: 7 * marks, color: color(name), line: { width: 1, color: "#ffffff" } }
          : { symbol: "x-thin-open", size: 11 * marks, color: color(name), line: { width: stroke, color: color(name) } };
      traces.push({
        type: "scatter",
        meta: `${role} ${name}`,
        name,
        mode: "markers",
        x: points.map((point) => point.px),
        y: points.map((point) => point.py),
        opacity: opacity(name),
        showlegend: false,
        marker,
        customdata: points.map((point) => customdata(point.file, point.line, point.series, point.x, point.y)),
        hovertemplate: role === "raw" ? RAW_HOVER : MAPPED_HOVER,
        hoverlabel: hoverLabel(theme.colors, color(name)),
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

/** `time (h)`, `concentration (mg/l)`: the measurement and the unit of an axis, as far as known. */
function axisTitle(name: string, unit: string): string {
  if (name && unit) return `${name} (${unit})`;
  return name || unit;
}

/** The axis titles of the first plotted series, as `pkdb plot` labels its axes. */
function axisTitles(view: SourceView, first: MappedPoint | undefined): [string, string] {
  const table = first && view.mapped.find((entry) => entry.file === first.file);
  const cells = table?.rows.find(([line]) => line === first?.line)?.[1];
  if (!table || !cells || !first) return ["x", "y"];
  const cell = (name: string) => cells[table.header.indexOf(name)] ?? "";
  return first.kind === "timecourses"
    ? [axisTitle("time", cell("time_unit")), axisTitle(cell("measurement"), cell("unit")) || "value"]
    : [
        axisTitle(cell("x_measurement"), cell("x_unit")) || "x",
        axisTitle(cell("y_measurement"), cell("y_unit")) || "y",
      ];
}

/**
 * The data plot of the mapped rows of `plottedSeries` in the units of their tables: timecourses
 * as lines with error bars to the error bar end, scatters as points. With `highlight`, the other
 * series fade.
 */
export function plotTraces(view: SourceView, highlight: string | null = null, theme: PlotTheme = LIGHT): OverlayPlot {
  const order = colorOrder(view);
  const points = plottedPoints(view);
  const series = unique(points.map((point) => point.series));
  const opacity = opacities(series, highlight);
  const traces = series.map((name): OverlayTrace => {
    const rows = points.filter((point) => point.series === name);
    const color = colorOf(order, name, theme.dark);
    const errors = rows.map((point) => (point.error === null ? null : Math.abs(point.error - point.y)));
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
      customdata: rows.map((point) => customdata(point.file, point.line, point.series, point.x, point.y)),
      hovertemplate: MAPPED_HOVER,
      hoverlabel: hoverLabel(theme.colors, color),
    };
  });
  const [xTitle, yTitle] = axisTitles(view, points[0]);
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
  const order = colorOrder(view);
  const series =
    mode === "overlay" ? unique(view.overlay.map((point) => baseSeries(point.series))) : plottedSeries(view);
  // The overlay marks sit on the image, which keeps its light colors.
  return series.map((name) => ({ series: name, color: colorOf(order, name, mode === "plot" && dark) }));
}

/** A point of the data table of the plot. */
export interface DataRow {
  series: string;
  kind: "Digitized" | "Mapped";
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
      kind: point.role === "raw" ? "Digitized" : "Mapped",
      x: formatValue(point.x),
      y: formatValue(point.y),
      file: point.file,
      line: point.line,
    }));
  return plottedPoints(view).map((point) => ({
    series: point.series,
    kind: "Mapped",
    x: formatValue(point.x),
    y: formatValue(point.y),
    file: point.file,
    line: point.line,
  }));
}

function unescapeMarkup(text: string): string {
  return text.replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
}

/** How far a mapped row may lie from its digitized point, as `digitized_mismatch` of the library allows. */
const MATCH_PIXELS = 2;

/** A point of a Plotly hover or click event: its customdata and its position in the plot. */
export interface EventPoint {
  customdata?: unknown;
  x?: unknown;
  y?: unknown;
}

/**
 * The row that a click on a point selects: the row of a mapped point, or the mapped row of its
 * series within 2 pixels of a digitized point. Plotly prefers the small dot of a digitized point
 * to the cross of the mapped row below it, so the dot stands for its row.
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
    if (distance <= MATCH_PIXELS && (best === null || distance < best.distance))
      best = { file: mapped.file, line: mapped.line, distance };
  }
  return best && { file: best.file, line: best.line };
}
