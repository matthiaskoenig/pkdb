import { NBSP, formatNumber } from "../results/format";
import { isRecord } from "./types";

function finite(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value)
    ? value
    : undefined;
}

// Dosing schedules read as a person would say them: an irregular schedule is a
// list (`0, 12, 40 h`), a regular one an interval (`every 24 h, 7 doses from
// 0 h`) and a continuous administration a span (`from 0 h to 24 h`).
export function scheduleText(row: unknown): string | undefined {
  if (!isRecord(row)) return undefined;
  const unit = typeof row.time_unit === "string" ? row.time_unit : "";
  const at = (value: number) => {
    const shown = formatNumber(value);
    return unit ? `${shown}${NBSP}${unit}` : shown;
  };
  const times = (Array.isArray(row.time) ? row.time : [row.time]).flatMap(
    (item) => finite(item) ?? [],
  );
  if (times.length > 1) {
    const list = times.map(formatNumber).join(", ");
    return unit ? `${list}${NBSP}${unit}` : list;
  }
  const start = times[0];
  const interval = finite(row.interval);
  const doses = finite(row.doses);
  const end = finite(row.time_end);
  const count =
    doses === undefined
      ? ""
      : `${doses}${NBSP}${doses === 1 ? "dose" : "doses"}`;
  const cadence = [interval === undefined ? "" : `every ${at(interval)}`, count]
    .filter(Boolean)
    .join(", ");
  if (!cadence && end === undefined)
    return start === undefined ? undefined : at(start);
  const span =
    start !== undefined && end !== undefined
      ? `from ${at(start)} to ${at(end)}`
      : start !== undefined
        ? `from ${at(start)}`
        : end !== undefined
          ? `until ${at(end)}`
          : "";
  return [cadence, span].filter(Boolean).join(" ");
}
