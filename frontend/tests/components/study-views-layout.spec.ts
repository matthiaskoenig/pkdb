import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import DataSection from "../../src/study-views/sections/DataSection.vue";
import type { TableResponse } from "../../src/study-views/types";
import { studyDetail } from "../unit/curation-fixtures";
import { setViewport } from "./curation-dom";
import { memoryData, mountViews, PUBLIC, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => {
  setActivePinia(undefined);
  setViewport(1440);
});

const SUBJECTS: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [{ line: 1, cells: ["Example", "all", "Tab2"] }],
};

async function section(props: Record<string, unknown>) {
  const router = websiteRouter();
  await router.push("/data/caffeine/Example/data?file=subjects.tsv");
  const wrapper = mountViews(DataSection, {
    context: viewsContext({ capabilities: PUBLIC, data: memoryData({ detail: studyDetail(), tables: { "subjects.tsv": SUBJECTS } }) }),
    props,
    plugins: [router],
    stubs: { SourcePane: true, PaperViewer: true },
    attachTo: document.body,
  });
  await flushPromises();
  return wrapper.get(".data-section");
}

describe("the layout of the Data section", () => {
  it("scrolls with its page unless the page asks it to fill the window, also wide and with a table", async () => {
    expect((await section({})).classes()).not.toContain("data-section--fill");
  });

  it("fills the window while its panes stand side by side when the page asks for it", async () => {
    expect((await section({ fill: true })).classes()).toContain("data-section--fill");
  });
});
