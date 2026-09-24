import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import CurationPage from "../../src/features/curation/components/CurationPage.vue";
import VocabularyMetadata from "../../src/features/curation/components/VocabularyMetadata.vue";
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
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
it("debounces typed vocabulary search and pages on the server", async () => {
  vi.useFakeTimers();
  mocks.get.mockResolvedValue(envelope("Drug", 30));
  const wrapper = mount(CurationPage);
  await flushPromises();
  await wrapper.find("input").setValue("caffeine");
  expect(mocks.get).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(250);
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

it("copies exact names and renders safe annotation links", async () => {
  const response = envelope("inr change");
  Object.assign(response.data.data.data[0]!, {
    label: "INR change",
    annotations: [{ term: "CMO:123", label: "Change in INR", relation: "BQB_IS", url: "https://example.org/term" }],
    xrefs: [{ name: "External reference", accession: "123", url: "javascript:alert(1)" }],
  });
  mocks.get.mockResolvedValue(response);
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  const wrapper = mount(CurationPage);
  await flushPromises();
  await wrapper.get('button[aria-label="Copy name inr change"]').trigger("click");
  await flushPromises();
  expect(writeText).toHaveBeenCalledWith("inr change");
  expect(wrapper.text()).toContain("Copied inr change");
  expect(wrapper.text()).toContain("INR change");
  expect(wrapper.get('a[href="https://example.org/term"]').text()).toContain("CMO:123");
  expect(wrapper.text()).toContain("BQB_IS");
  expect(wrapper.find('a[href^="javascript:"]').exists()).toBe(false);
  writeText.mockRejectedValue(new Error("Denied"));
  await wrapper.get('button[aria-label="Copy name inr change"]').trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("Select and copy the name manually: inr change");
  wrapper.unmount();
});
it("cancels pending search on unmount", async () => {
  vi.useFakeTimers();
  mocks.get.mockResolvedValue(envelope("Drug"));
  const wrapper = mount(CurationPage);
  await flushPromises();
  await wrapper.find("input").setValue("caffeine");
  wrapper.unmount();
  await vi.advanceTimersByTimeAsync(300);
  expect(mocks.get).toHaveBeenCalledTimes(1);
});
it("ignores a stale response when the next typed search is pending", async () => {
  vi.useFakeTimers();
  let resolveOld!: (value: ReturnType<typeof envelope>) => void;
  mocks.get.mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }));
  mocks.get.mockResolvedValue(envelope("Caffeine"));
  const wrapper = mount(CurationPage);
  await wrapper.find("input").setValue("caff");
  resolveOld(envelope("Obsolete result"));
  await flushPromises();
  expect(wrapper.text()).not.toContain("Obsolete result");
  await wrapper.find("input").setValue("caffeine");
  await vi.advanceTimersByTimeAsync(250);
  await flushPromises();
  expect(mocks.get).toHaveBeenCalledTimes(2);
  expect(wrapper.text()).toContain("Caffeine");
  wrapper.unmount();
});

it("resolves legacy annotation templates without duplicating ontology prefixes", () => {
  const wrapper = mount(VocabularyMetadata, { props: { row: {
    annotations: [
      { collection: "chebi", term: "CHEBI:691622", url: "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:{$id}" },
      { collection: "pubchem.compound", term: "79437", url: "https://pubchem.ncbi.nlm.nih.gov/compound/%7B$id%7D" },
      { collection: "test", term: "a&b#c", url: "https://example.org/?id={$id}" },
      { collection: "missing", url: "https://example.org/{$id}" },
      { term: "unsafe", url: "javascript:alert('{$id}')" },
    ],
    xrefs: [{ name: "EFO", accession: "0004503", url: "http://www.ebi.ac.uk/efo/EFO_0004503" }],
  } } });
  const links = wrapper.findAll("a");
  expect(links.map(link => link.attributes("href"))).toEqual([
    "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:691622",
    "https://pubchem.ncbi.nlm.nih.gov/compound/79437",
    "https://example.org/?id=a%26b%23c",
    "http://www.ebi.ac.uk/efo/EFO_0004503",
  ]);
  expect(links[1]!.text()).toContain("pubchem.compound: 79437");
  expect(links[3]!.text()).toContain("EFO: 0004503");
  for (const link of links) {
    expect(link.attributes("target")).toBe("_blank");
    expect(link.attributes("rel")).toBe("noopener noreferrer");
  }
  wrapper.unmount();
});
