import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import PaperViewer from "../../src/study-views/components/PaperViewer.vue";
import SourcePane from "../../src/study-views/components/SourcePane.vue";
import TargetView from "../../src/study-views/components/TargetView.vue";
import { ApiError, NO_SESSION, SessionMissing } from "../../src/study-views/errors";
import type { Problem, SourceView, TableResponse } from "../../src/study-views/types";
import { reviewItem, sourceSummary, studyDetail } from "../unit/curation-fixtures";
import { CURATOR, memoryData, mountViews, viewsContext, websiteRouter } from "./study-views";

// PDF.js does not run in jsdom: the viewer gets a fake engine.
const engine = vi.hoisted(() => ({ openPaper: vi.fn() }));
vi.mock("../../src/study-views/paperEngine", () => engine);

enableAutoUnmount(afterEach);

beforeEach(() => {
  setActivePinia(undefined);
  engine.openPaper.mockReset();
});

const PROBLEM: Problem = {
  code: "unit_unknown",
  severity: "error",
  message: "Unknown unit mg/dl.",
  source: { file: "outputs_Tab2.tsv", row: 1 },
  acknowledgeable: false,
};

const OUTPUTS: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "label"],
  rows: [{ line: 1, cells: ["Example", "Tab2", "caf_cl"] }],
};

const TAB2: SourceView = {
  source: "Tab2",
  image: "Example_Tab2.png",
  image_url: "/files/Example_Tab2.png",
  image_size: [640, 220],
  raw_grid: [
    ["", "Caffeine 150 mg"],
    ["CL [ml/min/kg]", "1.20"],
  ],
  digitization: null,
  mapped: [{ file: "outputs_Tab2.tsv", kind: "outputs", header: OUTPUTS.header, rows: [[1, ["Example", "Tab2", "caf_cl"]]], shared: false }],
  overlay: [],
  unmatched: [],
  layout: "side_by_side",
  points: [],
  series: [],
  log_x: false,
  log_y: false,
};

async function router() {
  const routes = websiteRouter();
  await routes.push("/data/caffeine/Example/data");
  return routes;
}

describe("the shared views read through their context, never through a store", () => {
  it("shows a source with its image, raw extraction and problems from the reads of the page", async () => {
    const detail = studyDetail({ problems: [PROBLEM], counts: { errors: 1, warnings: 0 } });
    const summary = sourceSummary({ source: "Tab2", image: "Example_Tab2.png", raw: "Example_Tab2.tsv", raw_kind: "table", tables: ["outputs_Tab2.tsv"] });
    const wrapper = mountViews(SourcePane, {
      context: viewsContext({ data: memoryData({ detail }) }),
      props: { summary, view: TAB2, loading: false, error: null, selected: null },
      plugins: [await router()],
    });
    await flushPromises();
    expect(wrapper.get("img.source-image").attributes("src")).toBe("/files/Example_Tab2.png");
    expect(wrapper.find(".source-raw").exists()).toBe(true);
    expect(wrapper.get(".source-problems > summary").text()).toBe("Problems (1)");
  });

  it("shows the rows that a review item targets from the reads of the page", async () => {
    const item = reviewItem({ target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } });
    const detail = studyDetail({ targets: { [item.id]: { lines: [1], series: null, total: 1 } } });
    const wrapper = mountViews(TargetView, {
      context: viewsContext({ data: memoryData({ detail, tables: { "outputs_Tab2.tsv": OUTPUTS } }) }),
      props: { item },
      plugins: [await router()],
    });
    await flushPromises();
    expect(wrapper.get(".review-target").text()).toContain("caf_cl");
  });

  it("aborts the read of a table that a newer read replaces or whose view unmounts, without a failure", async () => {
    const signals: AbortSignal[] = [];
    // A read that answers only by its abort, as a fetch does.
    const table = vi.fn(
      (_file: string, signal?: AbortSignal) =>
        new Promise<TableResponse>((_resolve, reject) => {
          signals.push(signal!);
          signal!.addEventListener("abort", () => reject(signal!.reason));
        }),
    );
    const outputs = reviewItem({ id: "01A", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } });
    const subjects = reviewItem({ id: "01B", target: { file: "subjects.tsv" } });
    const wrapper = mountViews(TargetView, {
      context: viewsContext({ data: { ...memoryData({ detail: studyDetail() }), table } }),
      props: { item: outputs },
      plugins: [await router()],
    });
    await flushPromises();
    expect(table.mock.calls.map(([file]) => file)).toEqual(["outputs_Tab2.tsv"]);
    expect(signals[0]!.aborted).toBe(false);
    await wrapper.setProps({ item: subjects });
    await flushPromises();
    expect(table.mock.calls.map(([file]) => file)).toEqual(["outputs_Tab2.tsv", "subjects.tsv"]);
    expect(signals.map((signal) => signal.aborted)).toEqual([true, false]);
    expect(wrapper.find(".action-failure-text").exists()).toBe(false);
    wrapper.unmount();
    expect(signals[1]!.aborted).toBe(true);
  });

  it("opens a PDF with the PDF.js files of the page", async () => {
    engine.openPaper.mockResolvedValue({
      goTo: vi.fn(),
      zoom: vi.fn(),
      fit: vi.fn(),
      find: vi.fn(),
      close: vi.fn(async () => undefined),
    });
    mountViews(PaperViewer, {
      context: viewsContext({ data: memoryData() }),
      props: { url: "/files/Example.pdf", file: "Example.pdf", version: "v1" },
      attachTo: document.body,
    });
    await flushPromises();
    expect(engine.openPaper).toHaveBeenCalledTimes(1);
    expect(engine.openPaper.mock.calls[0]![1]).toBe("/files/Example.pdf");
    expect(engine.openPaper.mock.calls[0]![5]).toBe("https://pk-db.example/pdfjs/");
  });

  it("asks the page why a PDF did not load", async () => {
    engine.openPaper.mockRejectedValue(
      Object.assign(new Error("Unexpected server response (404)."), { name: "ResponseException", status: 404 }),
    );
    const checkFile = vi.fn(() => Promise.reject(new ApiError(404, { error: "Not found.", code: "not_found" }, "GET /files/Example.pdf")));
    const wrapper = mountViews(PaperViewer, {
      context: viewsContext({ data: { ...memoryData(), checkFile } }),
      props: { url: "/files/Example.pdf", file: "Example.pdf", version: "v1" },
      attachTo: document.body,
    });
    await flushPromises();
    expect(checkFile).toHaveBeenCalledWith("/files/Example.pdf");
    expect(wrapper.get(".action-failure-text").text()).toBe("Example.pdf is no longer in the study folder.");
  });

  it("tells a reader who may not edit the study what the server answered, without the study folder", async () => {
    engine.openPaper.mockRejectedValue(
      Object.assign(new Error("Unexpected server response (404)."), { name: "ResponseException", status: 404 }),
    );
    const checkFile = vi.fn(() => Promise.reject(new ApiError(404, { error: "Not found.", code: "not_found" }, "GET /files/Example.pdf")));
    const wrapper = mountViews(PaperViewer, {
      context: viewsContext({ capabilities: CURATOR, data: { ...memoryData(), checkFile } }),
      props: { url: "/files/Example.pdf", file: "Example.pdf", version: "v1" },
      attachTo: document.body,
    });
    await flushPromises();
    expect(wrapper.get(".action-failure-text").text()).toBe("Could not load Example.pdf: the server answered 404.");
  });

  it("tells only the curation app how to get a session, and a reader who may not edit to sign in again", async () => {
    engine.openPaper.mockRejectedValue(
      Object.assign(new Error("Unexpected server response (401)."), { name: "ResponseException", status: 401 }),
    );
    const checkFile = vi.fn(() => Promise.reject(new SessionMissing("No session")));
    const texts: string[] = [];
    for (const capabilities of [undefined, CURATOR]) {
      const wrapper = mountViews(PaperViewer, {
        context: viewsContext({ ...(capabilities ? { capabilities } : {}), data: { ...memoryData(), checkFile } }),
        props: { url: "/files/Example.pdf", file: "Example.pdf", version: "v1" },
        attachTo: document.body,
      });
      await flushPromises();
      texts.push(wrapper.get(".action-failure-text").text());
      wrapper.unmount();
    }
    expect(texts).toEqual([NO_SESSION, "The session has ended. Sign in again to show the PDF."]);
  });
});
