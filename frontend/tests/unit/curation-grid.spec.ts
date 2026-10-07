import { describe, expect, it } from "vitest";
import type {
  ConflictData,
  SourceLocation,
  TableResponse,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import {
  columnName,
  conflictGrids,
  issueCells,
  itemsWithoutRows,
  listText,
  rawTable,
  ROW,
  syncAlert,
  syncSummary,
  tableOrder,
  targetLines,
  visibleColumns,
} from "../../src/curation-app/grid";
import { reviewItem } from "./curation-fixtures";

const outputs: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "label", "mean", "sd", "comment"],
  rows: [
    { line: 2, cells: ["Example", "Tab2", "caf_cl", "1.2", "", ""] },
    { line: 3, cells: ["Example", "Tab2", "caf_thalf", "4.8", "0.3", ""] },
    { line: 4, cells: ["Example", "Tab2", "caf_vd", "0.7", "", ""] },
  ],
};

const raw: TableResponse = {
  file: "Example_Tab2.tsv",
  kind: "raw",
  rows: [
    { line: 1, cells: ["", "", "Caffeine 150 mg"] },
    { line: 2, cells: ["CL", "", "1.20"] },
    { line: 4, cells: ["t1/2"] },
  ],
};

function issue(code: string, source: SourceLocation | null, severity: ValidationIssue["severity"] = "error") {
  return { code, severity, message: `${code} message`, source } satisfies ValidationIssue;
}

describe("visibleColumns", () => {
  it("shows every column unless empty columns are hidden", () => {
    expect(visibleColumns(outputs, false)).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("hides the columns that are empty in every row, except those to keep", () => {
    expect(visibleColumns(outputs, true)).toEqual([0, 1, 2, 3, 4]);
    expect(visibleColumns(outputs, true, ["comment"])).toEqual([0, 1, 2, 3, 4, 5]);
    expect(visibleColumns({ ...outputs, rows: outputs.rows.slice(0, 1) }, true)).toEqual([0, 1, 2, 3]);
  });

  it("names the columns of a raw table as its sheet does and pads them to the widest row", () => {
    expect(visibleColumns(raw, false)).toEqual([0, 1, 2]);
    expect(visibleColumns(raw, true)).toEqual([0, 2]);
    expect(visibleColumns(raw, true, ["B"])).toEqual([0, 1, 2]);
    expect([0, 1, 2].map((index) => columnName(raw, index))).toEqual(["A", "B", "C"]);
    expect(columnName(outputs, 3)).toBe("mean");
  });

  it("shows every column of a table without rows", () => {
    expect(visibleColumns({ ...outputs, rows: [] }, true)).toEqual([0, 1, 2, 3, 4, 5]);
  });
});

describe("targetLines", () => {
  it("matches the rows of the open items about the table by their row filters", () => {
    const items = [
      reviewItem({ id: "a", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } }),
      reviewItem({ id: "b", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_vd", mean: "0.7" } } }),
      // Resolved items, other files, the whole table and filters that match nothing add no rows.
      reviewItem({ id: "c", state: "resolved", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_thalf" } } }),
      reviewItem({ id: "d", target: { file: "subjects.tsv", rows: { label: "caf_thalf" } } }),
      reviewItem({ id: "e", target: { file: "outputs_Tab2.tsv", column: "sd" } }),
      reviewItem({ id: "f", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_vd", mean: "0.8" } } }),
      reviewItem({ id: "g" }),
    ];
    expect([...targetLines(outputs, items)].sort()).toEqual([2, 4]);
  });

  it("finds no rows in a raw table, which has no column names to filter", () => {
    const items = [reviewItem({ target: { file: "Example_Tab2.tsv", rows: { A: "CL" } } })];
    expect(targetLines(raw, items).size).toBe(0);
  });
});

describe("itemsWithoutRows", () => {
  it("counts the open items about the whole table and those whose row filters match no row", () => {
    const items = [
      reviewItem({ id: "a", target: { file: "outputs_Tab2.tsv", column: "sd" } }),
      reviewItem({ id: "b", target: { file: "outputs_Tab2.tsv", rows: {} } }),
      reviewItem({ id: "c", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_auc" } } }),
      reviewItem({ id: "d", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } }),
      reviewItem({ id: "e", state: "dismissed", target: { file: "outputs_Tab2.tsv" } }),
      reviewItem({ id: "f", target: { file: "subjects.tsv" } }),
    ];
    expect(itemsWithoutRows(outputs, items)).toEqual({ whole: 2, unmatched: 1 });
    // A raw table has no column names to filter: its items are about the whole table.
    const rawItems = [reviewItem({ target: { file: "Example_Tab2.tsv", rows: { A: "CL" } } })];
    expect(itemsWithoutRows(raw, rawItems)).toEqual({ whole: 1, unmatched: 0 });
  });
});

describe("issueCells", () => {
  it("maps the issues of the file to their line and column, errors before warnings", () => {
    const cells = issueCells(
      [
        issue("invalid_number", { file: "outputs_Tab2.tsv", row: 3, header: "mean", column: "D" }, "warning"),
        issue("missing_value", { file: "outputs_Tab2.tsv", row: 3, header: "mean", column: "D" }),
        issue("unknown_term", { file: "outputs_Tab2.tsv", row: 4, header: "label" }, "warning"),
        issue("duplicate_row", { file: "outputs_Tab2.tsv", row: 2 }),
        // Other files, the whole file and the workbook are not cells of the table.
        issue("unknown_term", { file: "subjects.tsv", row: 3, header: "mean" }),
        issue("missing_image", { file: "outputs_Tab2.tsv" }),
        issue("invalid_cell", { file: "Example.xlsx", sheet: "outputs_Tab2", row: 3, column: "D" }),
        issue("no_source", null),
      ],
      "outputs_Tab2.tsv",
    );
    expect([...cells.keys()]).toEqual([3, 4, 2]);
    expect(cells.get(3)?.get("mean")).toEqual({
      severity: "error",
      messages: ["invalid_number message", "missing_value message"],
    });
    expect(cells.get(4)?.get("label")).toEqual({ severity: "warning", messages: ["unknown_term message"] });
    // An issue of a whole row has no column.
    expect(cells.get(2)?.get(ROW)).toEqual({ severity: "error", messages: ["duplicate_row message"] });
  });

  it("names the cells of a raw table by their column letter", () => {
    const issues = [issue("invalid_encoding", { file: "Example_Tab2.tsv", row: 2, column: "C" })];
    const cells = issueCells(issues, "Example_Tab2.tsv");
    expect(cells.get(2)?.get("C")?.messages).toEqual(["invalid_encoding message"]);
  });
});

describe("tableOrder", () => {
  it("orders the tables as the sheets of the workbook, the raw tables last", () => {
    const files = [
      "characteristica.tsv",
      "Example_Tab10.tsv",
      "Example_Tab2.tsv",
      "interventions.tsv",
      "outputs_Tab10.tsv",
      "outputs_Tab2.tsv",
      "scatters_Fig2.tsv",
      "subjects.tsv",
      "timecourses_Fig1.tsv",
    ];
    expect(tableOrder(files)).toEqual([
      "subjects.tsv",
      "interventions.tsv",
      "characteristica.tsv",
      "outputs_Tab2.tsv",
      "outputs_Tab10.tsv",
      "timecourses_Fig1.tsv",
      "scatters_Fig2.tsv",
      "Example_Tab2.tsv",
      "Example_Tab10.tsv",
    ]);
  });
});

describe("rawTable", () => {
  it("makes the grid of a raw extraction a raw table with the lines of its rows", () => {
    expect(rawTable("Example_Tab2.tsv", [["a"], ["b", "c"]])).toEqual({
      file: "Example_Tab2.tsv",
      kind: "raw",
      rows: [
        { line: 1, cells: ["a"] },
        { line: 2, cells: ["b", "c"] },
      ],
    });
  });
});

describe("listText", () => {
  it("joins names as a sentence does", () => {
    expect(listText(["a.tsv"])).toBe("a.tsv");
    expect(listText(["a.tsv", "b.tsv"])).toBe("a.tsv and b.tsv");
    expect(listText(["a.tsv", "b.tsv", "c.tsv"])).toBe("a.tsv, b.tsv and c.tsv");
  });
});

describe("syncAlert", () => {
  const conflict: ConflictData = {
    file: "outputs_Tab2.tsv",
    sheet: "outputs_Tab2",
    workbook_rows: [],
    table_lines: [],
    base_lines: [],
    kept: null,
  };

  it("says what each sync status means, with the tone of its chip", () => {
    const state = (status: Parameters<typeof syncAlert>[0]["status"], changes = 0) => ({
      status,
      changes,
      conflicts: 0,
    });
    expect(syncAlert(state("in_sync"), [])).toEqual({ tone: "success", text: "In sync" });
    expect(syncAlert(state("workbook_open"), [])).toEqual({ tone: "info", text: "Workbook open: close it to sync" });
    expect(syncAlert(state("syncing"), [])).toEqual({ tone: "info", text: "Syncing" });
    expect(syncAlert(state("changed", 2), [])).toEqual({
      tone: "warning",
      text: "Changed: the next sync writes 2 files",
    });
    expect(syncAlert(state("changed", 1), []).text).toBe("Changed: the next sync writes 1 file");
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
    expect(syncAlert(state, [conflict])).toEqual({ tone: "error", text: "Conflict in outputs_Tab2.tsv" });
    const conflicts: ConflictData[] = [
      conflict,
      { ...conflict, file: "subjects.tsv" },
      { ...conflict, file: "a.tsv", kept: "tables" },
    ];
    expect(syncAlert(state, conflicts).text).toBe("Conflict in outputs_Tab2.tsv and subjects.tsv");
    expect(syncAlert(state, []).text).toBe("Conflict between the workbook and the tables");
  });
});

describe("syncSummary", () => {
  const result: TablesResult = { ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [] };

  it("says which files the last sync wrote and removed and what it did to the workbook", () => {
    expect(syncSummary(result)).toBe("The last sync in the app changed no files.");
    expect(
      syncSummary({
        ...result,
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
        ...result,
        workbook_action: "created",
        changes: ["a", "b", "c", "d"].map((name) => ({ file: `${name}.tsv`, action: "write" as const })),
      }),
    ).toBe("The last sync in the app wrote 4 files and created the workbook.");
  });
});

describe("conflictGrids", () => {
  const conflict: ConflictData = {
    file: "outputs_Tab2.tsv",
    sheet: "outputs_Tab2",
    workbook_rows: [{ row: 3, text: "Example\tTab2\tcaf_cl\t1.25\t\t" }],
    table_lines: [{ line: 3, text: "Example\tTab2\tcaf_cl\t1.3\t0.2\t" }],
    base_lines: ["Example\tTab2\tcaf_cl\t1.2\t\t"],
    kept: null,
  };

  it("splits the rows of both sides and the last sync into the cells of the table header", () => {
    const grids = conflictGrids(conflict, outputs.kind === "table" ? outputs.header : []);
    expect(grids.workbook).toEqual({
      file: "outputs_Tab2.tsv",
      kind: "table",
      header: outputs.kind === "table" ? outputs.header : [],
      rows: [{ line: 3, cells: ["Example", "Tab2", "caf_cl", "1.25", "", ""] }],
    });
    expect(grids.tables.rows).toEqual([{ line: 3, cells: ["Example", "Tab2", "caf_cl", "1.3", "0.2", ""] }]);
    expect(grids.base.rows).toEqual([{ line: 1, cells: ["Example", "Tab2", "caf_cl", "1.2", "", ""] }]);
    // The columns with a value on a side, the same for all three; the ones that differ first.
    expect(grids.changed).toEqual([3, 4]);
    expect(grids.columns).toEqual([3, 4, 0, 1, 2]);
  });

  it("finds no changed columns when a side removed the table", () => {
    const grids = conflictGrids({ ...conflict, workbook_rows: [] }, null);
    expect(grids.changed).toEqual([]);
    expect(grids.columns).toEqual([0, 1, 2, 3, 4]);
  });

  it("names the cells by their column letter without a header", () => {
    const grids = conflictGrids({ ...conflict, file: "Example_Tab2.tsv", sheet: "Example_Tab2" }, null);
    expect(grids.workbook.kind).toBe("raw");
    expect(grids.columns.map((index) => columnName(grids.workbook, index))).toEqual(["D", "E", "A", "B", "C"]);
  });
});
