import { describe, expect, it } from "vitest";
import type { ReviewItem, TableRow } from "../../src/curation-app/api/types";
import {
  emptyText,
  filterItems,
  matchText,
  rowsAt,
  shownColumns,
  stateCounts,
  targetParts,
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
    expect(targetText(undefined)).toBe("Whole study");
    expect(targetText(null)).toBe("Whole study");
    expect(targetText({})).toBe("Whole study");
    expect(targetText({ rows: {} })).toBe("Whole study");
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

describe("targetParts", () => {
  const ID = "01JA2XK7Q8M3R5T6V9W0Y1Z2AB";
  const unmatched = reviewItem({ id: ID, kind: "uncertainty", text: "The error bars may be SE rather than SD, see the legend." });

  it("names the review item that a key of review.json is the id of, linked to it", () => {
    expect(targetParts({ file: "review.json", key: ID }, [unmatched])).toEqual([
      { text: "review.json · " },
      { text: "uncertainty “The error bars may be SE rather than SD…”", item: ID },
    ]);
  });

  it("keeps the text of other targets and of a key that names no item", () => {
    const keyed = { file: "Demo2020_Fig1.wpd.json", key: "legend" };
    expect(targetParts(keyed, [unmatched])).toEqual([{ text: "Demo2020_Fig1.wpd.json · legend" }]);
    expect(targetParts({ file: "review.json", key: ID }, [])).toEqual([{ text: `review.json · ${ID}` }]);
    expect(targetParts(null, [unmatched])).toEqual([{ text: "Whole study" }]);
  });
});

const header = ["label", "time", "mean", "comment"];
const rows: TableRow[] = [
  { line: 2, cells: ["caf_plasma_D150", "0", "0.166", ""] },
  { line: 3, cells: ["caf_plasma_D150", "0.5", "2.419", ""] },
  { line: 4, cells: ["caf_plasma_D300", "0", "0.2", "smoker"] },
];

describe("rowsAt", () => {
  it("keeps the rows at the lines, in their order in the table", () => {
    expect(rowsAt(rows, [4, 2]).map((row) => row.line)).toEqual([2, 4]);
    expect(rowsAt(rows, [3])).toEqual([rows[1]]);
  });

  it("keeps no row for no lines or lines that the table no longer has", () => {
    expect(rowsAt(rows, [])).toEqual([]);
    expect(rowsAt(rows, [7])).toEqual([]);
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
