import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ServerStopped,
  SessionMissing,
  UnexpectedResponse,
  isAbort,
  isRevisionConflict,
  setCsrfToken,
} from "../../src/curation-app/api/client";
import type { StudyDetail } from "../../src/curation-app/api/types";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { json, snapshot, studyDetail, studyMetadata } from "./curation-fixtures";

const metadata = studyMetadata();

/** The detail of the study `id` with the `study.json` revision `revision` and no `review.json`. */
function detail(revision: string, id = "caffeine/Example"): StudyDetail {
  return studyDetail({
    id,
    path: `studies/${id}`,
    metadata: { revision, value: metadata, issues: [] },
    reference_match: false,
    review: { revision: "absent", value: null, issues: [] },
    sources: [],
    files: ["study.json"],
    tables: [],
  });
}

/** Records the requests that the stores send: method, URL, If-None-Match, JSON body and signal. */
function server(answer: (method: string, url: string) => Response | Promise<Response>) {
  const requests: { method: string; url: string; etag: string | null; body: unknown; signal: AbortSignal | null }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const method = init?.method ?? "GET";
    const url = String(input);
    requests.push({
      method,
      url,
      etag: new Headers(init?.headers).get("If-None-Match"),
      body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
      signal: init?.signal ?? null,
    });
    return answer(method, url);
  });
  return requests;
}

/** The error that a promise rejects with. */
async function rejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("Expected the promise to reject");
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

  it("refreshes the detail after a stale revision too", async () => {
    let revision = "r1";
    const requests = server((method) => {
      if (method === "GET") return json(detail(revision), { etag: `"${revision}"` });
      revision = "r2";
      return json({ error: "study.json changed on disk since it was read", file: "study.json", revision, content: "{}" }, { status: 409 });
    });
    const store = useStudyStore();
    await store.open("caffeine", "Example");
    expect(isRevisionConflict(await rejection(store.saveMetadata("r1", metadata)))).toBe(true);
    expect(requests.map(({ method }) => method)).toEqual(["GET", "POST", "GET"]);
    expect(store.detail?.metadata.revision).toBe("r2");
  });

  it("polls a newly opened study from scratch and ignores a late answer for the previous one", async () => {
    let answerLate: (response: Response) => void = () => {};
    let loadsOfA = 0;
    const requests = server((_method, url) => {
      if (url.endsWith("/B")) return json(detail("b1", "caffeine/B"), { etag: '"b1"' });
      loadsOfA += 1;
      if (loadsOfA === 1) return json(detail("a1", "caffeine/A"), { etag: '"a1"' });
      return new Promise<Response>((resolve) => (answerLate = resolve));
    });
    const store = useStudyStore();
    await store.open("caffeine", "A");
    const late = store.refresh();
    await store.open("caffeine", "B");
    answerLate(json(detail("a2", "caffeine/A"), { etag: '"a2"' }));
    await late;
    expect(store.identity).toBe("caffeine/B");
    expect(store.detail?.id).toBe("caffeine/B");
    expect(requests[1]?.signal?.aborted).toBe(true);

    await store.refresh();
    expect(requests.map(({ url, etag }) => [url, etag])).toEqual([
      ["/local/studies/caffeine/A", null],
      ["/local/studies/caffeine/A", '"a1"'],
      ["/local/studies/caffeine/B", null],
      ["/local/studies/caffeine/B", '"b1"'],
    ]);
  });

  it("drops a late table answer of a study that was closed", async () => {
    const table = { file: "outputs_Tab3.tsv", kind: "table", header: ["label"], rows: [{ line: 2, cells: ["a"] }] };
    let answerLate: (response: Response) => void = () => {};
    let tableLoads = 0;
    const requests = server((_method, url) => {
      if (!url.includes("/tables/")) return json(detail("r1", url.endsWith("/B") ? "caffeine/B" : "caffeine/A"));
      tableLoads += 1;
      if (tableLoads > 1) return json(table, { etag: '"t2"' });
      return new Promise<Response>((resolve) => (answerLate = resolve));
    });
    const store = useStudyStore();
    await store.open("caffeine", "A");
    const late = store.table("outputs_Tab3.tsv");
    await store.open("caffeine", "B");
    answerLate(json(table, { etag: '"t1"' }));
    expect(isAbort(await rejection(late))).toBe(true);
    expect(requests[1]?.signal?.aborted).toBe(true);

    await store.open("caffeine", "A");
    await expect(store.table("outputs_Tab3.tsv")).resolves.toEqual(table);
    expect(requests.at(-1)).toMatchObject({ url: "/local/studies/caffeine/A/tables/outputs_Tab3.tsv", etag: null });
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
      layout: "overlay",
      points: [],
      series: [],
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

  it("sends the acknowledgment of an unknown upload outcome as given", async () => {
    const requests = server(() => json(snapshot()));
    const store = useOverviewStore();
    await store.retry("caffeine/Example", { acknowledgeUnknown: true });
    await store.retry("caffeine/Example", { acknowledgeUnknown: false });
    expect(requests.filter(({ method }) => method === "POST").map(({ url, body }) => [url, body])).toEqual([
      ["/local/retry", { id: "caffeine/Example", acknowledge_unknown: true }],
      ["/local/retry", { id: "caffeine/Example", acknowledge_unknown: false }],
    ]);
  });

  it("loads the state after an action whose answer is unexpected", async () => {
    const requests = server((method) =>
      method === "POST" ? json({ ok: true }) : json(snapshot({ workspace: "/work/other" })),
    );
    const store = useOverviewStore();
    expect(await rejection(store.selectWorkspace("/work/other"))).toBeInstanceOf(UnexpectedResponse);
    expect(requests.map(({ method, url }) => `${method} ${url}`)).toEqual(["POST /local/workspace", "GET /local/state"]);
    expect(store.snapshot?.workspace).toBe("/work/other");
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
