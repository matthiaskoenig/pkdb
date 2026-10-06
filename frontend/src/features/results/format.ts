// Statistics and times are shown with at most four significant digits; the stored
// values are never changed. A non-breaking space keeps a number with its unit or sign.
export const NBSP = " ";
const SIGNIFICANT = 4;
// Coefficients of variation are fractions in the data and percent on screen.
const percents = new Set(["cv", "gcv"]);
// Statistics and the times of a record are shown rounded; the record is not.
const statistics = new Set([
  "time",
  "time_end",
  "interval",
  "mean",
  "median",
  "min",
  "max",
  "minimum",
  "maximum",
  "sd",
  "se",
  "gmean",
  "gsd",
  "error_bar",
]);

export function formatNumber(value: number): string {
  return String(Number(value.toPrecision(SIGNIFICANT)));
}
export function formatPercent(fraction: number): string {
  return `${formatNumber(fraction * 100)}${NBSP}%`;
}
// The display of a statistic of a record, or undefined for any other field.
export function statisticText(key: string, value: unknown): string | undefined {
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  if (percents.has(key)) return formatPercent(value);
  return statistics.has(key) ? formatNumber(value) : undefined;
}
