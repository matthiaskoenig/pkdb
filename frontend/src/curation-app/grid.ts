/**
 * The parts of the Tables section: the columns, review targets and problem cells of a table grid,
 * the order of the tables, what the sync status means and what a sync did, and the rows of a
 * sync conflict.
 */
import type {
  ConflictData,
  ReviewItem,
  SyncState,
  TableResponse,
  TableRow,
  TablesResult,
  ValidationIssue,
} from "./api/types";
import { plural, SYNC_LABELS, SYNC_TONES, type Tone } from "./overview";
import { matchingRows } from "./review";
import { columnLetters } from "./sources";
import { actionFailure, type ActionFailure } from "./study";

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

/** The row filters of an open review item about the table, or null for another item or the whole table. */
function rowFilters(table: TableResponse, item: ReviewItem): Record<string, string> | null {
  const filters = item.target?.rows;
  if (item.state !== "open" || item.target?.file !== table.file || !filters) return null;
  return Object.keys(filters).length ? filters : null;
}

/** The lines of the rows that the row filters of open review items about the table match. */
export function targetLines(table: TableResponse, items: readonly ReviewItem[]): Set<number> {
  const lines = new Set<number>();
  // A raw table has no column names to filter.
  if (table.kind !== "table") return lines;
  for (const item of items) {
    const filters = rowFilters(table, item);
    if (filters) for (const row of matchingRows(table.header, table.rows, filters)) lines.add(row.line);
  }
  return lines;
}

/**
 * The open review items about the table that color no row: those about the whole table, such as
 * all items about a raw table, and those whose row filters match no row.
 */
export function itemsWithoutRows(
  table: TableResponse,
  items: readonly ReviewItem[],
): { whole: number; unmatched: number } {
  let whole = 0;
  let unmatched = 0;
  for (const item of items) {
    if (item.state !== "open" || item.target?.file !== table.file) continue;
    const filters = rowFilters(table, item);
    if (!filters || table.kind !== "table") whole += 1;
    else if (!matchingRows(table.header, table.rows, filters).length) unmatched += 1;
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

// Tables

const DATA_TABLES = ["subjects", "interventions", "characteristica"];
const SOURCE_TABLES = ["outputs", "timecourses", "scatters"];

/** The rank of a table file in the workbook: data tables, per-source tables, then raw tables. */
function rank(file: string): number {
  const data = DATA_TABLES.indexOf(file.replace(/\.tsv$/, ""));
  if (data >= 0) return data;
  const source = SOURCE_TABLES.indexOf(file.slice(0, file.indexOf("_")));
  return source >= 0 ? DATA_TABLES.length + source : DATA_TABLES.length + SOURCE_TABLES.length;
}

/** The table files (`tableFiles`) in the order of the sheets of the workbook. */
export function tableOrder(files: readonly string[]): string[] {
  return [...files].sort(
    (a, b) => rank(a) - rank(b) || a.localeCompare(b, "en", { numeric: true, sensitivity: "base" }),
  );
}

/** The raw extraction of a paper table, as `GET /tables/<file>` serves it, from the grid of its source view. */
export function rawTable(file: string, grid: readonly string[][]): TableResponse {
  return { file, kind: "raw", rows: grid.map((cells, index) => ({ line: index + 1, cells: [...cells] })) };
}

// Sync

/** `a.tsv`, `a.tsv and b.tsv`, `a.tsv, b.tsv and c.tsv`. */
export function listText(items: readonly string[]): string {
  if (items.length < 2) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

/** The files of the unresolved conflicts, each once. */
function conflictFiles(conflicts: readonly ConflictData[]): string[] {
  return [...new Set(conflicts.filter((conflict) => conflict.kept === null).map((conflict) => conflict.file))];
}

/** What the sync status of a study means, after the label of its chip, and the tone of the chip. */
export function syncAlert(sync: SyncState, conflicts: readonly ConflictData[]): { tone: Tone; text: string } {
  const label = SYNC_LABELS[sync.status];
  const tone = SYNC_TONES[sync.status];
  switch (sync.status) {
    case "workbook_open":
      return { tone, text: `${label}: close it to sync` };
    case "changed":
      return {
        tone,
        text: sync.changes
          ? `${label}: the next sync writes ${plural(sync.changes, "file")}`
          : `${label}: the next sync updates the workbook`,
      };
    case "conflict": {
      const files = conflictFiles(conflicts);
      return {
        tone,
        text: files.length ? `${label} in ${listText(files)}` : `${label} between the workbook and the tables`,
      };
    }
    case "no_workbook":
      return { tone, text: `${label} yet: Open tables creates it` };
    case "unknown":
      return { tone, text: `${label}: the workbook or the tables cannot be read` };
    default:
      return { tone, text: label };
  }
}

/** `outputs_Tab2.tsv and subjects.tsv`, or `4 files` for more than two. */
function filesText(files: readonly string[]): string {
  return files.length > 2 ? plural(files.length, "file") : listText(files);
}

/** What the last sync from the app did to the tables and the workbook. */
export function syncSummary(result: TablesResult): string {
  const written = result.changes.filter((change) => change.action === "write").map((change) => change.file);
  const removed = result.changes.filter((change) => change.action === "delete").map((change) => change.file);
  const parts = [
    ...(written.length ? [`wrote ${filesText(written)}`] : []),
    ...(removed.length ? [`removed ${filesText(removed)}`] : []),
    ...(result.workbook_action === "created" ? ["created the workbook"] : []),
    ...(result.workbook_action === "regenerated" ? ["updated the workbook"] : []),
  ];
  return parts.length ? `The last sync in the app ${listText(parts)}.` : "The last sync in the app changed no files.";
}

/** A side of a conflict that the curator keeps. */
export type Side = "workbook" | "tables";

const KEPT: Record<Side, string> = { workbook: "Kept the workbook rows", tables: "Kept the table rows" };

/**
 * What the curator should know after a sync, or after keeping a side of the conflicts: a
 * notice, or the problems that the sync found.
 */
export function syncOutcome(
  result: TablesResult,
  keep: Side | null,
): { notice: string; failure: ActionFailure | null } {
  if (!result.ok && result.issues.length)
    return {
      notice: "",
      failure: actionFailure(
        keep ? `${KEPT[keep]}, but the sync found problems.` : "The sync found problems.",
        result.issues.map((issue) => issue.message),
      ),
    };
  const unresolved = conflictFiles(result.conflicts).length;
  // The conflict panel shows the conflicts.
  if (unresolved) return { notice: "The workbook and the tables conflict.", failure: null };
  if (result.workbook_action === "close_to_update")
    return { notice: "Close the workbook so that the sync can update it.", failure: null };
  if (result.workbook_action === "sync_again")
    return { notice: "The workbook was saved during the sync. Sync again.", failure: null };
  return {
    notice: keep ? `${KEPT[keep]}. The workbook and the tables are in sync.` : "Synced the workbook and the tables.",
    failure: null,
  };
}

/** The rows of a conflict as grids, and the columns with a value in one of them. */
export interface ConflictGrids {
  /** The lines that both sides changed, as they were at the last sync; numbered from 1. */
  base: TableResponse;
  /** The rows of the sheet. */
  workbook: TableResponse;
  /** The lines of the TSV file. */
  tables: TableResponse;
  /** The columns with a value in one of the rows, those that differ first. */
  columns: number[];
  /** The columns whose values differ between the sides; none when a side removed the table. */
  changed: number[];
}

/**
 * The rows of a conflict, split into the cells of `header`, the header of the table; a raw table
 * or a table whose header is unknown names its columns by letter.
 */
export function conflictGrids(conflict: ConflictData, header: readonly string[] | null): ConflictGrids {
  const grid = (rows: TableRow[]): TableResponse =>
    header
      ? { file: conflict.file, kind: "table", header: [...header], rows }
      : { file: conflict.file, kind: "raw", rows };
  const base = grid(conflict.base_lines.map((text, index) => ({ line: index + 1, cells: text.split("\t") })));
  const workbook = grid(conflict.workbook_rows.map(({ row, text }) => ({ line: row, cells: text.split("\t") })));
  const tables = grid(conflict.table_lines.map(({ line, text }) => ({ line, cells: text.split("\t") })));
  const rows = [...base.rows, ...workbook.rows, ...tables.rows];
  const width = Math.max(header?.length ?? 0, ...rows.map((row) => row.cells.length));
  const filled = Array.from({ length: width }, (_, index) => index).filter((index) =>
    rows.some((row) => (row.cells[index] ?? "") !== ""),
  );
  // The values of a column on a side, in order; the sides that have rows are compared.
  const values = (grid: TableResponse, index: number) =>
    grid.rows
      .map((row) => row.cells[index] ?? "")
      .sort()
      .join("\t");
  const sides = [base, workbook, tables].filter((grid) => grid.rows.length);
  const changed =
    workbook.rows.length && tables.rows.length
      ? filled.filter((index) => new Set(sides.map((grid) => values(grid, index))).size > 1)
      : [];
  const columns = [...changed, ...filled.filter((index) => !changed.includes(index))];
  return { base, workbook, tables, columns, changed };
}
