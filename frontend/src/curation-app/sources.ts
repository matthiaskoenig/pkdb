/**
 * The parts of the Sources section: the column letters of a raw table, the mapped rows that it
 * lists and the problems of the files of a source. What a source is and which files it lacks
 * come from the library, in the summaries of the study detail.
 */
import type { MappedTable, SourceSummary, SourceView, TableRow, ValidationIssue } from "./api/types";
import { shownColumns } from "./review";

/** The letters of a column of a spreadsheet: A for the first, AA after Z. */
export function columnLetters(index: number): string {
  let letters = "";
  for (let rest = index + 1; rest > 0; rest = Math.floor((rest - 1) / 26))
    letters = String.fromCharCode(65 + ((rest - 1) % 26)) + letters;
  return letters;
}

/** The columns that a list of mapped rows leaves out: every row of a source has them alike. */
const IMPLIED_COLUMNS = new Set(["study", "source"]);

/** The first `limit` mapped rows of a table, with the columns that have a value in one of them. */
export function listedRows(
  table: MappedTable,
  limit: number,
): { rows: TableRow[]; columns: number[]; total: number } {
  const rows = table.rows.slice(0, limit).map(([line, cells]) => ({ line, cells }));
  const columns = shownColumns(table.header, rows, []).filter((index) => !IMPLIED_COLUMNS.has(table.header[index]!));
  return { rows, columns, total: table.rows.length };
}

/**
 * The problems of the files of a source: its image, its raw extraction and its own tables; of a
 * table that several sources share, only the problems at a mapped row of the source.
 */
export function sourceProblems(
  problems: readonly ValidationIssue[],
  summary: SourceSummary,
  view: SourceView,
): ValidationIssue[] {
  const whole = new Set([summary.image, summary.raw, ...view.mapped.filter((t) => !t.shared).map((t) => t.file)]);
  const lines = new Map(view.mapped.map((table) => [table.file, new Set(table.rows.map(([line]) => line))]));
  return problems.filter((issue) => {
    const file = issue.source?.file;
    if (!file) return false;
    if (whole.has(file)) return true;
    const row = issue.source?.row;
    return row != null && (lines.get(file)?.has(row) ?? false);
  });
}
