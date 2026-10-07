import { describe, expect, it } from "vitest";
import type { SourceLocation, ValidationIssue } from "../../src/curation-app/api/types";
import {
  acknowledgement,
  DID_YOU_MEAN,
  filterIssues,
  groupByFile,
  groupCounts,
  isLimitIssue,
  location,
  locationKey,
  noIssuesText,
  severityCounts,
  suggestionText,
  tableQuery,
} from "../../src/curation-app/problems";

function issue(
  code: string,
  severity: ValidationIssue["severity"],
  source: SourceLocation | null = null,
  changes: Partial<ValidationIssue> = {},
): ValidationIssue {
  return { code, severity, message: `${code} message`, source, ...changes };
}

/** A cell of a TSV table as the library locates it: the sheet is the table, the cell its column letter and line. */
function cell(file: string, row: number, header: string, letter: string): SourceLocation {
  const sheet = file.replace(/\.tsv$/, "");
  return { file, sheet, row, column: letter, cell: `${letter}${row}`, header };
}

const mean = issue("outside_range", "warning", cell("timecourses_Fig1.tsv", 6, "mean", "O"));
const unit = issue("unit_dimension", "error", cell("outputs_Tab2.tsv", 2, "unit", "X"));
const group = issue("unknown_reference", "error", cell("outputs_Tab2.tsv", 3, "group", "E"));
const header = issue("unknown_column", "error", { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2" });
const study = issue("invalid_study_json", "error", { file: "study.json" });
const limit = issue("row_limit", "error", null, { message: "The study tables have more than 1000000 rows" });
const unused = issue("unused_intervention", "warning", cell("interventions.tsv", 3, "name", "B"));

describe("groupByFile", () => {
  it("groups the issues by file, the files with errors first, and by line within a file", () => {
    const groups = groupByFile([unused, group, mean, study, unit, header, limit]);
    // Each in the order of their first issue.
    expect(groups.map((entry) => entry.file)).toEqual([
      "outputs_Tab2.tsv",
      "study.json",
      null,
      "interventions.tsv",
      "timecourses_Fig1.tsv",
    ]);
    // The issues of the whole file come first, then those of a line, by line.
    expect(groups[0]!.issues).toEqual([header, unit, group]);
    expect(groups[2]!.issues).toEqual([limit]);
  });

  it("has no groups without issues", () => {
    expect(groupByFile([])).toEqual([]);
  });
});

describe("location", () => {
  it("names the file, line, column and the cell of the workbook sheet", () => {
    expect(location(mean)).toBe("timecourses_Fig1.tsv · line 6 · mean · sheet cell timecourses_Fig1!O6");
    expect(location(mean, { file: false })).toBe("line 6 · mean · sheet cell timecourses_Fig1!O6");
  });

  it("names what it knows: a line, or the file alone", () => {
    const line = issue("duplicate_observation", "warning", { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row: 4 });
    expect(location(line)).toBe("outputs_Tab2.tsv · line 4");
    expect(location(study)).toBe("study.json");
    expect(location(study, { file: false })).toBe("");
    expect(location(limit)).toBe("");
  });

  it("names the sheet and its row for an issue of the workbook", () => {
    const sheet = issue("formula_value", "warning", { file: "Example.xlsx", sheet: "timecourses_Fig1", row: 4 });
    expect(location(sheet)).toBe("Example.xlsx · row 4 · sheet timecourses_Fig1");
    const located = issue("formula_value", "warning", {
      file: "Example.xlsx",
      sheet: "timecourses_Fig1",
      row: 4,
      column: "C",
      cell: "C4",
      header: "time",
    });
    expect(location(located)).toBe("Example.xlsx · row 4 · time · sheet cell timecourses_Fig1!C4");
  });
});

describe("severity", () => {
  const issues = [mean, unit, group, unused];

  it("filters and counts the issues of a severity", () => {
    expect(filterIssues(issues, "all")).toEqual(issues);
    expect(filterIssues(issues, "error")).toEqual([unit, group]);
    expect(filterIssues(issues, "warning")).toEqual([mean, unused]);
    expect(severityCounts(issues)).toEqual({ all: 4, error: 2, warning: 2 });
  });

  it("counts the issues of a file and says when a filter leaves none", () => {
    expect(groupCounts([unit, group, mean])).toBe("2 errors · 1 warning");
    expect(groupCounts([mean])).toBe("1 warning");
    expect(noIssuesText("all")).toBe("No errors or warnings.");
    expect(noIssuesText("error")).toBe("No errors.");
    expect(noIssuesText("warning")).toBe("No warnings.");
  });

  it("knows the issues of the upload limits", () => {
    expect(isLimitIssue(limit)).toBe(true);
    expect(isLimitIssue(issue("file_limit", "error"))).toBe(true);
    expect(isLimitIssue(unit)).toBe(false);
  });
});

describe("suggestionText", () => {
  it("offers the candidates of a spelling suggestion as Did you mean", () => {
    expect(suggestionText({ kind: "fix", message: DID_YOU_MEAN, candidates: ["all", "smokers"] })).toEqual({
      text: "Did you mean: all, smokers",
      candidates: [],
    });
  });

  it("shows a hint with its candidates, as the command line does", () => {
    const hint = "Units of cmax; amounts convert with the molar mass.";
    expect(suggestionText({ kind: "fix", message: hint, candidates: ["g/l", 1] })).toEqual({
      text: hint,
      candidates: ["g/l", "1"],
    });
    expect(suggestionText({ kind: "fix", message: "Close the workbook first." })).toEqual({
      text: "Close the workbook first.",
      candidates: [],
    });
  });
});

describe("links and acknowledgements", () => {
  it("shows a cell in its table by file, line and column", () => {
    expect(tableQuery(mean)).toEqual({ file: "timecourses_Fig1.tsv", line: "6", column: "mean" });
    expect(tableQuery(header)).toEqual({ file: "outputs_Tab2.tsv" });
    expect(tableQuery(limit)).toBeNull();
  });

  it("acknowledges a warning at its file, line and column", () => {
    expect(acknowledgement(mean)).toEqual({
      code: "outside_range",
      file: "timecourses_Fig1.tsv",
      line: 6,
      column: "mean",
    });
    const whole = issue("digitized_mismatch", "warning", { file: "Example_Fig1.wpd.json", path: [] });
    expect(acknowledgement(whole)).toEqual({ code: "digitized_mismatch", file: "Example_Fig1.wpd.json" });
  });

  it("acknowledges no error and no warning without a file", () => {
    expect(acknowledgement(unit)).toBeNull();
    expect(acknowledgement(issue("unknown_dataset", "warning"))).toBeNull();
  });

  it("keys a warning by the location that an acknowledgement covers", () => {
    expect(locationKey(mean)).toBe(locationKey({ ...mean, message: "Another message" }));
    expect(locationKey(mean)).not.toBe(locationKey(unused));
    expect(locationKey(mean)).not.toBe(locationKey({ ...mean, source: { ...mean.source!, header: "sd" } }));
  });
});
