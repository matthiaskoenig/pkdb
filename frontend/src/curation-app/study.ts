/**
 * The sections of the study page, the section it opens on, the counts of its rail, the labels
 * of its header and the names of a new table.
 */
import type { IssueState, Release, StudyDetail, StudySummary } from "./api/types";

/** The sections of the study page in the order of the rail. */
export const SECTIONS = ["metadata", "review", "problems", "sources", "tables", "activity"] as const;

export type Section = (typeof SECTIONS)[number];

export const SECTION_LABELS: Record<Section, string> = {
  metadata: "Metadata",
  review: "Review",
  problems: "Problems",
  sources: "Sources",
  tables: "Tables",
  activity: "Activity",
};

export function isSection(value: unknown): value is Section {
  return typeof value === "string" && (SECTIONS as readonly string[]).includes(value);
}

/** The open review items: from `review.json`, or from the row summary when it is invalid. */
export function openItems(detail: StudyDetail): number {
  const items = detail.review.value?.items;
  return items ? items.filter((item) => item.state === "open").length : (detail.summary.open_items ?? 0);
}

/** Review when items are open, Problems when there are errors, otherwise Metadata. */
export function defaultSection(detail: StudyDetail): Section {
  if (openItems(detail) > 0) return "review";
  if (detail.counts.errors > 0) return "problems";
  return "metadata";
}

/** The name of a study folder: the second part of its identity `<substance>/<name>`. */
export function studyName(detail: Pick<StudyDetail, "id">): string {
  return detail.id.slice(detail.id.indexOf("/") + 1);
}

/** A paper table, a figure or the text, as `SOURCE_PATTERN` of the library accepts it. */
const SOURCE = /^(?:Text|(?:Tab|Fig)[A-Za-z0-9_-]+)$/;
/** A paper table, the only source of a raw table. */
const RAW_SOURCE = /^Tab[A-Za-z0-9_-]+$/;
const DATA_TABLE = /^(?:subjects|interventions|characteristica)\.tsv$/;
const SOURCE_TABLE = /^(?:outputs|timecourses|scatters)_(.+)\.tsv$/;

/** The files of the data tables and the raw tables of a study, in the order of its files. */
export function tableFiles(detail: Pick<StudyDetail, "id" | "files">): string[] {
  const prefix = `${studyName(detail)}_`;
  return detail.files.filter((file) => {
    if (DATA_TABLE.test(file)) return true;
    const source = SOURCE_TABLE.exec(file)?.[1];
    if (source !== undefined) return SOURCE.test(source);
    // A raw table `<name>_<source>.tsv` of a paper table.
    return file.startsWith(prefix) && file.endsWith(".tsv") && RAW_SOURCE.test(file.slice(prefix.length, -4));
  });
}

/** The counts of the rail: open items, errors plus warnings, sources, and table and raw table files. */
export function railCounts(detail: StudyDetail): Partial<Record<Section, number>> {
  return {
    review: openItems(detail),
    problems: detail.counts.errors + detail.counts.warnings,
    sources: detail.sources.length,
    tables: tableFiles(detail).length,
  };
}

// Header

export function releaseLabel(release: Release): string {
  return `${release.pkdb_id} · released ${release.date}`;
}

/** `#2158 · check`: the issue with its GitHub labels, or the number of study.json alone. */
export function issueLabel(issue: IssueState | null, number: number | null | undefined): string | null {
  const shown = issue?.number ?? number;
  if (shown === null || shown === undefined) return null;
  const labels = issue?.labels ?? [];
  return labels.length ? `#${shown} · ${labels.join(", ")}` : `#${shown}`;
}

/** `AI curated · <method>` for an automatic curation, `Data import` for imported data, else null. */
export function provenanceLabel(summary: Pick<StudySummary, "provenance">): string | null {
  const provenance = summary.provenance;
  if (provenance?.kind === "automatic_curation")
    return provenance.method ? `AI curated · ${provenance.method}` : "AI curated";
  if (provenance?.kind === "data_import") return "Data import";
  return null;
}

/** The requirements of approval, followed by the reason of the refusal from the server. */
export function approvalRefusal(reason: string): string {
  const sentence = reason.trim().replace(/\.?$/, ".");
  return `Approved needs zero open review items and zero validation errors. ${sentence}`;
}

// Paths

/** The folder of a study, given relative to the workspace with `/`, joined with the separator of the workspace. */
export function folderPath(workspace: string, relative: string): string {
  const separator = workspace.includes("\\") && !workspace.includes("/") ? "\\" : "/";
  const base = workspace.replace(/[\\/]+$/, "");
  return [base, ...relative.split("/").filter(Boolean)].join(separator);
}

/** The folders of a duplicate identity, from the 409 message `... two folders: <a>, <b>; rename one`. */
export function duplicatePaths(message: string): string[] {
  const listed = /folders: (.+); rename one$/.exec(message)?.[1];
  return listed ? listed.split(", ") : [];
}

// New tables

/** Excel limits sheet names to 31 characters. */
const SHEET_NAME_LIMIT = 31;

/** The kind of a new table: a table of mapped data split by source, or the raw table of a paper table. */
export type NewTableKind = "outputs" | "timecourses" | "scatters" | "raw";

export const NEW_TABLE_KINDS: readonly { value: NewTableKind; label: string }[] = [
  { value: "outputs", label: "Outputs" },
  { value: "timecourses", label: "Timecourses" },
  { value: "scatters", label: "Scatters" },
  { value: "raw", label: "Raw table" },
];

export interface NewTable {
  /** The sheet of the workbook, also the name of the table. */
  sheet: string;
  file: string;
  /** The image of the source that the table needs; null for the text of the paper. */
  image: string | null;
  imageFound: boolean;
  /** The body of the `add` action besides the study. */
  payload: { table: string } | { raw: string };
  /** Why the table cannot be added, or null. */
  problem: string | null;
}

/** The sheet, file and image of a new table of `kind` for `source`; null without a source. */
export function newTable(
  detail: Pick<StudyDetail, "id" | "files">,
  kind: NewTableKind,
  source: string,
): NewTable | null {
  const name = source.trim();
  if (!name) return null;
  const study = studyName(detail);
  const sheet = kind === "raw" ? `${study}_${name}` : `${kind}_${name}`;
  const file = `${sheet}.tsv`;
  const image = name === "Text" ? null : `${study}_${name}.png`;
  const files = new Set(detail.files.map((entry) => entry.toLowerCase()));
  let problem: string | null = null;
  if (kind === "raw" && !RAW_SOURCE.test(name)) problem = "A raw table needs a paper table source such as Tab3.";
  else if (!SOURCE.test(name)) problem = "Use a source such as Tab3, Fig2A or Text.";
  else if (files.has(file.toLowerCase())) problem = `${file} already exists.`;
  else if (sheet.length > SHEET_NAME_LIMIT)
    problem = `The sheet ${sheet} has ${sheet.length} characters. Excel allows ${SHEET_NAME_LIMIT}.`;
  return {
    sheet,
    file,
    image,
    imageFound: image !== null && detail.files.includes(image),
    payload: kind === "raw" ? { raw: name } : { table: sheet },
    problem,
  };
}
