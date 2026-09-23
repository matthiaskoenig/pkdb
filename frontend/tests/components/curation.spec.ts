import { beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import CurationPage from "../../src/features/curation/components/CurationPage.vue";
import VocabularyHighlight from "../../src/features/curation/components/VocabularyHighlight.vue";
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
const envelope = (name: string, count = 1) => ({
  data: {
    data: {
      count,
      data: [
        {
          sid: name.toLowerCase(),
          name,
          label: name,
          description: "Scientific definition",
          ntype: "substance",
          synonyms: ["Alternative"],
        },
      ],
    },
  },
});
beforeEach(() => {
  setActivePinia(createPinia());
  mocks.get.mockReset();
});
it("highlights literal vocabulary terms without interpreting markup or regex", () => {
  const wrapper = mount(VocabularyHighlight, {
    props: { value: "<script>[drug]</script>", query: "[drug]" },
  });
  expect(wrapper.find("mark").text()).toBe("[drug]");
  expect(wrapper.find("script").exists()).toBe(false);
  wrapper.unmount();
});
it("applies vocabulary text only on submit and pages on the server", async () => {
  mocks.get.mockResolvedValue(envelope("Drug", 30));
  const wrapper = mount(CurationPage);
  await flushPromises();
  await wrapper.find("input").setValue("caffeine");
  expect(mocks.get).toHaveBeenCalledTimes(1);
  await wrapper.find("form").trigger("submit");
  await flushPromises();
  expect(mocks.get).toHaveBeenLastCalledWith(
    "/api/v1/info_nodes/",
    expect.objectContaining({
      params: expect.objectContaining({ search: "caffeine", page: 1 }),
    }),
  );
  await wrapper
    .findAll("button")
    .find((button) => button.text() === "Next")
    ?.trigger("click");
  await flushPromises();
  expect(mocks.get).toHaveBeenLastCalledWith(
    "/api/v1/info_nodes/",
    expect.objectContaining({ params: expect.objectContaining({ page: 2 }) }),
  );
  expect(wrapper.text()).toContain("Scientific definition");
  expect(wrapper.text()).toContain("Alternative");
  wrapper.unmount();
});
it("shows an invalid response as failure rather than zero vocabulary terms", async () => {
  mocks.get.mockResolvedValue({ data: {} });
  const wrapper = mount(CurationPage);
  await flushPromises();
  expect(
    wrapper
      .findAll('[role="alert"]')
      .some((alert) => alert.text().includes("invalid")),
  ).toBe(true);
  expect(wrapper.text()).not.toContain("0 vocabulary terms");
  wrapper.unmount();
});
