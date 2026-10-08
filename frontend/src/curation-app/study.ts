/**
 * The sections of the study page, the section it opens on, the counts of its rail, the labels
 * of its header, failed actions and the profiles of its people.
 */
import type { RouteLocationRaw } from "vue-router";
import type { ApiError } from "./api/client";
import type {
  IssueState,
  People,
  Profile,
  Release,
  StudyDetail,
  StudySummary,
  TablesResult,
  ValidationIssue,
} from "./api/types";

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

/** The route of a section of the study `id`, such as `#/studies/caffeine/Example/review?item=<id>`. */
export function sectionRoute(id: string, section: Section, query: Record<string, string> = {}): RouteLocationRaw {
  const params = { substance: id.slice(0, id.indexOf("/")), name: studyName({ id }), section };
  return Object.keys(query).length ? { name: "Study", params, query } : { name: "Study", params };
}

/** The table files of a study, data tables and raw tables, in the order of the workbook sheets, as the server lists them. */
export function tableFiles(detail: Pick<StudyDetail, "tables">): string[] {
  return detail.tables.map((table) => table.file);
}

/** The raw tables of a study, the paper tables as printed. */
export function rawTableFiles(detail: Pick<StudyDetail, "tables">): Set<string> {
  return new Set(detail.tables.filter((table) => table.kind === "raw").map((table) => table.file));
}

/** Whether a table file of the study is a raw table, the paper table as printed. */
export function isRawTable(detail: Pick<StudyDetail, "tables">, file: string): boolean {
  return rawTableFiles(detail).has(file);
}

/** The issues of the upload limits, which the library reports before reading the whole study. */
const LIMIT_CODES: ReadonlySet<string> = new Set(["row_limit", "file_limit"]);

/** Whether the issue says that the study is beyond the upload limits. */
export function isLimitIssue(issue: ValidationIssue): boolean {
  return LIMIT_CODES.has(issue.code);
}

/**
 * Whether the study is beyond the upload limits. Its page then lists no files, sources, tables
 * or targets, because the local server does not read the study, and names the limit in its problems.
 */
export function beyondLimits(detail: Pick<StudyDetail, "problems">): boolean {
  return detail.problems.some(isLimitIssue);
}

/**
 * The counts of the rail: open items, errors plus warnings, sources, and table and raw table
 * files; none of the sources and tables beyond the upload limits, where the page cannot list them.
 */
export function railCounts(detail: StudyDetail): Partial<Record<Section, number>> {
  const counts = { review: openItems(detail), problems: detail.counts.errors + detail.counts.warnings };
  return beyondLimits(detail)
    ? counts
    : { ...counts, sources: detail.sources.length, tables: detail.tables.length };
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

/** How long the header and the sections show the notice of an action that succeeded. */
export const NOTICE_MS = 5000;

// Failures of actions

/** The message of a failed action. */
export function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught);
}

/** What to do about a write that was refused without a user (`isNoUser`). */
export function userHint(error: ApiError): string {
  return error.body.error === "no_user" ? "Set your PK-DB user in Connection settings." : error.message;
}

/** At most this many issues of a failed action are listed; the section of the link has all of them. */
export const LISTED_ISSUES = 3;

/** What went wrong in an action: some of the issues of the API, and the section with all of them. */
export interface ActionFailure {
  text: string;
  issues: string[];
  /** The issues beyond the listed ones. */
  more: number;
  link: { section: Section; label: string } | null;
}

/** A failure that lists at most `LISTED_ISSUES` of `messages`. */
export function actionFailure(
  text: string,
  messages: string[] = [],
  link: ActionFailure["link"] = null,
): ActionFailure {
  return {
    text,
    issues: messages.slice(0, LISTED_ISSUES),
    more: Math.max(0, messages.length - LISTED_ISSUES),
    link,
  };
}

/** What the curator should know after Open tables: nothing for a clean sync. */
export function tablesOutcome(result: TablesResult): ActionFailure | null {
  const issues = result.issues.map((item) => item.message);
  const unresolved = result.conflicts.filter((conflict) => conflict.kept === null).length;
  const link: ActionFailure["link"] = unresolved ? { section: "tables", label: "Show the conflicts" } : null;
  if (unresolved === 1) issues.unshift("A sheet conflicts with its table.");
  if (unresolved > 1) issues.unshift(`${unresolved} sheets conflict with their tables.`);
  if (!result.opened) return actionFailure("The workbook could not be opened.", issues, link);
  return issues.length ? actionFailure("The workbook opened, but the sync found problems.", issues, link) : null;
}

// People

/**
 * Profiles by user name, matched without regard to case as the local server matches them
 * (`curation/metadata.py`): a `study.json` may spell a user name otherwise than the roster. The
 * first profile of a user name wins. Look a user up with `findProfile` or `profileOf`.
 */
export function profileMap(profiles: Iterable<Profile>): Map<string, Profile> {
  const map = new Map<string, Profile>();
  for (const profile of profiles) {
    const key = profile.username.toLowerCase();
    if (!map.has(key)) map.set(key, profile);
  }
  return map;
}

/** The profiles of the roster and of the people of the study who are not in it (`profileMap`). */
export function knownProfiles(roster: readonly Profile[], people: People | null | undefined): Map<string, Profile> {
  return profileMap([
    ...roster,
    ...(people?.creator ? [people.creator] : []),
    ...(people?.curators.map((curator) => curator.profile) ?? []),
    ...(people?.collaborators ?? []),
  ]);
}

/** The profile of `user` in a `profileMap`, whatever the case of the name. */
export function findProfile(profiles: ReadonlyMap<string, Profile>, user: string): Profile | undefined {
  return profiles.get(user.toLowerCase());
}

/** The profile of `user`, or a profile with the user name alone for someone unknown. */
export function profileOf(profiles: ReadonlyMap<string, Profile>, user: string): Profile {
  return (
    findProfile(profiles, user) ?? { username: user, display_name: user, title: null, affiliation: null, avatar_url: null }
  );
}

// Paths

/** The folder of a study, given relative to the workspace with `/`, joined with the separator of the workspace. */
export function folderPath(workspace: string, relative: string): string {
  const separator = workspace.includes("\\") && !workspace.includes("/") ? "\\" : "/";
  const base = workspace.replace(/[\\/]+$/, "");
  return [base, ...relative.split("/").filter(Boolean)].join(separator);
}

/** The folders of a duplicate identity, relative to the workspace, from the `paths` of the 409 answer. */
export function duplicateFolders(body: Record<string, unknown>): string[] {
  const paths = body.paths;
  return Array.isArray(paths) ? paths.filter((path): path is string => typeof path === "string") : [];
}

const NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];

/** `This identity belongs to two folders`, for the number of folders that the server listed. */
export function duplicateHeading(folders: number): string {
  if (folders < 2) return "This identity belongs to more than one folder";
  return `This identity belongs to ${NUMBERS[folders] ?? folders} folders`;
}
