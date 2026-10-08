/** Responses of the local API of `pkdb curate` for the tests of the curation app. */
import type {
  ConflictData,
  Profile,
  ReviewItem,
  Snapshot,
  SourceSummary,
  StudyDetail,
  StudyMetadata,
  StudyRow,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import limitsFixture from "../fixtures/curation-contract/limits.json";

/** The overview row of the valid study `caffeine/Example`. */
export function studyRow(changes: Partial<StudyRow> = {}): StudyRow {
  return {
    id: "caffeine/Example",
    name: "Example",
    path: "studies/caffeine/Example",
    duplicate: false,
    substance: "caffeine",
    mode: "validate",
    status: "valid",
    stale: false,
    files: [{ id: "study.json", path: "study.json" }],
    problems: [],
    last_upload: null,
    progress: null,
    report_id: null,
    summary: {
      title: "Caffeine pharmacokinetics",
      review_status: "draft",
      open_items: 0,
      curators: ["curator"],
      creator: "curator",
      release: null,
      issue: null,
      provenance: { kind: "manual_curation" },
      ai: false,
    },
    reference: null,
    sync: { status: "in_sync", changes: 0, conflicts: 0 },
    counts: { errors: 0, warnings: 0 },
    issue: null,
    ...changes,
  };
}

/** The state of `GET /local/state` for the workspace `/work/pkdb_data` with the user `curator`, offline. */
export function snapshot(changes: Partial<Snapshot> = {}): Snapshot {
  return {
    workspace: "/work/pkdb_data",
    endpoint: "",
    user: "curator",
    author: { user: "curator", reason: null },
    authenticated: false,
    account: null,
    can_upload: false,
    connection: "offline",
    connection_error: null,
    checked_at: null,
    client_version: "0.11.1",
    server_version: null,
    update_required: false,
    offline: true,
    paused: false,
    theme: "system",
    vocabulary: { status: "offline" },
    github: { users: [], issues: [], status: "not_loaded", user: "", repository: "matthiaskoenig/pkdb_data" },
    studies: [studyRow()],
    format1_folders: 0,
    jobs: [],
    clearable_jobs: 0,
    recent_workspaces: [{ path: "/work/pkdb_data", exists: true }],
    ...changes,
  };
}

/** The `study.json` of `caffeine/Example`: manually curated by `curator`, with a PMID. */
export function studyMetadata(changes: Partial<StudyMetadata> = {}): StudyMetadata {
  return {
    format: 2,
    reference: { pmid: "3678553" },
    creator: "curator",
    curators: [{ user: "curator", rating: 4.5 }],
    collaborators: [],
    licence: "open",
    access: "public",
    provenance: { kind: "manual_curation", source_key: "pkdb.manual" },
    descriptions: [],
    comments: [],
    notes: {},
    ...changes,
  };
}

/**
 * A `study.json` with every field: an AI curation with two curators, a collaborator, an issue,
 * a release, descriptions, comments and notes of two table kinds.
 */
export function fullStudyMetadata(changes: Partial<StudyMetadata> = {}): StudyMetadata {
  return {
    format: 2,
    reference: { pmid: "2895442", doi: "10.1007/BF00637675" },
    creator: "curator",
    curators: [
      { user: "mkoenig", rating: 3 },
      { user: "janekg", rating: 4.5 },
    ],
    collaborators: ["Jane Doe"],
    licence: "closed",
    access: "public",
    provenance: {
      kind: "automatic_curation",
      source_key: "pkdb.ai",
      method: "claude-opus-5-5",
      version: "2026-10",
      assets: [{ url: "https://example.org/Harder1988.pdf", sha256: "a".repeat(64) }],
      run_id: "run-2026-10-07-01",
    },
    issue: 2158,
    release: { pkdb_id: "PKDB00198", date: "2026-09-28" },
    descriptions: ["Plasma levels in µg/l."],
    comments: [{ user: "mkoenig", text: "Checked against the PDF." }],
    notes: {
      outputs: { descriptions: ["Clearance from Table 2."], comments: [{ user: "janekg", text: "AUC rounded." }] },
      timecourses: { descriptions: ["Digitized from Figure 1."], comments: [] },
    },
    ...changes,
  };
}

/** The profile of a curator of the roster, with an avatar unless `avatar` is false. */
export function profile(username: string, display_name: string, avatar = true): Profile {
  return {
    username,
    display_name,
    title: null,
    affiliation: null,
    avatar_url: avatar ? `/avatars/${username}.webp` : null,
  };
}

/** The bundled curator roster of `GET /local/curators`. */
export function roster(): Profile[] {
  return [
    profile("janekg", "Jan Grzegorzewski"),
    profile("mkoenig", "Matthias König"),
    profile("curator", "Curator", false),
  ];
}

/**
 * An open question of `curator` about the whole study, without replies; a resolved or dismissed
 * item gets `resolved_by` and `resolved` unless `changes` sets them.
 */
export function reviewItem(changes: Partial<ReviewItem> = {}): ReviewItem {
  const closed = changes.state !== undefined && changes.state !== "open";
  return {
    id: "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
    kind: "question",
    state: "open",
    text: "Is the mean read from the table?",
    author: "curator",
    created: "2026-10-05T10:12:00Z",
    thread: [],
    ...(closed ? { resolved_by: "mkoenig", resolved: "2026-10-06T09:00:00Z" } : {}),
    ...changes,
  };
}

/**
 * The study page of the valid draft study `caffeine/Example` (`GET /local/studies/caffeine/Example`),
 * built from the fields of its overview row: no review items, a paper table `Tab2` with its raw
 * table and a figure `Fig1`.
 */
export function studyDetail(changes: Partial<StudyDetail> = {}): StudyDetail {
  const row = studyRow();
  return {
    id: row.id,
    path: row.path,
    status: row.status,
    mode: row.mode,
    sync: row.sync,
    counts: row.counts,
    summary: row.summary,
    issue: row.issue,
    problems: [],
    message: null,
    last_upload: null,
    jobs: [],
    report_id: null,
    files_version: "files-1",
    metadata: { revision: "study-1", value: studyMetadata(), issues: [] },
    reference: null,
    reference_match: null,
    people: {
      creator: { username: "curator", display_name: "curator", title: null, affiliation: null, avatar_url: null },
      curators: [],
      collaborators: [],
    },
    review: { revision: "review-1", value: { status: "draft", reviewers: [], items: [] }, issues: [] },
    acknowledged: [],
    conflicts: [],
    sources: [
      sourceSummary({
        source: "Fig1",
        kind: "figure",
        image: "Example_Fig1.png",
        tables: ["timecourses_Fig1.tsv"],
        missing_raw: "Example_Fig1.wpd.json",
      }),
      sourceSummary({
        source: "Tab2",
        image: "Example_Tab2.png",
        raw: "Example_Tab2.tsv",
        raw_kind: "table",
        tables: ["outputs_Tab2.tsv"],
      }),
    ],
    files: [
      "characteristica.tsv",
      "Example.pdf",
      "Example_Fig1.png",
      "Example_Tab2.png",
      "Example_Tab2.tsv",
      "interventions.tsv",
      "outputs_Tab2.tsv",
      "reference.json",
      "review.json",
      "study.json",
      "subjects.tsv",
      "timecourses_Fig1.tsv",
    ],
    tables: [
      { file: "subjects.tsv", kind: "subjects" },
      { file: "interventions.tsv", kind: "interventions" },
      { file: "characteristica.tsv", kind: "characteristica" },
      { file: "outputs_Tab2.tsv", kind: "outputs" },
      { file: "timecourses_Fig1.tsv", kind: "timecourses" },
      { file: "Example_Tab2.tsv", kind: "raw" },
    ],
    targets: {},
    ...changes,
  };
}

/** The fields of a study page that the local server sends beyond the upload limits. */
type BeyondLimits = Pick<StudyDetail, "problems" | "sources" | "files" | "tables" | "targets">;

/**
 * What the local server sends for a study beyond the upload limits, by limit: the limit as the
 * first problem, and no files, sources, tables or targets (python/tests/test_curation_contract.py).
 */
export const BEYOND_LIMITS = limitsFixture.details as BeyondLimits[];

/**
 * The study page of `caffeine/Example` beyond the upload limit of files, with `changes`: the
 * fields beyond the limits as the local server sends them, on the fields of `studyDetail`.
 */
export function beyondLimitsDetail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({ status: "invalid", counts: { errors: 1, warnings: 0 }, ...BEYOND_LIMITS[0], ...changes });
}

/** A source of `GET /local/studies/<id>`: a paper table with its image and raw extraction unless `changes` say otherwise. */
export function sourceSummary(changes: Partial<SourceSummary> & Pick<SourceSummary, "source">): SourceSummary {
  return {
    kind: "table",
    image: null,
    raw: null,
    raw_kind: null,
    tables: [],
    missing_image: null,
    missing_raw: null,
    ...changes,
  };
}

/** A JSON response, with an ETag when given. */
export function json(body: unknown, { status = 200, etag }: { status?: number; etag?: string } = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...(etag ? { ETag: etag } : {}) },
  });
}

// Sync conflicts, as `pkdb tables sync --format json` and `POST /local/studies/tables` report them:
// real answers for caffeine/Approved2001 and two copies of it, with the study renamed to Example.

/** The columns of `outputs_<source>.tsv` as the library writes them. */
export const OUTPUTS_COLUMNS = [
  ...["study", "source", "subjects", "interventions", "measurement", "calculation", "substance", "tissue"],
  ...["method", "choice", "time", "time_unit", "count", "mean", "sd", "se", "cv", "gmean", "gsd", "gcv"],
  ...["median", "min", "max", "unit", "error_bar", "error_type", "comment"],
];

/** The columns of `subjects.tsv`. */
export const SUBJECTS_COLUMNS = ["study", "name", "parent", "count", "source", "comment"];

/** The columns of `scatters_<source>.tsv`. */
export const SCATTERS_COLUMNS = [
  ...["study", "source", "name", "subjects", "x_interventions", "x_measurement", "x_substance", "x_tissue"],
  ...["x_method", "x_time", "x_time_unit", "x_mean", "x_unit", "y_interventions", "y_measurement"],
  ...["y_substance", "y_tissue", "y_method", "y_time", "y_time_unit", "y_mean", "y_unit", "comment"],
];

/** A canonical TSV line: the cells of `columns` from `cells`, empty otherwise. */
function tsvLine(columns: string[], cells: Record<string, string>): string {
  return columns.map((column) => cells[column] ?? "").join("\t");
}

function outputsLine(mean: string): string {
  return tsvLine(OUTPUTS_COLUMNS, {
    study: "Example",
    source: "Tab2",
    subjects: "all",
    interventions: "D1",
    measurement: "cmax",
    substance: "caffeine",
    tissue: "plasma",
    mean,
    sd: "0.5",
    unit: "mg/l",
  });
}

function scattersLine(subjects: string, x: string, y: string): string {
  return tsvLine(SCATTERS_COLUMNS, {
    study: "Example",
    source: "Fig2",
    name: "age_vs_cmax",
    subjects,
    x_measurement: "age",
    x_mean: x,
    x_unit: "yr",
    y_interventions: "D1",
    y_measurement: "cmax",
    y_substance: "caffeine",
    y_tissue: "plasma",
    y_mean: y,
    y_unit: "mg/l",
  });
}

/** The `sync_conflict` error of a conflict, located at the sheet in the workbook. */
function syncConflict(sheet: string, row: number | null, message: string): ValidationIssue {
  return {
    code: "sync_conflict",
    severity: "error",
    message,
    source: { file: "Example.xlsx", sheet, row, column: null, path: [] },
    category: "workbook",
    stage: "parse",
    field: null,
    expected: {},
    context: {},
    related_sources: [],
    suggestions: [
      {
        kind: "fix",
        message:
          "Keep one side with pkdb tables sync --keep workbook or --keep tables, or edit the workbook so that the " +
          "conflicting rows equal the tables.",
        candidates: [],
        command: null,
      },
    ],
    documentation_url: null,
  };
}

/** The workbook and the table changed the mean of the same row differently. */
export const REGION_CONFLICT: ConflictData = {
  file: "outputs_Tab2.tsv",
  kind: "outputs",
  sheet: "outputs_Tab2",
  workbook_rows: [{ row: 2, text: outputsLine("6.1") }],
  table_lines: [{ line: 2, text: outputsLine("6.3") }],
  base_lines: [outputsLine("5.9")],
  kept: null,
  removed: null,
};

export const REGION_ISSUE = syncConflict(
  "outputs_Tab2",
  2,
  "The workbook and the tables changed the same rows of outputs_Tab2 differently since the last sync: row 2 of the " +
    "sheet, line 2 of outputs_Tab2.tsv",
);

/** The workbook removed a row that the table changed. */
export const ROWS_REMOVED_CONFLICT: ConflictData = {
  file: "subjects.tsv",
  kind: "subjects",
  sheet: "subjects",
  workbook_rows: [],
  table_lines: [{ line: 3, text: "Example\tS1\tall\t2\tTabA\t" }],
  base_lines: ["Example\tS1\tall\t1\tTabA\t"],
  kept: null,
  removed: null,
};

export const ROWS_REMOVED_ISSUE = syncConflict(
  "subjects",
  2,
  "The workbook and the tables changed the same rows of subjects differently since the last sync: rows removed " +
    "after row 2 of the sheet, line 3 of subjects.tsv",
);

/** The table file was deleted while its sheet changed: the sides list the whole table from its header. */
export const FILE_DELETED_CONFLICT: ConflictData = {
  file: "scatters_Fig2.tsv",
  kind: "scatters",
  sheet: "scatters_Fig2",
  workbook_rows: [
    { row: 1, text: SCATTERS_COLUMNS.join("\t") },
    { row: 2, text: scattersLine("S1", "31", "2") },
    { row: 3, text: scattersLine("S2", "40", "3") },
  ],
  table_lines: [],
  base_lines: [SCATTERS_COLUMNS.join("\t"), scattersLine("S1", "30", "2"), scattersLine("S2", "40", "3")],
  kept: null,
  removed: "tables",
};

export const FILE_DELETED_ISSUE = syncConflict(
  "scatters_Fig2",
  1,
  "scatters_Fig2.tsv was deleted, but the scatters_Fig2 sheet changed since the last sync",
);

/** A sync that found conflicts: not ok, with the conflicts and their `sync_conflict` errors. */
export function conflictAnswer(
  conflicts: [ConflictData, ValidationIssue][],
  changes: Partial<TablesResult> = {},
): TablesResult {
  return {
    ok: false,
    workbook_action: "unchanged",
    changes: [],
    conflicts: conflicts.map(([conflict]) => conflict),
    issues: conflicts.map(([, issue]) => issue),
    ...changes,
  };
}
