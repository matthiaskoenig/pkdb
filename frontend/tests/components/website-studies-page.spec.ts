import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h } from "vue";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import { routes } from "../../src/router";
import { useSessionStore } from "../../src/stores/session";
import { useStudyListStore } from "../../src/stores/studyList";
import StudyFilters from "../../src/study-views/components/StudyFilters.vue";
import rowsCurator from "../fixtures/website-views/study-rows-curator.json";
import rowsPublic from "../fixtures/website-views/study-rows-public.json";
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

const ROWS = "/api/v2/study-rows";
const PUBLIC_COLUMNS = ["Study", "Release", "Curators"];
const CURATOR_COLUMNS = ["Study", "Release", "Issue", "Curators", "Review", "Open items", "Problems"];

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
    global: { plugins: [router, pinia] },
    attachTo: document.body,
  });
  await flushPromises();
  await navigated();
  return { router, wrapper };
}

const headers = (wrapper: Awaited<ReturnType<typeof open>>["wrapper"]) =>
  wrapper.findAll("table thead th").map((cell) => cell.text());

describe("the Studies page", () => {
  it("lists the public rows with Study, Release and Curators and no status chips", async () => {
    serve({ [ROWS]: rowsPublic });
    const { wrapper } = await open("/studies");
    expect(wrapper.get("h1").text()).toBe("Studies");
    expect(headers(wrapper)).toEqual(PUBLIC_COLUMNS);
    expect(wrapper.find(".overview-chips").exists()).toBe(false);
    expect(wrapper.get("a.study-identity").attributes("href")).toBe("/data/drug/Format2Fixture");
  });

  it("shows the curation columns and the status chips to a reader who may write a listed study", async () => {
    serve({ [ROWS]: rowsCurator });
    const { wrapper } = await open("/studies");
    expect(headers(wrapper)).toEqual(CURATOR_COLUMNS);
    expect(wrapper.find(".overview-chips").exists()).toBe(true);
  });

  it("fills the curation only for the rows that the reader may write and counts the chips by them", async () => {
    const [own] = rowsCurator.rows;
    const [other] = rowsPublic.rows;
    serve({ [ROWS]: { rows: [own, { ...other, id: "drug/Other", name: "Other" }], profiles: rowsCurator.profiles } });
    const { wrapper } = await open("/studies");
    const row = wrapper.get('tr[data-study="drug/Other"]');
    for (const cell of [".cell-issue", ".cell-review", ".cell-open", ".cell-problems"]) expect(row.get(cell).text()).toBe("-");
    expect(wrapper.get('tr[data-study="drug/Format2Fixture"] .cell-review').text()).toContain("In review");
    const filters = wrapper.findComponent(StudyFilters);
    expect(filters.props("counts")).toMatchObject({ all: 2, in_review: 1 });
  });

  it("replaces an address that sorts or filters by what the reader does not see, once the rows are there", async () => {
    serve({ [ROWS]: rowsPublic });
    const visitor = await open("/studies?sort=review&order=desc&status=attention&substance=drug");
    expect(visitor.router.currentRoute.value.fullPath).toBe("/studies?substance=drug");
    serve({ [ROWS]: rowsCurator });
    const curator = await open("/studies?sort=review&order=desc&status=attention");
    expect(curator.router.currentRoute.value.query).toEqual({ sort: "review", order: "desc", status: "attention" });
  });

  it("writes a sort change of the table into the address, and a descending sort into no study link", async () => {
    serve({ [ROWS]: rowsCurator });
    const { router, wrapper } = await open("/studies");
    const sortReview = () => wrapper.get("table thead").findAll("button").find((button) => button.text() === "Review")!.trigger("click");
    await sortReview();
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ sort: "review" }));
    await sortReview();
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ sort: "review", order: "desc" }));
    await navigated();
    expect(wrapper.get("a.study-identity").attributes("href")).toBe("/data/drug/Format2Fixture");
  });

  it("links the rows without the order of a descending sort", async () => {
    serve({ [ROWS]: rowsCurator });
    const { wrapper } = await open("/studies?sort=review&order=desc");
    expect(wrapper.get("a.study-identity").attributes("href")).toBe("/data/drug/Format2Fixture");
  });

  it("writes a filter into the address and remembers it for the study pages", async () => {
    serve({ [ROWS]: rowsCurator });
    const { router, wrapper } = await open("/studies");
    wrapper.findComponent(StudyFilters).vm.$emit("update:substance", "drug");
    // The replace of the address can take more than one task on a busy runner.
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ substance: "drug" }));
    expect(useStudyListStore().query).toEqual({ substance: "drug" });
  });

  it("leaves the address of the next page and the remembered one alone when the reader leaves", async () => {
    serve({ [ROWS]: rowsCurator });
    const { router } = await open("/studies?substance=drug");
    await router.push("/elsewhere?v=1");
    await navigated();
    expect(router.currentRoute.value.fullPath).toBe("/elsewhere?v=1");
    expect(useStudyListStore().query).toEqual({ substance: "drug" });
  });

  it("says that no study is listed yet and points to the data search", async () => {
    serve({ [ROWS]: { rows: [], profiles: {} } });
    const { wrapper } = await open("/studies");
    expect(wrapper.get(".studies-none").text()).toContain("No studies are listed yet.");
    expect(wrapper.get(".studies-none a").attributes("href")).toBe("/data");
  });

  it("says why the studies could not be loaded and loads them again on Retry", async () => {
    const answers: Record<string, unknown> = { [ROWS]: httpError(500, { detail: "Database unavailable" }) };
    serve(answers);
    const { wrapper } = await open("/studies");
    expect(wrapper.get(".action-failure").text()).toContain("The studies could not be loaded.");
    answers[ROWS] = rowsPublic;
    await wrapper.get(".action-failure button.v-btn").trigger("click");
    await flushPromises();
    expect(headers(wrapper)).toEqual(PUBLIC_COLUMNS);
  });

  it("shows no row of the earlier session when the read after a session change fails", async () => {
    const answers: Record<string, unknown> = { [ROWS]: rowsCurator };
    serve(answers);
    const { wrapper } = await open("/studies");
    answers[ROWS] = httpError(500, { detail: "Database unavailable" });
    useSessionStore().epoch += 1;
    await flushPromises();
    expect(wrapper.get(".action-failure").text()).toContain("The studies could not be loaded.");
    expect(wrapper.find("table").exists()).toBe(false);
    expect(wrapper.find(".studies-none").exists()).toBe(false);
  });

  it("shows the columns of the new session after a sign-in", async () => {
    const answers: Record<string, unknown> = { [ROWS]: rowsPublic };
    serve(answers);
    const { wrapper } = await open("/studies");
    expect(headers(wrapper)).toEqual(PUBLIC_COLUMNS);
    answers[ROWS] = rowsCurator;
    useSessionStore().epoch += 1;
    await flushPromises();
    expect(headers(wrapper)).toEqual(CURATOR_COLUMNS);
  });
});
