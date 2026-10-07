/** Responses of the local API of `pkdb curate` for the tests of the curation app. */
import type { Profile, Snapshot, StudyDetail, StudyMetadata, StudyRow } from "../../src/curation-app/api/types";

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
      { source: "Fig1", image: "Example_Fig1.png", raw: null, raw_kind: null, tables: ["timecourses_Fig1.tsv"] },
      {
        source: "Tab2",
        image: "Example_Tab2.png",
        raw: "Example_Tab2.tsv",
        raw_kind: "table",
        tables: ["outputs_Tab2.tsv"],
      },
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
