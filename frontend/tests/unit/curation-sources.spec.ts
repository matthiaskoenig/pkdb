import { describe, expect, it } from "vitest";
import type { MappedTable, SourceSummary, SourceView, ValidationIssue } from "../../src/curation-app/api/types";
import { columnLetters, listedRows, missingFiles, sourceKind, sourceProblems } from "../../src/curation-app/sources";

describe("sourceKind", () => {
  it("tells paper tables, figures and the text apart", () => {
    expect(sourceKind("Tab2")).toBe("table");
    expect(sourceKind("TabS1")).toBe("table");
    expect(sourceKind("Fig1")).toBe("figure");
    expect(sourceKind("Fig2A")).toBe("figure");
    expect(sourceKind("Text")).toBe("text");
  });
});

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

describe("missingFiles", () => {
  const view: SourceView = {
    source: "Tab3",
    image: null,
    image_url: null,
    image_size: null,
    raw_grid: null,
    digitization: null,
    mapped: [],
    overlay: [],
    unmatched: [],
  };

  it("names the image and the raw extraction that a paper table lacks", () => {
    expect(missingFiles("Example", view)).toEqual({ image: "Example_Tab3.png", raw: "Example_Tab3.tsv" });
    expect(missingFiles("Example", { ...view, raw_grid: [["a"]], image: "Example_Tab3.png" })).toEqual({
      image: null,
      raw: null,
    });
  });

  it("names the WebPlotDigitizer project of a figure", () => {
    expect(missingFiles("Example", { ...view, source: "Fig2" })).toEqual({
      image: "Example_Fig2.png",
      raw: "Example_Fig2.wpd.json",
    });
    expect(missingFiles("Example", { ...view, source: "Fig2", digitization: "Example_Fig2.wpd.json" }).raw).toBeNull();
  });

  it("names nothing for the text, which has neither", () => {
    expect(missingFiles("Example", { ...view, source: "Text" })).toEqual({ image: null, raw: null });
  });
});

describe("listedRows", () => {
  const table: MappedTable = {
    file: "outputs_Tab2.tsv",
    kind: "outputs",
    header: ["study", "source", "label", "mean", "sd", "comment"],
    rows: [
      [2, ["Example", "Tab2", "caf_cl", "1.2", "", ""]],
      [3, ["Example", "Tab2", "caf_thalf", "4.8", "0.3", ""]],
      [4, ["Example", "Tab2", "caf_vd", "0.7", "", ""]],
    ],
  };

  it("leaves out the study and source columns and empty columns", () => {
    const listed = listedRows(table, 100);
    expect(listed.columns.map((index) => table.header[index])).toEqual(["label", "mean", "sd"]);
    expect(listed.rows.map((row) => row.line)).toEqual([2, 3, 4]);
    expect(listed.total).toBe(3);
  });

  it("lists at most the first rows", () => {
    const listed = listedRows(table, 2);
    expect(listed.rows.map((row) => row.line)).toEqual([2, 3]);
    expect(listed.total).toBe(3);
    // The columns follow the listed rows.
    expect(listedRows({ ...table, rows: table.rows.slice(0, 1) }, 2).columns.map((i) => table.header[i])).toEqual([
      "label",
      "mean",
    ]);
  });
});

describe("sourceProblems", () => {
  const summary: SourceSummary = {
    source: "Tab2",
    image: "Example_Tab2.png",
    raw: "Example_Tab2.tsv",
    raw_kind: "table",
    tables: ["outputs_Tab2.tsv", "subjects.tsv"],
  };
  const view: SourceView = {
    source: "Tab2",
    image: "Example_Tab2.png",
    image_url: "/x.png",
    image_size: [10, 10],
    raw_grid: [["a"]],
    digitization: null,
    mapped: [
      { file: "outputs_Tab2.tsv", kind: "outputs", header: ["label"], rows: [[2, ["a"]]] },
      { file: "subjects.tsv", kind: "subjects", header: ["name"], rows: [[4, ["all"]]] },
    ],
    overlay: [],
    unmatched: [],
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
