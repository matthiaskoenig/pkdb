import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ServerStopped, SessionMissing, setCsrfToken } from "../../src/curation-app/api/client";
import type { Snapshot, StudyDetail, StudyMetadata, StudyRow } from "../../src/curation-app/api/types";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";

const metadata: StudyMetadata = {
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
};

const row: StudyRow = {
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
};

function snapshot(changes: Partial<Snapshot> = {}): Snapshot {
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
    studies: [row],
    format1_folders: 0,
    jobs: [],
    recent_workspaces: [{ path: "/work/pkdb_data", exists: true }],
    ...changes,
  };
}

function detail(revision: string, id = "caffeine/Example"): StudyDetail {
  return {
    id,
    path: `studies/${id}`,
    status: row.status,
    mode: row.mode,
    sync: row.sync,
    counts: row.counts,
    summary: row.summary,
    issue: null,
    problems: [],
    message: null,
    last_upload: null,
    jobs: [],
    report_id: null,
    metadata: { revision, value: metadata, issues: [] },
    reference: null,
    reference_match: false,
    people: {
      creator: { username: "curator", display_name: "curator", title: null, affiliation: null, avatar_url: null },
      curators: [],
      collaborators: [],
    },
    review: { revision: "absent", value: null, issues: [] },
    acknowledged: [],
    conflicts: [],
    sources: [],
    files: ["study.json"],
  };
}

function json(body: unknown, { status = 200, etag }: { status?: number; etag?: string } = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...(etag ? { ETag: etag } : {}) },
  });
}

/** Records the requests that the stores send: method, URL, If-None-Match and JSON body. */
function server(answer: (method: string, url: string) => Response) {
  const requests: { method: string; url: string; etag: string | null; body: unknown }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const method = init?.method ?? "GET";
    const url = String(input);
    requests.push({
      method,
      url,
      etag: new Headers(init?.headers).get("If-None-Match"),
      body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
    });
    return answer(method, url);
  });
  return requests;
}

let pinia: Pinia;

beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  setCsrfToken("csrf");
});

afterEach(() => {
  // Stops the polling of the stores.
  disposePinia(pinia);
});

describe("useStudyStore", () => {
  it("opens a study by loading its detail", async () => {
    const requests = server(() => json(detail("r1"), { etag: '"d1"' }));
    const store = useStudyStore();
    await store.open("caffeine", "Example");
    expect(requests.map(({ method, url }) => `${method} ${url}`)).toEqual(["GET /local/studies/caffeine/Example"]);
    expect(store.identity).toBe("caffeine/Example");
    expect(store.detail?.metadata.revision).toBe("r1");
  });

  it("percent-encodes each segment of the identity", async () => {
    const requests = server((_method, url) =>
      url.includes("/tables/")
        ? json({ file: "outputs Tab3.tsv", kind: "table", header: ["label"], rows: [{ line: 2, cells: ["a"] }] })
        : json(detail("r1", "caffeine/Smith 2020%")),
    );
    const store = useStudyStore();
    await store.open("caffeine", "Smith 2020%");
    await store.table("outputs Tab3.tsv");
    expect(requests.map(({ url }) => url)).toEqual([
      "/local/studies/caffeine/Smith%202020%25",
      "/local/studies/caffeine/Smith%202020%25/tables/outputs%20Tab3.tsv",
    ]);
  });

  it("refreshes the detail after saving the metadata", async () => {
    let revision = "r1";
    const requests = server((method) => {
      if (method === "POST") {
        revision = "r2";
        return json({ revision, reference: null, reference_error: null });
      }
      return json(detail(revision), { etag: `"${revision}"` });
    });
    const store = useStudyStore();
    await store.open("caffeine", "Example");
    const result = await store.saveMetadata("r1", metadata);
    expect(result.revision).toBe("r2");
    expect(requests[1]).toMatchObject({
      method: "POST",
      url: "/local/studies/metadata",
      body: { study: "caffeine/Example", revision: "r1", metadata },
    });
    expect(requests[2]).toMatchObject({ method: "GET", url: "/local/studies/caffeine/Example", etag: '"r1"' });
    expect(store.detail?.metadata.revision).toBe("r2");
  });

  it("sends the review and tables actions of the open study", async () => {
    const requests = server((_method, url) => {
      if (url === "/local/studies/review") return json({ revision: "v2" });
      if (url === "/local/studies/tables")
        return json({ ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [], opened: true });
      return json(detail("r1"));
    });
    const store = useStudyStore();
    await store.open("caffeine", "Example");
    await expect(store.reviewAction("v1", "status", { status: "in_review" })).resolves.toEqual({ revision: "v2" });
    await expect(store.tablesAction("open")).resolves.toMatchObject({ ok: true, opened: true });
    expect(requests.filter(({ method }) => method === "POST").map(({ body }) => body)).toEqual([
      { status: "in_review", study: "caffeine/Example", revision: "v1", action: "status" },
      { study: "caffeine/Example", action: "open" },
    ]);
    expect(requests.filter(({ method }) => method === "GET")).toHaveLength(3);
  });

  it("revalidates tables and sources with their own ETags", async () => {
    const view = {
      source: "Fig2",
      image: "Example_Fig2.png",
      image_size: [640, 480],
      raw_grid: null,
      digitization: "Example_Fig2.json",
      mapped: [],
      overlay: [],
      unmatched: [],
      image_url: "/local/studies/caffeine/Example/files/Example_Fig2.png",
    };
    const requests = server((_method, url) => {
      const etag = requests.at(-1)?.etag;
      if (!url.endsWith("/sources/Fig2")) return json(detail("r1"), { etag: '"d1"' });
      return etag ? new Response(null, { status: 304, headers: { ETag: etag } }) : json(view, { etag: '"s1"' });
    });
    const store = useStudyStore();
    await store.open("caffeine", "Example");
    const first = await store.source("Fig2");
    const second = await store.source("Fig2");
    expect(second).toBe(first);
    expect(requests.slice(1).map(({ url, etag }) => [url, etag])).toEqual([
      ["/local/studies/caffeine/Example/sources/Fig2", null],
      ["/local/studies/caffeine/Example/sources/Fig2", '"s1"'],
    ]);
  });

  it("loads the curator roster once", async () => {
    const curator = { username: "curator", display_name: "Curator", title: null, affiliation: null, avatar_url: null };
    const requests = server(() => json({ curators: [curator] }));
    const store = useStudyStore();
    await expect(store.curators()).resolves.toEqual([curator]);
    await expect(store.curators()).resolves.toEqual([curator]);
    expect(requests.map(({ url }) => url)).toEqual(["/local/curators"]);
  });

  it("forgets the study when it is closed", async () => {
    server(() => json(detail("r1")));
    const store = useStudyStore();
    await store.open("caffeine", "Example");
    store.close();
    expect(store.identity).toBeNull();
    expect(store.detail).toBeNull();
  });
});

describe("useOverviewStore", () => {
  it("posts the studies and the action of a job and refreshes the state", async () => {
    const requests = server((method) => (method === "POST" ? json({ ok: true }) : json(snapshot(), { etag: '"s1"' })));
    const store = useOverviewStore();
    await store.enqueue(["caffeine/Example"], "validate");
    expect(requests[0]).toMatchObject({
      method: "POST",
      url: "/local/jobs",
      body: { ids: ["caffeine/Example"], action: "validate" },
    });
    expect(requests[1]).toMatchObject({ method: "GET", url: "/local/state" });
    expect(store.snapshot?.workspace).toBe("/work/pkdb_data");
  });

  it("shows a stopped server or a missing session and recovers with the next answer", async () => {
    const answers: (() => Response)[] = [
      () => json(snapshot(), { etag: '"s1"' }),
      () => {
        throw new TypeError("Failed to fetch");
      },
      () => json({ error: "Open the launch URL printed in your terminal" }, { status: 401 }),
      () => json(snapshot({ paused: true }), { etag: '"s2"' }),
    ];
    server(() => {
      const answer = answers.shift();
      if (!answer) throw new Error("No more answers");
      return answer();
    });
    const store = useOverviewStore();
    await store.start();
    expect(store.snapshot?.paused).toBe(false);

    await store.refresh();
    expect(store.error).toBeInstanceOf(ServerStopped);
    expect(store.snapshot?.paused).toBe(false);

    await store.refresh();
    expect(store.error).toBeInstanceOf(SessionMissing);

    await store.refresh();
    expect(store.error).toBeNull();
    expect(store.snapshot?.paused).toBe(true);
    store.stop();
  });
});
