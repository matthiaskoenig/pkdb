import { isRecord } from "../details/types";

export interface ScientificPoint {
  pk: string | number;
  time: number | null;
  time_unit: string | null;
  unit: string | null;
  mean: number | null;
  median: number | null;
  gmean: number | null;
  sd: number | null;
  se: number | null;
  cv: number | null;
  gsd: number | null;
  gcv: number | null;
  label: string | null;
}
export interface ErrorBars {
  type: "data";
  array: (number | null)[];
  // A multiplicative band is asymmetric: the lower end is not the mirrored upper.
  arrayminus?: (number | null)[];
  symmetric?: false;
  visible: boolean;
}
export interface Trace {
  type: "scatter";
  mode: "markers" | "lines+markers";
  name: string;
  showlegend: boolean;
  x: (number | null)[];
  y: (number | null)[];
  error_x?: ErrorBars;
  error_y?: ErrorBars;
  connectgaps: false;
}
export interface PlotAxis {
  title: { text: string };
  type: "linear" | "log";
  // Hover labels show at most four significant digits.
  hoverformat: string;
  gridcolor: string;
  linecolor: string;
  zerolinecolor: string;
}
export interface PlotLayout {
  autosize: boolean;
  height: number;
  xaxis: PlotAxis;
  yaxis: PlotAxis;
  paper_bgcolor: string;
  plot_bgcolor: string;
  font: { color: string };
  modebar: { bgcolor: string; color: string; activecolor: string };
  legend: {
    orientation: "h";
    x: number;
    xanchor: "left";
    y: number;
    yanchor: "bottom";
  };
  margin: { l: number; r: number; t: number; b: number };
  uirevision: string;
}
export interface PlotModel {
  traces: Trace[];
  xLabel: string;
  yLabel: string;
  notes: string[];
  points: ScientificPoint[][];
}

function number(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "number" || !Number.isFinite(value))
    throw new Error(
      "Plot contains a non-numeric or non-finite scientific value.",
    );
  return value;
}
function unit(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string")
    throw new Error("Plot contains an invalid unit.");
  return value;
}
function seriesLabel(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string")
    throw new Error("Plot contains an invalid label.");
  return value;
}
export function parsePoints(value: unknown): ScientificPoint[][] {
  if (!Array.isArray(value)) throw new Error("Plot points are unavailable.");
  return value.map((pair: unknown) => {
    if (!Array.isArray(pair)) throw new Error("Plot dimensions are invalid.");
    return pair.map((point: unknown) => {
      if (
        !isRecord(point) ||
        (typeof point.pk !== "number" && typeof point.pk !== "string")
      )
        throw new Error("Plot point identity is missing.");
      return {
        pk: point.pk,
        time: number(point.time),
        time_unit: unit(point.time_unit),
        unit: unit(point.unit),
        mean: number(point.mean),
        median: number(point.median),
        gmean: number(point.gmean),
        sd: number(point.sd),
        se: number(point.se),
        cv: number(point.cv),
        gsd: number(point.gsd),
        gcv: number(point.gcv),
        label: seriesLabel(point.label),
      };
    });
  });
}

const statisticNames = {
  mean: "mean",
  median: "median",
  gmean: "geometric mean",
} as const;
type Statistic = keyof typeof statisticNames;
type ErrorName = "sd" | "se" | "gsd";
const errorNotes: Record<ErrorName, string> = {
  sd: "SD",
  se: "SE",
  gsd: "geometric mean divided and multiplied by the geometric SD",
};

// The error of a series follows its central statistic: the geometric SD
// belongs to the geometric mean and spreads multiplicatively, the arithmetic
// SD or SE to the mean or median and spread symmetrically.
function errors(
  points: ScientificPoint[],
  statistic: Statistic | undefined,
): { name: ErrorName; bars: ErrorBars } | undefined {
  const candidates: ErrorName[] =
    statistic === "gmean" ? ["gsd"] : ["sd", "se"];
  const name = candidates.find((key) =>
    points.some((point) => point[key] !== null),
  );
  if (!name) return undefined;
  if (name !== "gsd")
    return {
      name,
      bars: {
        type: "data",
        array: points.map((point) => point[name]),
        visible: true,
      },
    };
  const factor = (point: ScientificPoint) =>
    point.gmean !== null && point.gsd !== null && point.gsd >= 1
      ? { mean: point.gmean, gsd: point.gsd }
      : undefined;
  return {
    name,
    bars: {
      type: "data",
      symmetric: false,
      array: points.map((point) => {
        const f = factor(point);
        return f ? f.mean * (f.gsd - 1) : null;
      }),
      arrayminus: points.map((point) => {
        const f = factor(point);
        return f ? f.mean * (1 - 1 / f.gsd) : null;
      }),
      visible: true,
    },
  };
}

function axis(points: ScientificPoint[]) {
  const statistic = (Object.keys(statisticNames) as Statistic[]).find((key) =>
    points.some((point) => point[key] !== null),
  );
  const error = errors(points, statistic);
  const units = new Set(points.map((point) => point.unit));
  if (units.size > 1)
    throw new Error(
      "This series contains mixed units. Inspect the data; no automatic conversion is performed.",
    );
  return {
    values: points.map((point) => (statistic ? point[statistic] : null)),
    label: `${statistic ? statisticNames[statistic] : "Not reported"} [${points[0]?.unit ?? "unit not reported"}]`,
    error: error?.bars,
    errorName: error?.name,
  };
}

function seriesName(points: ScientificPoint[]): string | undefined {
  const labels = new Set(points.flatMap((point) => point.label ?? []));
  return labels.size ? [...labels].join(", ") : undefined;
}

export function plotModel(
  value: unknown,
  kind: "timecourse" | "scatter",
): PlotModel {
  const points = parsePoints(value);
  if (!points.length) throw new Error("No plot points are available.");
  const width = kind === "timecourse" ? 1 : 2;
  if (points.some((pair) => pair.length !== width))
    throw new Error("Unexpected number of plot dimensions.");
  const ordered =
    kind === "timecourse"
      ? [...points].sort(
          (a, b) => (a[0]?.time ?? Infinity) - (b[0]?.time ?? Infinity),
        )
      : points;
  const first = ordered
    .map((pair) => pair[0])
    .filter((point): point is ScientificPoint => point !== undefined);
  const second = ordered
    .map((pair) => pair[1])
    .filter((point): point is ScientificPoint => point !== undefined);
  const x = kind === "scatter" ? axis(first) : undefined;
  const y = axis(kind === "scatter" ? second : first);
  if (
    kind === "timecourse" &&
    new Set(first.map((point) => point.time_unit)).size > 1
  )
    throw new Error("This timecourse contains mixed time units.");
  // A timecourse is named by its label; the legend shows it only then.
  const label = kind === "timecourse" ? seriesName(first) : undefined;
  const trace: Trace = {
    type: "scatter",
    mode: kind === "scatter" ? "markers" : "lines+markers",
    name: label ?? y.label,
    showlegend: label !== undefined,
    x: x?.values ?? first.map((point) => point.time),
    y: y.values,
    connectgaps: false,
  };
  if (x?.error) trace.error_x = x.error;
  if (y.error) trace.error_y = y.error;
  const notes = [
    "The complete subset is shown as context; not every point necessarily matches the applied search.",
  ];
  if (y.errorName) notes.push(`Y error bars: ${errorNotes[y.errorName]}.`);
  if (x?.errorName) notes.push(`X error bars: ${errorNotes[x.errorName]}.`);
  for (const [key, name] of [
    ["cv", "Coefficient of variation"],
    ["gcv", "Geometric coefficient of variation"],
  ] as const)
    if (points.flat().some((point) => point[key] !== null))
      notes.push(
        `${name} is retained in the data table; it is not plotted as an absolute error.`,
      );
  return {
    traces: [trace],
    xLabel: x?.label ?? `Time [${first[0]?.time_unit ?? "unit not reported"}]`,
    yLabel: y.label,
    notes,
    points: ordered,
  };
}
