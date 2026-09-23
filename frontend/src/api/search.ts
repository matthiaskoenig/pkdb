import { api } from "./client";
import { asRecord, parsePage } from "./contracts";
import { tabs } from "../features/search/model";
import type { Criteria, ResultTab } from "../features/search/model";
import type { FilterField } from "../features/search/fields";
import { serializeCriteria } from "../features/search/serialize";
export interface Selection {
  uuid: string;
  counts: Record<ResultTab, number>;
}
export function parseSelection(value: unknown): Selection {
  const r = asRecord(value);
  if (typeof r.uuid !== "string" || !/^[\da-f-]{36}$/iu.test(r.uuid))
    throw new Error("The server returned an invalid search selection.");
  const counts: Record<ResultTab, number> = {
    studies: 0,
    groups: 0,
    individuals: 0,
    interventions: 0,
    measurements: 0,
    timecourses: 0,
    scatters: 0,
  };
  for (const tab of tabs) {
    const n = r[tab === "measurements" ? "outputs" : tab];
    if (typeof n !== "number" || !Number.isSafeInteger(n) || n < 0)
      throw new Error("The server returned invalid result counts.");
    counts[tab] = n;
  }
  return { uuid: r.uuid, counts };
}
export async function createSelection(
  criteria: Criteria,
  signal: AbortSignal,
): Promise<Selection> {
  const response = await api.get<unknown>(
    `/api/v1/filter/?${serializeCriteria(criteria)}`,
    { signal },
  );
  return parseSelection(response.data);
}
export interface Suggestion {
  id: string;
  title: string;
  description: string;
}
export async function suggestions(
  field: FilterField,
  search: string,
  signal: AbortSignal,
): Promise<Suggestion[]> {
  const params = new URLSearchParams({
    search_multi_match: search,
    page_size: "30",
  });
  if (field.kind) {
    params.set("ntype", field.kind);
    if (field.kind === "measurement_type")
      params.set("dtype__exclude", "abstract");
  }
  const people = field.idKey === "username";
  if (people) params.delete("search_multi_match");
  const response = await api.get<unknown>(
    `/api/v1/${field.endpoint}/?${params}`,
    { signal },
  );
  // Public study responses expose only people associated with visible studies.
  const items = Array.isArray(response.data)
    ? response.data.map(asRecord)
    : parsePage(response.data).items;
  if (people) {
    const names = new Map<string, Suggestion>();
    for (const study of items) {
      const values = field.key.includes("curators")
        ? study.curators
        : [study.creator];
      if (!Array.isArray(values)) continue;
      for (const value of values) {
        if (
          typeof value !== "object" ||
          value === null ||
          Array.isArray(value) ||
          typeof value.username !== "string"
        )
          continue;
        const id = value.username;
        if (id.toLowerCase().includes(search.toLowerCase()))
          names.set(id, {
            id,
            title: id,
            description:
              "From a visible study. You may also enter an exact username.",
          });
      }
    }
    return [...names.values()];
  }
  return items.flatMap((item) => {
    const id = item[field.idKey];
    if (typeof id !== "string") return [];
    return [
      {
        id,
        title:
          typeof item.name === "string"
            ? item.name
            : typeof item.label === "string"
              ? item.label
              : id,
        description:
          typeof item.description === "string" ? item.description : "",
      },
    ];
  });
}
