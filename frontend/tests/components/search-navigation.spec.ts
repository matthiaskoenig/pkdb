import { beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import SearchPage from "../../src/features/search/components/SearchPage.vue";
import { useSearchStore } from "../../src/stores/search";
const handlers = vi.hoisted(() => ({
  submit: vi.fn(),
  changeView: vi.fn(),
  retry: vi.fn(),
}));
vi.mock("../../src/features/search/useSearchController", async () => {
  const { useSearchStore } = await import("../../src/stores/search");
  return {
    useSearchController: () => {
      const search = useSearchStore();
      return {
        search,
        submit: handlers.submit,
        retry: handlers.retry,
        changeView: async (patch: Partial<typeof search.view>) => {
          Object.assign(search.view, patch);
          handlers.changeView(patch);
        },
      };
    },
  };
});
beforeEach(() => {
  setActivePinia(createPinia());
  handlers.submit.mockReset();
  handlers.changeView.mockReset();
  handlers.retry.mockReset();
});
async function page() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/data", component: SearchPage }],
  });
  await router.push("/data");
  await router.isReady();
  return mount(SearchPage, {
    attachTo: document.body,
    global: {
      plugins: [router],
      stubs: {
        SearchPanel: true,
        QuerySummary: true,
        ResultsTable: true,
        DetailPanel: true,
      },
    },
  });
}
it("uses one roving tab stop and supports arrows, Home, End and wrapping", async () => {
  const wrapper = await page();
  expect(wrapper.findAll('[role="tab"][tabindex="0"]')).toHaveLength(1);
  const first = wrapper.get("#tab-studies");
  (first.element as HTMLElement).focus();
  await first.trigger("keydown", { key: "ArrowRight" });
  await flushPromises();
  expect(handlers.changeView).toHaveBeenLastCalledWith({ tab: "groups" });
  expect(document.activeElement?.id).toBe("tab-groups");
  expect(wrapper.get("#tab-groups").attributes("tabindex")).toBe("0");
  await wrapper.get("#tab-groups").trigger("keydown", { key: "End" });
  await flushPromises();
  expect(document.activeElement?.id).toBe("tab-scatters");
  await wrapper.get("#tab-scatters").trigger("keydown", { key: "ArrowRight" });
  await flushPromises();
  expect(document.activeElement?.id).toBe("tab-studies");
  await wrapper.get("#tab-studies").trigger("keydown", { key: "ArrowLeft" });
  await flushPromises();
  expect(document.activeElement?.id).toBe("tab-scatters");
  await wrapper.get("#tab-scatters").trigger("keydown", { key: "Home" });
  await flushPromises();
  expect(document.activeElement?.id).toBe("tab-studies");
  wrapper.unmount();
});
it("loads an example into draft without touching the applied query or submitting", async () => {
  const wrapper = await page();
  const search = useSearchStore();
  search.applied.filters = { studies__sid__in: ["CURRENT"] };
  const choose = wrapper
    .findAll("button")
    .find(
      (button) => button.text() === "Midazolam half-life in human subjects",
    );
  await choose?.trigger("click");
  await flushPromises();
  expect(search.draft.filters.interventions__substance_sid__in).toEqual([
    "midazolam",
  ]);
  expect(search.applied.filters.studies__sid__in).toEqual(["CURRENT"]);
  expect(handlers.submit).not.toHaveBeenCalled();
  expect(wrapper.text()).toContain("Example loaded into the draft");
  wrapper.unmount();
});
