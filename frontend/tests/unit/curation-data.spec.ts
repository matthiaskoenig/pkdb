import { describe, expect, it } from "vitest";
import type { Problem, StudyDetail, TableResponse } from "../../src/curation-app/api/types";
import {
  defaultSource,
  fileCounts,
  fileForSource,
  isShared,
  ownerOf,
  rowSource,
  selectionOf,
  selectionQuery,
  sourceCounts,
  sourceLines,
} from "../../src/curation-app/data";
import { reviewItem, sourceSummary, studyDetail } from "./curation-fixtures";

const fig1 = sourceSummary({
  source: "Fig1",
  kind: "figure",
  image: "Example_Fig1.png",
  raw: "Example_Fig1.wpd.json",
  raw_kind: "digitization",
  tables: ["timecourses_Fig1.tsv", "subjects.tsv"],
});
const tab2 = sourceSummary({
  source: "Tab2",
  image: "Example_Tab2.png",
  raw: "Example_Tab2.tsv",
  raw_kind: "table",
  tables: ["outputs_Tab2.tsv", "subjects.tsv"],
});
const text = sourceSummary({ source: "Text", kind: "text" });

function problem(file: string, row: number | null = null): Problem {
  return { code: "c", severity: "error", message: "m", source: { file, row }, acknowledgeable: false };
}

function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({
    sources: [fig1, tab2, text],
    tables: [
      { file: "subjects.tsv", kind: "subjects" },
      { file: "interventions.tsv", kind: "interventions" },
      { file: "outputs_Tab2.tsv", kind: "outputs" },
      { file: "timecourses_Fig1.tsv", kind: "timecourses" },
      { file: "Example_Tab2.tsv", kind: "raw" },
    ],
    ...changes,
  });
}

const subjects: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [
    { line: 2, cells: ["Example", "all", "Tab2"] },
    { line: 3, cells: ["Example", "S13", "Fig1"] },
    { line: 4, cells: ["Example", "S14", ""] },
  ],
};

describe("selection of the route", () => {
  it("reads source, file, a positive whole line and column, and drops empty values", () => {
    expect(selectionOf({ source: "Fig1", file: "subjects.tsv", line: "3", column: "name" })).toEqual({
      source: "Fig1",
      file: "subjects.tsv",
      line: 3,
      column: "name",
    });
    expect(selectionOf({ source: "", line: "0" })).toEqual({ source: null, file: null, line: null, column: null });
    expect(selectionOf({ line: "2.5" }).line).toBeNull();
    expect(selectionOf({ line: ["2", "3"] }).line).toBeNull();
  });

  it("writes only the parts of a selection that it has", () => {
    expect(selectionQuery({ source: "Fig1", file: null, line: 4, column: null })).toEqual({ source: "Fig1", line: "4" });
  });
});

describe("owners of table files", () => {
  it("knows the shared tables by their kind", () => {
    expect(isShared(detail(), "subjects.tsv")).toBe(true);
    expect(isShared(detail(), "outputs_Tab2.tsv")).toBe(false);
  });

  it("gives a raw table and a table of one source their source, and a shared table none", () => {
    expect(ownerOf(detail(), "Example_Tab2.tsv")).toBe("Tab2");
    expect(ownerOf(detail(), "outputs_Tab2.tsv")).toBe("Tab2");
    expect(ownerOf(detail(), "timecourses_Fig1.tsv")).toBe("Fig1");
    expect(ownerOf(detail(), "subjects.tsv")).toBeNull();
    expect(ownerOf(detail(), "unknown.tsv")).toBeNull();
  });
});

describe("the file of a source", () => {
  it("keeps the current file when the source owns it or has rows in the shared table", () => {
    expect(fileForSource(detail(), tab2, "Example_Tab2.tsv")).toBe("Example_Tab2.tsv");
    expect(fileForSource(detail(), fig1, "subjects.tsv")).toBe("subjects.tsv");
  });

  it("opens the first own table in workbook order, else the raw table, else the first table", () => {
    expect(fileForSource(detail(), tab2, "timecourses_Fig1.tsv")).toBe("outputs_Tab2.tsv");
    expect(fileForSource(detail(), fig1, null)).toBe("timecourses_Fig1.tsv");
    const rawOnly = sourceSummary({ source: "Tab2", raw: "Example_Tab2.tsv", raw_kind: "table" });
    expect(fileForSource(detail(), rawOnly, null)).toBe("Example_Tab2.tsv");
  });

  it("keeps a valid current file, else the first table, for a source without tables", () => {
    expect(fileForSource(detail(), text, "outputs_Tab2.tsv")).toBe("outputs_Tab2.tsv");
    expect(fileForSource(detail(), text, "gone.tsv")).toBe("subjects.tsv");
    expect(fileForSource(detail({ tables: [] }), text, null)).toBeNull();
  });
});

describe("counts", () => {
  const counted = detail({
    problems: [problem("outputs_Tab2.tsv", 3), problem("outputs_Tab2.tsv"), problem("Example_Fig1.png"), problem("subjects.tsv", 2)],
    review: {
      ...studyDetail().review,
      value: {
        ...studyDetail().review.value!,
        items: [
          reviewItem({ id: "a", state: "open", target: { file: "timecourses_Fig1.tsv" } }),
          reviewItem({ id: "b", state: "resolved", target: { file: "timecourses_Fig1.tsv" } }),
          reviewItem({ id: "c", state: "open" }),
        ],
      },
    },
  });

  it("counts the problems and the open review items of each file", () => {
    const counts = fileCounts(counted);
    expect(counts.problems.get("outputs_Tab2.tsv")).toBe(2);
    expect(counts.items.get("timecourses_Fig1.tsv")).toBe(1);
    expect(counts.items.size).toBe(1);
  });

  it("counts for a source its image, raw extraction and own tables, not the shared tables", () => {
    expect(sourceCounts(counted, tab2)).toEqual({ problems: 2, items: 0 });
    expect(sourceCounts(counted, fig1)).toEqual({ problems: 1, items: 1 });
    expect(sourceCounts(counted, text)).toEqual({ problems: 0, items: 0 });
  });

  it("opens the first source with problems, else the first source, else none", () => {
    expect(defaultSource(detail({ problems: [problem("outputs_Tab2.tsv")] }))?.source).toBe("Tab2");
    expect(defaultSource(detail())?.source).toBe("Fig1");
    expect(defaultSource(detail({ sources: [] }))).toBeNull();
  });
});

describe("rows and their sources", () => {
  it("reads the source of a row, or null without one", () => {
    expect(rowSource(subjects, 3)).toBe("Fig1");
    expect(rowSource(subjects, 4)).toBeNull();
    expect(rowSource(subjects, 99)).toBeNull();
    expect(rowSource({ file: "Example_Tab2.tsv", kind: "raw", rows: [{ line: 1, cells: ["a"] }] }, 1)).toBeNull();
  });

  it("lists the lines of a source; a table without a source column keeps all its lines", () => {
    expect([...sourceLines(subjects, "Tab2")]).toEqual([2]);
    expect([...sourceLines({ file: "x.tsv", kind: "raw", rows: [{ line: 1, cells: [] }] }, "Tab2")]).toEqual([1]);
  });
});
