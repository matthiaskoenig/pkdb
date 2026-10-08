import { describe, expect, it } from "vitest";
import { ApiError } from "../../src/curation-app/api/client";
import type { AcknowledgedWarning, Job, SourceLocation, ValidationIssue } from "../../src/curation-app/api/types";
import {
  acknowledgeFailure,
  acknowledgement,
  AMBIGUOUS_WARNING,
  NO_EXACT_TARGET,
  filterIssues,
  groupByFile,
  groupCounts,
  isLimitIssue,
  location,
  locationKey,
  lastWrite,
  NO_SUCH_WARNING,
  noIssuesText,
  reportAfter,
  scopeText,
  severityCounts,
  suggestionView,
  tableQuery,
  validatesAfterWrite,
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

describe("suggestionView", () => {
  it("offers the candidates of a spelling suggestion after Did you mean", () => {
    // The kind decides, not the message.
    expect(suggestionView({ kind: "did_you_mean", message: "Any message.", candidates: ["all", "smokers"] })).toEqual({
      lead: "Did you mean:",
      candidates: ["all", "smokers"],
      note: null,
    });
  });

  it("offers term suggestions after Did you mean, with their caveat", () => {
    const caveat = "Candidates are spelling suggestions, not equivalent terms.";
    expect(
      suggestionView({ kind: "check_vocabulary", message: caveat, candidates: ["plasma", "saliva/plasma"] }),
    ).toEqual({ lead: "Did you mean:", candidates: ["plasma", "saliva/plasma"], note: caveat });
    // Without candidates, the caveat alone is the message.
    expect(suggestionView({ kind: "check_vocabulary", message: caveat, candidates: [] })).toEqual({
      lead: caveat,
      candidates: [],
      note: null,
    });
  });

  it("shows another hint before its candidates", () => {
    const hint = "Units of cmax; amounts convert with the molar mass.";
    expect(suggestionView({ kind: "fix", message: hint, candidates: ["g/l", 1] })).toEqual({
      lead: hint,
      candidates: ["g/l", "1"],
      note: null,
    });
    expect(suggestionView({ kind: "fix", message: "Close the workbook first." })).toEqual({
      lead: "Close the workbook first.",
      candidates: [],
      note: null,
    });
    // A hint with the message of another kind keeps its kind.
    expect(suggestionView({ kind: "fix", message: "Did you mean one of these?", candidates: ["a"] }).lead).toBe(
      "Did you mean one of these?",
    );
  });
});

describe("links and acknowledgements", () => {
  it("shows a cell in its table by file, line and column", () => {
    expect(tableQuery(mean)).toEqual({ file: "timecourses_Fig1.tsv", line: "6", column: "mean" });
    expect(tableQuery(header)).toEqual({ file: "outputs_Tab2.tsv" });
    expect(tableQuery(limit)).toBeNull();
  });

  it("names the cell of a raw table by its column letter, as the grid of the Tables section does", () => {
    const raw = issue("invalid_encoding", "error", {
      file: "Example_Tab2.tsv",
      sheet: "Example_Tab2",
      row: 3,
      column: "B",
      cell: "B3",
    });
    expect(tableQuery(raw)).toEqual({ file: "Example_Tab2.tsv", line: "3", column: "B" });
  });

  it("acknowledges a warning at exactly its file, line, column and key", () => {
    expect(acknowledgement(mean)).toEqual({
      code: "outside_range",
      file: "timecourses_Fig1.tsv",
      line: 6,
      column: "mean",
      key: null,
    });
    // A null line, column or key matches only warnings without one, never every line.
    const whole = issue("digitized_mismatch", "warning", { file: "Example_Fig1.wpd.json", path: [] });
    expect(acknowledgement(whole)).toEqual({
      code: "digitized_mismatch",
      file: "Example_Fig1.wpd.json",
      line: null,
      column: null,
      key: null,
    });
    const row = issue("duplicate_observation", "warning", { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row: 4 });
    expect(acknowledgement(row)).toMatchObject({ line: 4, column: null, key: null });
    // A warning of a whole file is told apart from the others of its code by its key.
    const legend = issue("unknown_dataset", "warning", { file: "Example_Fig1.wpd.json", path: [], key: "legend" });
    expect(acknowledgement(legend)).toEqual({
      code: "unknown_dataset",
      file: "Example_Fig1.wpd.json",
      line: null,
      column: null,
      key: "legend",
    });
  });

  it("names the key of a warning of a whole file in its location", () => {
    const legend = issue("unknown_dataset", "warning", { file: "Example_Fig1.wpd.json", path: [], key: "legend" });
    expect(location(legend)).toBe("Example_Fig1.wpd.json · legend");
    expect(location(legend, { file: false })).toBe("legend");
  });

  it("says plainly that a warning is no longer in the files", () => {
    const gone = new ApiError(422, { error: "No warning [x] in a.tsv matches", issues: [], code: "no_such_warning" });
    expect(acknowledgeFailure(gone)).toEqual({ kind: "error", text: NO_SUCH_WARNING, issues: [] });
    expect(NO_SUCH_WARNING).toBe("This warning is not in the current files. Validate the study and try again.");
    const several = "2 warnings [x] match in a.tsv at line 3, line 4; give the line, column and key of one";
    const ambiguous = new ApiError(422, { error: several, issues: [], code: "ambiguous_warning" });
    expect(acknowledgeFailure(ambiguous)).toEqual({ kind: "error", text: AMBIGUOUS_WARNING, issues: [] });
    expect(AMBIGUOUS_WARNING).toBe("Several warnings match this location. Validate the study and try again.");
    const inexact = new ApiError(422, {
      error: "The warning [x] in a.wpd.json has no row of a data table and no key, so it cannot be acknowledged alone.",
      issues: [],
      code: "no_exact_target",
    });
    expect(acknowledgeFailure(inexact)).toEqual({ kind: "error", text: NO_EXACT_TARGET, issues: [] });
    expect(NO_EXACT_TARGET).toBe("This warning cannot be acknowledged on its own.");
    // Any other refusal keeps the message of the server after the lead.
    const other = new ApiError(422, { error: "Expected text in text", issues: [] });
    expect(acknowledgeFailure(other)).toEqual({
      kind: "error",
      text: "The warning was not acknowledged. Expected text in text",
      issues: [],
    });
  });

  it("knows when the local server validates after a write", () => {
    const state = { paused: false, offline: false, account: "mkoenig", can_upload: true };
    expect(validatesAfterWrite("validate", state)).toBe(true);
    expect(validatesAfterWrite("upload", state)).toBe(true);
    expect(validatesAfterWrite("off", state)).toBe(false);
    expect(validatesAfterWrite("validate", { ...state, paused: true })).toBe(false);
    expect(validatesAfterWrite("upload", { ...state, offline: true })).toBe(false);
    expect(validatesAfterWrite("upload", { ...state, account: null })).toBe(false);
    expect(validatesAfterWrite("upload", { ...state, can_upload: false })).toBe(false);
    expect(validatesAfterWrite("validate", { ...state, offline: true, can_upload: false })).toBe(true);
    expect(validatesAfterWrite("validate", null)).toBe(true);
    expect(validatesAfterWrite("off", null)).toBe(false);
  });

  it("acknowledges no error and no warning without a file", () => {
    expect(acknowledgement(unit)).toBeNull();
    expect(acknowledgement(issue("unknown_dataset", "warning"))).toBeNull();
  });

  it("keys a warning by the location that an acknowledgement covers", () => {
    expect(locationKey(mean)).toBe(locationKey({ ...mean, message: "Another message" }));
    expect(locationKey(mean)).not.toBe(locationKey(unused));
    expect(locationKey(mean)).not.toBe(locationKey({ ...mean, source: { ...mean.source!, header: "sd" } }));
    // Two datasets of one project: one code in one file without a row, told apart by their keys.
    const dataset = (key: string) => issue("unknown_dataset", "warning", { file: "Example_Fig1.wpd.json", key });
    expect(locationKey(dataset("legend"))).not.toBe(locationKey(dataset("axis labels")));
    expect(locationKey(dataset("legend"))).toBe(locationKey({ ...dataset("legend"), message: "Another message" }));
  });

  it("says what an acknowledgement covers beyond its own warning", () => {
    const entry = (scope: AcknowledgedWarning["scope"], target: AcknowledgedWarning["target"]): AcknowledgedWarning => ({
      id: "01JA33A1B2C3D4E5F6G7H8J9K0",
      code: "digitized_mismatch",
      target,
      text: "Expected.",
      author: "curator",
      resolved_by: "curator",
      resolved: "2026-10-06T09:00:00Z",
      scope,
    });
    expect(scopeText(entry("study", null))).toBe("Covers every digitized_mismatch warning of the study, also later ones.");
    expect(scopeText(entry("file", { file: "timecourses_Fig1.tsv" }))).toBe(
      "Covers every digitized_mismatch warning in timecourses_Fig1.tsv, also later ones.",
    );
    expect(scopeText(entry("column", { file: "timecourses_Fig1.tsv", column: "mean" }))).toBe(
      "Covers every digitized_mismatch warning in column mean of timecourses_Fig1.tsv, also later ones.",
    );
    expect(scopeText(entry("rows", { file: "timecourses_Fig1.tsv", rows: { time: "1" }, column: "mean" }))).toBeNull();
    expect(scopeText(entry("key", { file: "Example_Fig1.wpd.json", key: "legend" }))).toBeNull();
  });

  it("ends a mark only with the report of a job queued after the write", () => {
    const at = (id: string, action: Job["action"], created: string): Job => ({
      id,
      study_id: "caffeine/Example",
      study_name: "Example",
      action,
      status: "succeeded",
      created_at: created,
      message: "",
      automatic: true,
      report_id: null,
    });
    const earlier = at("job-1", "validate", "2026-10-07T11:59:59.900000+00:00");
    const write = at("write-1", "write", "2026-10-07T12:00:00+00:00");
    const later = at("job-2", "validate", "2026-10-07T12:00:00.000001+00:00");
    expect(lastWrite([later, write, earlier])).toBe("2026-10-07T12:00:00+00:00");
    expect(lastWrite([earlier])).toBeNull();
    const mark = { key: "k", since: lastWrite([write, earlier]), report: "job-1" };
    expect(reportAfter({ jobs: [write, earlier], report_id: "job-1" }, mark)).toBe(false);
    expect(reportAfter({ jobs: [later, write, earlier], report_id: "job-2" }, mark)).toBe(true);
    // A job queued before the write that reports after it does not end the mark.
    const running = at("job-3", "validate", "2026-10-07T11:59:59.950000+00:00");
    expect(reportAfter({ jobs: [write, running, earlier], report_id: "job-3" }, mark)).toBe(false);
    // Without the job of the report or the time of the write, another report ends the mark.
    expect(reportAfter({ jobs: [], report_id: "job-9" }, mark)).toBe(true);
    expect(reportAfter({ jobs: [], report_id: "job-1" }, mark)).toBe(false);
    expect(reportAfter({ jobs: [later], report_id: "job-2" }, { ...mark, since: null })).toBe(true);
  });
});
