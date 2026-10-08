/**
 * Filtering, sorting and labels of the study rows of the overview. The study page uses the same
 * labels for the review status, the sync status and the problem counts.
 */
import type { ReviewStatus, RowStatus, SaveMode, Snapshot, StudyRow, SyncStatus } from "./api/types";

/** The status chips above the table. */
export type StatusChip = "all" | "attention" | "draft" | "in_review" | "approved";

export interface StudyFilter {
  /** Matches the identity and the title of a study, ignoring case. */
  search: string;
  /** One substance, or "" for all. */
  substance: string;
  chip: StatusChip;
}

/** A color of the theme for a tinted chip; undefined for a neutral chip. */
export type Tone = "success" | "info" | "warning" | "error" | undefined;

export const STATUS_CHIPS: readonly { value: StatusChip; label: string }[] = [
  { value: "all", label: "All" },
  { value: "attention", label: "Needs attention" },
  { value: "draft", label: "Draft" },
  { value: "in_review", label: "In review" },
  { value: "approved", label: "Approved" },
];

/** Errors, a sync conflict, or open review items while the study is in review. */
export function needsAttention(row: StudyRow): boolean {
  return (
    row.counts.errors > 0 ||
    row.sync.status === "conflict" ||
    ((row.summary.open_items ?? 0) > 0 && row.summary.review_status === "in_review")
  );
}

function matchesChip(row: StudyRow, chip: StatusChip): boolean {
  if (chip === "all") return true;
  if (chip === "attention") return needsAttention(row);
  return row.summary.review_status === chip;
}

export function filterStudies(rows: StudyRow[], { search, substance, chip }: StudyFilter): StudyRow[] {
  const needle = search.trim().toLowerCase();
  return rows.filter(
    (row) =>
      (!substance || row.substance === substance) &&
      matchesChip(row, chip) &&
      (!needle || row.id.toLowerCase().includes(needle) || (row.summary.title ?? "").toLowerCase().includes(needle)),
  );
}

/** The number of rows behind each status chip. */
export function chipCounts(rows: StudyRow[]): Record<StatusChip, number> {
  return Object.fromEntries(
    STATUS_CHIPS.map(({ value }) => [value, rows.filter((row) => matchesChip(row, value)).length]),
  ) as Record<StatusChip, number>;
}

/** The substances of the rows in alphabetical order. */
export function substancesOf(rows: StudyRow[]): string[] {
  return [...new Set(rows.map((row) => row.substance))].sort((a, b) => a.localeCompare(b));
}

// Sorting

export type SortKey = "study" | "review" | "open_items" | "problems" | "sync" | "release" | "issue" | "mode" | "upload";

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

const MODE_ORDER: Record<SaveMode, number> = { off: 0, validate: 1, upload: 2 };

function sortValue(row: StudyRow, key: SortKey): string | number | null {
  switch (key) {
    case "study":
      return row.id;
    case "review":
      return row.summary.review_status ? REVIEW_ORDER[row.summary.review_status] : null;
    case "open_items":
      return row.summary.open_items ?? null;
    case "problems":
      // Errors weigh more than any number of warnings.
      return row.counts.errors * 1_000_000 + row.counts.warnings;
    case "sync":
      return SYNC_ORDER[row.sync.status];
    case "release":
      return row.summary.release?.pkdb_id ?? null;
    case "issue":
      return row.summary.issue ?? null;
    case "mode":
      return MODE_ORDER[row.mode];
    case "upload":
      return row.last_upload?.at ?? null;
  }
}

function compare(a: string | number, b: string | number): number {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), "en", { numeric: true, sensitivity: "base" });
}

/** The rows sorted by `key`; rows without a value come last, and equal rows by identity. */
export function sortStudies(rows: StudyRow[], { key, descending }: StudySort): StudyRow[] {
  return [...rows].sort((left, right) => {
    const a = sortValue(left, key);
    const b = sortValue(right, key);
    if (a === null || b === null) {
      if (a !== b) return a === null ? 1 : -1;
    } else {
      const order = compare(a, b);
      if (order !== 0) return descending ? -order : order;
    }
    return compare(left.id, right.id) || compare(left.path, right.path);
  });
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

export const MODE_LABELS: Record<SaveMode, string> = { validate: "Validate", upload: "Upload", off: "Off" };

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

/** Why uploads are not possible, or null when they are. */
export function uploadBlocker(snapshot: Snapshot): string | null {
  if (snapshot.can_upload) return null;
  if (snapshot.offline) return "Work offline is on. Turn it off in the settings to upload.";
  if (!snapshot.authenticated) return "Add your personal API key in the settings to upload.";
  if (snapshot.connection !== "connected") return "The PK-DB server is not connected.";
  return "Your PK-DB account cannot upload studies.";
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
