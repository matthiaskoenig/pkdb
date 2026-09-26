import { provenanceText } from "../../api/provenance";
import { label, type ApiRecord, type JsonValue } from "../../api/contracts";
function record(value: JsonValue | undefined): value is ApiRecord {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function science(value: JsonValue): string {
  if (!record(value)) return label(value);
  const quantity = value.value ?? value.mean ?? value.median ?? value.choice;
  return [
    label(value.measurement_type),
    quantity === undefined || quantity === null
      ? "Not reported"
      : label(quantity),
    value.unit ? label(value.unit) : "",
  ]
    .filter(Boolean)
    .join(" ");
}
export function cellText(row: ApiRecord, key: string): string {
  if (key === "provenance") return provenanceText(row.provenance);
  if (key === "subject") return label(row.individual ?? row.group);
  if (key === "study") return label(row.study ?? row.study_sid);
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
