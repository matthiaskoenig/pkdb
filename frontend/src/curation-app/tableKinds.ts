/** The kinds of the tables of a study, in the order of the sheets of the workbook (`studyformat`). */
import type { TableKind } from "./api/types";

export const TABLE_KINDS = [
  "subjects",
  "interventions",
  "characteristica",
  "outputs",
  "timecourses",
  "scatters",
] as const satisfies readonly TableKind[];

export const TABLE_KIND_LABELS: Record<TableKind, string> = {
  subjects: "Subjects",
  interventions: "Interventions",
  characteristica: "Characteristica",
  outputs: "Outputs",
  timecourses: "Timecourses",
  scatters: "Scatters",
};

/** The kinds of a new table, as the local server adds them (`NEW_TABLE_KINDS` of the library). */
export type NewTableKind = "outputs" | "timecourses" | "scatters" | "raw";

export const NEW_TABLE_KINDS: readonly { value: NewTableKind; label: string }[] = [
  { value: "outputs", label: TABLE_KIND_LABELS.outputs },
  { value: "timecourses", label: TABLE_KIND_LABELS.timecourses },
  { value: "scatters", label: TABLE_KIND_LABELS.scatters },
  { value: "raw", label: "Raw table" },
];
