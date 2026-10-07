/**
 * The sources of the study page: paper tables, figures and the text, the files that a source
 * lacks, the mapped rows that it lists and the problems of its files.
 */
import type { MappedTable, SourceSummary, SourceView, TableRow, ValidationIssue } from "./api/types";
import { shownColumns } from "./review";

export type SourceKind = "table" | "figure" | "text";

/** A paper table `Tab…`, a figure `Fig…` or the text. */
export function sourceKind(source: string): SourceKind {
  if (source.startsWith("Tab")) return "table";
  if (source.startsWith("Fig")) return "figure";
  return "text";
}

/** The letters of a column of a spreadsheet: A for the first, AA after Z. */
export function columnLetters(index: number): string {
  let letters = "";
  for (let rest = index + 1; rest > 0; rest = Math.floor((rest - 1) / 26))
    letters = String.fromCharCode(65 + ((rest - 1) % 26)) + letters;
  return letters;
}

/**
 * The files that a source lacks: the image `<name>_<source>.png`, and the raw extraction, which is
 * `<name>_<source>.tsv` of a paper table and the WebPlotDigitizer project `<name>_<source>.wpd.json`
 * of a figure. The text has neither.
 */
export function missingFiles(name: string, view: SourceView): { image: string | null; raw: string | null } {
  const kind = sourceKind(view.source);
  if (kind === "text") return { image: null, raw: null };
  const stem = `${name}_${view.source}`;
  const raw = kind === "table" ? (view.raw_grid ? null : `${stem}.tsv`) : view.digitization ? null : `${stem}.wpd.json`;
  return { image: view.image ? null : `${stem}.png`, raw };
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

/** The table of the rows of a single source, whose problems all belong to it. */
const SOURCE_TABLE = /^(?:outputs|timecourses|scatters)_(.+)\.tsv$/;

/**
 * The problems of the files of a source: its image, its raw extraction and its tables; of a
 * table that several sources share, only the problems at a mapped row of the source.
 */
export function sourceProblems(
  problems: readonly ValidationIssue[],
  summary: SourceSummary,
  view: SourceView,
): ValidationIssue[] {
  const own = new Set([summary.image, summary.raw]);
  const whole = (file: string) => own.has(file) || SOURCE_TABLE.exec(file)?.[1] === summary.source;
  const lines = new Map(view.mapped.map((table) => [table.file, new Set(table.rows.map(([line]) => line))]));
  return problems.filter((issue) => {
    const file = issue.source?.file;
    if (!file) return false;
    if (whole(file)) return true;
    const row = issue.source?.row;
    return row != null && (lines.get(file)?.has(row) ?? false);
  });
}
