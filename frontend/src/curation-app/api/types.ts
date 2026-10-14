/**
 * Response shapes of the local API of `pkdb curate` and their structural guards.
 *
 * The field lists follow the part B engine: `engine.py` (snapshot), `workspace.py` (rows and
 * folders), `jobs.py` (jobs), `studies.py` (study page, tables, sources and writes),
 * `metadata.py` (profiles and people), `studyformat/models.py`, `schemas/review.py` and
 * `schemas/validation.py`. Optional fields are those the server leaves out.
 */

/** A JSON value. */
export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

export type Guard<T> = (value: unknown) => value is T;

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A guard that accepts an object with all of the given top-level keys. */
export function hasKeys<T extends object>(...keys: (keyof T & string)[]): Guard<T> {
  return (value): value is T => isRecord(value) && keys.every((key) => key in value);
}

// Validation

export interface SourceLocation {
  file: string;
  sheet?: string | null;
  /** The line of a table file (its header is line 0, a raw table starts at line 1), the row of a sheet of the workbook, or the line of a JSON file. */
  row?: number | null;
  column?: string | null;
  path?: (string | number)[];
  /** The address of the cell in the workbook, such as Y97. */
  cell?: string;
  header?: string;
  /** Names the place of an issue in a file without rows: a dataset of a WebPlotDigitizer project, a review item. */
  key?: string;
}

export interface Suggestion {
  kind: string;
  message: string;
  candidates?: Json[];
  command?: string | null;
}

export interface RelatedSource {
  label: string;
  source: SourceLocation;
}

export interface ValidationIssue {
  code: string;
  severity: "error" | "warning";
  message: string;
  source?: SourceLocation | null;
  category?: string | null;
  stage?: string | null;
  field?: string | null;
  actual?: Json;
  expected?: Record<string, Json>;
  context?: Record<string, Json>;
  related_sources?: RelatedSource[];
  suggestions?: Suggestion[];
  documentation_url?: string | null;
}

/** An issue of the study page: of the last validation, of a sync that stopped it, or of the limits. */
export interface Problem extends ValidationIssue {
  /**
   * Whether a review item can acknowledge it, as the local server knows: a warning of the
   * validation, not an issue of a stopped sync.
   */
  acknowledgeable: boolean;
}

// study.json

export type TableKind = "subjects" | "interventions" | "characteristica" | "outputs" | "timecourses" | "scatters";

/** The kind of a table file: a table kind, or `raw` for the raw table of a paper table. */
export type TableFileKind = TableKind | "raw";

/** The class of information of a table, by which the Data section groups and colors it. */
export type InfoClass = "subjects" | "interventions" | "data" | "raw";

/**
 * A table file of the study; the study detail lists them in the order of the workbook sheets.
 * `source` is the source it belongs to, such as Tab2 of `outputs_Tab2.tsv` or of the raw table
 * `<name>_Tab2.tsv`, and null for a table shared by several sources, which names the source of
 * each row. `rows` is the number of its data rows; null when it cannot be read.
 */
export interface TableEntry {
  file: string;
  kind: TableFileKind;
  info: InfoClass;
  source: string | null;
  rows: number | null;
}

/** A kind of table as the local server describes it, in the order of the workbook sheets with the raw table last. */
export interface TableKindEntry {
  kind: TableFileKind;
  label: string;
  info: InfoClass;
  /** Whether a table of the kind belongs to one source; the others name the source of each row. */
  per_source: boolean;
  /** Whether Add table adds a table of the kind. */
  addable: boolean;
}

export interface StudyReference {
  pmid?: string;
  doi?: string;
}

export interface Curator {
  user: string;
  /** From 0 to 5 in half steps. */
  rating: number;
}

export interface Comment {
  user: string;
  text: string;
}

export interface Notes {
  descriptions: string[];
  comments: Comment[];
}

export interface SourceAsset {
  url: string;
  sha256: string;
}

export interface ManualCuration {
  kind: "manual_curation";
  source_key: string;
}

export interface DataImport {
  kind: "data_import";
  source_key: string;
  release: string;
  revision: string;
  importer: string;
  importer_version: string;
  assets: SourceAsset[];
  dataset_ids: string[];
  report_file?: string;
  evidence_kind: "observed" | "derived" | "simulated" | "unknown";
  reference_scope: "primary_publication" | "source_document" | "compilation" | "unknown";
  source_terms?: string;
}

export interface AutomaticCuration {
  kind: "automatic_curation";
  source_key: string;
  method: string;
  version: string;
  assets: SourceAsset[];
  run_id: string;
}

export type Provenance = ManualCuration | DataImport | AutomaticCuration;

export interface Release {
  pkdb_id: string;
  date: string;
}

export interface StudyMetadata {
  format: 2;
  reference?: StudyReference;
  creator: string;
  curators: Curator[];
  collaborators: string[];
  licence: "open" | "closed";
  access: "public" | "private";
  provenance: Provenance;
  issue?: number;
  release?: Release;
  descriptions: string[];
  comments: Comment[];
  notes: Partial<Record<TableKind, Notes>>;
}

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

// review.json

export type ReviewStatus = "draft" | "in_review" | "approved";

export interface ReviewTarget {
  file?: string;
  rows?: Record<string, string>;
  column?: string;
  /** A part of a file without rows, such as a dataset of a WebPlotDigitizer project; excludes rows and column. */
  key?: string;
}

export interface ThreadEntry {
  author: string;
  created: string;
  text: string;
}

export interface ReviewItem {
  id: string;
  kind: "question" | "uncertainty" | "issue";
  state: "open" | "resolved" | "dismissed";
  target?: ReviewTarget;
  acknowledges?: string;
  text: string;
  author: string;
  agent?: string;
  created: string;
  thread: ThreadEntry[];
  resolved_by?: string;
  resolved?: string;
}

export interface Review {
  status: ReviewStatus;
  reviewers: string[];
  approved_by?: string;
  approved?: string;
  items: ReviewItem[];
}

/** `study.json` or `review.json` with the revision to write over; `value` is null when invalid. */
export interface DocumentState<T> {
  revision: string | null;
  value: T | null;
  issues: ValidationIssue[];
}

// Study rows of the overview

export type RowStatus =
  | "discovered"
  | "queued"
  | "validating"
  | "uploading"
  | "valid"
  | "invalid"
  | "changed"
  | "conflict"
  | "failed"
  | "waiting"
  | "unknown";

export type SaveMode = "validate" | "upload" | "off";

export type SyncStatus =
  | "in_sync"
  | "workbook_open"
  | "syncing"
  | "changed"
  | "conflict"
  | "no_workbook"
  | "unknown"
  | "not_checked";

export interface SyncState {
  status: SyncStatus;
  changes: number;
  conflicts: number;
}

/** The row summary of a study; empty until the first scan reads the folder. */
export interface StudySummary {
  title?: string | null;
  review_status?: ReviewStatus | null;
  open_items?: number;
  curators?: string[];
  creator?: string | null;
  release?: Release | null;
  issue?: number | null;
  provenance?: { kind: string | null; method?: string };
  ai?: boolean;
}

export interface IssueState {
  number: number;
  state: string | null;
  labels: string[];
  assignees: string[];
  url: string | null;
}

export interface Upload {
  persistence: string;
  at: string;
  endpoint: string;
  url: string | null;
}

export interface Progress {
  stage: string;
  completed: number;
  total: number;
}

export type ReferenceSummary =
  | { error: string }
  | {
      sid: string | null;
      pmid: string | null;
      doi: string | null;
      title: string | null;
      journal: string | null;
      abstract: string | null;
      publication_date: string | null;
      authors: string[];
    };

/** A study row of the state: the counts of its problems; the study page lists them. */
export interface StudyRow {
  /** The identity `<substance>/<name>`. */
  id: string;
  name: string;
  /** The folder relative to the workspace. */
  path: string;
  duplicate: boolean;
  substance: string;
  /**
   * The folder substance first, then the other substance folders of the workspace that the tables
   * of the study name, as the app last read them (`pkdb issues sync` labels its issue so).
   */
  substances: string[];
  mode: SaveMode;
  status: RowStatus;
  stale: boolean;
  files: { id: string; path: string }[];
  last_upload: Upload | null;
  progress: Progress | null;
  report_id: string | null;
  summary: StudySummary;
  reference: ReferenceSummary | null;
  sync: SyncState;
  counts: { errors: number; warnings: number };
  issue: IssueState | null;
  message?: string;
  report_complete?: boolean;
  report_truncated?: boolean;
  report_incomplete?: boolean;
}

// Errors

/** The error body of the local API, `describe` in python/src/pkdb/curation/errors.py. */
export interface ErrorBody {
  /** What could not be done, such as `Could not open the tables of caffeine/Demo2020.` */
  error: string;
  code: string;
  detail: string | null;
  /** `Open tables (POST /local/studies/tables)` */
  action: string;
  request_id: string;
  time: string;
  /** Only of an unexpected error; the activity keeps the body without it. */
  traceback?: string;
  /** The entry of a failed action of a study in its activity. */
  activity_id?: string;
}

/** The last failure of the file watcher of pkdb curate; `recovered` once a later check succeeded. */
export interface WatcherError {
  time: string;
  detail: string | null;
  recovered: boolean;
}

// Jobs

export type JobAction = "validate" | "validate_remote" | "upload" | "write";

export type JobStatus =
  | "queued"
  | "running"
  | "succeeded"
  /** The validation ran and found problems; `failed` is a job that could not run. */
  | "invalid"
  | "failed"
  | "canceled"
  | "conflict"
  | "unknown"
  | "reviewed";

/** A part of the message of a job: text, or the review item that the message names. */
export type JobMessagePart = { text: string } | { item: string };

export interface Job {
  id: string;
  study_id: string;
  study_name: string;
  /** The workspace of the job; jobs saved by an earlier version have none. */
  workspace?: string;
  action: JobAction;
  status: JobStatus;
  stage?: string;
  created_at: string;
  message: string;
  /** The review item that a write of the app named. */
  item?: string;
  /** The message split around the review item it names, from the server. */
  parts?: JobMessagePart[];
  automatic: boolean;
  endpoint?: string;
  persistence?: string;
  report_id: string | null;
  upload?: Upload;
  sid?: string;
  /** The error of a failed job or of a failed change in the app, without its traceback. */
  error?: ErrorBody;
  source_digest?: string;
}

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

/** An axis of the plot of mapped rows. */
export type Axis = "x" | "y";

/** The scale of an axis of the plot of mapped rows, as Plotly names it. */
export type AxisScale = "linear" | "log";

/** The scales of the axes of the plot of mapped rows. */
export interface AxisScales {
  x: AxisScale;
  y: AxisScale;
}

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

// Study page

export interface Profile {
  username: string;
  display_name: string;
  title: string | null;
  affiliation: string | null;
  avatar_url: string | null;
}

export interface People {
  creator: Profile | null;
  curators: { user: string; rating: number | null; profile: Profile }[];
  collaborators: Profile[];
}

/** A warning that a review item acknowledges. */
export interface AcknowledgedWarning {
  id: string;
  code: string;
  target: ReviewTarget | null;
  text: string;
  author: string;
  resolved_by: string | null;
  resolved: string | null;
  /**
   * What the acknowledgement covers (`acknowledgement_scope` in `studyformat/validation.py`):
   * every warning of its code in the study, in its file or in a column of the file, also later
   * ones; or just the warnings at its rows or with its key.
   */
  scope: "study" | "file" | "column" | "rows" | "key";
}

export interface ConflictData {
  file: string;
  kind: TableFileKind;
  sheet: string;
  /** The rows of the sheet, from 1; the header of a data sheet is row 1. */
  workbook_rows: { row: number; text: string }[];
  /** The lines of the file: the header of a table is line 0, a raw table starts at line 1. */
  table_lines: { line: number; text: string }[];
  base_lines: string[];
  kept: "workbook" | "tables" | null;
  /** The side that removed the whole table, which the other side lists from its header; null for rows that both sides changed. */
  removed: "workbook" | "tables" | null;
}

export interface SourceSummary {
  source: string;
  /** A paper table `Tab…`, a figure `Fig…` or the text. */
  kind: "table" | "figure" | "text";
  image: string | null;
  /** The URL of the image on the local server, or null without an image. */
  image_url: string | null;
  raw: string | null;
  raw_kind: "table" | "digitization" | null;
  tables: string[];
  /** The image `<name>_<source>.png` that the source lacks. */
  missing_image: string | null;
  /** The raw extraction that the source lacks: `<name>_<source>.tsv` or `<name>_<source>.wpd.json`. */
  missing_raw: string | null;
}

/** A PDF at the top of the study folder: `<name>.pdf`, the paper, first, then the others by name. */
export interface PaperFile {
  file: string;
  /** Where the local server serves it: whole, or in byte ranges as PDF.js reads it. */
  url: string;
  bytes: number;
  /**
   * The version of its content, which changes when the PDF is written, also at the same size:
   * the viewer opens it again then, as PDF.js reads it in ranges, which must not mix two PDFs.
   */
  version: string;
}

export interface StudyDetail {
  id: string;
  path: string;
  status: RowStatus;
  mode: SaveMode;
  sync: SyncState;
  counts: { errors: number; warnings: number };
  summary: StudySummary;
  issue: IssueState | null;
  problems: Problem[];
  message: string | null;
  last_upload: Upload | null;
  /** Newest first. */
  jobs: Job[];
  report_id: string | null;
  /**
   * Changes with the content of any file of the study, as the local server last scanned it; null
   * before the first scan. Unlike the ETag of the page, it stays when only a job changes.
   */
  files_version: string | null;
  metadata: DocumentState<StudyMetadata>;
  reference: ReferenceSummary | null;
  /** Whether `reference.json` has the identifiers of `study.json`; null when it names none. */
  reference_match: boolean | null;
  people: People;
  review: DocumentState<Review>;
  acknowledged: AcknowledgedWarning[];
  conflicts: ConflictData[];
  sources: SourceSummary[];
  files: string[];
  /** The PDFs of the folder, `<name>.pdf` first; empty without any. */
  papers: PaperFile[];
  /** The table files and raw tables in the order of the workbook sheets; empty beyond the upload limits. */
  tables: TableEntry[];
  /** The kinds of tables, also beyond the upload limits. */
  table_kinds: TableKindEntry[];
  /**
   * What the target of each review item with a file selects, by item id, as the library matches
   * it; empty beyond the upload limits.
   */
  targets: Record<string, TargetMatch>;
}

/** A series of a figure with a WebPlotDigitizer project: the figure and the series name. */
export interface DigitizedSeries {
  source: string;
  series: string;
}

/** What a review target selects, as the local server matches it. */
export interface TargetMatch {
  /**
   * The lines (from 1, below the header line 0) of the rows that its row filter matches in a data table, in file order; null
   * for a target without a row filter or of a file that is no data table, such as a raw table.
   */
  lines: number[] | null;
  /** The series that its filter names in a timecourse or scatter table of a digitized figure. */
  series: DigitizedSeries | null;
  /** The rows of the data table that `lines` were matched in; null for a file that is no data table. */
  total: number | null;
}

export interface TableRow {
  /** The line of the row: the first row of a table is line 1, below its header, line 0; a raw table starts at line 1. */
  line: number;
  cells: string[];
}

export type TableResponse =
  | { file: string; kind: "table"; header: string[]; rows: TableRow[] }
  | { file: string; kind: "raw"; rows: TableRow[] };

export interface MappedTable {
  file: string;
  kind: string;
  header: string[];
  /** The line (from 1, below the header line 0) and the cells in header order. */
  rows: [number, string[]][];
  /** Whether the table names the source of each row, as subjects.tsv does; else all its rows belong to the source. */
  shared: boolean;
}

export interface OverlayPoint {
  /** The series of the point: the label of a timecourse row, the name of a scatter row, or the series of an outputs row with a time. */
  series: string;
  role: "raw" | "mapped";
  px: number;
  py: number;
  x: number;
  y: number;
  file: string;
  line: number | null;
  /**
   * The pixels of the low and the high end of the error bar of a mapped row; null without that
   * end, and for an end at or below 0 on a log axis of the digitization.
   */
  error_low_px: [number, number] | null;
  error_high_px: [number, number] | null;
  /** The values as printed: the cells of a mapped row, six significant digits of a digitized point. */
  x_text: string;
  y_text: string;
  /** A digitized end of an error bar, of the dataset `<series>;error_bar`. */
  error_bar_end: boolean;
}

/** A mapped row of a timecourse or scatter table, or an outputs row with a time, in the units of its table. */
export interface SourcePoint {
  /**
   * The series of the point: the `label` of a timecourse row, the `name` of a scatter row, or the
   * subjects, interventions, measurement, substance and tissue of an outputs row joined with " · ".
   */
  series: string;
  kind: "timecourses" | "scatters" | "outputs";
  file: string;
  line: number;
  x: number;
  y: number;
  /**
   * The low and the high end of the error bar of a timecourse row around `y`: the first statistic that
   * fits, the one that `error_type` names first (as reported or as the digitized `error_bar` gives it),
   * then around a `gmean` `gsd`, `sd`, `se`, and around a `mean` or `median` `sd`, `se`. A negative `sd`
   * or `se` or a `gsd` below 1 is skipped and the next statistic is tried; a row with no valid
   * statistic has no bar, and an `error_bar` without `error_type` is mirrored. Null without a bar.
   */
  error_low: number | null;
  error_high: number | null;
  /** The cells as printed. */
  x_text: string;
  y_text: string;
}

/** A series of a figure in the order of its colors, which `pkdb plot` shares. */
export interface SourceSeries {
  name: string;
  /** On paper and the light surface. */
  color: string;
  /** On the dark surface. */
  dark_color: string;
  x_label: string | null;
  y_label: string | null;
}

export interface SourceView {
  source: string;
  image: string | null;
  image_url: string | null;
  image_size: [number, number] | null;
  raw_grid: string[][] | null;
  digitization: string | null;
  mapped: MappedTable[];
  overlay: OverlayPoint[];
  unmatched: string[];
  /** `overlay` when the overlay draws on the image; else the image and a plot of `points` go side by side. */
  layout: "overlay" | "side_by_side";
  points: SourcePoint[];
  series: SourceSeries[];
  /** Whether the digitization draws the x axis on a log scale; false without a digitization. */
  log_x: boolean;
  /** Whether the digitization draws the y axis on a log scale; false without a digitization. */
  log_y: boolean;
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

export const isStudyDetail = hasKeys<StudyDetail>(
  "id",
  "path",
  "status",
  "mode",
  "sync",
  "counts",
  "summary",
  "issue",
  "problems",
  "message",
  "last_upload",
  "jobs",
  "report_id",
  "files_version",
  "metadata",
  "reference",
  "reference_match",
  "people",
  "review",
  "acknowledged",
  "conflicts",
  "sources",
  "files",
  "papers",
  "tables",
  "table_kinds",
  "targets",
);

export const isJobReport = hasKeys<JobReport>("job", "persistence", "report");

export const isTableResponse = hasKeys<TableResponse>("file", "kind", "rows");

export const isSourceView = hasKeys<SourceView>(
  "source",
  "image",
  "image_url",
  "image_size",
  "raw_grid",
  "digitization",
  "mapped",
  "overlay",
  "unmatched",
  "layout",
  "points",
  "series",
  "log_x",
  "log_y",
);

export const isCurators = hasKeys<{ curators: Profile[] }>("curators");

export const isDirectories = hasKeys<Directories>("path", "parent", "home", "kind", "truncated", "entries");

export const isGitHubAssignments = hasKeys<GitHubAssignments>("users", "issues", "status");

export const isMetadataWrite = hasKeys<MetadataWrite>("revision", "reference", "reference_error");

export const isReviewWrite = hasKeys<ReviewWrite>("revision");

export const isTablesResult = hasKeys<TablesResult>("ok", "workbook_action", "changes", "conflicts", "issues");

export const isTablePreview = hasKeys<TablePreview>("table", "file", "image", "image_found", "issues");

export const isTargetMatch = hasKeys<TargetMatch>("lines", "series", "total");

export const isReferenceRead = hasKeys<{ reference: ReferenceRecord }>("reference");

export const isReferenceCandidates = hasKeys<{ candidates: ReferenceRecord[] }>("candidates");

export const isReferencePreview = hasKeys<ReferencePreview>("reference", "changes", "revision", "token");

export const isReferenceSaved = hasKeys<{ ok: boolean }>("ok");
