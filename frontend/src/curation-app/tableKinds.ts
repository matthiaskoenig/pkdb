/** The kinds of the tables of a study, in the order of the sheets of the workbook (`studyformat`). */
import type { TableKind } from "./api/types";

/** The data tables, one file each: `subjects.tsv`, `interventions.tsv` and `characteristica.tsv`. */
export const DATA_TABLE_KINDS = ["subjects", "interventions", "characteristica"] as const satisfies readonly TableKind[];

/** The tables of mapped data, split by their source: `<kind>_<source>.tsv`. */
export const SOURCE_TABLE_KINDS = ["outputs", "timecourses", "scatters"] as const satisfies readonly TableKind[];

export type SourceTableKind = (typeof SOURCE_TABLE_KINDS)[number];

export const TABLE_KINDS: readonly TableKind[] = [...DATA_TABLE_KINDS, ...SOURCE_TABLE_KINDS];

export const TABLE_KIND_LABELS: Record<TableKind, string> = {
  subjects: "Subjects",
  interventions: "Interventions",
  characteristica: "Characteristica",
  outputs: "Outputs",
  timecourses: "Timecourses",
  scatters: "Scatters",
};
