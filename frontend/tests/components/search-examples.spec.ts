import { expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import SearchExamples from "../../src/features/search/components/SearchExamples.vue";
import { searchExamples } from "../../src/features/search/examples";
import { canonicalCriteria } from "../../src/features/search/codec";
import { serializeCriteria } from "../../src/features/search/serialize";
it("offers examples as draft criteria without submitting a search", async () => {
  const wrapper = mount(SearchExamples);
  await wrapper.findAll("button")[1]?.trigger("click");
  expect(wrapper.emitted("choose")?.[0]?.[0]).toEqual(
    expect.objectContaining({
      scope: "matching",
      filters: expect.objectContaining({
        subjects__choice_sid__in: ["homo-sapiens"],
      }),
    }),
  );
  expect(wrapper.emitted("search")).toBeUndefined();
  expect(wrapper.text()).toContain("only after you select Search");
  expect(wrapper.text()).toContain("OR, not AND");
  wrapper.unmount();
});
it("produces fresh defaults on every example selection", () => {
  const example = searchExamples[1];
  expect(example).toBeDefined();
  const first = example?.criteria();
  if (first) {
    first.subjects.groups = false;
    first.filters.subjects__choice_sid__in?.push("healthy-yes");
  }
  expect(example?.criteria().subjects.groups).toBe(true);
  expect(example?.criteria().filters.subjects__choice_sid__in).toEqual([
    "homo-sapiens",
  ]);
});
it("selects the single-study example by PKDB identifier, which the filter supports", () => {
  const example = searchExamples.find((item) => item.id === "single-study");
  const criteria = example?.criteria();
  expect(criteria?.filters).toEqual({ studies__pkdb_id__in: ["PKDB00198"] });
  if (!criteria) throw new Error("Missing example");
  expect(canonicalCriteria(criteria).scope).toBe("studies");
  expect(serializeCriteria(criteria).get("studies__pkdb_id__in")).toBe(
    "PKDB00198",
  );
});
