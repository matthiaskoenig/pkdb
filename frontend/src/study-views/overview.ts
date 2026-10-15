/**
 * Filtering, sorting and labels of the study rows of the overview. The study page uses the same
 * labels for the review status, the sync status and the problem counts.
 */
import type { StudyCapabilities } from "./context";
import type { ReviewStatus, RowStatus, StudyRow, SyncStatus } from "./types";

/** The status chips above the table. */
export type StatusChip = "all" | "attention" | "draft" | "in_review" | "approved";

export interface StudyFilter {
  /** Matches the identity and the title of a study, ignoring case. */
  search: string;
  /** One substance, or "" for all. */
  substance: string;
  /** The user name of one curator, matched ignoring case, or "" for all. */
  curator: string;
  chip: StatusChip;
}

/** A color of the theme for a tinted chip; undefined for a neutral chip. */
export type Tone = "success" | "info" | "warning" | "error" | undefined;

/** How long the search waits after the last keystroke before it filters the table. */
export const SEARCH_DELAY_MS = 150;

/**
 * Compares identities and names: without case, and the numbers in them by value. One for the
 * app: creating a collator costs more than many comparisons, which `localeCompare` with options
 * does on every call.
 */
export const COLLATOR = new Intl.Collator("en", { numeric: true, sensitivity: "base" });

export const STATUS_CHIPS: readonly { value: StatusChip; label: string }[] = [
  { value: "all", label: "All" },
  { value: "attention", label: "Needs attention" },
  { value: "draft", label: "Draft" },
  { value: "in_review", label: "In review" },
  { value: "approved", label: "Approved" },
];

/**
 * Errors, a sync conflict, or open review items while the study is in review. The sync state
 * counts only with the jobs of a local server, which the reader sees it with.
 */
export function needsAttention(row: StudyRow, { jobs }: Pick<StudyCapabilities, "jobs">): boolean {
  return (
    row.counts.errors > 0 ||
    (jobs && row.sync?.status === "conflict") ||
    ((row.summary.open_items ?? 0) > 0 && row.summary.review_status === "in_review")
  );
}

/** What the search compares of a row, in lower case. */
interface SearchKeys {
  id: string;
  title: string;
  curators: readonly string[];
}

/** The search keys of each row object: computed once, and so again only for a row that changed. */
const searchKeys = new WeakMap<StudyRow, SearchKeys>();

function keysOf(row: StudyRow): SearchKeys {
  let keys = searchKeys.get(row);
  if (!keys) {
    keys = {
      id: row.id.toLowerCase(),
      title: (row.summary.title ?? "").toLowerCase(),
      // User names are compared ignoring case, as the curator roster does.
      curators: (row.summary.curators ?? []).map((name) => name.toLowerCase()),
    };
    searchKeys.set(row, keys);
  }
  return keys;
}

/** Whether the study is in the folder of `substance` or its tables name that substance folder. */
export function namesSubstance(row: StudyRow, substance: string): boolean {
  return row.substances.includes(substance);
}

/** The substance folders that the tables of the study name besides its own folder. */
export function otherSubstances(row: StudyRow): string[] {
  return row.substances.filter((name) => name !== row.substance);
}

export interface FilteredStudies {
  /** The rows of the filter, in the order of the input. */
  shown: StudyRow[];
  /** The rows behind each status chip, within the search, the substance and the curator. */
  counts: Record<StatusChip, number>;
}

/**
 * The rows of `filter` and the counts of the status chips, in one pass over `rows`; `capabilities`
 * decide what needs attention (`needsAttention`).
 */
export function filterStudies(
  rows: readonly StudyRow[],
  { search, substance, curator, chip }: StudyFilter,
  capabilities: Pick<StudyCapabilities, "jobs">,
): FilteredStudies {
  const needle = search.trim().toLowerCase();
  const user = curator.toLowerCase();
  const counts: Record<StatusChip, number> = { all: 0, attention: 0, draft: 0, in_review: 0, approved: 0 };
  const shown: StudyRow[] = [];
  for (const row of rows) {
    if (substance && !namesSubstance(row, substance)) continue;
    const keys = keysOf(row);
    if (user && !keys.curators.includes(user)) continue;
    if (needle && !keys.id.includes(needle) && !keys.title.includes(needle)) continue;
    counts.all += 1;
    const attention = needsAttention(row, capabilities);
    if (attention) counts.attention += 1;
    const status = row.summary.review_status;
    if (status) counts[status] += 1;
    if (chip === "all" || (chip === "attention" ? attention : status === chip)) shown.push(row);
  }
  return { shown, counts };
}

/**
 * The curators of the rows with the number of their studies, in alphabetical order of the user
 * name. User names that differ only in case are one curator, named by its first spelling.
 */
export function curatorsOf(rows: StudyRow[]): { user: string; studies: number }[] {
  const curators = new Map<string, { user: string; studies: number }>();
  for (const row of rows) {
    const seen = new Set<string>();
    for (const user of row.summary.curators ?? []) {
      const key = user.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const entry = curators.get(key);
      if (entry) entry.studies += 1;
      else curators.set(key, { user, studies: 1 });
    }
  }
  return [...curators.entries()].sort(([a], [b]) => COLLATOR.compare(a, b)).map(([, entry]) => entry);
}

/** The substance folders of the rows and those that their tables name, in alphabetical order. */
export function substancesOf(rows: StudyRow[]): string[] {
  return [...new Set(rows.flatMap((row) => row.substances))].sort(COLLATOR.compare);
}

// Sorting

export type SortKey = "study" | "review" | "open_items" | "problems" | "sync" | "release" | "issue" | "upload";

export interface StudySort {
  key: SortKey;
  descending: boolean;
}

const REVIEW_ORDER: Record<ReviewStatus, number> = { draft: 0, in_review: 1, approved: 2 };

/** Sync states from settled to urgent. */
const SYNC_ORDER: Record<SyncStatus, number> = {
  not_checked: 0,
  unknown: 1,
  no_workbook: 2,
  in_sync: 3,
  workbook_open: 4,
  syncing: 5,
  changed: 6,
  conflict: 7,
};

function sortValue(row: StudyRow, key: SortKey): string | number | null {
  switch (key) {
    case "study":
      return row.id;
    case "review": {
      const status = row.summary.review_status;
      return status ? REVIEW_ORDER[status] : null;
    }
    case "open_items":
      return row.summary.open_items ?? null;
    case "problems":
      // A duplicate and a row without its curation show "-", so they sort last as rows without a value.
      if (row.duplicate || row.curator === false) return null;
      // Errors weigh more than any number of warnings.
      return row.counts.errors * 1_000_000 + row.counts.warnings;
    case "sync":
      return row.sync ? SYNC_ORDER[row.sync.status] : null;
    case "release":
      return row.summary.release?.pkdb_id ?? null;
    case "issue":
      return row.summary.issue ?? null;
    case "upload":
      return row.last_upload?.at ?? null;
  }
}

function compareValues(a: string | number, b: string | number): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return COLLATOR.compare(String(a), String(b));
}

/**
 * The rows sorted by `key`; rows without a value come last, and equal rows by identity. The
 * value of each row is computed once, not per comparison.
 */
export function sortStudies(rows: readonly StudyRow[], { key, descending }: StudySort): StudyRow[] {
  const keyed = rows.map((row) => ({ row, value: sortValue(row, key) }));
  keyed.sort((left, right) => {
    const a = left.value;
    const b = right.value;
    if (a === null || b === null) {
      if (a !== b) return a === null ? 1 : -1;
    } else {
      const order = compareValues(a, b);
      if (order !== 0) return descending ? -order : order;
    }
    return COLLATOR.compare(left.row.id, right.row.id) || COLLATOR.compare(left.row.path, right.row.path);
  });
  return keyed.map(({ row }) => row);
}

// Labels

export const REVIEW_LABELS: Record<ReviewStatus, string> = {
  draft: "Draft",
  in_review: "In review",
  approved: "Approved",
};

export const REVIEW_TONES: Record<ReviewStatus, Tone> = {
  draft: undefined,
  in_review: "info",
  approved: "success",
};

export const SYNC_LABELS: Record<SyncStatus, string> = {
  in_sync: "In sync",
  workbook_open: "Workbook open",
  syncing: "Syncing",
  changed: "Changed",
  conflict: "Conflict",
  no_workbook: "No workbook",
  unknown: "Unknown",
  not_checked: "Not checked yet",
};

export const SYNC_TONES: Record<SyncStatus, Tone> = {
  in_sync: "success",
  workbook_open: "info",
  syncing: "info",
  changed: "warning",
  conflict: "error",
  no_workbook: undefined,
  unknown: undefined,
  not_checked: undefined,
};

/** What a study does while its row status is not a finished check; null for a finished check. */
const ACTIVITY_LABELS: Record<RowStatus, string | null> = {
  // Not "Not checked yet": the sync status of a row before the first scan says that.
  discovered: "Not validated yet",
  queued: "Queued",
  validating: "Validating",
  uploading: "Uploading",
  valid: null,
  invalid: null,
  changed: "Changed since the last check",
  // The sync status shows the conflict.
  conflict: null,
  failed: "The last check failed",
  waiting: "Waiting",
  unknown: "Upload outcome unknown",
};

/** `1,412 folders`, `1 folder`; `many` is the plural of an irregular noun such as `studies`. */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count.toLocaleString("en-US")} ${count === 1 ? one : many}`;
}

/** `a.tsv`, `a.tsv and b.tsv`, `a.tsv, b.tsv and c.tsv`. */
export function listText(items: readonly string[]): string {
  if (items.length < 2) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

/** The problems of the last check: `2 errors`, `1 warning`, or `valid` for a passed check. */
export function problemLabels(row: Pick<StudyRow, "counts" | "status">): { label: string; tone: Tone }[] {
  const labels: { label: string; tone: Tone }[] = [];
  if (row.counts.errors > 0) labels.push({ label: plural(row.counts.errors, "error"), tone: "error" });
  if (row.counts.warnings > 0) labels.push({ label: plural(row.counts.warnings, "warning"), tone: "warning" });
  if (labels.length === 0 && (row.status === "valid" || row.status === "uploading"))
    labels.push({ label: "valid", tone: "success" });
  return labels;
}

/** What the study is doing, or why its last check is not current; null for a finished check. */
export function activityLabel(row: Pick<StudyRow, "status">): string | null {
  return ACTIVITY_LABELS[row.status];
}

/** A local date and time such as `2026-10-07 14:32`. */
export function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const pad = (value: number) => String(value).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/**
 * `url` when it is a web page, else null: a link from the local server or a study file goes into
 * an `href` only with `http:` or `https:`.
 */
export function webUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return ["https:", "http:"].includes(new URL(url).protocol) ? url : null;
  } catch {
    return null;
  }
}

/** The GitHub page of an issue: its URL, else the issue of the configured repository. */
export function issueUrl(row: Pick<StudyRow, "issue" | "summary">, repository: string): string | null {
  const own = webUrl(row.issue?.url);
  if (own) return own;
  const number = row.issue?.number ?? row.summary.issue;
  if (number === undefined || number === null || !/^[\w.-]+\/[\w.-]+$/.test(repository)) return null;
  return `https://github.com/${repository}/issues/${number}`;
}
