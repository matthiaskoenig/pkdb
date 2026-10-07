import { describe, expect, it } from "vitest";
import type { ReviewItem, TableRow } from "../../src/curation-app/api/types";
import {
  emptyText,
  filterItems,
  matchText,
  matchingRows,
  seriesOfTarget,
  shownColumns,
  stateCounts,
  targetText,
} from "../../src/curation-app/review";
import { reviewItem } from "./curation-fixtures";

function item(id: string, kind: ReviewItem["kind"], state: ReviewItem["state"]): ReviewItem {
  return reviewItem({ id, kind, state });
}

const items = [
  item("A", "question", "open"),
  item("B", "uncertainty", "open"),
  item("C", "issue", "resolved"),
  item("D", "question", "dismissed"),
  item("E", "question", "resolved"),
];

describe("filterItems", () => {
  it("keeps the items of a state", () => {
    expect(filterItems(items, "open", "all").map((entry) => entry.id)).toEqual(["A", "B"]);
    expect(filterItems(items, "resolved", "all").map((entry) => entry.id)).toEqual(["C", "E"]);
    expect(filterItems(items, "dismissed", "all").map((entry) => entry.id)).toEqual(["D"]);
    expect(filterItems(items, "all", "all")).toHaveLength(5);
  });

  it("keeps the items of a kind", () => {
    expect(filterItems(items, "all", "question").map((entry) => entry.id)).toEqual(["A", "D", "E"]);
    expect(filterItems(items, "resolved", "question").map((entry) => entry.id)).toEqual(["E"]);
    expect(filterItems(items, "open", "issue")).toEqual([]);
  });
});

describe("stateCounts", () => {
  it("counts the items of each state chip within the kind", () => {
    expect(stateCounts(items, "all")).toEqual({ open: 2, resolved: 2, dismissed: 1, all: 5 });
    expect(stateCounts(items, "question")).toEqual({ open: 1, resolved: 1, dismissed: 1, all: 3 });
  });
});

describe("emptyText", () => {
  it("names the state and the kind that no item has", () => {
    expect(emptyText("all", "all")).toBe("No review items yet.");
    expect(emptyText("open", "all")).toBe("No open items.");
    expect(emptyText("dismissed", "uncertainty")).toBe("No dismissed uncertainties.");
    expect(emptyText("all", "issue")).toBe("No issues.");
  });
});

describe("targetText", () => {
  it("names the whole study without a file", () => {
    expect(targetText(undefined)).toBe("whole study");
    expect(targetText(null)).toBe("whole study");
    expect(targetText({})).toBe("whole study");
    expect(targetText({ rows: {} })).toBe("whole study");
  });

  it("names the file, the rows and the column", () => {
    expect(targetText({ file: "outputs_Tab2.tsv" })).toBe("outputs_Tab2.tsv");
    expect(targetText({ file: "outputs_Tab2.tsv", column: "mean" })).toBe("outputs_Tab2.tsv · column mean");
    expect(targetText({ file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150" } })).toBe(
      "timecourses_Fig1.tsv · label = caf_plasma_D150",
    );
    expect(
      targetText({ file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150" }, column: "error_type" }),
    ).toBe("timecourses_Fig1.tsv · label = caf_plasma_D150 · column error_type");
    expect(targetText({ file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150", time: "0.5" } })).toBe(
      "timecourses_Fig1.tsv · label = caf_plasma_D150, time = 0.5",
    );
  });
});

describe("seriesOfTarget", () => {
  it("maps the label rows of a timecourse table to the series of its figure", () => {
    expect(seriesOfTarget({ file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150" } })).toEqual({
      source: "Fig1",
      series: "caf_plasma_D150",
    });
    expect(
      seriesOfTarget({ file: "timecourses_Fig2A.tsv", rows: { label: "caf_plasma", time: "1" }, column: "mean" }),
    ).toEqual({ source: "Fig2A", series: "caf_plasma" });
  });

  it("is null for other targets", () => {
    expect(seriesOfTarget(undefined)).toBeNull();
    expect(seriesOfTarget({})).toBeNull();
    expect(seriesOfTarget({ file: "timecourses_Fig1.tsv" })).toBeNull();
    expect(seriesOfTarget({ file: "timecourses_Fig1.tsv", rows: { subjects: "all" } })).toBeNull();
    expect(seriesOfTarget({ file: "timecourses_Fig1.tsv", rows: { label: "" } })).toBeNull();
    expect(seriesOfTarget({ file: "outputs_Tab2.tsv", rows: { label: "clearance" } })).toBeNull();
    expect(seriesOfTarget({ file: "timecourses_Tab2.tsv", rows: { label: "caf_plasma" } })).toBeNull();
  });
});

const header = ["label", "time", "mean", "comment"];
const rows: TableRow[] = [
  { line: 2, cells: ["caf_plasma_D150", "0", "0.166", ""] },
  { line: 3, cells: ["caf_plasma_D150", "0.5", "2.419", ""] },
  { line: 4, cells: ["caf_plasma_D300", "0", "0.2", "smoker"] },
];

describe("matchingRows", () => {
  it("keeps the rows with every value of the filters", () => {
    expect(matchingRows(header, rows, { label: "caf_plasma_D150" }).map((row) => row.line)).toEqual([2, 3]);
    expect(matchingRows(header, rows, { label: "caf_plasma_D150", time: "0.5" }).map((row) => row.line)).toEqual([3]);
    expect(matchingRows(header, rows, {}).map((row) => row.line)).toEqual([2, 3, 4]);
  });

  it("compares the cells as printed and matches nothing for an unknown column", () => {
    expect(matchingRows(header, rows, { time: "0.50" })).toEqual([]);
    expect(matchingRows(header, rows, { dose: "150" })).toEqual([]);
    expect(matchingRows(header, rows, { comment: "" }).map((row) => row.line)).toEqual([2, 3]);
  });
});

describe("matchText", () => {
  it("counts the rows that a filter matches", () => {
    expect(matchText(2, 3)).toBe("Matches 2 of 3 rows.");
    expect(matchText(1, 1)).toBe("Matches 1 of 1 row.");
    expect(matchText(0, 1200)).toBe("Matches none of 1,200 rows.");
  });
});

describe("shownColumns", () => {
  it("hides the columns that are empty in every row unless the target names them", () => {
    expect(shownColumns(header, rows.slice(0, 2), [])).toEqual([0, 1, 2]);
    expect(shownColumns(header, rows.slice(0, 2), ["comment"])).toEqual([0, 1, 2, 3]);
    expect(shownColumns(header, rows, [])).toEqual([0, 1, 2, 3]);
    expect(shownColumns(header, [], [])).toEqual([]);
  });
});
