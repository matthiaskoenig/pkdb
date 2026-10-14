import { describe, expect, it } from "vitest";
import type {
  ColumnClass,
  SourceLocation,
  TableResponse,
  TargetMatch,
  ValidationIssue,
} from "../../src/study-views/types";
import {
  columnClass,
  columnName,
  HEADER_LINE,
  issueCells,
  itemsWithoutRows,
  lineIssues,
  rawTable,
  ROW,
  targetLines,
  targetMatch,
  visibleColumns,
} from "../../src/curation-app/grid";
import { reviewItem } from "./curation-fixtures";

const outputs: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "label", "mean", "sd", "comment"],
  rows: [
    { line: 1, cells: ["Example", "Tab2", "caf_cl", "1.2", "", ""] },
    { line: 2, cells: ["Example", "Tab2", "caf_thalf", "4.8", "0.3", ""] },
    { line: 3, cells: ["Example", "Tab2", "caf_vd", "0.7", "", ""] },
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

/** The lines of `lines` as the local server matches a row filter, without a digitized series. */
function rowsOf(lines: number[] | null): TargetMatch {
  return { lines, series: null, total: 3 };
}

describe("targetMatch", () => {
  it("is what the local server matched for the item, and nothing for an item without a match", () => {
    const series = { lines: [2], series: { source: "Fig1", series: "caf_plasma" }, total: 3 };
    expect(targetMatch({ a: series }, reviewItem({ id: "a" }))).toEqual(series);
    expect(targetMatch({ a: series }, reviewItem({ id: "b" }))).toEqual({ lines: null, series: null, total: null });
  });
});

describe("targetLines", () => {
  it("joins the lines that the server matched for the open items about the file", () => {
    const items = [
      reviewItem({ id: "a", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } }),
      reviewItem({ id: "b", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_vd", mean: "0.7" } } }),
      // Resolved items, other files, the whole table and filters that match nothing add no rows.
      reviewItem({ id: "c", state: "resolved", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_thalf" } } }),
      reviewItem({ id: "d", target: { file: "subjects.tsv", rows: { label: "caf_thalf" } } }),
      reviewItem({ id: "e", target: { file: "outputs_Tab2.tsv", column: "sd" } }),
      reviewItem({ id: "f", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_vd", mean: "0.8" } } }),
      reviewItem({ id: "g" }),
      // An item that the server has not matched yet adds no rows either.
      reviewItem({ id: "h", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } }),
    ];
    const targets = {
      a: rowsOf([2]),
      b: rowsOf([4, 2]),
      c: rowsOf([3]),
      d: rowsOf([5]),
      e: rowsOf(null),
      f: rowsOf([]),
    };
    expect([...targetLines("outputs_Tab2.tsv", items, targets)].sort()).toEqual([2, 4]);
  });

  it("finds no rows in a raw table, which the server matches no row filter in", () => {
    const items = [reviewItem({ id: "a", target: { file: "Example_Tab2.tsv", rows: { A: "CL" } } })];
    expect(targetLines(raw.file, items, { a: rowsOf(null) }).size).toBe(0);
  });
});

describe("itemsWithoutRows", () => {
  it("counts the open items about the file without a row filter and those whose filter matches no row", () => {
    const items = [
      reviewItem({ id: "a", target: { file: "outputs_Tab2.tsv", column: "sd" } }),
      reviewItem({ id: "b", target: { file: "outputs_Tab2.tsv", rows: {} } }),
      reviewItem({ id: "c", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_auc" } } }),
      reviewItem({ id: "d", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } }),
      reviewItem({ id: "e", state: "dismissed", target: { file: "outputs_Tab2.tsv" } }),
      reviewItem({ id: "f", target: { file: "subjects.tsv" } }),
    ];
    const targets = {
      a: rowsOf(null),
      b: rowsOf(null),
      c: rowsOf([]),
      d: rowsOf([2]),
      e: rowsOf(null),
      f: rowsOf(null),
    };
    expect(itemsWithoutRows(outputs.file, items, targets)).toEqual({ whole: 2, unmatched: 1 });
    // The server matches no row filter in a raw table: its items are about the whole table.
    const rawItems = [reviewItem({ id: "r", target: { file: "Example_Tab2.tsv", rows: { A: "CL" } } })];
    expect(itemsWithoutRows(raw.file, rawItems, { r: rowsOf(null) })).toEqual({ whole: 1, unmatched: 0 });
  });
});

describe("issueCells", () => {
  it("maps the issues of the file to their line and column, with the worst severity and the issues in their order", () => {
    const number = issue("invalid_number", { file: "outputs_Tab2.tsv", row: 3, header: "mean", column: "D" }, "warning");
    const missing = issue("missing_value", { file: "outputs_Tab2.tsv", row: 3, header: "mean", column: "D" });
    const term = issue("unknown_term", { file: "outputs_Tab2.tsv", row: 4, header: "label" }, "warning");
    const duplicate = issue("duplicate_row", { file: "outputs_Tab2.tsv", row: 2 });
    const cells = issueCells(
      [
        number,
        missing,
        term,
        duplicate,
        // Other files, the whole file and the workbook are not cells of the table.
        issue("unknown_term", { file: "subjects.tsv", row: 3, header: "mean" }),
        issue("missing_image", { file: "outputs_Tab2.tsv" }),
        issue("invalid_cell", { file: "Example.xlsx", sheet: "outputs_Tab2", row: 3, column: "D" }),
        issue("no_source", null),
      ],
      "outputs_Tab2.tsv",
    );
    expect([...cells.keys()]).toEqual([3, 4, 2]);
    expect(cells.get(3)?.get("mean")).toEqual({ severity: "error", issues: [number, missing] });
    expect(cells.get(4)?.get("label")).toEqual({ severity: "warning", issues: [term] });
    // An issue of a whole row has no column.
    expect(cells.get(2)?.get(ROW)).toEqual({ severity: "error", issues: [duplicate] });
  });

  it("names the cells of a raw table by their column letter", () => {
    const encoding = issue("invalid_encoding", { file: "Example_Tab2.tsv", row: 2, column: "C" });
    expect(issueCells([encoding], "Example_Tab2.tsv").get(2)?.get("C")?.issues).toEqual([encoding]);
  });

  it("keeps the issues of the header of a table at its header line", () => {
    const header = issue("unknown_column", { file: "outputs_Tab2.tsv", row: HEADER_LINE, header: "dose" });
    expect(issueCells([header], "outputs_Tab2.tsv").get(HEADER_LINE)?.get("dose")?.issues).toEqual([header]);
  });
});

describe("lineIssues", () => {
  it("gathers every issue of a line: of its cells and of the whole row", () => {
    const mean = issue("missing_value", { file: "outputs_Tab2.tsv", row: 3, header: "mean" });
    const row = issue("duplicate_row", { file: "outputs_Tab2.tsv", row: 3 }, "warning");
    const other = issue("unknown_term", { file: "outputs_Tab2.tsv", row: 4, header: "label" });
    const cells = issueCells([mean, row, other], "outputs_Tab2.tsv");
    expect(lineIssues(cells, 3)).toEqual([mean, row]);
    expect(lineIssues(cells, 5)).toEqual([]);
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

describe("column classes", () => {
  it("gives the class of a column of a table by its index, and none for a raw table or a table without classes", () => {
    const classes: ColumnClass[] = ["meta", "meta", "data", "data", "data", "data"];
    const classed: TableResponse = {
      file: "outputs_Tab2.tsv",
      kind: "table",
      header: ["study", "source", "label", "mean", "sd", "comment"],
      classes,
      rows: [],
    };
    expect([0, 1, 2, 5, 6].map((index) => columnClass(classed, index))).toEqual(["meta", "meta", "data", "data", null]);
    expect(columnClass(outputs, 0)).toBeNull();
    expect(columnClass(raw, 0)).toBeNull();
  });
});
