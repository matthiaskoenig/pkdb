import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises, enableAutoUnmount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { useSessionStore } from "../../src/stores/session";
import HomeStatistics from "../../src/features/home/HomeStatistics.vue";
import * as statistics from "../../src/features/home/statistics";
import { decodeLocation } from "../../src/features/search/codec";
import { deferred } from "../unit/account-fixtures";
enableAutoUnmount(afterEach);
let pinia = createPinia();
const data = {
  study_count: 4,
  group_count: 7,
  individual_count: 0,
  intervention_count: 8,
  output_count: 33,
  timecourse_count: 2,
  scatter_count: 1,
};
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  vi.spyOn(statistics, "fetchStatistics").mockResolvedValue(
    statistics.parseStatistics(data),
  );
});
afterEach(() => {
  disposePinia(pinia);
  vi.restoreAllMocks();
});
async function mounted() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { template: "<div />" } }],
  });
  await router.push("/");
  return mount(HomeStatistics, { global: { plugins: [pinia, router] } });
}
describe("permission-scoped home database statistics", () => {
  it("waits for session initialization and links all seven counts to valid whole-study views", async () => {
    const wrapper = await mounted();
    await flushPromises();
    expect(statistics.fetchStatistics).not.toHaveBeenCalled();
    useSessionStore().ready = true;
    await flushPromises();
    const links = wrapper.findAll("a");
    expect(links).toHaveLength(7);
    expect(links.map((link) => link.text())).toContain("0Individuals");
    const tabs = links.map((link) => {
      const href = link.attributes("href");
      if (!href) throw new Error("Missing statistics link");
      const url = new URL(href, "http://localhost");
      const location = decodeLocation(Object.fromEntries(url.searchParams));
      expect(location.criteria.scope).toBe("studies");
      return location.view.tab;
    });
    expect(tabs).toEqual([
      "studies",
      "groups",
      "individuals",
      "interventions",
      "measurements",
      "timecourses",
      "scatters",
    ]);
  });
  it("shows failures and retry instead of manufacturing zero counts", async () => {
    vi.mocked(statistics.fetchStatistics).mockRejectedValueOnce(
      new Error("offline"),
    );
    useSessionStore().ready = true;
    const wrapper = await mounted();
    await flushPromises();
    expect(wrapper.findAll("a")).toHaveLength(0);
    expect(wrapper.text()).toContain("could not be completed");
    await wrapper.get("button").trigger("click");
    await flushPromises();
    expect(wrapper.findAll("a")).toHaveLength(7);
  });
  it("discards counts from a previous identity and cancels on unmount", async () => {
    const old = deferred<statistics.DatabaseStatistic[]>();
    vi.mocked(statistics.fetchStatistics).mockReturnValueOnce(old.promise);
    const session = useSessionStore();
    session.ready = true;
    const wrapper = await mounted();
    session.invalidate();
    await flushPromises();
    old.complete(statistics.parseStatistics({ ...data, study_count: 999 }));
    await flushPromises();
    expect(wrapper.text()).not.toContain("999");
    expect(wrapper.findAll("a")[0]?.text()).toBe("4Studies");
    const signal = vi.mocked(statistics.fetchStatistics).mock.calls.at(-1)?.[0];
    wrapper.unmount();
    expect(signal?.aborted).toBe(true);
  });
  it("rejects absent and malformed counts while accepting real zeroes", () => {
    expect(() =>
      statistics.parseStatistics({ ...data, group_count: -1 }),
    ).toThrow();
    expect(() => statistics.parseStatistics({ study_count: 1 })).toThrow();
    expect(
      statistics.parseStatistics(data).find((row) => row.tab === "individuals")
        ?.count,
    ).toBe(0);
  });
});
