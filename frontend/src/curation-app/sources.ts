/**
 * The parts of the Sources section: the mapped rows that a source lists and the problems of the
 * files of a source. What a source is and which files it lacks come from the library, in the
 * summaries of the study detail.
 */
import type { MappedTable, SourceSummary, SourceView, TableResponse, ValidationIssue } from "./api/types";
import { shownColumns } from "./review";

/** The columns that a list of mapped rows leaves out: every row of a source has them alike. */
const IMPLIED_COLUMNS = new Set(["study", "source"]);

/** The mapped rows of a table as a table grid, and the columns that have a value in one of them. */
export function mappedGrid(table: MappedTable): { grid: TableResponse; columns: number[] } {
  const rows = table.rows.map(([line, cells]) => ({ line, cells }));
  const columns = shownColumns(table.header, rows, []).filter((index) => !IMPLIED_COLUMNS.has(table.header[index]!));
  return { grid: { file: table.file, kind: "table", header: table.header, rows }, columns };
}

/**
 * The problems of the files of a source: its image, its raw extraction and its own tables; of a
 * table that several sources share, only the problems at a mapped row of the source.
 */
export function sourceProblems<I extends ValidationIssue>(
  problems: readonly I[],
  summary: SourceSummary,
  view: SourceView,
): I[] {
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
