/**
 * The selection of the Data section and its rules: which source owns a table file, which file a
 * source opens, the source of a row, and the counts of the navigator.
 *
 * A shared table (subjects, interventions, characteristica) names the source of each row in its
 * `source` column; every other table, and a raw table, belongs to one source as a whole.
 */
import type { LocationQuery } from "vue-router";
import type { SourceSummary, StudyDetail, TableResponse } from "./api/types";
import { tableFiles } from "./study";

/** The kinds of the tables that name the source of each row. */
export const SHARED_KINDS: ReadonlySet<string> = new Set(["subjects", "interventions", "characteristica"]);

type Study = Pick<StudyDetail, "sources" | "tables">;
type Counted = Pick<StudyDetail, "sources" | "tables" | "problems" | "review">;

/** The selection of the Data section: the query of its route. */
export interface Selection {
  source: string | null;
  file: string | null;
  line: number | null;
  column: string | null;
}

function text(value: unknown): string | null {
  return typeof value === "string" && value !== "" ? value : null;
}

/** The selection of a route query; a line is a whole number from 1. */
export function selectionOf(query: LocationQuery): Selection {
  const line = typeof query.line === "string" ? Number(query.line) : Number.NaN;
  return {
    source: text(query.source),
    file: text(query.file),
    line: Number.isInteger(line) && line >= 1 ? line : null,
    column: text(query.column),
  };
}

/** The route query of a selection, without the parts that it lacks. */
export function selectionQuery(selection: Selection): Record<string, string> {
  const query: Record<string, string> = {};
  if (selection.source !== null) query.source = selection.source;
  if (selection.file !== null) query.file = selection.file;
  if (selection.line !== null) query.line = String(selection.line);
  if (selection.column !== null) query.column = selection.column;
  return query;
}

/** Whether a table file of the study names the source of each row. */
export function isShared(study: Pick<StudyDetail, "tables">, file: string): boolean {
  return study.tables.some((table) => table.file === file && SHARED_KINDS.has(table.kind));
}

/**
 * The source that a table file belongs to: the source of a raw extraction, or the one source
 * whose rows fill a table that is not shared. Null for a shared table or an unknown file.
 */
export function ownerOf(study: Study, file: string): string | null {
  const raw = study.sources.find((source) => source.raw === file);
  if (raw) return raw.source;
  if (isShared(study, file)) return null;
  const owners = study.sources.filter((source) => source.tables.includes(file));
  return owners.length === 1 ? owners[0]!.source : null;
}

/**
 * The table file that a source opens: the current one when the source owns it or has rows in
 * it as a shared table; else its first own table in workbook order, its raw table, or its first
 * table; a source without tables keeps a valid current file, else the first table of the study.
 */
export function fileForSource(study: Study, source: SourceSummary, current: string | null): string | null {
  const files = tableFiles(study);
  const valid = current !== null && files.includes(current) ? current : null;
  if (valid !== null && (ownerOf(study, valid) === source.source || (isShared(study, valid) && source.tables.includes(valid))))
    return valid;
  const own = files.find((file) => source.tables.includes(file) && !isShared(study, file));
  if (own) return own;
  if (source.raw !== null && files.includes(source.raw)) return source.raw;
  return files.find((file) => source.tables.includes(file)) ?? valid ?? files[0] ?? null;
}

/** The problems of a navigator entry by severity. */
export interface ProblemCounts {
  errors: number;
  warnings: number;
}

/** The problems by severity and the open review items of a navigator entry. */
export interface Counts extends ProblemCounts {
  items: number;
}

/** The problems by severity and the open review items of each file. */
export function fileCounts(detail: Pick<StudyDetail, "problems" | "review">): {
  problems: Map<string, ProblemCounts>;
  items: Map<string, number>;
} {
  const problems = new Map<string, ProblemCounts>();
  const items = new Map<string, number>();
  for (const issue of detail.problems) {
    const file = issue.source?.file;
    if (!file) continue;
    const counts = problems.get(file) ?? { errors: 0, warnings: 0 };
    if (issue.severity === "error") counts.errors += 1;
    else counts.warnings += 1;
    problems.set(file, counts);
  }
  for (const item of detail.review.value?.items ?? []) {
    const file = item.target?.file;
    if (item.state === "open" && file) items.set(file, (items.get(file) ?? 0) + 1);
  }
  return { problems, items };
}

/** The files that belong to a source as a whole: image, raw extraction and tables that are not shared. */
function sourceFiles(study: Study, source: SourceSummary): string[] {
  return [source.image, source.raw, ...source.tables.filter((file) => !isShared(study, file))].filter(
    (file): file is string => file !== null,
  );
}

/**
 * The problems by severity and open review items of the files of a source. A shared table counts
 * for no source: its rows belong to several. The source pane lists the problems of its rows.
 */
export function sourceCounts(detail: Counted, source: SourceSummary): Counts {
  const counts = fileCounts(detail);
  return sourceFiles(detail, source).reduce<Counts>(
    (sum, file) => {
      const problems = counts.problems.get(file);
      return {
        errors: sum.errors + (problems?.errors ?? 0),
        warnings: sum.warnings + (problems?.warnings ?? 0),
        items: sum.items + (counts.items.get(file) ?? 0),
      };
    },
    { errors: 0, warnings: 0, items: 0 },
  );
}

/** Whether an entry has an error or a warning. */
function hasProblems(counts: ProblemCounts): boolean {
  return counts.errors + counts.warnings > 0;
}

/** The source that the Data section opens on: the first with problems, else the first. */
export function defaultSource(detail: Counted): SourceSummary | null {
  return detail.sources.find((source) => hasProblems(sourceCounts(detail, source))) ?? detail.sources[0] ?? null;
}

/** The text of the `source` cell of a row, or null for a raw table, a missing row or an empty cell. */
export function rowSource(table: TableResponse, line: number): string | null {
  if (table.kind !== "table") return null;
  const index = table.header.indexOf("source");
  const row = table.rows.find((entry) => entry.line === line);
  return index < 0 || !row ? null : row.cells[index] || null;
}

/** The lines of the rows of a source; every line of a table without a `source` column. */
export function sourceLines(table: TableResponse, source: string): Set<number> {
  const index = table.kind === "table" ? table.header.indexOf("source") : -1;
  return new Set(table.rows.filter((row) => index < 0 || row.cells[index] === source).map((row) => row.line));
}

/** The characters at the end of a table name without an underscore that stay when the name is cut. */
const NAME_END = 6;

/**
 * The name of a table file without `.tsv`, split before the part that tells the files of a kind
 * apart, so that a cut shortens the start: the part from the last underscore, such as `_Fig1` of
 * `timecourses_Fig1.tsv`, else the last six characters.
 */
export function nameParts(file: string): { start: string; end: string } {
  const name = file.endsWith(".tsv") ? file.slice(0, -".tsv".length) : file;
  const cut = name.lastIndexOf("_");
  const at = cut > 0 && cut < name.length - 1 ? cut : Math.max(0, name.length - NAME_END);
  return { start: name.slice(0, at), end: name.slice(at) };
}
