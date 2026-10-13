/**
 * The selection of the Data section and its rules: the table that a source opens, the source of
 * a table and of a row, the selection that the section opens on, the filter of the rows of a
 * shared table, and the groups and counts of the navigator.
 *
 * The study page lists every table with its source: a table of one source, such as
 * `outputs_Tab2.tsv` or the raw table `<name>_Tab2.tsv`, belongs to it as a whole; a shared table
 * (subjects, characteristica, interventions) has none and names the source of each row in its
 * `source` column. The paper, the PDFs of the folder, comes first among the sources: a shared
 * table shows beside it when the study has a PDF.
 */
import type { LocationQuery } from "vue-router";
import type { InfoClass, SourceSummary, StudyDetail, TableEntry, TableKind, TableResponse } from "./api/types";
import { INFO_CLASSES } from "./info";
import { tableFiles } from "./study";
import { noteKinds } from "./tableKinds";

type Study = Pick<StudyDetail, "sources" | "tables">;
type Counted = Pick<StudyDetail, "sources" | "tables" | "problems" | "review">;

/** The `source` of the route that shows the paper; no source of a study has this name (`SOURCE_PATTERN` of the study format). */
export const PAPER = "paper";

/** The selection of the Data section: the query of its route. */
export interface Selection {
  source: string | null;
  /** The PDF that the paper shows, while it shows (`source=paper`); none for the first. */
  pdf: string | null;
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
    pdf: text(query.pdf),
    file: text(query.file),
    line: Number.isInteger(line) && line >= 1 ? line : null,
    column: text(query.column),
  };
}

/** The route query of a selection, without the parts that it lacks. */
export function selectionQuery(selection: Selection): Record<string, string> {
  const query: Record<string, string> = {};
  if (selection.source !== null) query.source = selection.source;
  if (selection.pdf !== null) query.pdf = selection.pdf;
  if (selection.file !== null) query.file = selection.file;
  if (selection.line !== null) query.line = String(selection.line);
  if (selection.column !== null) query.column = selection.column;
  return query;
}

/** The entry of a table file in the study page; undefined for a file that the study does not have. */
export function findTable(study: Pick<StudyDetail, "tables">, file: string): TableEntry | undefined {
  return study.tables.find((table) => table.file === file);
}

/** Whether a table file of the study is shared by several sources, which it names per row. */
export function isShared(study: Pick<StudyDetail, "tables">, file: string): boolean {
  return findTable(study, file)?.source === null;
}

/**
 * The tables of a study by class of information, in the order of the navigator and each class in
 * the order of the study page, without the classes that the study has no tables of: the groups of
 * the navigator and of the Table select that replaces it in a narrow window.
 */
export function tablesByInfo(study: Pick<StudyDetail, "tables">): { info: InfoClass; tables: TableEntry[] }[] {
  return INFO_CLASSES.map((info) => ({ info, tables: study.tables.filter((table) => table.info === info) })).filter(
    (group) => group.tables.length > 0,
  );
}

/**
 * The source of the study that a table file belongs to as a whole: that of a table of one source
 * or of a raw table. Null for a shared table, an unknown file, or a source the study lacks.
 */
export function ownerOf(study: Study, file: string): string | null {
  const source = findTable(study, file)?.source ?? null;
  return source !== null && study.sources.some((entry) => entry.source === source) ? source : null;
}

/**
 * The table file that a source opens: the current one when the source owns it, else its first
 * own table in the order of the study page, its raw table last. A source without tables of its
 * own, such as a text, keeps the current table only when it is a shared table, which shows the
 * rows of every source; else it opens the first table that names the source in its rows, else
 * the current table, else the first table of the study.
 */
export function fileForSource(study: Study, source: SourceSummary, current: string | null): string | null {
  const files = tableFiles(study);
  const valid = current !== null && files.includes(current) ? current : null;
  if (valid !== null && ownerOf(study, valid) === source.source) return valid;
  const own = files.find((file) => ownerOf(study, file) === source.source);
  if (own !== undefined) return own;
  if (valid !== null && isShared(study, valid)) return valid;
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

/** The first entry of the Sources list of the navigator: the paper when the study has a PDF, else its first source. */
export function firstSource(study: Pick<StudyDetail, "sources" | "papers">): string | null {
  return study.papers.length ? PAPER : (study.sources[0]?.source ?? null);
}

/** The source that a table shows beside its rows when the route names none: its own, else the paper, else the first source. */
export function sourceOfFile(
  study: Pick<StudyDetail, "sources" | "tables" | "papers">,
  file: string | null,
): string | null {
  return (file === null ? null : ownerOf(study, file)) ?? firstSource(study);
}

/** The table that the section opens on: the first with problems or open review items, else the first. */
export function defaultFile(detail: Counted): string | null {
  const counts = fileCounts(detail);
  const flagged = detail.tables.find(({ file }) => {
    const problems = counts.problems.get(file);
    return (problems ? problems.errors + problems.warnings : 0) + (counts.items.get(file) ?? 0) > 0;
  });
  return (flagged ?? detail.tables[0])?.file ?? null;
}

/**
 * The table that the Data section shows for the route `selection`: its file when the study has
 * it, else the first table of its source, else the table that the section opens on.
 */
export function selectedFile(study: Counted, selection: Pick<Selection, "source" | "file">): string | null {
  if (selection.file !== null && tableFiles(study).includes(selection.file)) return selection.file;
  const named = study.sources.find((entry) => entry.source === selection.source);
  return named ? fileForSource(study, named, null) : defaultFile(study);
}

/** The kind of the notes in study.json of the table `file`; null for a raw table or a file that the study lacks, which have none. */
export function tableNotesKind(
  study: Pick<StudyDetail, "tables" | "table_kinds">,
  file: string | null,
): TableKind | null {
  const entry = file === null ? undefined : findTable(study, file);
  return entry ? (noteKinds(study).find((kind) => kind === entry.kind) ?? null) : null;
}

/**
 * The kind of the notes above the table that the Data section shows for the route `selection`,
 * whose fields a refused save marks there; null for a raw table or none.
 */
export function selectedNotesKind(
  study: Counted & Pick<StudyDetail, "table_kinds">,
  selection: Pick<Selection, "source" | "file">,
): TableKind | null {
  return tableNotesKind(study, selectedFile(study, selection));
}

/** The text of the `source` cell of a row, or null for a raw table, a missing row or an empty cell. */
export function rowSource(table: TableResponse, line: number): string | null {
  const index = sourceColumn(table);
  const row = table.rows.find((entry) => entry.line === line);
  return index < 0 || !row ? null : row.cells[index] || null;
}

/** Which rows of a shared table show: all, those of one source, or those without a source. */
export type RowFilter = { kind: "all" } | { kind: "source"; source: string } | { kind: "none" };

export const ALL_ROWS: RowFilter = { kind: "all" };

/** The value of a filter as an option of the Source select. */
export function filterValue(filter: RowFilter): string {
  return filter.kind === "source" ? `source:${filter.source}` : filter.kind;
}

/** The filter of an option of the Source select; All for a value it does not know. */
export function filterOf(value: string): RowFilter {
  if (value === "none") return { kind: "none" };
  if (value.startsWith("source:")) return { kind: "source", source: value.slice("source:".length) };
  return ALL_ROWS;
}

/** The index of the `source` column of a table; -1 for a raw table or a table without one. */
function sourceColumn(table: TableResponse): number {
  return table.kind === "table" ? table.header.indexOf("source") : -1;
}

/**
 * The options of the Source select of a shared table, each with its number of rows: All, each
 * source that the rows name in natural order, and No source. None for a table without a `source`
 * column.
 */
export function filterChoices(table: TableResponse): { value: string; title: string }[] {
  const index = sourceColumn(table);
  if (index < 0) return [];
  const counts = new Map<string, number>();
  for (const row of table.rows) {
    const source = row.cells[index] ?? "";
    counts.set(source, (counts.get(source) ?? 0) + 1);
  }
  const named = [...counts.keys()]
    .filter((source) => source !== "")
    .sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
  return [
    { value: filterValue(ALL_ROWS), title: `All (${table.rows.length})` },
    ...named.map((source) => ({ value: filterValue({ kind: "source", source }), title: `${source} (${counts.get(source)})` })),
    { value: filterValue({ kind: "none" }), title: `No source (${counts.get("") ?? 0})` },
  ];
}

/** The lines of the rows that a filter shows; null shows every row, as for a table without a `source` column. */
export function filteredLines(table: TableResponse, filter: RowFilter): Set<number> | null {
  const index = sourceColumn(table);
  if (filter.kind === "all" || index < 0) return null;
  const wanted = filter.kind === "source" ? filter.source : "";
  return new Set(table.rows.filter((row) => (row.cells[index] ?? "") === wanted).map((row) => row.line));
}
