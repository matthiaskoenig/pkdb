import { describe, expect, it } from "vitest";
import type { SourceSummary, SourceView, ValidationIssue } from "../../src/curation-app/api/types";
import { columnLetters } from "../../src/curation-app/columns";
import { sourceProblems } from "../../src/curation-app/sources";

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

describe("sourceProblems", () => {
  const summary: SourceSummary = {
    source: "Tab2",
    kind: "table",
    image: "Example_Tab2.png",
    image_url: "/x.png",
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
