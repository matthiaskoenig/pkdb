import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { h } from "vue";
import DataSection from "../../src/curation-app/sections/DataSection.vue";
import type { SourceView, TableResponse } from "../../src/study-views/types";
import { studyDetail } from "../unit/curation-fixtures";
import { setViewport } from "./curation-dom";
import { memoryData, mountViews, viewsContext, websiteRouter } from "./study-views";

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

function view(source: string): SourceView {
  return {
    source,
    image: null,
    image_url: null,
    image_size: null,
    raw_grid: null,
    digitization: null,
    mapped: [],
    overlay: [],
    unmatched: [],
    layout: "side_by_side",
    points: [],
    series: [],
    log_x: false,
    log_y: false,
  };
}

async function mountData(slots: Record<string, (props: Record<string, unknown>) => unknown> = {}) {
  const router = websiteRouter();
  await router.push("/data/caffeine/Example/data?file=subjects.tsv");
  const data = memoryData({ detail: studyDetail(), tables: { "subjects.tsv": SUBJECTS }, sources: { Fig1: view("Fig1"), Tab2: view("Tab2") } });
  const wrapper = mountViews(DataSection, {
    context: viewsContext({ data }),
    plugins: [router],
    slots,
    stubs: { SourceOverlay: true, PaperViewer: true },
    attachTo: document.body,
  });
  await flushPromises();
  return wrapper;
}

describe("the shared Data section", () => {
  it("shows the tables and sources of the page without a store and without actions of its own", async () => {
    const wrapper = await mountData();
    expect(wrapper.get(".rows-pane").attributes("aria-label")).toBe("Table subjects.tsv");
    expect(wrapper.text()).not.toMatch(/Open sheet|Sync|Add table/);
  });

  it("puts the actions of its page into its toolbar, its status line and above the rows", async () => {
    const wrapper = await mountData({
      toolbar: (props) => h("button", { class: "page-sheet" }, `Open ${String(props.file)}`),
      status: (props) => h("p", { class: "page-status" }, props.rows ? "with rows" : "without rows"),
      rows: (props) => h("p", { class: "page-notes" }, String(props.kind)),
    });
    expect(wrapper.get(".data-toolbar .page-sheet").text()).toBe("Open subjects.tsv");
    expect(wrapper.get(".page-status").text()).toBe("with rows");
    expect(wrapper.get(".rows-pane .page-notes").text()).toBe("subjects");
  });
});
