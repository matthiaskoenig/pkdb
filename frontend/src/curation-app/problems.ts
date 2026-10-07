/**
 * The validation issues of the Problems section: severity filters, groups by file, locations,
 * suggestions, links to the tables and the acknowledgements of warnings.
 */
import type { Json, Suggestion, ValidationIssue } from "./api/types";
import { plural } from "./overview";

/** The severity chips above the issues. */
export type SeverityFilter = ValidationIssue["severity"] | "all";

export const SEVERITY_CHIPS: readonly { value: SeverityFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "error", label: "Errors" },
  { value: "warning", label: "Warnings" },
];

export const SEVERITY_LABELS: Record<ValidationIssue["severity"], string> = { error: "Error", warning: "Warning" };

/** The issues of a severity, in their order. */
export function filterIssues(issues: readonly ValidationIssue[], severity: SeverityFilter): ValidationIssue[] {
  return issues.filter((issue) => severity === "all" || issue.severity === severity);
}

/** The number of issues behind each severity chip. */
export function severityCounts(issues: readonly ValidationIssue[]): Record<SeverityFilter, number> {
  return Object.fromEntries(
    SEVERITY_CHIPS.map(({ value }) => [value, filterIssues(issues, value).length]),
  ) as Record<SeverityFilter, number>;
}

/** What the section says when a severity has no issues: `No warnings.` */
export function noIssuesText(severity: SeverityFilter): string {
  if (severity === "error") return "No errors.";
  if (severity === "warning") return "No warnings.";
  return "No errors or warnings.";
}

/** `2 errors · 1 warning`: the issues of a file. */
export function groupCounts(issues: readonly ValidationIssue[]): string {
  const errors = filterIssues(issues, "error").length;
  const warnings = filterIssues(issues, "warning").length;
  return [errors ? plural(errors, "error") : "", warnings ? plural(warnings, "warning") : ""]
    .filter(Boolean)
    .join(" · ");
}

/** The issues of the upload limits, which the library reports before reading the whole study. */
const LIMIT_CODES: ReadonlySet<string> = new Set(["row_limit", "file_limit"]);

/** Whether the issue says that the study is beyond the upload limits. */
export function isLimitIssue(issue: ValidationIssue): boolean {
  return LIMIT_CODES.has(issue.code);
}

/** The issues of one file; `file` is null for issues of the whole study. */
export interface IssueGroup {
  file: string | null;
  issues: ValidationIssue[];
}

/**
 * The issues by file: the files with errors first, then the others, each in the order of their
 * first issue. Within a file, the issues of the whole file come first, then those of its lines,
 * by line.
 */
export function groupByFile(issues: readonly ValidationIssue[]): IssueGroup[] {
  const groups = new Map<string | null, ValidationIssue[]>();
  for (const issue of issues) {
    const file = issue.source?.file ?? null;
    const group = groups.get(file);
    if (group) group.push(issue);
    else groups.set(file, [issue]);
  }
  const errors = (entries: ValidationIssue[]) => (entries.some((issue) => issue.severity === "error") ? 0 : 1);
  return [...groups]
    .toSorted(([, a], [, b]) => errors(a) - errors(b))
    .map(([file, entries]) => ({
      file,
      issues: entries.toSorted((a, b) => (a.source?.row ?? 0) - (b.source?.row ?? 0)),
    }));
}

/**
 * Where an issue is: `timecourses_Fig1.tsv · line 6 · mean · sheet cell timecourses_Fig1!O6`.
 * A table names its TSV line and the cell of its workbook sheet; the workbook names the row of
 * its sheet. Without `file`, the location starts after the file, which a group names already.
 */
export function location(issue: ValidationIssue, { file = true }: { file?: boolean } = {}): string {
  const source = issue.source;
  if (!source) return "";
  const workbook = source.file.endsWith(".xlsx");
  const parts = file ? [source.file] : [];
  if (source.row != null) parts.push(`${workbook ? "row" : "line"} ${source.row}`);
  if (source.header) parts.push(source.header);
  if (source.sheet && source.cell) parts.push(`sheet cell ${source.sheet}!${source.cell}`);
  else if (source.sheet && workbook) parts.push(`sheet ${source.sheet}`);
  return parts.join(" · ");
}

/** The message of a spelling suggestion of the library (`DID_YOU_MEAN` in `studyformat/issues.py`). */
export const DID_YOU_MEAN = "Did you mean one of these?";

function candidateText(candidate: Json): string {
  return typeof candidate === "string" ? candidate : JSON.stringify(candidate);
}

/**
 * A suggestion as `pkdb validate` prints it: the candidates of a spelling suggestion after
 * `Did you mean:`, else the hint followed by its candidates, such as lines to add to a file.
 */
export function suggestionText(suggestion: Suggestion): { text: string; candidates: string[] } {
  const candidates = (suggestion.candidates ?? []).map(candidateText);
  if (suggestion.message === DID_YOU_MEAN) return { text: `Did you mean: ${candidates.join(", ")}`, candidates: [] };
  return { text: suggestion.message, candidates };
}

/**
 * The query of the Tables section that shows the cell of an issue: its file, and its line and
 * column when it has them; null without a file. Only the tables of a study can be shown.
 */
export function tableQuery(issue: ValidationIssue): Record<string, string> | null {
  const source = issue.source;
  if (!source) return null;
  return {
    file: source.file,
    ...(source.row != null ? { line: String(source.row) } : {}),
    ...(source.header ? { column: source.header } : {}),
  };
}

/** The location of the `acknowledge` action of review.json: the warnings of `code` there. */
export interface Acknowledgement {
  code: string;
  file: string;
  line?: number;
  column?: string;
}

/**
 * Where an acknowledgement of a warning applies: its code, file, line and column, as
 * `pkdb review acknowledge` takes them; null for an error or an issue without a file.
 */
export function acknowledgement(issue: ValidationIssue): Acknowledgement | null {
  const source = issue.source;
  if (issue.severity !== "warning" || !source?.file) return null;
  return {
    code: issue.code,
    file: source.file,
    ...(source.row != null ? { line: source.row } : {}),
    ...(source.header ? { column: source.header } : {}),
  };
}

/** A key that the warnings of one acknowledgement share: one code at one file, line and column. */
export function locationKey(issue: ValidationIssue): string {
  const source = issue.source;
  return JSON.stringify([issue.code, source?.file ?? null, source?.row ?? null, source?.header ?? null]);
}
