import { describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref, shallowRef } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import {
  AUDIENCE_CAPABILITIES,
  hasSearch,
  listCapabilities,
  pdfjsAssets,
  searchQuery,
  studyListData,
  studyPageData,
  websiteRoutes,
} from "../../src/features/studies/context";
import { studyRows } from "../../src/features/studies/api";
import { SEARCH_QUERY_KEYS } from "../../src/features/search/codec";
import { ALL_ROWS } from "../../src/study-views/data";
import type { StudyDetail } from "../../src/study-views/types";
import rowsCurator from "../fixtures/website-views/study-rows-curator.json";

const mocks = vi.hoisted(() => ({ table: vi.fn(), source: vi.fn() }));
vi.mock("../../src/features/studies/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/features/studies/api")>();
  return { ...actual, studyViewsApi: { ...actual.studyViewsApi, table: mocks.table, source: mocks.source } };
});

const SID = "drug/Format2Fixture";
const SEARCH = "v=1&q={}&scope=all&tab=studies&page=1&pageSize=20";

async function routeAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/studies", name: "Studies", component: { render: () => null } },
      { path: "/data/:substance/:name/:section?", name: "StudyByName", component: { render: () => null } },
    ],
  });
  await router.push(path);
  return router;
}

describe("the capabilities of the website", () => {
  it("follow the audience of the study and, on the list, whether the reader may write any study", () => {
    expect(AUDIENCE_CAPABILITIES.public).toEqual({ edit: false, curation: false, files: false, jobs: false });
    expect(AUDIENCE_CAPABILITIES.curator).toEqual({ edit: false, curation: true, files: true, jobs: false });
    const [row] = studyRows(rowsCurator, "GET rows").rows;
    expect(listCapabilities([row!]).curation).toBe(true);
    expect(listCapabilities([{ ...row!, curator: false }]).curation).toBe(false);
    expect(listCapabilities([])).toEqual(AUDIENCE_CAPABILITIES.public);
  });
});

describe("the routes of the website", () => {
  it("keep the keys of the data search on every study and section link and in a query that a section sets", async () => {
    const router = await routeAt(`/data/${SID}/review?${SEARCH}&item=01J&file=a.tsv`);
    const routes = websiteRoutes(router.currentRoute.value);
    expect(router.resolve(routes.section(SID, "data", { file: "b.tsv" })).fullPath).toBe(
      `/data/${SID}/data?${SEARCH}&file=b.tsv`,
    );
    expect(router.resolve(routes.study(SID)).fullPath).toBe(`/data/${SID}?${SEARCH}`);
    expect(Object.keys(routes.query(router.currentRoute.value.query, { item: "01K" }))).toEqual([
      ...SEARCH_QUERY_KEYS.filter((key) => !["order", "tableSearch"].includes(key)),
      "item",
    ]);
    expect(routes.current(router.currentRoute.value)).toEqual({ id: SID, section: "review" });
    expect(routes.paper(SID, "Format2Fixture.pdf")).toBeNull();
    expect(router.resolve(routes.overview()).fullPath).toBe("/studies");
    expect(hasSearch(router.currentRoute.value.query)).toBe(true);
  });

  it("show no study for another page and keep no other key of it", async () => {
    const router = await routeAt("/studies?search=caf&sort=review");
    const routes = websiteRoutes(router.currentRoute.value);
    expect(routes.current(router.currentRoute.value)).toBeNull();
    expect(router.resolve(routes.study(SID)).fullPath).toBe(`/data/${SID}`);
    expect(searchQuery(router.currentRoute.value.query)).toEqual({});
    expect(hasSearch(router.currentRoute.value.query)).toBe(false);
  });
});

describe("the reads of a study page", () => {
  it("read the tables and sources of the shown study and load PDF.js from the root of the site", async () => {
    const id = ref(SID);
    const data = studyPageData({ id, detail: shallowRef<StudyDetail | null>(null), error: shallowRef(null) });
    mocks.table.mockResolvedValue({ file: "a.tsv", kind: "table", header: [], rows: [] });
    await data.table("a.tsv");
    expect(mocks.table).toHaveBeenCalledWith(SID, "a.tsv", undefined);
    expect(pdfjsAssets()).toBe(`${window.location.origin}/pdfjs/`);
    expect(data.pdfjsAssets()).toBe(pdfjsAssets());
  });

  it("answer every view that names people with one roster", async () => {
    const data = studyPageData({ id: SID, detail: shallowRef<StudyDetail | null>(null), error: shallowRef(null) });
    expect(data.curators()).toBe(data.curators());
    expect(await data.curators()).toEqual([]);
  });

  it("keep the row filters and the open notes of the shown study and forget them for another study", async () => {
    const scope = effectScope();
    const id = ref(SID);
    const data = scope.run(() =>
      studyPageData({ id, detail: shallowRef<StudyDetail | null>(null), error: shallowRef(null) }),
    )!;
    data.setRowFilter("a.tsv", { kind: "none" });
    data.setNotesOpen("outputs", true);
    expect(data.rowFilter("a.tsv")).toEqual({ kind: "none" });
    expect(data.notesOpen.value.has("outputs")).toBe(true);
    id.value = "drug/Other";
    await nextTick();
    expect(data.rowFilter("a.tsv")).toBe(ALL_ROWS);
    expect(data.notesOpen.value.size).toBe(0);
    scope.stop();
  });
});

describe("the reads of the Studies page", () => {
  it("name people by the profiles of the rows answer, one roster per answer", async () => {
    const answer = studyRows(rowsCurator, "GET rows");
    const profiles = shallowRef(answer.profiles);
    const data = studyListData({ rows: shallowRef(answer.rows), profiles });
    expect(data.profiles.value.get("curator")?.username).toBe("curator");
    const first = data.curators();
    expect(data.curators()).toBe(first);
    expect((await first).map((profile) => profile.username)).toEqual(answer.profiles.map((profile) => profile.username));
    profiles.value = [];
    expect(data.curators()).not.toBe(first);
  });
});
