import { api } from "../../api/client";
import { asRecord } from "../../api/contracts";
import type { ResultTab } from "../search/model";
export interface DatabaseStatistic {
  tab: ResultTab;
  label: string;
  count: number;
}
const fields: { field: string; tab: ResultTab; label: string }[] = [
  { field: "study_count", tab: "studies", label: "Studies" },
  { field: "group_count", tab: "groups", label: "Groups" },
  { field: "individual_count", tab: "individuals", label: "Individuals" },
  { field: "intervention_count", tab: "interventions", label: "Interventions" },
  { field: "output_count", tab: "measurements", label: "Measurements" },
  { field: "timecourse_count", tab: "timecourses", label: "Timecourses" },
  { field: "scatter_count", tab: "scatters", label: "Scatter data" },
];
export function parseStatistics(value: unknown): DatabaseStatistic[] {
  const data = asRecord(value);
  return fields.map(({ field, tab, label }) => {
    const count = data[field];
    if (typeof count !== "number" || !Number.isSafeInteger(count) || count < 0)
      throw new Error("Invalid database statistics response");
    return { tab, label, count };
  });
}
export async function fetchStatistics(
  signal: AbortSignal,
): Promise<DatabaseStatistic[]> {
  return parseStatistics(
    (await api.get<unknown>("/api/v1/statistics/?format=json", { signal }))
      .data,
  );
}
