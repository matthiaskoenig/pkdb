import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import DetailPanel from "../../src/features/details/components/DetailPanel.vue";
import RecordFields from "../../src/features/details/components/RecordFields.vue";
import { useSessionStore } from "../../src/stores/session";
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
  setActivePinia(createPinia());
  mocks.get.mockReset();
});
describe("record exploration", () => {
  it("identifies automatically imported studies with their provider and release", async () => {
    mocks.get.mockResolvedValueOnce({ data: { sid: "OSP1", name: "OSP study", provenance: {
      kind: "data_import", source_key: "osp.observed-data", release: "v1.9",
    } } });
    const wrapper = mount(DetailPanel, {
      props: { entity: "studies", identifier: "OSP1" },
      global: { stubs: { StudyContents: true } },
    });
    await flushPromises();
    expect(wrapper.get('[aria-label="Data source"]').text()).toContain("Automatic import · osp.observed-data · v1.9");
    wrapper.unmount();
  });
  it("keeps zero and uncertainty visible and prevents unsafe external links", () => {
    const wrapper = mount(RecordFields, {
      props: {
        data: {
          value: 0,
          mean: null,
          sd: 1e-9,
          annotations: [{ url: "javascript:alert(1)", term: "<b>escaped</b>" }],
        },
      },
    });
    expect(wrapper.text()).toContain("0");
    expect(wrapper.text()).toContain("Not reported");
    expect(wrapper.text()).toContain("1e-9");
    expect(wrapper.find("a").exists()).toBe(false);
    expect(wrapper.find("b").exists()).toBe(false);
    wrapper.unmount();
  });
  it("discards a stale detail response after navigation despite cancellation racing", async () => {
    let finish: ((value: { data: unknown }) => void) | undefined;
    mocks.get
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      )
      .mockResolvedValueOnce({
        data: { pk: 2, name: "Current record", value: 0 },
      });
    const wrapper = mount(DetailPanel, {
      props: { entity: "outputs", identifier: 1 },
    });
    await wrapper.setProps({ identifier: 2 });
    await flushPromises();
    finish?.({ data: { pk: 1, name: "Obsolete private record" } });
    await flushPromises();
    expect(wrapper.text()).toContain("Current record");
    expect(wrapper.text()).not.toContain("Obsolete private record");
    wrapper.unmount();
  });
  it("clears protected details immediately when the session changes", async () => {
    mocks.get
      .mockResolvedValueOnce({ data: { pk: 1, name: "Private subject" } })
      .mockImplementationOnce(() => new Promise(() => {}));
    const wrapper = mount(DetailPanel, {
      props: { entity: "groups", identifier: 1 },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Private subject");
    useSessionStore().invalidate();
    await nextTick();
    expect(wrapper.text()).not.toContain("Private subject");
    wrapper.unmount();
  });
  it("opens a linked scientific record and returns to the original detail", async () => {
    mocks.get
      .mockResolvedValueOnce({
        data: {
          pk: 1,
          name: "Measurement",
          group: { pk: 4, name: "Participants" },
        },
      })
      .mockResolvedValueOnce({
        data: { pk: 4, name: "Participants", count: 0 },
      })
      .mockResolvedValueOnce({ data: { pk: 1, name: "Measurement" } });
    const wrapper = mount(DetailPanel, {
      props: { entity: "outputs", identifier: 1 },
    });
    await flushPromises();
    const related = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Group: Participants"));
    expect(related).toBeDefined();
    await related?.trigger("click");
    await flushPromises();
    expect(mocks.get).toHaveBeenLastCalledWith(
      "/api/v1/groups/4/",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    const back = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Back to previous record"));
    await back?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Measurement");
    wrapper.unmount();
  });
});
