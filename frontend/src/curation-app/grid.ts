/**
 * The parts of a table grid: its columns, the rows that open review items target, the cells with
 * problems, and the raw extraction of a source as a table.
 */
import type { ReviewItem, TableResponse, TargetMatch, ValidationIssue } from "./api/types";
import { columnLetters } from "./columns";

// Columns

/** The number of columns: the header of a table, the widest row of a raw table. */
export function columnCount(table: TableResponse): number {
  if (table.kind === "table") return table.header.length;
  return table.rows.reduce((widest, row) => Math.max(widest, row.cells.length), 0);
}

/** The name of a column: its header in a table, its letter in the sheet of a raw table. */
export function columnName(table: TableResponse, index: number): string {
  return (table.kind === "table" ? table.header[index] : undefined) ?? columnLetters(index);
}

/**
 * The indices of the columns to show: all of them, or with `hideEmpty` those with a value in a
 * row and those named in `keep`. A table without rows shows its header.
 */
export function visibleColumns(table: TableResponse, hideEmpty: boolean, keep: readonly string[] = []): number[] {
  const indices = Array.from({ length: columnCount(table) }, (_, index) => index);
  if (!hideEmpty || table.rows.length === 0) return indices;
  return indices.filter(
    (index) =>
      keep.includes(columnName(table, index)) || table.rows.some((row) => (row.cells[index] ?? "") !== ""),
  );
}

// Review targets and problems

/** What the target of an item without a file selects. */
export const NOTHING: TargetMatch = { lines: null, series: null, total: null };

/** What the target of `item` selects, as the local server matched it; nothing for an item without a file. */
export function targetMatch(targets: Readonly<Record<string, TargetMatch>>, item: ReviewItem): TargetMatch {
  return targets[item.id] ?? NOTHING;
}

function openItemsOf(file: string, items: readonly ReviewItem[]): ReviewItem[] {
  return items.filter((item) => item.state === "open" && item.target?.file === file);
}

/** The lines of the rows of `file` that the row filters of its open review items match. */
export function targetLines(
  file: string,
  items: readonly ReviewItem[],
  targets: Readonly<Record<string, TargetMatch>>,
): Set<number> {
  return new Set(openItemsOf(file, items).flatMap((item) => targetMatch(targets, item).lines ?? []));
}

/**
 * The open review items about `file` that color no row: those without a row filter, such as all
 * items about a raw table, and those whose row filter matches no row.
 */
export function itemsWithoutRows(
  file: string,
  items: readonly ReviewItem[],
  targets: Readonly<Record<string, TargetMatch>>,
): { whole: number; unmatched: number } {
  let whole = 0;
  let unmatched = 0;
  for (const item of openItemsOf(file, items)) {
    const lines = targetMatch(targets, item).lines;
    if (lines === null) whole += 1;
    else if (lines.length === 0) unmatched += 1;
  }
  return { whole, unmatched };
}

/** The problems of a cell: the severity of the worst and the messages in the order of the report. */
export interface CellIssues {
  severity: ValidationIssue["severity"];
  messages: string[];
}

/** The problems of the cells of a table by line, then by column name, or `ROW` for the whole row. */
export type IssueCells = Map<number, Map<string, CellIssues>>;

/** The column of a problem of the whole row. */
export const ROW = "";

/**
 * The problems at the lines of `file`, by line and column: the header of a table column, the
 * letter of a raw table column, or `ROW` for a problem of the whole row.
 */
export function issueCells(issues: readonly ValidationIssue[], file: string): IssueCells {
  const cells: IssueCells = new Map();
  for (const issue of issues) {
    const source = issue.source;
    if (source?.file !== file || source.row == null) continue;
    const column = source.header ?? source.column ?? ROW;
    const line = cells.get(source.row) ?? new Map<string, CellIssues>();
    cells.set(source.row, line);
    const found = line.get(column);
    if (found) {
      found.messages.push(issue.message);
      if (issue.severity === "error") found.severity = "error";
    } else line.set(column, { severity: issue.severity, messages: [issue.message] });
  }
  return cells;
}

/**
 * The columns that stay when empty columns are hidden: the columns with a problem and the
 * columns of `names`, such as the marked and the focused column.
 */
export function keptColumns(issues: IssueCells, ...names: (string | null | undefined)[]): string[] {
  const kept = new Set(names.filter((name): name is string => Boolean(name)));
  for (const cells of issues.values()) for (const name of cells.keys()) if (name !== ROW) kept.add(name);
  return [...kept];
}

/** The raw extraction of a paper table, as `GET /tables/<file>` serves it, from the grid of its source view. */
export function rawTable(file: string, grid: readonly string[][]): TableResponse {
  return { file, kind: "raw", rows: grid.map((cells, index) => ({ line: index + 1, cells: [...cells] })) };
}
