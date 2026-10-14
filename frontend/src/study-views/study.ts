/**
 * The sections of the study page, the section it opens on, the counts of its sections, the labels
 * of its header, failed actions and the profiles of its people.
 */
import { ApiError } from "./errors";
import type {
  IssueState,
  People,
  Profile,
  Release,
  StudyDetail,
  StudySummary,
  ValidationIssue,
} from "./types";

/**
 * The sections of the study page in the order of their tabs, the order of the work on a study:
 * its metadata, its data, the problems of both, the review and the activity.
 */
export const SECTIONS = ["metadata", "data", "problems", "review", "activity"] as const;

export type Section = (typeof SECTIONS)[number];

export const SECTION_LABELS: Record<Section, string> = {
  metadata: "Metadata",
  data: "Data",
  problems: "Problems",
  review: "Review",
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

/** The counts of the section tabs: open items, and errors plus warnings. */
export function sectionCounts(detail: StudyDetail): Partial<Record<Section, number>> {
  return { review: openItems(detail), problems: detail.counts.errors + detail.counts.warnings };
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

// Failures of actions

export interface FailureDetails {
  /** The HTTP status; 0 when the local server could not be reached, null for an entry of the activity. */
  status: number | null;
  code: string | null;
  detail: string | null;
  action: string | null;
  requestId: string | null;
  time: string | null;
  traceback: string | null;
  activityId: string | null;
}

/**
 * The details of a failed request; null for another error, and for an answer without the error
 * body of the local server, which has no request id.
 */
export function detailsOf(caught: unknown): FailureDetails | null {
  if (!(caught instanceof ApiError) || (caught.requestId === null && caught.status !== 0)) return null;
  return {
    status: caught.status,
    code: caught.code,
    detail: caught.detail,
    action: caught.action,
    requestId: caught.requestId,
    time: caught.time,
    traceback: caught.traceback,
    activityId: caught.activityId,
  };
}

/** The message of a failed action. */
export function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught);
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
  /** What the local server said about the failure; null for a failure the app explains itself. */
  details: FailureDetails | null;
}

/** A failure that lists at most `LISTED_ISSUES` of `messages`. */
export function actionFailure(
  text: string,
  messages: string[] = [],
  link: ActionFailure["link"] = null,
  details: FailureDetails | null = null,
): ActionFailure {
  return {
    text,
    issues: messages.slice(0, LISTED_ISSUES),
    more: Math.max(0, messages.length - LISTED_ISSUES),
    link,
    details,
  };
}

/** A failure that lists all of `messages`, for a refusal whose issues the curator fixes one by one. */
export function issuesFailure(text: string, messages: string[]): ActionFailure {
  return { text, issues: messages, more: 0, link: null, details: null };
}

/**
 * The failure of `caught` with the details of the local server. The message of the server names
 * the action when it has a detail; a refusal meant for the curator, which has none, follows `lead`.
 */
export function failureOf(caught: unknown, lead = ""): ActionFailure {
  const message = messageOf(caught);
  const details = detailsOf(caught);
  const text = lead && !details?.detail ? `${lead} ${message}` : message;
  return actionFailure(text, [], null, details);
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
