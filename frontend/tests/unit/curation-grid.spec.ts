import { describe, expect, it } from "vitest";
import type { SourceLocation, TableResponse, ValidationIssue } from "../../src/curation-app/api/types";
import {
  columnName,
  issueCells,
  itemsWithoutRows,
  rawTable,
  ROW,
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
