import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, nextTick } from "vue";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import { routes } from "../../src/router";
import { useSessionStore } from "../../src/stores/session";
import { useStudyListStore } from "../../src/stores/studyList";
import studyCurator from "../fixtures/website-views/study-curator.json";
import studyPublic from "../fixtures/website-views/study-public.json";
import { setViewport } from "./curation-dom";
import { httpError, navigated, serve as serveWith } from "./website-api";

const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", () => ({
  api: { get: mocks.get },
  apiBase: "",
  errorMessage: (error: unknown) => (error instanceof Error ? error.message : "Request failed"),
  clearCsrf: vi.fn(),
  cleanLegacyCredentials: vi.fn(),
  onUnauthorized: () => () => {},
}));

const SID = "drug/Format2Fixture";
const VIEW = `/api/v2/studies/${SID}/view`;
/** The keys of a data search, as the router writes them. */
const SEARCH = "v=1&q={}&scope=all&tab=studies&page=1&pageSize=20";
const STUBS = {
  StudyDetailPage: true,
  MetadataView: true,
  DataSection: true,
  ProblemsSection: true,
  ReviewSection: true,
  SearchPage: true,
  StudiesPage: true,
};

const serve = (answers: Record<string, unknown>) => serveWith(mocks.get, answers);

enableAutoUnmount(afterEach);
let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  mocks.get.mockReset();
  setViewport(1280);
});

async function open(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes });
  await router.push(path);
  await router.isReady();
  const wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    global: { plugins: [router, pinia], stubs: STUBS },
    attachTo: document.body,
  });
  await flushPromises();
  await navigated();
  return { router, wrapper };
}

const tabs = (wrapper: Awaited<ReturnType<typeof open>>["wrapper"]) =>
  wrapper.findAll(".section-tab .section-tab-label").map((label) => label.attributes("data-label"));

describe("the study page of the website", () => {
  it("shows a study that the reader may write with Metadata, Data, Problems and Review, on its open item", async () => {
    serve({ [VIEW]: studyCurator });
    const { router, wrapper } = await open(`/data/${SID}`);
    expect(router.currentRoute.value.fullPath).toBe(`/data/${SID}/review`);
    expect(tabs(wrapper)).toEqual(["Metadata", "Data", "Problems", "Review"]);
    expect(wrapper.get(".issue-chip").text()).toContain("#2158");
    expect(wrapper.get(".fact-review").text()).toBe("In review");
    expect(wrapper.findComponent({ name: "ReviewSection" }).exists()).toBe(true);
    expect(document.activeElement?.classList.contains("study-identity")).toBe(true);
    expect(wrapper.find("[data-study-section-heading]").text()).toBe("Review");
  });

  it("shows the public view with Metadata and Data, and opens a section that the reader does not see on Metadata", async () => {
    serve({ [VIEW]: studyPublic });
    const { router, wrapper } = await open(`/data/${SID}/review`);
    expect(router.currentRoute.value.fullPath).toBe(`/data/${SID}/metadata`);
    expect(tabs(wrapper)).toEqual(["Metadata", "Data"]);
    expect(wrapper.find(".issue-chip").exists()).toBe(false);
    expect(wrapper.findComponent({ name: "MetadataView" }).exists()).toBe(true);
  });

  it("shows a study without a view on its record page", async () => {
    serve({});
    const { wrapper } = await open("/data/drug/Format2Legacy");
    const record = wrapper.findComponent({ name: "StudyDetailPage" });
    expect(record.exists()).toBe(true);
    expect(record.props("sid")).toBe("drug/Format2Legacy");
    expect(wrapper.find('nav[aria-label="Study sections"]').exists()).toBe(false);
  });

  it("says why the study could not be loaded, never with the record page, and loads it again on Retry", async () => {
    const answers: Record<string, unknown> = { [VIEW]: httpError(500, { detail: "Database unavailable" }) };
    serve(answers);
    const { wrapper } = await open(`/data/${SID}`);
    expect(wrapper.get(".action-failure").text()).toContain("The study could not be loaded.");
    expect(wrapper.findComponent({ name: "StudyDetailPage" }).exists()).toBe(false);
    answers[VIEW] = studyCurator;
    await wrapper.get(".action-failure button.v-btn").trigger("click");
    await flushPromises();
    await navigated();
    expect(tabs(wrapper)).toEqual(["Metadata", "Data", "Problems", "Review"]);
  });

  it("shows the view of the new session: a reader who can no longer write the study leaves Review for Metadata", async () => {
    const answers: Record<string, unknown> = { [VIEW]: studyCurator };
    serve(answers);
    const { router, wrapper } = await open(`/data/${SID}/review`);
    answers[VIEW] = studyPublic;
    useSessionStore().epoch += 1;
    await flushPromises();
    await navigated();
    expect(router.currentRoute.value.fullPath).toBe(`/data/${SID}/metadata`);
    expect(tabs(wrapper)).toEqual(["Metadata", "Data"]);
  });

  it("keeps the record page of a study without a view while it reads again for a new session", async () => {
    serve({});
    const { wrapper } = await open("/data/drug/Format2Legacy");
    useSessionStore().epoch += 1;
    await nextTick();
    expect(wrapper.findComponent({ name: "StudyDetailPage" }).exists()).toBe(true);
    await flushPromises();
    expect(wrapper.findComponent({ name: "StudyDetailPage" }).exists()).toBe(true);
    expect(mocks.get).toHaveBeenCalledTimes(2);
  });

  it("keeps the data search on its tabs and goes back to the search with only its keys", async () => {
    serve({ [VIEW]: studyCurator });
    const { router, wrapper } = await open(`/data/${SID}/review?${SEARCH}&item=01J`);
    const data = wrapper.findAll("a.section-tab").find((tab) => tab.text().startsWith("Data"))!;
    expect(data.attributes("href")).toBe(`/data/${SID}/data?${SEARCH}`);
    const back = wrapper.findAll("button.v-btn").find((button) => button.text() === "Back to the search")!;
    // The search page loads with the navigation, which takes longer than a timer.
    const left = new Promise<void>((resolve) => {
      const stop = router.afterEach(() => {
        stop();
        resolve();
      });
    });
    await back.trigger("click");
    await left;
    expect(router.currentRoute.value.fullPath).toBe(`/data?${SEARCH}`);
  });

  it("offers the Studies page, as the reader left it, without a search", async () => {
    serve({ [VIEW]: studyPublic });
    useStudyListStore().query = { substance: "drug" };
    const { wrapper } = await open(`/data/${SID}/metadata`);
    const link = wrapper.findAll("a.v-btn").find((button) => button.text() === "All studies")!;
    expect(link.attributes("href")).toBe("/studies?substance=drug");
  });
});
