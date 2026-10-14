/**
 * The links of the names in the cells of a table to their rows. A column of subjects, such as
 * `subjects` or `parent`, names rows of subjects.tsv, a column of interventions rows of
 * interventions.tsv, by the name of the column. The study page has the line of each name
 * (`name_lines`), so that the grid links them without loading those tables.
 */
import type { NameKind, NameLines } from "../study-views/types";

/** Where the link of a name goes: the file of its table and the line of its row. */
export interface NameLink {
  file: string;
  line: number;
}

/** A part of the text of a cell: a name with the row it links to, or text without a link. */
export interface CellPart {
  text: string;
  link: NameLink | null;
}

/**
 * The table whose names a column holds, by the name of the column: `subjects`, `parent` and the
 * columns that end in `_subjects` name rows of subjects.tsv, `interventions` and the columns
 * that end in `_interventions` rows of interventions.tsv. Null for every other column, such as
 * `name` of subjects.tsv.
 */
export function namedKind(column: string): NameKind | null {
  if (column === "subjects" || column === "parent" || column.endsWith("_subjects")) return "subjects";
  if (column === "interventions" || column.endsWith("_interventions")) return "interventions";
  return null;
}

/**
 * The parts of the text of a cell of a column of names: each comma-separated name that `names`
 * has links to its row, and the commas and the spaces around the names stay text, so that the
 * parts read as the cell. A name without a row stays text, as validation reports it. Only the
 * own names of `lines` count, not the properties of every object, such as `constructor`.
 */
export function cellParts(text: string, names: NameLines): CellPart[] {
  const parts: CellPart[] = [];
  const plain = (value: string): void => {
    if (!value) return;
    const last = parts.at(-1);
    if (last && !last.link) last.text += value;
    else parts.push({ text: value, link: null });
  };
  text.split(",").forEach((piece, index) => {
    if (index > 0) plain(",");
    const name = piece.trim();
    if (!name || !Object.hasOwn(names.lines, name)) {
      plain(piece);
      return;
    }
    const start = piece.indexOf(name);
    plain(piece.slice(0, start));
    parts.push({ text: name, link: { file: names.file, line: names.lines[name]! } });
    plain(piece.slice(start + name.length));
  });
  return parts;
}
