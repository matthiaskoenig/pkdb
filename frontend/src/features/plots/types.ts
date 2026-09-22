import { isRecord } from "../details/types";

export interface ScientificPoint {
  pk: string | number;
  time: number | null;
  time_unit: string | null;
  unit: string | null;
  value: number | null;
  mean: number | null;
  median: number | null;
  sd: number | null;
  se: number | null;
  cv: number | null;
}
export interface ErrorBars {
  type: "data";
  array: (number | null)[];
  visible: boolean;
}
export interface Trace {
  type: "scatter";
  mode: "markers" | "lines+markers";
  name: string;
  x: (number | null)[];
  y: (number | null)[];
  error_x?: ErrorBars;
  error_y?: ErrorBars;
  connectgaps: false;
}
export interface PlotLayout {
  autosize: boolean;
  height: number;
  xaxis: { title: { text: string }; type: "linear" | "log" };
  yaxis: { title: { text: string }; type: "linear" | "log" };
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
        value: number(point.value),
        mean: number(point.mean),
        median: number(point.median),
        sd: number(point.sd),
        se: number(point.se),
        cv: number(point.cv),
      };
    });
  });
}

function axis(points: ScientificPoint[]) {
  const statistic = (["value", "mean", "median"] as const).find((key) =>
    points.some((point) => point[key] !== null),
  );
  const error = (["sd", "se"] as const).find((key) =>
    points.some((point) => point[key] !== null),
  );
  const units = new Set(points.map((point) => point.unit));
  if (units.size > 1)
    throw new Error(
      "This series contains mixed units. Inspect the data; no automatic conversion is performed.",
    );
  return {
    values: points.map((point) => (statistic ? point[statistic] : null)),
    label: `${statistic ?? "Not reported"} [${points[0]?.unit ?? "unit not reported"}]`,
    error: error
      ? {
          type: "data" as const,
          array: points.map((point) => point[error]),
          visible: true,
        }
      : undefined,
    errorName: error,
  };
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
  const trace: Trace = {
    type: "scatter",
    mode: kind === "scatter" ? "markers" : "lines+markers",
    name: y.label,
    x: x?.values ?? first.map((point) => point.time),
    y: y.values,
    connectgaps: false,
  };
  if (x?.error) trace.error_x = x.error;
  if (y.error) trace.error_y = y.error;
  const notes = [
    "The complete subset is shown as context; not every point necessarily matches the applied search.",
  ];
  if (y.errorName) notes.push(`Y error bars: ${y.errorName.toUpperCase()}.`);
  if (x?.errorName) notes.push(`X error bars: ${x.errorName.toUpperCase()}.`);
  if (points.flat().some((point) => point.cv !== null))
    notes.push(
      "Coefficient of variation is retained in the data table; it is not plotted as an absolute error.",
    );
  return {
    traces: [trace],
    xLabel: x?.label ?? `Time [${first[0]?.time_unit ?? "unit not reported"}]`,
    yLabel: y.label,
    notes,
    points: ordered,
  };
}
