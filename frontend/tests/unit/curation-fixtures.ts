/** Responses of the local API of `pkdb curate` for the tests of the curation app. */
import type { Snapshot, StudyRow } from "../../src/curation-app/api/types";

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
    vocabulary: { status: "offline" },
    github: { users: [], issues: [], status: "not_loaded", user: "", repository: "matthiaskoenig/pkdb_data" },
    studies: [studyRow()],
    format1_folders: 0,
    jobs: [],
    recent_workspaces: [{ path: "/work/pkdb_data", exists: true }],
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
