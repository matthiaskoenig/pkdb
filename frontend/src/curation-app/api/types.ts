/**
 * The answers of the local API of `pkdb curate` that only the curation app reads: the state of
 * the server (`engine.py`), the reports of its jobs (`jobs.py`), the folder browser, the GitHub
 * assignments, `reference.json` reads and previews, the answers of writes (`studies.py`) and
 * their error bodies, with their structural guards. The documents of a study are shared with
 * the website (`src/study-views/types.ts`).
 */
import {
  hasKeys,
  type AxisScales,
  type ConflictData,
  type Job,
  type Json,
  type Profile,
  type ReviewItem,
  type StudyRow,
  type ValidationIssue,
} from "../../study-views/types";

// reference.json

export interface ReferenceAuthor {
  first_name?: string;
  last_name?: string;
  organization?: string | null;
}

/** `reference.json`, the reference of a preview, or a candidate of a citation search. */
export interface ReferenceRecord {
  sid?: string;
  name?: string;
  pmid?: string | null;
  doi?: string | null;
  url?: string | null;
  title?: string | null;
  abstract?: string | null;
  journal?: string | null;
  date?: string | null;
  publication_date?: string | null;
  authors?: ReferenceAuthor[];
  /** Input, overrides and sources of the lookup, and its `warnings`. */
  provenance?: Record<string, Json>;
}

/** The answer of `POST /local/reference/preview`: the reference to save with `token`. */
export interface ReferencePreview {
  reference: ReferenceRecord;
  changes: Record<string, { before: Json; after: Json }>;
  revision: string;
  token: string;
}

// Jobs

/**
 * The report of a finished job, `GET /local/reports/{id}`: the job, its validation report and
 * what the server saved, with more outcome fields that differ by action.
 */
export interface JobReport {
  job: Job;
  persistence: string;
  report: Record<string, Json>;
}

// Snapshot of GET /local/state

export type SaveMode = "validate" | "upload" | "off";

/** The last failure of the file watcher of pkdb curate; `recovered` once a later check succeeded. */
export interface WatcherError {
  time: string;
  detail: string | null;
  recovered: boolean;
}

export type ConnectionStatus =
  | "offline"
  | "not_configured"
  | "connecting"
  | "connected"
  | "unauthorized"
  | "incompatible"
  | "error";

export interface VocabularyState {
  status: "offline" | "not_checked" | "current";
  hash?: string;
  processing_version?: string;
}

export interface GitHubUser {
  id: number;
  login: string;
  name: string | null;
  avatar_url: string | null;
}

export interface GitHubIssue {
  number: number;
  title: string;
  html_url: string;
  state: string;
  assignees: string[];
  labels: string[];
}

/** The cached GitHub assignments, as `POST /local/assignments/refresh` returns them. */
export interface GitHubAssignments {
  users: GitHubUser[];
  issues: GitHubIssue[];
  status: "not_loaded" | "ready" | "unavailable" | "offline";
  limited?: boolean;
  refreshed_at?: string;
  error?: string | null;
}

/** The color theme of the app: one that the curator chose, or the theme of the system. */
export type ThemeChoice = "light" | "dark" | "system";

export interface Snapshot {
  workspace: string;
  endpoint: string;
  user: string;
  /** Who writes study files, or why writes are refused. */
  author: { user: string | null; reason: string | null };
  authenticated: boolean;
  account: string | null;
  can_upload: boolean;
  connection: ConnectionStatus;
  connection_error: string | null;
  checked_at: string | null;
  client_version: string;
  server_version: string | null;
  update_required: boolean;
  offline: boolean;
  paused: boolean;
  /** On save: what a save of a file starts, for every study of the workspace with this server and account. */
  mode: SaveMode;
  /** Kept by the local server: the browser forgets it, as the port and so the origin change with every start. */
  theme: ThemeChoice;
  /**
   * The scales that the curator chose for the plots of mapped rows, by figure
   * `<substance>/<study>/<source>`. Kept by the local server, as the browser forgets them with
   * every new port; a figure without an entry follows its digitization.
   */
  plot_scales: Record<string, AxisScales>;
  vocabulary: VocabularyState;
  github: GitHubAssignments & { user: string; repository: string };
  studies: StudyRow[];
  format1_folders: number;
  jobs: Job[];
  /** The finished jobs of the workspace that Clear finished history removes. */
  clearable_jobs: number;
  recent_workspaces: { path: string; exists: boolean }[];
  /** The log file of pkdb curate, which has the traceback of every failure. */
  log_file: string;
  /** The last failure of the file watcher, null when it never failed. */
  watcher_error: WatcherError | null;
  /** Only in `GET /local/state`, not in the snapshots that actions return. */
  csrf_token?: string;
}

// Folder browser

export type FolderKind = "repository" | "study" | "folder";

export interface Directories {
  path: string;
  parent: string | null;
  home: string;
  kind: FolderKind;
  truncated: boolean;
  entries: { name: string; path: string; kind: FolderKind }[];
}

// Results of writes

export interface MetadataWrite {
  revision: string;
  reference: string | null;
  reference_error: string | null;
}

export interface ReviewWrite {
  revision: string;
  item?: ReviewItem;
}

export interface TablesResult {
  ok: boolean;
  workbook_action: "created" | "regenerated" | "unchanged" | "close_to_update" | "sync_again";
  changes: { file: string; action: "write" | "delete" }[];
  conflicts: ConflictData[];
  issues: ValidationIssue[];
  /** `open`: whether the workbook exists and was opened. */
  opened?: boolean;
  /**
   * `open` at a `file`: what to do when the workbook could not be switched to the sheet, such as
   * `The workbook is already open. Go to sheet outputs_Fig6, cell Y97.`; null when it opened there.
   */
  notice?: string | null;
  /** `add`: the name of the added table. */
  table?: string;
}

/** What Add table would add for a kind and a source, and why the local server would refuse it. */
export interface TablePreview {
  /** The sheet of the workbook, also the name of the table. */
  table: string;
  file: string;
  /** The image of the source that the table needs; null for the text of the paper. */
  image: string | null;
  image_found: boolean;
  /** Why the table cannot be added; empty when it can. */
  issues: ValidationIssue[];
  /** The raw table of a paper table when it exists or is the table to add: the source without an image. */
  raw: string | null;
}

// Error bodies

/** The body of a 409 for a file that changed on disk since the app read it. */
export interface RevisionConflictBody {
  error: string;
  file: string;
  revision: string;
  content: string | null;
}

/** The body of a 422 for a document that the library refuses. */
export interface ValidationErrorBody {
  error: string;
  issues: ValidationIssue[];
  code?: string;
}

// Guards

export const isSession = hasKeys<{ csrf_token: string }>("csrf_token");

export const isSnapshot = hasKeys<Snapshot>(
  "workspace",
  "endpoint",
  "user",
  "author",
  "authenticated",
  "account",
  "can_upload",
  "connection",
  "connection_error",
  "checked_at",
  "client_version",
  "server_version",
  "update_required",
  "offline",
  "paused",
  "mode",
  "theme",
  "plot_scales",
  "vocabulary",
  "github",
  "studies",
  "format1_folders",
  "jobs",
  "clearable_jobs",
  "recent_workspaces",
  "log_file",
  "watcher_error",
);

export const isJobReport = hasKeys<JobReport>("job", "persistence", "report");

export const isCurators = hasKeys<{ curators: Profile[] }>("curators");

export const isDirectories = hasKeys<Directories>("path", "parent", "home", "kind", "truncated", "entries");

export const isGitHubAssignments = hasKeys<GitHubAssignments>("users", "issues", "status");

export const isMetadataWrite = hasKeys<MetadataWrite>("revision", "reference", "reference_error");

export const isReviewWrite = hasKeys<ReviewWrite>("revision");

export const isTablesResult = hasKeys<TablesResult>("ok", "workbook_action", "changes", "conflicts", "issues");

export const isTablePreview = hasKeys<TablePreview>("table", "file", "image", "image_found", "issues", "raw");

export const isReferenceRead = hasKeys<{ reference: ReferenceRecord }>("reference");

export const isReferenceCandidates = hasKeys<{ candidates: ReferenceRecord[] }>("candidates");

export const isReferencePreview = hasKeys<ReferencePreview>("reference", "changes", "revision", "token");

export const isReferenceSaved = hasKeys<{ ok: boolean }>("ok");
