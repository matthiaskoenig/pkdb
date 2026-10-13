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
import type {
  Axis,
  AxisScale,
  AxisScales,
  OverlayPoint,
  SourcePoint,
  SourceSeries,
  SourceView,
  ValidationIssue,
} from "./api/types";
import { SEVERITY_LABELS, tipProblems } from "./problems";
import { CAUTION_COLORS } from "./themes";
import { plotColors, type PlotColors } from "../features/plots/theme";

/**
 * The ring around a digitized point, which has contrast against the paper of the figure. The
 * same as `POINT_RING` of python/src/pkdb/studyformat/colors.py, which a test compares.
 */
export const POINT_RING = "#1f1f1f";

/** The color of a series that the source view does not list, which does not happen in a valid view. */
const UNKNOWN_COLOR = "#757575";

/**
 * The ring of the selected row: amber, apart from the series colors, on a dark outline of
 * `POINT_RING`. The outline has 16.5:1 on the white paper and on the plot of the light theme,
 * where the amber has only 2.2:1; the amber has 6.8:1 on the dark surface #192b31, where the
 * outline has 1.1:1, and 7.7:1 against the outline.
 */
const SELECTED_COLOR = "#e8a400";

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

/**
 * What the hover label and a click read of a point: file, TSV line (null for a digitized point),
 * series, x, y, and whether it is a digitized end of an error bar.
 */
type PointData = [file: string, line: number | null, series: string, x: string, y: string, errorBarEnd: boolean];

/** `PointData`, and for a point of the data plot the problems of its row as hover text (`problemHover`). */
export type Customdata = [...PointData, problems?: string];

interface HoverLabel {
  bgcolor: string;
  bordercolor: string;
  font: { color: string; family: string; size: number };
  /** How the lines of a label align; Plotly aligns them to the side of the point by default. */
  align?: "left";
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
  marker?: { symbol: string; size: number; color: string; opacity?: number[]; line?: { width: number; color: string; dash?: string } };
  line?: { color: string; width: number };
  error_y?: { type: "data"; array: (number | null)[]; visible: true; color: string; thickness: number; width: number };
  customdata?: Customdata[];
  hovertemplate?: string;
  hoverinfo?: "skip";
  hoverlabel?: HoverLabel;
}

export interface OverlayAxis {
  /** The scale of an axis of the data plot; the overlay keeps the pixels of the image without one. */
  type?: AxisScale;
  range?: [number, number];
  autorange?: false;
  visible: boolean;
  fixedrange: true;
  title?: { text: string; font?: { size: number } };
  tickfont?: { size: number };
  /** Full values on a log axis (0.2, 0.5, 1), not bare mantissas. */
  tickformat?: string;
  exponentformat?: "none";
  /** The ticks of a log axis by its span (`logTicks`): 1, 2 and 5 of each decade, or every n-th power of 10. */
  dtick?: "D2" | number;
  /** Fewer linear ticks of a log axis below a decade (`logTicks`). */
  nticks?: number;
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

export type { Axis, AxisScale, AxisScales };

export const AXES: readonly Axis[] = ["x", "y"];

/** Both axes linear, as without a choice and without a digitization. */
export const LINEAR_SCALES: AxisScales = { x: "linear", y: "linear" };

/** The scales of the digitization of the figure (`isLogX`, `isLogY` of its project), else linear. */
export function digitizedScales(view: SourceView): AxisScales {
  return { x: view.log_x ? "log" : "linear", y: view.log_y ? "log" : "linear" };
}

/** The axes on a log scale, x first. */
export function logAxes(scales: AxisScales): Axis[] {
  return AXES.filter((axis) => scales[axis] === "log");
}

/** Whether the axes can show a point: a log axis shows values above 0 only. */
function onScales(point: { x: number; y: number }, scales: AxisScales): boolean {
  return logAxes(scales).every((axis) => point[axis] > 0);
}

/** How many points of the data plot its log axes leave out, as they are at 0 or below. */
export function pointsOffScale(view: SourceView, scales: AxisScales): number {
  return plottedPoints(view).filter((point) => !onScales(point, scales)).length;
}

/** The points that the data plot draws on `scales`. */
function drawnPoints(view: SourceView, scales: AxisScales) {
  return plottedPoints(view).filter((point) => onScales(point, scales));
}

/** The span in decades of the values above 0, which a log axis draws; 0 without two such values. */
function decades(values: readonly number[]): number {
  let [low, high] = [Infinity, 0];
  for (const value of values) {
    if (value <= 0) continue;
    low = Math.min(low, value);
    high = Math.max(high, value);
  }
  return high > low ? Math.log10(high) - Math.log10(low) : 0;
}

/**
 * The ticks of a log axis of the plot of mapped rows whose drawn values span `span` decades, so that
 * its labels do not overlap; chosen by rendering on the 176 px of the y axis and on x axes of 200 to
 * 850 px. On the narrowest x axes (about 208 to 264 px), labels of 4 or more characters can still
 * touch at about 2.5 decades or below 0.75 decades, as with Plotly's own ticks. Plotly pads the
 * range of the values, by up to 30 % with the ring of a selected row, and
 * from a range of one decade, so from about 0.78 decades of values, labels every digit of each
 * decade (0.8 0.9 1 2 3 ... 9 10 20), which overlap. From 0.75 to 2.5 decades of values, the labels
 * are 1, 2 and 5 of each decade, which come too close from about 3 decades; above, every n-th power
 * of 10, at most about five. Below 0.75 decades, Plotly's linear ticks, at most 6, as more crowd at
 * the top of a log axis.
 */
export function logTicks(span: number): Pick<OverlayAxis, "dtick" | "nticks"> {
  if (span > 2.5) return { dtick: Math.ceil(span / 4) };
  if (span >= 0.75) return { dtick: "D2" };
  // Plotly draws 1.5 times `nticks` linear ticks below a decade.
  return { nticks: 4 };
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

function customdata(point: {
  file: string;
  line: number | null;
  series: string;
  x_text: string;
  y_text: string;
  error_bar_end?: boolean;
}): PointData {
  return [
    escapeMarkup(point.file),
    point.line,
    escapeMarkup(point.series),
    escapeMarkup(point.x_text),
    escapeMarkup(point.y_text),
    point.error_bar_end === true,
  ];
}

const XY = "<br>x %{customdata[3]} · y %{customdata[4]}";
const VALUES = `${XY}<extra></extra>`;
/** The hover text of a mapped row: `<file> line <line>`, the series, x and y. */
const MAPPED_HOVER = `%{customdata[0]} line %{customdata[1]}<br>%{customdata[2]}${VALUES}`;
/** The hover text of a point of the data plot: as of a mapped row, then the problems of its row. */
const PLOT_HOVER = `%{customdata[0]} line %{customdata[1]}<br>%{customdata[2]}${XY}%{customdata[6]}<extra></extra>`;
/** The hover text of a digitized point, which has no line. */
const RAW_HOVER = `%{customdata[0]}<br>%{customdata[2]}${VALUES}`;
/** The hover text of a digitized end of an error bar. */
const RAW_BAR_HOVER = `%{customdata[0]}<br>%{customdata[2]} (error bar)${VALUES}`;

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

/** A row that the curator selected, whose point gets a ring. */
export type SelectedRow = { file: string; line: number } | null;

/**
 * A ring around the points of the selected row, drawn last so that it stays on top: the amber
 * ring on a wider dark one, which shows on both sides of it (`SELECTED_COLOR`).
 */
function selectedTrace(points: { x: number; y: number }[]): OverlayTrace[] {
  if (!points.length) return [];
  const ring = (meta: string, color: string, width: number): OverlayTrace => ({
    type: "scatter",
    meta,
    name: "selected",
    mode: "markers",
    x: points.map((point) => point.x),
    y: points.map((point) => point.y),
    opacity: 1,
    showlegend: false,
    marker: { symbol: "circle-open", size: 16, color, line: { width, color } },
    hoverinfo: "skip",
  });
  return [ring("selected outline", POINT_RING, 5.5), ring("selected", SELECTED_COLOR, 2.5)];
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
 * series and kind of mark (small dots for digitized points, short bars for digitized error bar
 * ends, thin crosses for mapped rows), and the error bars of mapped rows as segments to their
 * digitized end. With `highlight`, the other series fade. `scale` is the size at which the image
 * is shown: the marks shrink with it, down to `MIN_MARK_SCALE`, so that they do not hide the
 * printed symbols of a small image.
 */
export function overlayTraces(
  view: SourceView,
  highlight: string | null = null,
  theme: PlotTheme = LIGHT,
  scale = 1,
  selected: SelectedRow = null,
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
      const line = { width: stroke, color: color(name) };
      const marker =
        role === "mapped"
          ? { symbol: "x-thin-open", size: 11 * marks, color: color(name), line }
          : end
            ? // A short bar, as `pkdb plot` draws the end of an error bar.
              { symbol: "line-ew-open", size: 9 * marks, color: color(name), line }
            : // A dark ring keeps a dot apart from the paper and from a mark of another color below it.
              { symbol: "circle", size: 7 * marks, color: color(name), line: { width: 1, color: POINT_RING } };
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
        customdata: points.map(customdata),
        hovertemplate: role === "mapped" ? MAPPED_HOVER : end ? RAW_BAR_HOVER : RAW_HOVER,
        hoverlabel: hoverLabel(theme, color(name)),
      });
    }
  }
  const hidden = { visible: false, fixedrange: true, autorange: false } as const;
  return {
    traces: [
      ...emphasizedLast(traces),
      ...selectedTrace(
        view.overlay
          .filter(
            (point) =>
              point.role === "mapped" && selected !== null && point.file === selected.file && point.line === selected.line,
          )
          .map((point) => ({ x: point.px, y: point.py })),
      ),
    ],
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
 * The colors of the ring around a plotted point whose row has a problem, as the grid outlines the
 * cell of a problem: the error color of the theme and the amber `caution` of the app
 * (`CAUTION_COLORS` in themes.ts), each with at least 3:1 on the surface of its theme (#ffffff and
 * #192b31). Plotly draws the rings outside of Vuetify, so the error colors repeat the `error`
 * colors of the themes in plugins/vuetify.ts; change them together.
 */
export const PROBLEM_COLORS: Record<"light" | "dark", Record<ValidationIssue["severity"], string>> = {
  light: { error: "#b3261e", warning: CAUTION_COLORS.light.caution },
  dark: { error: "#f28b82", warning: CAUTION_COLORS.dark.caution },
};

/** The key of a row of a table: `<file>:<line>`. */
export function rowKey(file: string, line: number | null): string {
  return `${file}:${line}`;
}

/** The worst severity of `issues`; null without issues. */
export function worstSeverity(issues: readonly ValidationIssue[]): ValidationIssue["severity"] | null {
  if (!issues.length) return null;
  return issues.some((issue) => issue.severity === "error") ? "error" : "warning";
}

/**
 * The problems of the rows whose points the data plot draws on `scales`, by `rowKey`, in the order
 * of the report: a log axis leaves out the points at 0 or below, and with them their problems.
 */
export function plottedProblems(
  view: SourceView,
  problems: readonly ValidationIssue[],
  scales: AxisScales = LINEAR_SCALES,
): Map<string, ValidationIssue[]> {
  const plotted = new Set(drawnPoints(view, scales).map((point) => rowKey(point.file, point.line)));
  const rows = new Map<string, ValidationIssue[]>();
  for (const issue of problems) {
    const source = issue.source;
    if (!source || source.row == null) continue;
    const key = rowKey(source.file, source.row);
    if (plotted.has(key)) rows.set(key, [...(rows.get(key) ?? []), issue]);
  }
  return rows;
}

/** The longest line of a message in a hover label, which Plotly does not wrap. */
const HOVER_WIDTH = 60;

/** `text` in lines of at most `width` characters, broken at spaces; a longer word has a line of its own. */
export function wrapText(text: string, width = HOVER_WIDTH): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    if (line && line.length + 1 + word.length > width) {
      lines.push(line);
      line = word;
    } else line = line ? `${line} ${word}` : word;
  }
  if (line) lines.push(line);
  return lines;
}

/**
 * The most lines of the problems in the hover label of a point. Plotly shows no label that is
 * higher than the plot: with the lines of the file, the series, x and y and the blank line, the
 * label has at most 12 lines of 17 pixels, which fit the 220 pixels of the data plot.
 */
const HOVER_PROBLEM_LINES = 8;

/**
 * The problems of a row in the hover label of its point, after a blank line, in at most
 * `HOVER_PROBLEM_LINES` lines: the severity and the code of each of at most `TIP_LIMIT`, the count
 * of the others, and the message of as many of the first as fit (no bold: Plotly sets the style
 * attribute for it, which the content security policy of the app blocks), escaped; empty without
 * problems.
 */
export function problemHover(issues: readonly ValidationIssue[]): string {
  if (!issues.length) return "";
  const { shown, more } = tipProblems(issues);
  // A line for each severity and code, and one for the count of the others.
  let free = HOVER_PROBLEM_LINES - shown.length - (more ? 1 : 0);
  const lines: string[] = [];
  for (const issue of shown) {
    lines.push(`${SEVERITY_LABELS[issue.severity]} · ${escapeMarkup(issue.code)}`);
    const message = wrapText(issue.message);
    // A message that does not fit ends the messages, so that they belong to the first problems.
    if (message.length > free) free = 0;
    else {
      lines.push(...message.map(escapeMarkup));
      free -= message.length;
    }
  }
  if (more) lines.push(`and ${more} more`);
  return `<br><br>${lines.join("<br>")}`;
}

/** The problems of a row as lines of the data table of the plot: `Warning digitized_mismatch: <message>`. */
export function problemLines(issues: readonly ValidationIssue[]): string[] {
  return issues.map((issue) => `${SEVERITY_LABELS[issue.severity]} ${issue.code}: ${issue.message}`);
}

/**
 * The rings around the plotted points of rows with problems, a trace per severity in the colors
 * of `PROBLEM_COLORS`, errors above warnings: the worst problem of a row colors its ring, and the
 * ring of a faded series fades with it. They take no hover, so that the point below a ring shows
 * its label and takes the click.
 */
function problemTraces(
  points: readonly SourcePoint[],
  problems: ReadonlyMap<string, ValidationIssue[]>,
  opacity: (series: string) => number,
  dark: boolean,
): OverlayTrace[] {
  const colors = PROBLEM_COLORS[dark ? "dark" : "light"];
  return (["warning", "error"] as const).flatMap((severity): OverlayTrace[] => {
    const ringed = points.filter((point) => worstSeverity(problems.get(rowKey(point.file, point.line)) ?? []) === severity);
    if (!ringed.length) return [];
    const color = colors[severity];
    return [
      {
        type: "scatter",
        meta: `problem ${severity}`,
        name: severity,
        mode: "markers",
        x: ringed.map((point) => point.x),
        y: ringed.map((point) => point.y),
        opacity: 1,
        showlegend: false,
        // A thin halo outside the ring of the selected row (`selectedTrace`, which ends 10.75 px from
        // the center): the two differ in size and weight, and both show on a selected point.
        // A warning ring is dashed and an error ring solid, so that they differ by more than color.
        marker: {
          symbol: "circle-open",
          size: 28,
          color,
          opacity: ringed.map((point) => opacity(point.series)),
          line: { width: 2, color, ...(severity === "warning" ? { dash: "dash" } : {}) },
        },
        hoverinfo: "skip",
      },
    ];
  });
}

/** The options of the data plot of `plotTraces`. */
export interface PlotOptions {
  /** The scales of the axes, linear without them. */
  scales?: AxisScales;
  /** The problems of the rows that the plot draws, by `rowKey` (`plottedProblems`). */
  rowProblems?: ReadonlyMap<string, ValidationIssue[]>;
}

/**
 * The data plot of the mapped rows of `plottedSeries` in the units of their tables: timecourses
 * as lines with error bars to the error bar end, scatters as points. With `highlight`, the other
 * series fade. `scales` sets the type of each axis; a log axis leaves out the points at 0 or
 * below, which `pointsOffScale` counts, and keeps their series in the legend. Drawn points of rows
 * with `rowProblems` (`plottedProblems`) get a ring in the color of their worst problem, and their
 * hover text lists the problems.
 */
export function plotTraces(
  view: SourceView,
  highlight: string | null = null,
  theme: PlotTheme = LIGHT,
  selected: SelectedRow = null,
  { scales = LINEAR_SCALES, rowProblems = new Map() }: PlotOptions = {},
): OverlayPlot {
  const styles = seriesStyles(view);
  const points = drawnPoints(view, scales);
  const series = unique(plottedPoints(view).map((point) => point.series));
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
      customdata: rows.map((point): Customdata => [
        ...customdata(point),
        problemHover(rowProblems.get(rowKey(point.file, point.line)) ?? []),
      ]),
      hovertemplate: PLOT_HOVER,
      // The lines of the problems read as a list.
      hoverlabel: { ...hoverLabel(theme, color), align: "left" },
    };
  });
  // The axes of the first series, as `pkdb plot` labels them.
  const first = styles.get(series[0] ?? "");
  const [xTitle, yTitle] = [first?.x_label ?? "x", first?.y_label ?? "y"];
  // The values that each axis draws: the points, and the ends of their error bars on the y axis.
  const drawn: Record<Axis, number[]> = {
    x: points.map((point) => point.x),
    y: points.flatMap((point) =>
      point.error_bar === null ? [point.y] : [point.y, point.error_bar, 2 * point.y - point.error_bar],
    ),
  };
  const axis = (name: Axis, text: string): OverlayAxis => ({
    type: scales[name],
    title: { text, font: { size: 11 } },
    tickfont: { size: 11 },
    ...(scales[name] === "log"
      ? { tickformat: "~g", exponentformat: "none" as const, ...logTicks(decades(drawn[name])) }
      : {}),
    visible: true,
    fixedrange: true,
    automargin: true,
    gridcolor: theme.colors.grid,
    linecolor: theme.colors.grid,
    zerolinecolor: theme.colors.grid,
  });
  return {
    traces: [
      ...emphasizedLast(traces),
      ...problemTraces(points, rowProblems, opacity, theme.dark),
      ...selectedTrace(
        points.filter((point) => selected !== null && point.file === selected.file && point.line === selected.line),
      ),
    ],
    layout: {
      ...baseLayout(theme),
      height: 220,
      paper_bgcolor: theme.colors.surface,
      plot_bgcolor: theme.colors.surface,
      xaxis: axis("x", xTitle),
      yaxis: axis("y", yTitle),
      margin: { l: 48, r: 8, t: 8, b: 36, pad: 2 },
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
 * How close, in image pixels, a mapped row, or the end of its error bar, must lie to a clicked
 * digitized point, or digitized error bar end, for the click to select it: within the radius of
 * the dot at the size of the image.
 */
const CLICK_PIXELS = 3;

/** A point of a Plotly hover or click event: its customdata and its position in the plot. */
export interface EventPoint {
  customdata?: unknown;
  x?: unknown;
  y?: unknown;
}

/**
 * The row that a click on a point selects: the row of a mapped point; the mapped row of its
 * series under a digitized point (`CLICK_PIXELS`), as Plotly prefers the small dot of a digitized
 * point to the cross of the mapped row below it, so the dot stands for its row; and the mapped
 * row of its series whose error bar ends at a digitized error bar end. Else nothing.
 */
export function rowAt(view: SourceView, point: EventPoint): { file: string; line: number } | null {
  if (!Array.isArray(point.customdata)) return null;
  const [file, line, series, , , errorBarEnd]: unknown[] = point.customdata;
  if (typeof file === "string" && typeof line === "number") return { file: unescapeMarkup(file), line };
  const { x, y } = point;
  if (typeof series !== "string" || typeof x !== "number" || typeof y !== "number") return null;
  const name = unescapeMarkup(series);
  let best: { file: string; line: number; distance: number } | null = null;
  for (const mapped of view.overlay) {
    if (mapped.role !== "mapped" || mapped.series !== name || mapped.line === null) continue;
    const at: [number, number] | null = errorBarEnd === true ? mapped.error_px : [mapped.px, mapped.py];
    if (at === null) continue;
    const distance = Math.hypot(at[0] - x, at[1] - y);
    if (distance <= CLICK_PIXELS && (best === null || distance < best.distance))
      best = { file: mapped.file, line: mapped.line, distance };
  }
  return best && { file: best.file, line: best.line };
}
