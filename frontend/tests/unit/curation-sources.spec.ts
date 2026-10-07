import { describe, expect, it } from "vitest";
import type { MappedTable, SourceSummary, SourceView, ValidationIssue } from "../../src/curation-app/api/types";
import { columnLetters, mappedGrid, sourceProblems } from "../../src/curation-app/sources";

describe("columnLetters", () => {
  it("names columns as a spreadsheet does", () => {
    expect([0, 1, 25, 26, 27, 51, 52, 701, 702].map(columnLetters)).toEqual([
      "A",
      "B",
      "Z",
      "AA",
      "AB",
      "AZ",
      "BA",
      "ZZ",
      "AAA",
    ]);
  });
});

describe("mappedGrid", () => {
  const table: MappedTable = {
    file: "outputs_Tab2.tsv",
    kind: "outputs",
    shared: false,
    header: ["study", "source", "label", "mean", "sd", "comment"],
    rows: [
      [2, ["Example", "Tab2", "caf_cl", "1.2", "", ""]],
      [3, ["Example", "Tab2", "caf_thalf", "4.8", "0.3", ""]],
      [4, ["Example", "Tab2", "caf_vd", "0.7", "", ""]],
    ],
  };

  it("makes the mapped rows a table and leaves out the study and source columns and empty columns", () => {
    const { grid, columns } = mappedGrid(table);
    expect(grid).toEqual({
      file: "outputs_Tab2.tsv",
      kind: "table",
      header: table.header,
      rows: table.rows.map(([line, cells]) => ({ line, cells })),
    });
    expect(columns.map((index) => table.header[index])).toEqual(["label", "mean", "sd"]);
  });

  it("keeps every row: the grid renders many rows as they scroll into view", () => {
    const rows: MappedTable["rows"] = Array.from({ length: 700 }, (_, index) => [
      index + 2,
      ["Example", "Tab2", `r${index}`, "", "", ""],
    ]);
    const { grid, columns } = mappedGrid({ ...table, rows });
    expect(grid.rows).toHaveLength(700);
    expect(columns.map((index) => table.header[index])).toEqual(["label"]);
  });
});

describe("sourceProblems", () => {
  const summary: SourceSummary = {
    source: "Tab2",
    kind: "table",
    image: "Example_Tab2.png",
    raw: "Example_Tab2.tsv",
    raw_kind: "table",
    tables: ["outputs_Tab2.tsv", "subjects.tsv"],
    missing_image: null,
    missing_raw: null,
  };
  const view: SourceView = {
    source: "Tab2",
    image: "Example_Tab2.png",
    image_url: "/x.png",
    image_size: [10, 10],
    raw_grid: [["a"]],
    digitization: null,
    mapped: [
      // A table of the source has its problems at any line; a shared one only at the lines of the source.
      { file: "outputs_Tab2.tsv", kind: "outputs", header: ["label"], rows: [[2, ["a"]]], shared: false },
      { file: "subjects.tsv", kind: "subjects", header: ["name"], rows: [[4, ["all"]]], shared: true },
    ],
    overlay: [],
    unmatched: [],
    layout: "side_by_side",
    points: [],
    series: [],
  };
  function issue(file: string, row: number | null = null): ValidationIssue {
    return { code: "c", severity: "warning", message: `${file} ${row}`, source: { file, row } };
  }

  it("keeps the problems of the files of the source and of its rows in shared tables", () => {
    const problems = [
      issue("Example_Tab2.tsv", 3),
      issue("Example_Tab2.png"),
      issue("outputs_Tab2.tsv", 9),
      issue("outputs_Tab2.tsv"),
      issue("subjects.tsv", 4),
      issue("subjects.tsv", 5),
      issue("subjects.tsv"),
      issue("study.json"),
      { code: "c", severity: "error", message: "whole study" } satisfies ValidationIssue,
    ];
    expect(sourceProblems(problems, summary, view).map((entry) => entry.message)).toEqual([
      "Example_Tab2.tsv 3",
      "Example_Tab2.png null",
      "outputs_Tab2.tsv 9",
      "outputs_Tab2.tsv null",
      "subjects.tsv 4",
    ]);
  });
});
