import { NBSP, formatNumber, statisticText } from "./format";

// The value shown where one statistic has to stand for a record: the
// arithmetic mean, else the median, else the geometric mean, else a
// categorical choice. A measured zero is kept; only a missing statistic falls
// through to the next.
export function centralValue<T>(row: Record<string, T>): T | undefined {
  return row.mean ?? row.median ?? row.gmean ?? row.choice;
}

function finite(row: Record<string, unknown>, key: string): number | undefined {
  const value = row[key];
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : undefined;
}
function choiceName(value: unknown): string | undefined {
  if (typeof value === "string") return value || undefined;
  if (typeof value !== "object" || value === null || Array.isArray(value))
    return undefined;
  const named: Record<string, unknown> = { ...value };
  const name = named.name ?? named.label;
  return typeof name === "string" && name ? name : undefined;
}

// A statistic with its spread on one line, as a table cell shows it: `2.5 ± 0.5
// (SD)` for an arithmetic mean, `2.7 ×/÷ 1.3 (GSD)` for a geometric mean,
// `median 2.8 [1.9-4.1]` with a range. Missing statistics read `-`.
export function compactValue(row: Record<string, unknown>): string {
  const n = (key: string) => finite(row, key);
  const number = (key: string) => statisticText(key, n(key)) ?? "";
  const low = n("min") ?? n("minimum");
  const high = n("max") ?? n("maximum");
  const range =
    low === undefined || high === undefined
      ? ""
      : `[${formatNumber(low)}${low < 0 || high < 0 ? " to " : "-"}${formatNumber(high)}]`;
  const arithmetic =
    n("sd") !== undefined
      ? `${NBSP}±${NBSP}${number("sd")}${NBSP}(SD)`
      : n("se") !== undefined
        ? `${NBSP}±${NBSP}${number("se")}${NBSP}(SE)`
        : n("cv") !== undefined
          ? `${NBSP}(CV${NBSP}${number("cv")})`
          : "";
  let center: string | undefined;
  if (n("mean") !== undefined) center = `${number("mean")}${arithmetic}`;
  else if (n("median") !== undefined)
    center = `median ${number("median")}${arithmetic}`;
  else if (n("gmean") !== undefined) {
    const geometric =
      n("gsd") !== undefined
        ? `${NBSP}×/÷${NBSP}${number("gsd")}${NBSP}(GSD)`
        : n("gcv") !== undefined
          ? `${NBSP}(GCV${NBSP}${number("gcv")})`
          : "";
    center =
      n("gsd") !== undefined
        ? `${number("gmean")}${geometric}`
        : `geometric mean ${number("gmean")}${geometric}`;
  } else center = choiceName(row.choice);
  return [center, range].filter(Boolean).join(" ") || "-";
}
