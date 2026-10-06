import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { VAutocomplete } from "vuetify/components";
import FilterSelect from "../../src/features/search/components/FilterSelect.vue";
import { fields } from "../../src/features/search/fields";

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
beforeEach(() => {
  vi.useFakeTimers();
  setActivePinia(createPinia());
  mocks.get.mockReset().mockResolvedValue({
    data: {
      current_page: 1,
      last_page: 1,
      data: {
        count: 2,
        data: [
          { sid: "PKDB00057", name: "Abernethy1982", pkdb_id: null },
          { sid: "caffeine/Draft", name: "Draft", pkdb_id: null },
        ],
      },
    },
  });
});
afterEach(() => vi.useRealTimers());

it("offers a study format 1 study when its PKDB identifier is typed", async () => {
  const field = fields.find((item) => item.key === "studies__pkdb_id__in");
  if (!field) throw new Error("Missing field");
  const wrapper = mount(FilterSelect, { props: { field, modelValue: [] } });
  wrapper.getComponent(VAutocomplete).vm.$emit("update:search", "PKDB00057");
  await vi.advanceTimersByTimeAsync(300);
  await flushPromises();
  expect(String(mocks.get.mock.calls[0]?.[0])).toContain(
    "search_multi_match=PKDB00057",
  );
  expect(wrapper.getComponent(VAutocomplete).props("items")).toEqual([
    {
      id: "PKDB00057",
      title: "PKDB00057 · Abernethy1982",
      description: "",
    },
  ]);
  wrapper.unmount();
});
