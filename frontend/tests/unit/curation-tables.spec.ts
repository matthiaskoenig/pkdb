import { describe, expect, it } from "vitest";
import type { ConflictData, TablesResult, ValidationIssue } from "../../src/curation-app/api/types";
import { columnName } from "../../src/curation-app/grid";
import {
  conflictView,
  listText,
  syncAlert,
  syncOutcome,
  syncSummary,
  withoutConflicts,
} from "../../src/curation-app/tables";
import { actionFailure } from "../../src/curation-app/study";
import {
  conflictAnswer,
  FILE_DELETED_CONFLICT,
  FILE_DELETED_ISSUE,
  OUTPUTS_COLUMNS,
  REGION_CONFLICT,
  REGION_ISSUE,
  ROWS_REMOVED_CONFLICT,
  ROWS_REMOVED_ISSUE,
  SCATTERS_COLUMNS,
  SUBJECTS_COLUMNS,
} from "./curation-fixtures";

const synced: TablesResult = { ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [] };

const invalidCell: ValidationIssue = {
  code: "invalid_number",
  severity: "error",
  message: "Cell N3 of outputs_Tab2 is not a number.",
  source: { file: "Example.xlsx", sheet: "outputs_Tab2", row: 3, column: "N" },
};

describe("listText", () => {
  it("joins names as a sentence does", () => {
    expect(listText(["a.tsv"])).toBe("a.tsv");
    expect(listText(["a.tsv", "b.tsv"])).toBe("a.tsv and b.tsv");
    expect(listText(["a.tsv", "b.tsv", "c.tsv"])).toBe("a.tsv, b.tsv and c.tsv");
  });
});

describe("syncAlert", () => {
  it("says what each sync status means, with the tone of its chip", () => {
    const state = (status: Parameters<typeof syncAlert>[0]["status"], changes = 0) => ({
      status,
      changes,
      conflicts: 0,
    });
    expect(syncAlert(state("in_sync"), [])).toEqual({ tone: "success", text: "In sync" });
    expect(syncAlert(state("workbook_open"), [])).toEqual({ tone: "info", text: "Workbook open: close it to sync" });
    expect(syncAlert(state("syncing"), [])).toEqual({ tone: "info", text: "Syncing" });
    // The changes are writes and deletes.
    expect(syncAlert(state("changed", 2), [])).toEqual({
      tone: "warning",
      text: "Changed: the next sync changes 2 files",
    });
    expect(syncAlert(state("changed", 1), []).text).toBe("Changed: the next sync changes 1 file");
    expect(syncAlert(state("changed", 0), []).text).toBe("Changed: the next sync updates the workbook");
    expect(syncAlert(state("no_workbook"), [])).toEqual({
      tone: undefined,
      text: "No workbook yet: Open tables creates it",
    });
    expect(syncAlert(state("not_checked"), [])).toEqual({ tone: undefined, text: "Not checked yet" });
    expect(syncAlert(state("unknown"), [])).toEqual({
      tone: undefined,
      text: "Unknown: the workbook or the tables cannot be read",
    });
  });

  it("names the files of the unresolved conflicts", () => {
    const state = { status: "conflict" as const, changes: 0, conflicts: 2 };
    expect(syncAlert(state, [REGION_CONFLICT])).toEqual({ tone: "error", text: "Conflict in outputs_Tab2.tsv" });
    const conflicts: ConflictData[] = [
      REGION_CONFLICT,
      ROWS_REMOVED_CONFLICT,
      { ...FILE_DELETED_CONFLICT, kept: "tables" },
    ];
    expect(syncAlert(state, conflicts).text).toBe("Conflict in outputs_Tab2.tsv and subjects.tsv");
    expect(syncAlert(state, []).text).toBe("Conflict between the workbook and the tables");
  });
});

describe("syncSummary", () => {
  it("says which files the last sync wrote and removed and what it did to the workbook", () => {
    expect(syncSummary(synced)).toBe("The last sync in the app changed no files.");
    expect(
      syncSummary({
        ...synced,
        workbook_action: "regenerated",
        changes: [
          { file: "outputs_Tab2.tsv", action: "write" },
          { file: "subjects.tsv", action: "write" },
          { file: "scatters_Fig2.tsv", action: "delete" },
        ],
      }),
    ).toBe(
      "The last sync in the app wrote outputs_Tab2.tsv and subjects.tsv, removed scatters_Fig2.tsv and updated the " +
        "workbook.",
    );
    expect(
      syncSummary({
        ...synced,
        workbook_action: "created",
        changes: ["a", "b", "c", "d"].map((name) => ({ file: `${name}.tsv`, action: "write" as const })),
      }),
    ).toBe("The last sync in the app wrote 4 files and created the workbook.");
  });
});

describe("withoutConflicts", () => {
  it("leaves out the unresolved conflicts and their errors, which the conflict panel explains", () => {
    const answer = conflictAnswer([
      [REGION_CONFLICT, REGION_ISSUE],
      [ROWS_REMOVED_CONFLICT, ROWS_REMOVED_ISSUE],
    ]);
    const kept = { ...FILE_DELETED_CONFLICT, kept: "workbook" as const };
    const result = { ...answer, conflicts: [...answer.conflicts, kept], issues: [...answer.issues, invalidCell] };
    expect(withoutConflicts(result)).toEqual({ ...answer, conflicts: [kept], issues: [invalidCell] });
  });
});

describe("syncOutcome", () => {
  it("leaves the conflicts to the conflict panel", () => {
    const answer = conflictAnswer([
      [REGION_CONFLICT, REGION_ISSUE],
      [FILE_DELETED_CONFLICT, FILE_DELETED_ISSUE],
    ]);
    expect(syncOutcome(answer, null)).toEqual({ notice: "The workbook and the tables conflict.", failure: null });
  });

  it("lists the other problems of a sync with conflicts", () => {
    const answer = conflictAnswer([[REGION_CONFLICT, REGION_ISSUE]]);
    expect(syncOutcome({ ...answer, issues: [...answer.issues, invalidCell] }, null)).toEqual({
      notice: "",
      failure: actionFailure("The sync found problems.", [invalidCell.message]),
    });
  });

  it("lists the problems of a failed sync, and says what keeping a side did", () => {
    expect(syncOutcome({ ...synced, ok: false, issues: [invalidCell] }, null)).toEqual({
      notice: "",
      failure: actionFailure("The sync found problems.", [invalidCell.message]),
    });
    expect(syncOutcome({ ...synced, ok: false, issues: [invalidCell] }, "workbook").failure?.text).toBe(
      "Kept the workbook rows, but the sync found problems.",
    );
    expect(syncOutcome(synced, "tables")).toEqual({
      notice: "Kept the table rows. The workbook and the tables are in sync.",
      failure: null,
    });
    expect(syncOutcome(synced, null).notice).toBe("Synced the workbook and the tables.");
    expect(syncOutcome({ ...synced, workbook_action: "close_to_update" }, null).notice).toBe(
      "Close the workbook so that the sync can update it.",
    );
    expect(syncOutcome({ ...synced, workbook_action: "sync_again" }, null).notice).toBe(
      "The workbook was saved during the sync. Sync again.",
    );
  });
});

describe("conflictView", () => {
  it("shows the last sync, the workbook row and the table line in one grid, the changed columns first", () => {
    const view = conflictView(REGION_CONFLICT, OUTPUTS_COLUMNS);
    expect(view.table.kind).toBe("table");
    expect(view.table.rows.map((row) => view.labels.get(row.line))).toEqual([
      "Last sync",
      "Workbook row 2",
      "Tables line 2",
    ]);
    expect(view.changed).toEqual(["mean"]);
    expect(view.columns.map((index) => columnName(view.table, index))).toEqual([
      "mean",
      "study",
      "source",
      "subjects",
      "interventions",
      "measurement",
      "substance",
      "tissue",
      "sd",
      "unit",
    ]);
    const mean = OUTPUTS_COLUMNS.indexOf("mean");
    expect(view.table.rows.map((row) => row.cells[mean])).toEqual(["5.9", "6.1", "6.3"]);
    expect(view.note).toBeNull();
  });

  it("says that the workbook removed the rows that the table changed", () => {
    const view = conflictView(ROWS_REMOVED_CONFLICT, SUBJECTS_COLUMNS);
    expect(view.table.rows.map((row) => view.labels.get(row.line))).toEqual(["Last sync", "Tables line 3"]);
    expect(view.changed).toEqual(["count"]);
    expect(view.note).toBe("The workbook removed these rows, and the tables changed them.");
    const tables = conflictView(
      { ...ROWS_REMOVED_CONFLICT, workbook_rows: [{ row: 3, text: "Example\tS1\tall\t3\tTabA\t" }], table_lines: [] },
      SUBJECTS_COLUMNS,
    );
    expect(tables.note).toBe("The tables removed these lines, and the workbook changed them.");
  });

  it("shows a deleted table without its header, which it takes from the sheet", () => {
    // The file is gone, so its header is not known.
    const view = conflictView(FILE_DELETED_CONFLICT, null);
    expect(view.table.kind === "table" && view.table.header).toEqual(SCATTERS_COLUMNS);
    expect(view.table.rows.map((row) => view.labels.get(row.line))).toEqual([
      "Last sync",
      "Last sync",
      "Workbook row 2",
      "Workbook row 3",
    ]);
    expect(view.table.rows.every((row) => row.cells[0] === "Example")).toBe(true);
    expect(view.changed).toEqual(["x_mean"]);
    expect(view.note).toBe("scatters_Fig2.tsv was deleted, but its sheet changed since the last sync.");
    const emptied = conflictView(
      {
        ...FILE_DELETED_CONFLICT,
        workbook_rows: [],
        table_lines: FILE_DELETED_CONFLICT.workbook_rows.map(({ row, text }) => ({ line: row, text })),
        removed: "workbook",
      },
      SCATTERS_COLUMNS,
    );
    expect(emptied.table.rows.map((row) => emptied.labels.get(row.line))).toEqual([
      "Last sync",
      "Last sync",
      "Tables line 2",
      "Tables line 3",
    ]);
    expect(emptied.note).toBe("The sheet has no rows in the workbook, but the table changed since the last sync.");
  });

  it("names the cells of a raw table by their letters and keeps its first line", () => {
    const view = conflictView(
      {
        file: "Example_Tab2.tsv",
        kind: "raw",
        sheet: "Example_Tab2",
        workbook_rows: [{ row: 1, text: "\tCaffeine 150 mg\t300 mg" }],
        table_lines: [{ line: 1, text: "\tCaffeine 150 mg\t300 mg (n=8)" }],
        base_lines: ["\t150 mg\t300 mg"],
        kept: null,
        removed: null,
      },
      null,
    );
    expect(view.table.kind).toBe("raw");
    expect(view.table.rows).toHaveLength(3);
    expect(view.changed).toEqual(["B", "C"]);
    expect(view.columns.map((index) => columnName(view.table, index))).toEqual(["B", "C"]);
  });
});
