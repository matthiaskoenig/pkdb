import { provenanceText } from "../../api/provenance";
import { label, type ApiRecord, type JsonValue } from "../../api/contracts";
import { scheduleText } from "../details/schedule";
import { formatNumber } from "./format";
import { centralValue, compactValue } from "./statistics";
function record(value: JsonValue | undefined): value is ApiRecord {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function science(value: JsonValue): string {
  if (!record(value)) return label(value);
  const quantity = centralValue(value);
  const reported = quantity !== undefined && quantity !== null;
  return [
    label(value.measurement_type),
    !reported
      ? "-"
      : typeof quantity === "number"
        ? formatNumber(quantity)
        : label(quantity),
    reported && value.unit ? label(value.unit) : "",
  ]
    .filter(Boolean)
    .join(" ");
}
// A study format 2 study is identified by `<substance>/<name>`; a format 1
// study by its name.
function studyText(row: ApiRecord): string {
  const study = row.study;
  const sid = record(study) ? study.sid : (row.study_sid ?? study);
  return typeof sid === "string" && sid.includes("/")
    ? sid
    : label(study ?? row.study_sid);
}
function rawCellText(row: ApiRecord, key: string): string {
  if (key === "provenance") return provenanceText(row.provenance);
  if (key === "schedule") return scheduleText(row) ?? "";
  if (key === "statistics") return compactValue(row);
  if (key === "unit") return typeof row.unit === "string" ? row.unit : "";
  if (key === "interventions" && Array.isArray(row.interventions))
    return row.interventions.length ? label(row.interventions) : "";
  if (key === "subject") return label(row.individual ?? row.group);
  if (key === "study") return studyText(row);
  if (key === "characteristica")
    return Array.isArray(row.characteristica)
      ? row.characteristica.map(science).join("; ")
      : label(row.characteristica);
  if (key === "dimensions") {
    const first = Array.isArray(row.array) ? row.array[0] : undefined;
    if (!Array.isArray(first)) return "Not reported";
    return first
      .filter(record)
      .map((point) =>
        [
          label(point.measurement_type),
          point.substance ? label(point.substance) : "",
          point.unit ? `[${label(point.unit)}]` : "",
        ]
          .filter(Boolean)
          .join(" "),
      )
      .join(" × ");
  }
  return label(row[key]);
}
// One placeholder for every empty cell of a table; detail views keep "Not
// reported" and the plot data table its own dash.
export const EMPTY_CELL = "-";
export function cellText(row: ApiRecord, key: string): string {
  const text = rawCellText(row, key);
  return text === "" || text === "Not reported" ? EMPTY_CELL : text;
}
