export type JsonValue =
  null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type ApiRecord = { [key: string]: JsonValue };
export interface ResultPage {
  items: ApiRecord[];
  count: number;
  page: number;
  lastPage: number;
}
export function isJson(value: unknown): value is JsonValue {
  if (value === null || typeof value === "string" || typeof value === "boolean")
    return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(isJson);
  return (
    typeof value === "object" &&
    value !== null &&
    Object.values(value).every(isJson)
  );
}
export function asRecord(value: unknown): ApiRecord {
  if (
    !isJson(value) ||
    value === null ||
    typeof value !== "object" ||
    Array.isArray(value)
  )
    throw new Error("The server returned an invalid record.");
  return value;
}
export function parsePage(value: unknown): ResultPage {
  const body = asRecord(value),
    data = asRecord(body.data);
  if (
    !Array.isArray(data.data) ||
    typeof data.count !== "number" ||
    !Number.isSafeInteger(data.count) ||
    data.count < 0 ||
    typeof body.current_page !== "number" ||
    typeof body.last_page !== "number"
  )
    throw new Error("The server returned an invalid result page.");
  return {
    items: data.data.map(asRecord),
    count: data.count,
    page: body.current_page,
    lastPage: body.last_page,
  };
}
export function label(value: JsonValue | undefined): string {
  if (value === null || value === undefined || value === "")
    return "Not reported";
  if (Array.isArray(value)) return value.map(label).join(", ");
  if (typeof value === "object")
    return label(
      value.name ?? value.label ?? value.sid ?? value.username ?? value.pk,
    );
  return String(value);
}
