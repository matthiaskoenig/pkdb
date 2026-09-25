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
export async function fetchStatistics(signal: AbortSignal): Promise<StatisticsOverview> {
  return parseOverview((await api.get<unknown>("/api/v2/statistics", { signal })).data);
}

export interface Coverage {
  year: number | null;
  study_count: number;
  timecourse_count: number;
  substance_count: number;
  pk_count: number;
  pk_calculated_count: number;
  cumulative_study_count: number;
  cumulative_substance_count: number;
}
export interface ParameterCount {
  sid: string; name: string; year: number | null; reported: number; calculated: number;
}
export interface SubstanceCount { sid: string; name: string; timecourse_count: number }
export interface StatisticsOverview {
  rows: DatabaseStatistic[];
  counts: { substance_count: number; pk_count: number; pk_calculated_count: number };
  years: Coverage[];
  undated: Coverage;
  parameters: ParameterCount[];
  substances: SubstanceCount[];
}
function count(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0)
    throw new Error("Invalid database statistics response");
  return value;
}
function label(value: unknown): string {
  if (typeof value !== "string" || !value) throw new Error("Invalid statistics label");
  return value;
}
function year(value: unknown): number | null {
  if (value === null) return null;
  const result = count(value);
  if (result < 1 || result > 9999) throw new Error("Invalid statistics year");
  return result;
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error("Missing statistics series");
  return value;
}
function coverage(value: unknown): Coverage {
  const row = asRecord(value);
  return { year: year(row.year), study_count: count(row.study_count),
    timecourse_count: count(row.timecourse_count), substance_count: count(row.substance_count),
    pk_count: count(row.pk_count), pk_calculated_count: count(row.pk_calculated_count),
    cumulative_study_count: count(row.cumulative_study_count),
    cumulative_substance_count: count(row.cumulative_substance_count) };
}
export function parseOverview(value: unknown): StatisticsOverview {
  const data = asRecord(value), counts = asRecord(data.counts);
  if (data.date_basis !== "study.date") throw new Error("Unsupported statistics date basis");
  const years = array(data.years).map(coverage);
  if (years.some((row, i) => row.year === null || (i > 0 && row.year !== years[i - 1]!.year! + 1)))
    throw new Error("Invalid statistics timeline");
  const undated = coverage(data.undated);
  if (undated.year !== null) throw new Error("Invalid undated statistics");
  return {
    rows: parseStatistics(counts),
    counts: { substance_count: count(counts.substance_count), pk_count: count(counts.pk_count), pk_calculated_count: count(counts.pk_calculated_count) },
    years, undated,
    parameters: array(data.parameters).map((value) => {
      const row = asRecord(value);
      return { sid: label(row.sid), name: label(row.name), year: year(row.year), reported: count(row.reported), calculated: count(row.calculated) };
    }),
    substances: array(data.substances).map((value) => {
      const row = asRecord(value);
      return { sid: label(row.sid), name: label(row.name), timecourse_count: count(row.timecourse_count) };
    }),
  };
}
