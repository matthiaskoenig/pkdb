/**
 * The kinds of the tables of a study as the local server describes them in the study page
 * (`table_kinds`): in the order of the workbook sheets with the raw table last, each with its
 * label, its class of information, whether its tables belong to one source and whether Add table
 * adds one. The app keeps no list of its own.
 */
import type { StudyDetail, TableFileKind, TableKind } from "./types";

type Kinds = Pick<StudyDetail, "table_kinds">;

/** The kinds whose tables have notes in `study.json`: every table kind, not the raw table. */
export function noteKinds(detail: Kinds): TableKind[] {
  return detail.table_kinds.flatMap((entry) => (entry.kind === "raw" ? [] : [entry.kind]));
}

/** The label of a kind, such as Outputs or Raw table; the kind itself for one that the server does not describe. */
export function kindLabel(detail: Kinds, kind: TableFileKind): string {
  return detail.table_kinds.find((entry) => entry.kind === kind)?.label ?? kind;
}

/** The kinds that Add table adds, with their labels. */
export function addableKinds(detail: Kinds): { value: TableFileKind; label: string }[] {
  return detail.table_kinds.filter((entry) => entry.addable).map((entry) => ({ value: entry.kind, label: entry.label }));
}
