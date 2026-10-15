import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import SourcePane from "../../src/study-views/components/SourcePane.vue";
import SplitPane from "../../src/study-views/components/SplitPane.vue";
import DataSection from "../../src/study-views/sections/DataSection.vue";
import type { SourceView, TableResponse } from "../../src/study-views/types";
import { sourceSummary, studyDetail } from "../unit/curation-fixtures";
import { setViewport } from "./curation-dom";
import { CURATOR, memoryData, mountViews, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => {
  setActivePinia(undefined);
  setViewport(1440);
  localStorage.clear();
});

const VIEW: SourceView = {
  source: "Tab2",
  image: "Example_Tab2.png",
  image_url: "/api/v2/studies/caffeine/Example/view/files/Example_Tab2.png",
  image_size: [640, 220],
  raw_grid: [["", "Caffeine 150 mg"]],
  digitization: null,
  mapped: [],
  overlay: [],
  unmatched: [],
  layout: "side_by_side",
  log_x: false,
  log_y: false,
  points: [],
  series: [],
};

const SUBJECTS: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [{ line: 1, cells: ["Example", "all", "Tab2"] }],
};

describe("what the views keep in the storage of the browser", () => {
  it("keep the zoom of an image under the storage prefix of the page", async () => {
    const wrapper = mountViews(SourcePane, {
      context: viewsContext({ capabilities: CURATOR, storagePrefix: "pkdb-website" }),
      props: {
        summary: sourceSummary({ source: "Tab2", image: "Example_Tab2.png", raw: "Example_Tab2.tsv", raw_kind: "table" }),
        view: VIEW,
        loading: false,
        error: null,
        selected: null,
      },
    });
    await wrapper.findAll(".zoom button")[1]!.trigger("click");
    expect(localStorage.getItem("pkdb-website:source-zoom")).toBe("full");
    expect(localStorage.getItem("pkdb-curation:source-zoom")).toBeNull();
  });

  it("keep the share of the source and the rows under the storage prefix of the page", async () => {
    const router = websiteRouter();
    await router.push("/data/caffeine/Example/data?file=subjects.tsv");
    const wrapper = mountViews(DataSection, {
      context: viewsContext({
        capabilities: CURATOR,
        storagePrefix: "pkdb-website",
        data: memoryData({ detail: studyDetail(), tables: { "subjects.tsv": SUBJECTS } }),
      }),
      plugins: [router],
      stubs: { SourcePane: true, PaperViewer: true },
    });
    await flushPromises();
    expect(wrapper.findComponent(SplitPane).props("storageKey")).toBe("pkdb-website:data-split");
  });
});
