import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import StudyDetailPage from "../../src/features/details/components/StudyDetailPage.vue";
const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", () => ({
  api: { get: mocks.get },
  apiBase: "",
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
  clearCsrf: vi.fn(),
  cleanLegacyCredentials: vi.fn(),
  onUnauthorized: () => () => {},
}));

const study = {
  pk: "5",
  sid: "caffeine/Harder1988",
  name: "Harder1988",
  pkdb_id: "PKDB00198",
  release_date: "2026-09-28",
  issue: 2158,
  review_status: "approved",
  open_review_items: 0,
};
async function open(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/data/:substance/:name",
        name: "StudyByName",
        props: (route) => ({
          sid: `${String(route.params.substance)}/${String(route.params.name)}`,
        }),
        component: StudyDetailPage,
      },
      {
        path: "/data/:sid",
        name: "DataSingle",
        props: true,
        component: StudyDetailPage,
      },
    ],
  });
  await router.push(path);
  await router.isReady();
  const wrapper = mount(StudyDetailPage, {
    props: {
      sid: String(
        router.currentRoute.value.params.sid ??
          `${String(router.currentRoute.value.params.substance)}/${String(router.currentRoute.value.params.name)}`,
      ),
    },
    global: { plugins: [router], stubs: { StudyContents: true } },
  });
  await flushPromises();
  return { router, wrapper };
}
beforeEach(() => {
  setActivePinia(createPinia());
  mocks.get.mockReset();
});
describe("study page address", () => {
  it("shows a study opened by substance and name without changing the address", async () => {
    mocks.get.mockResolvedValue({ data: study });
    const { router, wrapper } = await open(
      "/data/caffeine/Harder1988?tab=studies",
    );
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get.mock.calls[0]?.[0]).toBe(
      "/api/v1/studies/caffeine/Harder1988/",
    );
    expect(router.currentRoute.value.fullPath).toBe(
      "/data/caffeine/Harder1988?tab=studies",
    );
    expect(wrapper.text()).toContain("Harder1988");
    wrapper.unmount();
  });
  it("replaces the PKDB identifier with the address the API redirected to", async () => {
    // The browser follows the API's 308, so the response is the redirected study.
    mocks.get.mockResolvedValue({ data: study });
    const { router, wrapper } = await open("/data/PKDB00198?tab=studies");
    expect(mocks.get.mock.calls[0]?.[0]).toBe("/api/v1/studies/PKDB00198/");
    expect(router.currentRoute.value.fullPath).toBe(
      "/data/caffeine/Harder1988?tab=studies",
    );
    expect(mocks.get).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
  it("keeps the address of a study format 1 sid", async () => {
    mocks.get.mockResolvedValue({
      data: { pk: "1", sid: "PKDB00057", name: "Old" },
    });
    const { router, wrapper } = await open("/data/PKDB00057");
    expect(router.currentRoute.value.fullPath).toBe("/data/PKDB00057");
    wrapper.unmount();
  });
});
