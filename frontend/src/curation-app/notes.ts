/**
 * The notes of the tables in study.json: descriptions and comments per table kind, which the
 * Data section shows above each table of the kind, and which validation issues name by fields
 * such as `notes.subjects.comments.0.user`.
 */
import type { StudyDetail, TableKind } from "./api/types";
import type { NotesForm } from "./metadata";
import { plural } from "./overview";

/**
 * The table kind of a field of study.json in its notes, such as `subjects` for
 * `notes.subjects.descriptions.0`; null for another field or a kind that is not in `kinds`.
 */
export function notesKindOf(field: string | null | undefined, kinds: readonly TableKind[]): TableKind | null {
  const named = /^notes\.([^.]+)(?:\.|$)/.exec(field ?? "")?.[1];
  return kinds.find((kind) => kind === named) ?? null;
}

/** The kinds of `kinds` that a field among `fields` belongs to, each once, in the order of `kinds`. */
export function notesKindsOf(fields: Iterable<string | null | undefined>, kinds: readonly TableKind[]): TableKind[] {
  const found = new Set([...fields].map((field) => notesKindOf(field, kinds)));
  return kinds.filter((kind) => found.has(kind));
}

/** The kinds of `kinds` that a table of the study has: the Data section shows their notes above it. */
export function kindsWithTable(detail: Pick<StudyDetail, "tables">, kinds: readonly TableKind[]): TableKind[] {
  const tabled = new Set<string>(detail.tables.map((table) => table.kind));
  return kinds.filter((kind) => tabled.has(kind));
}

/** Whether notes have a description or a comment, also one that was just added and is empty. */
export function hasNotes(notes: NotesForm | undefined): boolean {
  return notes !== undefined && (notes.descriptions.length > 0 || notes.comments.length > 0);
}

/** What the notes of a kind hold, such as `2 descriptions · 1 comment`, or `No notes`. */
export function notesSummary(notes: NotesForm): string {
  const parts = [
    notes.descriptions.length ? plural(notes.descriptions.length, "description") : "",
    notes.comments.length ? plural(notes.comments.length, "comment") : "",
  ].filter(Boolean);
  return parts.join(" · ") || "No notes";
}
