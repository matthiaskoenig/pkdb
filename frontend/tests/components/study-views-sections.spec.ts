import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import ProblemsSection from "../../src/study-views/sections/ProblemsSection.vue";
import ReviewSection from "../../src/study-views/sections/ReviewSection.vue";
import { locationKey } from "../../src/study-views/problems";
import type { Problem } from "../../src/study-views/types";
import { reviewItem, studyDetail } from "../unit/curation-fixtures";
import { memoryData, mountViews, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => setActivePinia(undefined));

const WARNING: Problem = {
  code: "unit_unknown",
  severity: "warning",
  message: "Unknown unit mg/dl.",
  source: { file: "outputs_Tab2.tsv", row: 1, header: "unit" },
  acknowledgeable: true,
};

async function router(section: string) {
  const routes = websiteRouter();
  await routes.push(`/data/caffeine/Example/${section}`);
  return routes;
}

describe("the shared Problems section", () => {
  it("lists the problems of the page without a store and leaves the actions on them to its page", async () => {
    const detail = studyDetail({ problems: [WARNING], counts: { errors: 0, warnings: 1 } });
    const wrapper = mountViews(ProblemsSection, {
      context: viewsContext({ data: memoryData({ detail }) }),
      plugins: [await router("problems")],
    });
    await flushPromises();
    const section = wrapper.findComponent(ProblemsSection);
    expect(wrapper.get(".problem-file").text()).toBe("outputs_Tab2.tsv");
    await wrapper.get(".problem-acknowledge").trigger("click");
    expect(section.emitted("acknowledge")).toEqual([[WARNING, [locationKey(WARNING)]]]);
    await wrapper.get(".problem-open-tables").trigger("click");
    expect(section.emitted("open-tables")).toEqual([[WARNING]]);
  });

  it("waits while its page works", async () => {
    const detail = studyDetail({ problems: [WARNING], counts: { errors: 0, warnings: 1 } });
    const wrapper = mountViews(ProblemsSection, {
      context: viewsContext({ data: memoryData({ detail }) }),
      props: { busy: "validate", working: true },
      plugins: [await router("problems")],
    });
    await flushPromises();
    expect(wrapper.get(".problem-acknowledge").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".problem-open-tables").attributes("disabled")).toBeDefined();
  });
});

describe("the shared Review section", () => {
  it("shows the items of the page without a store and leaves the reply to its page", async () => {
    const item = reviewItem({ id: "01A" });
    const detail = studyDetail({
      review: { revision: "review-1", value: { status: "in_review", reviewers: [], items: [item] }, issues: [] },
    });
    const wrapper = mountViews(ReviewSection, {
      context: viewsContext({ data: memoryData({ detail }) }),
      plugins: [await router("review")],
    });
    await flushPromises();
    await wrapper.get(".review-reply textarea").setValue("  Read from Table 2.  ");
    const reply = wrapper.findAll("button").find((button) => button.text() === "Reply");
    await reply!.trigger("click");
    expect(wrapper.findComponent(ReviewSection).emitted("act")).toEqual([["reply", item, "Read from Table 2."]]);
  });
});
