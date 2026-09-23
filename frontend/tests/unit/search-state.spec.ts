import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { defineComponent, h } from "vue";
import { mount, flushPromises, enableAutoUnmount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { AxiosError, AxiosHeaders } from "axios";
import * as searchApi from "../../src/api/search";
import * as resultsApi from "../../src/api/results";
import type { ResultPage } from "../../src/api/contracts";
import type { SearchLocation } from "../../src/features/search/model";
import {
  defaultCriteria,
  defaultView,
} from "../../src/features/search/defaults";
import { encodeLocation } from "../../src/features/search/codec";
import { useSearchStore } from "../../src/stores/search";
import { useSessionStore } from "../../src/stores/session";
import { useSearchController } from "../../src/features/search/useSearchController";
import { deferred } from "./account-fixtures";
enableAutoUnmount(afterEach);
let pinia = createPinia();
const selection = (uuid = "selected"): searchApi.Selection => ({
  uuid,
  counts: {
    studies: 1,
    groups: 1,
    individuals: 0,
    interventions: 1,
    measurements: 1,
    timecourses: 0,
    scatters: 0,
  },
});
const page = (sid = "CURRENT", number = 1): ResultPage => ({
  items: [{ sid }],
  count: 1,
  page: number,
  lastPage: number,
});
const location = (): SearchLocation => ({
  criteria: defaultCriteria(),
  view: defaultView(),
});
function apiError(status: number, detail: string) {
  return new AxiosError(detail, "ERR_BAD_RESPONSE", undefined, undefined, {
    status,
    statusText: "error",
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() },
    data: { detail },
  });
}
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  vi.spyOn(searchApi, "createSelection").mockResolvedValue(selection());
  vi.spyOn(resultsApi, "fetchRows").mockResolvedValue(page());
});
afterEach(() => {
  disposePinia(pinia);
  vi.restoreAllMocks();
});
describe("search request ownership", () => {
  it("deduplicates the same in-flight submission and rejects superseded counts", async () => {
    const old = deferred<searchApi.Selection>();
    vi.mocked(searchApi.createSelection)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(selection("new"));
    const store = useSearchStore(),
      first = store.load(location(), 1);
    await store.load(location(), 1);
    expect(searchApi.createSelection).toHaveBeenCalledTimes(1);
    const next = location();
    next.criteria.scope = "studies";
    await store.load(next, 1);
    old.complete(selection("obsolete"));
    await first;
    expect(store.selection).toEqual({
      status: "ready",
      data: selection("new"),
    });
    expect(resultsApi.fetchRows).toHaveBeenCalledTimes(1);
    expect(store.applied.scope).toBe("studies");
  });
  it("does not install obsolete rows or an obsolete failure", async () => {
    const old = deferred<ResultPage>();
    vi.mocked(resultsApi.fetchRows)
      .mockReturnValueOnce(old.promise)
      .mockResolvedValueOnce(page("NEW"));
    const store = useSearchStore(),
      first = store.load(location(), 1);
    await flushPromises();
    await store.load({ ...location(), view: { ...defaultView(), page: 2 } }, 1);
    old.fail(apiError(503, "obsolete failure"));
    await first;
    expect(store.rows).toEqual({ status: "ready", data: page("NEW") });
  });
  it("keeps count errors distinct from genuine zero results", async () => {
    vi.mocked(searchApi.createSelection).mockRejectedValueOnce(
      apiError(503, "Try again"),
    );
    const store = useSearchStore();
    await store.load(location(), 1);
    expect(store.selection.status).toBe("error");
    expect(store.rows.status).toBe("error");
    expect(resultsApi.fetchRows).not.toHaveBeenCalled();
  });
  it("reuses the applied selection for view changes without replacing an edited draft", async () => {
    const store = useSearchStore();
    await store.load(location(), 1);
    store.draft.licences.open = false;
    await store.load(
      { ...location(), view: { ...defaultView(), page: 2 } },
      1,
      false,
      true,
    );
    expect(store.dirty).toBe(true);
    expect(store.draft.licences.open).toBe(false);
    expect(store.applied.licences.open).toBe(true);
    expect(searchApi.createSelection).toHaveBeenCalledTimes(1);
    await store.load(location(), 1);
    expect(store.dirty).toBe(false);
  });
  it("reconstructs one expired selection and bounds a repeated expiry", async () => {
    vi.mocked(resultsApi.fetchRows).mockRejectedValue(
      apiError(404, "Saved filter unavailable"),
    );
    const store = useSearchStore();
    await store.load(location(), 1);
    expect(searchApi.createSelection).toHaveBeenCalledTimes(2);
    expect(resultsApi.fetchRows).toHaveBeenCalledTimes(2);
    expect(store.rows.status).toBe("error");
    expect(store.selection.status).toBe("error");
  });
  it("hides unresolved expired counts and can recover an invalid page after recreation", async () => {
    const recreated = deferred<searchApi.Selection>();
    vi.mocked(searchApi.createSelection)
      .mockResolvedValueOnce(selection())
      .mockReturnValueOnce(recreated.promise);
    vi.mocked(resultsApi.fetchRows)
      .mockRejectedValueOnce(apiError(404, "Saved filter unavailable"))
      .mockRejectedValueOnce(apiError(404, "Invalid page"));
    const store = useSearchStore();
    const result = store.load(
      { ...location(), view: { ...defaultView(), page: 4 } },
      1,
    );
    await flushPromises();
    expect(store.selection.status).toBe("loading");
    recreated.complete(selection("fresh"));
    expect(await result).toBe(1);
    expect(store.notice).toContain("Returned to page 1");
  });
  it("does not reinterpret missing resources or denied selections as expired filters", async () => {
    vi.mocked(resultsApi.fetchRows).mockRejectedValueOnce(
      apiError(404, "Study not found"),
    );
    const store = useSearchStore();
    expect(
      await store.load(
        { ...location(), view: { ...defaultView(), page: 2 } },
        1,
      ),
    ).toBeUndefined();
    expect(searchApi.createSelection).toHaveBeenCalledTimes(1);
    vi.mocked(resultsApi.fetchRows).mockRejectedValueOnce(
      apiError(403, "Forbidden"),
    );
    await store.load(location(), 1);
    expect(store.selection.status).toBe("error");
    expect(store.rows.status).toBe("error");
    expect(searchApi.createSelection).toHaveBeenCalledTimes(1);
  });
  it("invalidates private state and ignores success completed in an old identity epoch", async () => {
    const pending = deferred<ResultPage>();
    vi.mocked(resultsApi.fetchRows).mockReturnValueOnce(pending.promise);
    const store = useSearchStore();
    const old = store.load(location(), 1);
    await flushPromises();
    store.invalidate();
    expect(store.selection.status).toBe("idle");
    expect(store.rows.status).toBe("idle");
    await store.load(location(), 2);
    pending.complete(page("PRIVATE"));
    await old;
    expect(store.rows).toEqual({ status: "ready", data: page() });
    expect(searchApi.createSelection).toHaveBeenCalledTimes(2);
  });
});
const Harness = defineComponent({
  setup() {
    const { search, changeView, retry } = useSearchController();
    return () =>
      h("div", [
        h(
          "button",
          {
            onClick: () => {
              search.draft.licences.open = false;
            },
          },
          "Edit draft",
        ),
        h("button", { onClick: () => changeView({ page: 2 }) }, "Next page"),
        h("button", { onClick: retry }, "Retry"),
        h(
          "output",
          `${search.draft.licences.open}:${search.view.page}:${search.notice}`,
        ),
      ]);
  },
});
async function controllerHarness() {
  const session = useSessionStore();
  session.ready = true;
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/data", component: Harness }],
  });
  await router.push({ path: "/data", query: encodeLocation(location()) });
  await router.isReady();
  const wrapper = mount(Harness, { global: { plugins: [pinia, router] } });
  await flushPromises();
  return { router, wrapper, store: useSearchStore(), session };
}
describe("search controller navigation", () => {
  it("preserves draft changes during explicit pagination and retry, but restores them on Back/Forward", async () => {
    const { router, wrapper, store } = await controllerHarness();
    await wrapper.findAll("button")[0]?.trigger("click");
    await wrapper.findAll("button")[1]?.trigger("click");
    await flushPromises();
    expect(store.view.page).toBe(2);
    expect(store.draft.licences.open).toBe(false);
    expect(store.dirty).toBe(true);
    await wrapper.findAll("button")[2]?.trigger("click");
    await flushPromises();
    expect(store.draft.licences.open).toBe(false);
    router.back();
    await vi.waitFor(() => expect(store.view.page).toBe(1));
    expect(store.draft.licences.open).toBe(true);
    store.draft.licences.open = false;
    router.forward();
    await vi.waitFor(() => expect(store.view.page).toBe(2));
    expect(store.draft.licences.open).toBe(true);
  });
  it("restores page one in the URL without losing a view-navigation draft", async () => {
    const { router, wrapper, store } = await controllerHarness();
    vi.mocked(resultsApi.fetchRows)
      .mockRejectedValueOnce(apiError(404, "Invalid page"))
      .mockResolvedValueOnce(page());
    await wrapper.findAll("button")[0]?.trigger("click");
    await wrapper.findAll("button")[1]?.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.page).toBe("1");
    expect(store.rows.status).toBe("ready");
    expect(store.draft.licences.open).toBe(false);
    expect(store.notice).toContain("Returned to page 1");
  });
  it("clears completed protected rows synchronously on an epoch change", async () => {
    const { session, store } = await controllerHarness();
    expect(store.rows.status).toBe("ready");
    vi.mocked(searchApi.createSelection).mockReturnValueOnce(
      new Promise(() => {}),
    );
    session.invalidate();
    expect(store.rows.status).not.toBe("ready");
    expect(store.selection.status).not.toBe("ready");
  });
});

it("keeps invalid unfinished draft controls renderable until submission", () => {
  const search = useSearchStore();
  search.draft.filters["studies__creator__in"] = ["name__ambiguous"];
  expect(() => search.dirty).not.toThrow();
  expect(search.dirty).toBe(true);
  search.resetDraft();
  expect(search.dirty).toBe(false);
});
