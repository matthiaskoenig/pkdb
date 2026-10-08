/**
 * The validation issues of the Problems section: severity filters, groups by file, locations,
 * suggestions, links to the tables and the acknowledgements of warnings.
 */
import { isValidationError } from "./api/client";
import type {
  AcknowledgedWarning,
  Job,
  Json,
  SaveMode,
  Snapshot,
  StudyDetail,
  Suggestion,
  ValidationIssue,
} from "./api/types";
import { plural } from "./overview";
import { reviewFailure, type ReviewFailure } from "./review";

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
 * its sheet; a file without rows names the key of the issue, such as a dataset of a
 * WebPlotDigitizer project. Without `file`, the location starts after the file, which a group
 * names already.
 */
export function location(issue: ValidationIssue, { file = true }: { file?: boolean } = {}): string {
  const source = issue.source;
  if (!source) return "";
  const workbook = source.file.endsWith(".xlsx");
  const parts = file ? [source.file] : [];
  if (source.row != null) parts.push(`${workbook ? "row" : "line"} ${source.row}`);
  if (source.header) parts.push(source.header);
  if (source.key) parts.push(source.key);
  if (source.sheet && source.cell) parts.push(`sheet cell ${source.sheet}!${source.cell}`);
  else if (source.sheet && workbook) parts.push(`sheet ${source.sheet}`);
  return parts.join(" · ");
}

function candidateText(candidate: Json): string {
  return typeof candidate === "string" ? candidate : JSON.stringify(candidate);
}

/** A suggestion: the text before its candidates, the candidates, and a note after them. */
export interface SuggestionView {
  lead: string;
  candidates: string[];
  note: string | null;
}

/**
 * A suggestion to show, by its kind (`studyformat/issues.py`): candidates alone follow
 * `Did you mean:`, and so do the spelling suggestions of an unknown term, with their caveat after
 * them; any other hint comes before its candidates, such as lines to add to a file.
 */
export function suggestionView(suggestion: Suggestion): SuggestionView {
  const candidates = (suggestion.candidates ?? []).map(candidateText);
  if (suggestion.kind === "did_you_mean") return { lead: "Did you mean:", candidates, note: null };
  if (suggestion.kind === "check_vocabulary" && candidates.length)
    return { lead: "Did you mean:", candidates, note: suggestion.message };
  return { lead: suggestion.message, candidates, note: null };
}

/**
 * The query of the Tables section that shows the cell of an issue: its file, and its line and
 * column (the header, or the letter in a raw table) when it has them; null without a file. Only
 * the tables of a study can be shown.
 */
export function tableQuery(issue: ValidationIssue): Record<string, string> | null {
  const source = issue.source;
  if (!source) return null;
  // A raw table has no header: its cells are named by their column letter.
  const column = source.header ?? source.column;
  return {
    file: source.file,
    ...(source.row != null ? { line: String(source.row) } : {}),
    ...(column ? { column } : {}),
  };
}

/**
 * The location of the `acknowledge` action of review.json: the warnings of `code` there. A null
 * line, column or key matches only warnings without one; the local server matches every line,
 * column or key only when the field is left out, as `pkdb review acknowledge` without the option.
 */
export interface Acknowledgement {
  code: string;
  file: string;
  line: number | null;
  column: string | null;
  key: string | null;
}

/**
 * Where an acknowledgement of a warning applies: exactly its code, file, line, column and key;
 * null for an error or an issue without a file. The local server writes a review item that
 * covers exactly this warning: at its row and column, or by its key.
 */
export function acknowledgement(issue: ValidationIssue): Acknowledgement | null {
  const source = issue.source;
  if (issue.severity !== "warning" || !source?.file) return null;
  return {
    code: issue.code,
    file: source.file,
    line: source.row ?? null,
    column: source.header ?? null,
    key: source.key ?? null,
  };
}

/** What an acknowledgement covers beyond its own warning, or null when it covers just that one. */
export function scopeText(entry: AcknowledgedWarning): string | null {
  const file = entry.target?.file;
  switch (entry.scope) {
    case "study":
      return `Covers every ${entry.code} warning of the study, also later ones.`;
    case "file":
      return `Covers every ${entry.code} warning in ${file}, also later ones.`;
    case "column":
      return `Covers every ${entry.code} warning in column ${entry.target?.column} of ${file}, also later ones.`;
    default:
      return null;
  }
}

/** What the dialog says when the warning is no longer in the files that the server validated. */
export const NO_SUCH_WARNING = "This warning is not in the current files. Validate the study and try again.";

/** What the dialog says when warnings at several locations match the one to acknowledge. */
export const AMBIGUOUS_WARNING = "Several warnings match this location. Validate the study and try again.";

/** What the dialog says for a warning without a row of a data table and without a key. */
export const NO_EXACT_TARGET = "This warning cannot be acknowledged on its own.";

/**
 * The plain sentences of the refusals of the `acknowledge` action, by their code
 * (`studyformat/review_edit.py`). Their messages are written for `pkdb review acknowledge`: they
 * list locations and name its options.
 */
const ACKNOWLEDGE_REFUSALS: ReadonlyMap<string, string> = new Map([
  ["no_such_warning", NO_SUCH_WARNING],
  ["ambiguous_warning", AMBIGUOUS_WARNING],
  ["no_exact_target", NO_EXACT_TARGET],
]);

/** The failure of an acknowledgement; a refusal of the warning itself gets a plain sentence. */
export function acknowledgeFailure(caught: unknown): ReviewFailure {
  const text = isValidationError(caught) ? ACKNOWLEDGE_REFUSALS.get(caught.body.code ?? "") : undefined;
  if (text) return { kind: "error", text, issues: [] };
  return reviewFailure(caught, "The warning was not acknowledged.");
}

/**
 * Whether the local server validates the study by itself after a write. It does not with On
 * save Off, while file watching is paused, or for an upload on save without an account that
 * can upload. Without the state of the server, it is assumed to.
 */
export function validatesAfterWrite(
  mode: SaveMode,
  snapshot: Pick<Snapshot, "paused" | "offline" | "account" | "can_upload"> | null,
): boolean {
  if (mode === "off") return false;
  if (!snapshot) return true;
  if (snapshot.paused) return false;
  return mode !== "upload" || (!snapshot.offline && snapshot.account !== null && snapshot.can_upload);
}

/** A key that the warnings of one acknowledgement share: one code at one file, line, column and key. */
export function locationKey(issue: ValidationIssue): string {
  const source = issue.source;
  return JSON.stringify([
    issue.code,
    source?.file ?? null,
    source?.row ?? null,
    source?.header ?? null,
    source?.key ?? null,
  ]);
}

/**
 * A warning acknowledged in the app: its location key, the time of the write in the activity of
 * the study, and the report of the study at that time.
 */
export interface AcknowledgedMark {
  key: string;
  since: string | null;
  report: string | null;
}

/** The time of the newest write of the app in the activity of a study (newest first), such as an acknowledgement. */
export function lastWrite(jobs: readonly Job[]): string | null {
  return jobs.find((job) => job.action === "write")?.created_at ?? null;
}

/**
 * Whether the report of a study comes from a job queued after the acknowledgement was written:
 * only such a job validated the acknowledgement. A job that was queued or running during the
 * write can still list the warning. The times are the server's, in one ISO format, so they
 * compare as text. Without the job of the report, any other report counts.
 */
export function reportAfter(detail: Pick<StudyDetail, "jobs" | "report_id">, mark: AcknowledgedMark): boolean {
  const job = detail.jobs.find((entry) => entry.id === detail.report_id);
  if (job && mark.since !== null) return job.created_at > mark.since;
  return detail.report_id !== mark.report;
}
