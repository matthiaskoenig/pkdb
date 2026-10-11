/**
 * The problems of the files of a source, which the source pane of the Data section lists. What a
 * source is and which files it lacks come from the library, in the summaries of the study detail.
 */
import type { SourceSummary, SourceView, ValidationIssue } from "./api/types";

/**
 * The problems of the files of a source: its image, its raw extraction and its own tables; of a
 * table that several sources share, only the problems at a mapped row of the source.
 */
export function sourceProblems<I extends ValidationIssue>(
  problems: readonly I[],
  summary: SourceSummary,
  view: SourceView,
): I[] {
  const whole = new Set([summary.image, summary.raw, ...view.mapped.filter((t) => !t.shared).map((t) => t.file)]);
  const lines = new Map(view.mapped.map((table) => [table.file, new Set(table.rows.map(([line]) => line))]));
  return problems.filter((issue) => {
    const file = issue.source?.file;
    if (!file) return false;
    if (whole.has(file)) return true;
    const row = issue.source?.row;
    return row != null && (lines.get(file)?.has(row) ?? false);
  });
}
