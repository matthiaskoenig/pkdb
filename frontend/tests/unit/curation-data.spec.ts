import { describe, expect, it } from "vitest";
import type { Problem, StudyDetail, TableResponse } from "../../src/curation-app/api/types";
import {
  ALL_ROWS,
  defaultFile,
  fileCounts,
  fileForSource,
  filterChoices,
  filteredLines,
  filterOf,
  filterValue,
  firstSource,
  isShared,
  ownerOf,
  PAPER,
  rowSource,
  selectionOf,
  selectionQuery,
  sourceCounts,
  sourceOfFile,
  tablesByInfo,
} from "../../src/curation-app/data";
import { paperFile, reviewItem, sourceSummary, studyDetail, tableEntry } from "./curation-fixtures";

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

function problem(file: string, row: number | null = null, severity: Problem["severity"] = "error"): Problem {
  return { code: "c", severity, message: "m", source: { file, row }, acknowledgeable: false };
}

function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({
    sources: [fig1, tab2, text],
    tables: [
      tableEntry("subjects.tsv", "subjects"),
      tableEntry("interventions.tsv", "interventions"),
      tableEntry("outputs_Tab2.tsv", "outputs"),
      tableEntry("timecourses_Fig1.tsv", "timecourses"),
      tableEntry("Example_Tab2.tsv", "raw"),
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
  it("keeps the current file when the source owns it", () => {
    expect(fileForSource(detail(), tab2, "Example_Tab2.tsv")).toBe("Example_Tab2.tsv");
  });

  it("leaves a shared table for the first table of the source, although the source has rows in it", () => {
    expect(fileForSource(detail(), fig1, "subjects.tsv")).toBe("timecourses_Fig1.tsv");
    expect(fileForSource(detail(), tab2, "subjects.tsv")).toBe("outputs_Tab2.tsv");
  });

  it("opens the first table of the source in the order of the study page, its raw table last", () => {
    expect(fileForSource(detail(), tab2, "timecourses_Fig1.tsv")).toBe("outputs_Tab2.tsv");
    expect(fileForSource(detail(), fig1, null)).toBe("timecourses_Fig1.tsv");
    const rawOnly = detail({ tables: detail().tables.filter((table) => table.file !== "outputs_Tab2.tsv") });
    expect(fileForSource(rawOnly, tab2, "subjects.tsv")).toBe("Example_Tab2.tsv");
  });

  it("keeps a shared current table for a source without tables of its own, else opens the first table naming it", () => {
    const named = sourceSummary({ source: "Text", kind: "text", tables: ["interventions.tsv"] });
    expect(fileForSource(detail(), named, "subjects.tsv")).toBe("subjects.tsv");
    expect(fileForSource(detail(), named, "interventions.tsv")).toBe("interventions.tsv");
    // A table of another source is not kept: its rows all name that other source.
    expect(fileForSource(detail(), named, "outputs_Tab2.tsv")).toBe("interventions.tsv");
    expect(fileForSource(detail(), named, "Example_Tab2.tsv")).toBe("interventions.tsv");
    const textual = sourceSummary({ source: "Text", kind: "text", tables: ["subjects.tsv"] });
    expect(fileForSource(detail(), textual, "outputs_Tab2.tsv")).toBe("subjects.tsv");
    const unnamed = sourceSummary({ source: "Text", kind: "text" });
    expect(fileForSource(detail(), unnamed, "outputs_Tab2.tsv")).toBe("outputs_Tab2.tsv");
    expect(fileForSource(detail(), named, "gone.tsv")).toBe("interventions.tsv");
    expect(fileForSource(detail(), named, null)).toBe("interventions.tsv");
    expect(fileForSource(detail(), text, null)).toBe("subjects.tsv");
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
    expect(counts.problems.get("outputs_Tab2.tsv")).toEqual({ errors: 2, warnings: 0 });
    expect(counts.items.get("timecourses_Fig1.tsv")).toBe(1);
    expect(counts.items.size).toBe(1);
  });

  it("counts for a source its image, raw extraction and own tables, not the shared tables", () => {
    expect(sourceCounts(counted, tab2)).toEqual({ errors: 2, warnings: 0, items: 0 });
    expect(sourceCounts(counted, fig1)).toEqual({ errors: 1, warnings: 0, items: 1 });
    expect(sourceCounts(counted, text)).toEqual({ errors: 0, warnings: 0, items: 0 });
  });

  it("counts errors and warnings apart, any other severity as a warning", () => {
    const mixed = detail({
      problems: [
        problem("outputs_Tab2.tsv", 1, "warning"),
        problem("outputs_Tab2.tsv", 2, "warning"),
        problem("outputs_Tab2.tsv", 3),
        problem("Example_Fig1.png", null, "warning"),
        { ...problem("timecourses_Fig1.tsv"), severity: "info" as never },
      ],
    });
    const counts = fileCounts(mixed);
    expect(counts.problems.get("outputs_Tab2.tsv")).toEqual({ errors: 1, warnings: 2 });
    expect(counts.problems.get("Example_Fig1.png")).toEqual({ errors: 0, warnings: 1 });
    expect(counts.problems.get("timecourses_Fig1.tsv")).toEqual({ errors: 0, warnings: 1 });
    expect(sourceCounts(mixed, tab2)).toEqual({ errors: 1, warnings: 2, items: 0 });
    expect(sourceCounts(mixed, fig1)).toEqual({ errors: 0, warnings: 2, items: 0 });
  });

  it("counts the warnings of a shared table for no source", () => {
    const shared = detail({ problems: [problem("subjects.tsv", 2, "warning"), problem("subjects.tsv", 3)] });
    expect(fileCounts(shared).problems.get("subjects.tsv")).toEqual({ errors: 1, warnings: 1 });
    expect(sourceCounts(shared, fig1)).toEqual({ errors: 0, warnings: 0, items: 0 });
    expect(sourceCounts(shared, tab2)).toEqual({ errors: 0, warnings: 0, items: 0 });
  });

  it("opens the first table with problems or open review items, else the first table, else none", () => {
    expect(defaultFile(detail({ problems: [problem("timecourses_Fig1.tsv", 2, "warning")] }))).toBe("timecourses_Fig1.tsv");
    const review = studyDetail().review;
    const items = { ...review, value: { ...review.value!, items: [reviewItem({ target: { file: "outputs_Tab2.tsv" } })] } };
    expect(defaultFile(detail({ review: items }))).toBe("outputs_Tab2.tsv");
    // A problem of an image counts for no table.
    expect(defaultFile(detail({ problems: [problem("Example_Fig1.png")] }))).toBe("subjects.tsv");
    expect(defaultFile(detail({ tables: [] }))).toBeNull();
  });

  it("shows a table beside its own source, and a shared table beside the paper, else the first source", () => {
    const withPaper = detail({ papers: [paperFile("Example.pdf")] });
    expect(sourceOfFile(withPaper, "outputs_Tab2.tsv")).toBe("Tab2");
    expect(sourceOfFile(withPaper, "Example_Tab2.tsv")).toBe("Tab2");
    expect(sourceOfFile(withPaper, "subjects.tsv")).toBe(PAPER);
    expect(sourceOfFile(withPaper, null)).toBe(PAPER);
    expect(sourceOfFile(detail(), "subjects.tsv")).toBe("Fig1");
    expect(sourceOfFile(detail(), null)).toBe("Fig1");
    expect(firstSource(detail({ sources: [] }))).toBeNull();
    expect(firstSource(detail({ sources: [], papers: [paperFile("Example.pdf")] }))).toBe(PAPER);
    expect(sourceOfFile(detail({ sources: [] }), "outputs_Tab2.tsv")).toBeNull();
  });
});

describe("rows and their sources", () => {
  it("reads the source of a row, or null without one", () => {
    expect(rowSource(subjects, 3)).toBe("Fig1");
    expect(rowSource(subjects, 4)).toBeNull();
    expect(rowSource(subjects, 99)).toBeNull();
    expect(rowSource({ file: "Example_Tab2.tsv", kind: "raw", rows: [{ line: 1, cells: ["a"] }] }, 1)).toBeNull();
  });

  it("offers All, each source that the rows name in natural order, and No source, with their rows", () => {
    const named: TableResponse = {
      ...subjects,
      rows: [...subjects.rows, { line: 5, cells: ["Example", "S15", "Tab10"] }, { line: 6, cells: ["Example", "S16", "Tab2"] }],
    };
    expect(filterChoices(named)).toEqual([
      { value: "all", title: "All (5)" },
      { value: "source:Fig1", title: "Fig1 (1)" },
      { value: "source:Tab2", title: "Tab2 (2)" },
      { value: "source:Tab10", title: "Tab10 (1)" },
      { value: "none", title: "No source (1)" },
    ]);
    expect(filterChoices({ file: "x.tsv", kind: "raw", rows: [{ line: 1, cells: [] }] })).toEqual([]);
  });

  it("shows the lines of a source, of no source, or all of them", () => {
    expect(filteredLines(subjects, ALL_ROWS)).toBeNull();
    expect([...filteredLines(subjects, { kind: "source", source: "Tab2" })!]).toEqual([2]);
    expect([...filteredLines(subjects, { kind: "none" })!]).toEqual([4]);
    expect(filteredLines({ file: "x.tsv", kind: "raw", rows: [{ line: 1, cells: [] }] }, { kind: "none" })).toBeNull();
  });

  it("writes a filter as the value of an option and reads it back", () => {
    for (const filter of [ALL_ROWS, { kind: "none" } as const, { kind: "source", source: "Tab2" } as const])
      expect(filterOf(filterValue(filter))).toEqual(filter);
    expect(filterOf("anything else")).toEqual(ALL_ROWS);
  });
});

describe("tables by class of information", () => {
  it("groups the tables in the order of the navigator, each class in the order of the study page", () => {
    const study = detail({
      tables: [
        tableEntry("subjects.tsv", "subjects"),
        tableEntry("interventions.tsv", "interventions"),
        tableEntry("characteristica.tsv", "characteristica"),
        tableEntry("outputs_Tab2.tsv", "outputs"),
        tableEntry("timecourses_Fig1.tsv", "timecourses"),
        tableEntry("Example_Tab2.tsv", "raw"),
      ],
    });
    expect(tablesByInfo(study).map(({ info, tables }) => [info, tables.map((table) => table.file)])).toEqual([
      ["subjects", ["subjects.tsv", "characteristica.tsv"]],
      ["interventions", ["interventions.tsv"]],
      ["data", ["outputs_Tab2.tsv", "timecourses_Fig1.tsv"]],
      ["raw", ["Example_Tab2.tsv"]],
    ]);
  });

  it("leaves out the classes without tables", () => {
    const study = detail({ tables: [tableEntry("Example_Tab2.tsv", "raw"), tableEntry("subjects.tsv", "subjects")] });
    expect(tablesByInfo(study).map((group) => group.info)).toEqual(["subjects", "raw"]);
    expect(tablesByInfo(detail({ tables: [] }))).toEqual([]);
  });
});
