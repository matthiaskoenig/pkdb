import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import type { Component } from "vue";
import DataSection from "../../src/curation-app/sections/DataSection.vue";
import ReviewSection from "../../src/curation-app/sections/ReviewSection.vue";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { curationStudyViews } from "../../src/curation-app/studyViews";
import type { Section } from "../../src/study-views/study";
import type { SourceView, StudyDetail } from "../../src/study-views/types";
import { reviewItem, snapshot, studyDetail } from "../unit/curation-fixtures";
import { serveApi, setViewport } from "./curation-dom";
import { mountViews, websiteRouter, websiteRoutes } from "./study-views";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
/** The search of the website, which the study page keeps in its address for Back to the search. */
const SEARCH = { v: "1", q: '{"filters":[]}', tab: "studies", page: "2" };

function view(source: string): SourceView {
  return {
    source,
    image: null,
    image_url: null,
    image_size: null,
    raw_grid: null,
    digitization: null,
    mapped: [],
    overlay: [],
    unmatched: [],
    layout: "side_by_side",
    points: [],
    series: [],
    log_x: false,
    log_y: false,
  };
}

let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  setViewport(1440);
});
afterEach(() => disposePinia(pinia));

/** `section` of the study `caffeine/Example` as a page of the website shows it, with the search in its query. */
async function mountSection(component: Component, section: Section, detail: StudyDetail, query: Record<string, string> = {}) {
  serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: detail,
    "GET /local/curators": { curators: [] },
    [`GET ${EXAMPLE}/tables/subjects.tsv`]: {
      file: "subjects.tsv",
      kind: "table",
      header: ["study", "name", "source"],
      rows: [{ line: 1, cells: ["Example", "all", "Tab2"] }],
    },
    [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: {
      file: "outputs_Tab2.tsv",
      kind: "table",
      header: ["study", "source", "label"],
      rows: [{ line: 1, cells: ["Example", "Tab2", "caf_cl"] }],
    },
    [`GET ${EXAMPLE}/sources/Tab2`]: view("Tab2"),
    [`GET ${EXAMPLE}/sources/Fig1`]: view("Fig1"),
  });
  await useOverviewStore().refresh();
  await useStudyStore().open("caffeine", "Example");
  const router = websiteRouter();
  await router.push({ name: "WebStudy", params: { substance: "caffeine", name: "Example", section }, query: { ...SEARCH, ...query } });
  const wrapper = mountViews(component, {
    context: { ...curationStudyViews(), routes: websiteRoutes() },
    plugins: [pinia, router],
    stubs: { SourceOverlay: true, PaperViewer: true },
    attachTo: document.body,
  });
  await flushPromises();
  return { wrapper, router };
}

// The router changes the address after the section asked for it, as in the curation specs of the
// sections: each test waits for the address that it expects.
describe("the address of a study page of the website", () => {
  it("keeps the search when the Data section puts its default selection into it and when a table is chosen", async () => {
    const { wrapper, router } = await mountSection(DataSection, "data", studyDetail());
    await vi.waitFor(() => expect(router.currentRoute.value.query).toMatchObject({ ...SEARCH, file: "subjects.tsv" }));
    const outputs = wrapper.findAll("button.nav-file").find((button) => button.text().includes("outputs_Tab2"));
    await outputs!.trigger("click");
    await flushPromises();
    await vi.waitFor(() =>
      expect(router.currentRoute.value.query).toEqual({ ...SEARCH, source: "Tab2", file: "outputs_Tab2.tsv" }),
    );
  });

  it("keeps the search when the Data section takes the notes of a link out of it", async () => {
    const { router } = await mountSection(DataSection, "data", studyDetail(), { file: "subjects.tsv", notes: "subjects" });
    await vi.waitFor(() => {
      expect(router.currentRoute.value.query.notes).toBeUndefined();
      expect(router.currentRoute.value.query).toMatchObject({ ...SEARCH, file: "subjects.tsv" });
    });
  });

  it("keeps the search when the Review section selects an item", async () => {
    const items = [reviewItem({ id: "01A", text: "First" }), reviewItem({ id: "01B", text: "Second" })];
    const detail = studyDetail({
      review: { revision: "review-1", value: { status: "in_review", reviewers: [], items }, issues: [] },
    });
    const { wrapper, router } = await mountSection(ReviewSection, "review", detail);
    await wrapper.findAll("button.review-card")[1]!.trigger("click");
    await flushPromises();
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ ...SEARCH, item: "01B" }));
  });
});
