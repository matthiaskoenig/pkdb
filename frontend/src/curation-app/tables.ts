/**
 * The parts of the Tables section: the order of the tables, what the sync status means and what a
 * sync did, and the rows of a sync conflict in one grid.
 */
import type { ConflictData, SyncState, TableResponse, TableRow, TablesResult } from "./api/types";
import { columnName } from "./grid";
import { plural, SYNC_LABELS, SYNC_TONES, type Tone } from "./overview";
import { actionFailure, isRawTable, type ActionFailure } from "./study";

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
          ? `${label}: the next sync changes ${plural(sync.changes, "file")}`
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
 * The result without the unresolved conflicts and their `sync_conflict` errors, which a sync
 * reports for each conflict: the conflict panel explains them.
 */
export function withoutConflicts(result: TablesResult): TablesResult {
  const unresolved = result.conflicts.some((conflict) => conflict.kept === null);
  return {
    ...result,
    conflicts: result.conflicts.filter((conflict) => conflict.kept !== null),
    issues: unresolved ? result.issues.filter((issue) => issue.code !== "sync_conflict") : result.issues,
  };
}

/**
 * What the curator should know after a sync, or after keeping a side of the conflicts: a
 * notice, or the problems that the sync found besides the conflicts, which the panel shows.
 */
export function syncOutcome(
  result: TablesResult,
  keep: Side | null,
): { notice: string; failure: ActionFailure | null } {
  const issues = withoutConflicts(result).issues;
  if (!result.ok && issues.length)
    return {
      notice: "",
      failure: actionFailure(
        keep ? `${KEPT[keep]}, but the sync found problems.` : "The sync found problems.",
        issues.map((issue) => issue.message),
      ),
    };
  if (conflictFiles(result.conflicts).length) return { notice: "The workbook and the tables conflict.", failure: null };
  if (result.workbook_action === "close_to_update")
    return { notice: "Close the workbook so that the sync can update it.", failure: null };
  if (result.workbook_action === "sync_again")
    return { notice: "The workbook was saved during the sync. Sync again.", failure: null };
  return {
    notice: keep ? `${KEPT[keep]}. The workbook and the tables are in sync.` : "Synced the workbook and the tables.",
    failure: null,
  };
}

// Conflicts

/** The rows of a conflict in one grid: the last sync, the rows of the sheet and the lines of the file. */
export interface ConflictView {
  /** The rows of all versions, numbered from 1 in this grid. */
  table: TableResponse;
  /** The version of each row: `Last sync`, `Workbook row 4` or `Tables line 3`. */
  labels: Map<number, string>;
  /** The columns with a value in a row, those that differ first. */
  columns: number[];
  /** The names of the columns whose values differ between the versions. */
  changed: string[];
  /** What a side without rows did, or null. */
  note: string | null;
}

/** The values of a column in rows, in order, to compare versions whatever the order of their rows. */
function values(rows: readonly TableRow[], index: number): string {
  return rows
    .map((row) => row.cells[index] ?? "")
    .sort()
    .join("\t");
}

/**
 * The rows of a conflict, split into the cells of `header`, the header of the table, in one grid
 * with a row per version.
 *
 * A side that removed a whole table that the other changed lists the table from its header,
 * which is line 1 and row 1 (`_removal_conflict` of the library): the header is no row here, and
 * it names the columns when the table is gone. Elsewhere a side without lines removed the rows
 * that the other changed. A raw table or a table whose header is unknown names its columns by
 * letter.
 */
export function conflictView(conflict: ConflictData, header: readonly string[] | null): ConflictView {
  const split = (text: string) => text.split("\t");
  const raw = isRawTable(conflict.file);
  const first = conflict.table_lines[0]?.line === 1 ? conflict.table_lines[0] : undefined;
  const firstRow = conflict.workbook_rows[0]?.row === 1 ? conflict.workbook_rows[0] : undefined;
  const removal = !raw && (first !== undefined || firstRow !== undefined);
  const columns = header ?? (removal ? split((first ?? firstRow)!.text) : null);
  const base = (removal ? conflict.base_lines.slice(1) : conflict.base_lines).map(split);
  const workbook = conflict.workbook_rows.filter(({ row }) => !(removal && row === 1));
  const tables = conflict.table_lines.filter(({ line }) => !(removal && line === 1));

  const labels = new Map<number, string>();
  const rows: TableRow[] = [];
  const add = (label: string, cells: string[]) => {
    rows.push({ line: rows.length + 1, cells });
    labels.set(rows.length, label);
  };
  for (const cells of base) add("Last sync", cells);
  for (const { row, text } of workbook) add(`Workbook row ${row}`, split(text));
  for (const { line, text } of tables) add(`Tables line ${line}`, split(text));
  const table: TableResponse = columns
    ? { file: conflict.file, kind: "table", header: [...columns], rows }
    : { file: conflict.file, kind: "raw", rows };

  const width = Math.max(columns?.length ?? 0, ...rows.map((row) => row.cells.length));
  const filled = Array.from({ length: width }, (_, index) => index).filter((index) =>
    rows.some((row) => (row.cells[index] ?? "") !== ""),
  );
  // The versions with rows are compared: a side without rows differs in every column.
  const versions = [
    rows.slice(0, base.length),
    rows.slice(base.length, base.length + workbook.length),
    rows.slice(base.length + workbook.length),
  ].filter((version) => version.length);
  const changing =
    versions.length > 1
      ? filled.filter((index) => new Set(versions.map((version) => values(version, index))).size > 1)
      : [];

  let note: string | null = null;
  if (removal && !workbook.length)
    note = "The sheet has no rows in the workbook, but the table changed since the last sync.";
  else if (removal && !tables.length) note = `${conflict.file} was deleted, but its sheet changed since the last sync.`;
  else if (!workbook.length) note = "The workbook removed these rows, and the tables changed them.";
  else if (!tables.length) note = "The tables removed these lines, and the workbook changed them.";
  else if (!base.length) note = "Both sides added these rows.";

  return {
    table,
    labels,
    columns: [...changing, ...filled.filter((index) => !changing.includes(index))],
    changed: changing.map((index) => columnName(table, index)),
    note,
  };
}
