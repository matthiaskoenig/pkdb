import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { Problem, SourceView } from "../../src/curation-app/api/types";
import SourcePane from "../../src/curation-app/components/SourcePane.vue";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { snapshot, sourceSummary, studyDetail } from "../unit/curation-fixtures";
import { serveApi } from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";

const view: SourceView = {
  source: "Tab2",
  image: "Example_Tab2.png",
  image_url: `${EXAMPLE}/files/Example_Tab2.png`,
  image_size: [640, 220],
  raw_grid: [
    ["", "Caffeine 150 mg", "Caffeine 300 mg"],
    ["CL [ml/min/kg]", "1.20 ± 0.3", "1.10 ± 0.2"],
  ],
  digitization: null,
  mapped: [],
  overlay: [],
  unmatched: [],
  layout: "side_by_side",
  points: [],
  series: [],
};

const summary = sourceSummary({
  source: "Tab2",
  image: "Example_Tab2.png",
  raw: "Example_Tab2.tsv",
  raw_kind: "table",
});

function mountPane(props: Record<string, unknown> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(SourcePane, {
    props: { summary, view, loading: false, error: null, selected: null, ...props },
    global: { plugins: [pinia] },
  });
}

beforeEach(() => localStorage.clear());

describe("source pane", () => {
  it("shows the image and the raw extraction of a paper table", () => {
    const wrapper = mountPane();
    expect(wrapper.get("section").attributes("aria-label")).toBe("Source Tab2");
    expect(wrapper.get("img").attributes("src")).toBe(`${EXAMPLE}/files/Example_Tab2.png`);
    expect(wrapper.get('[role="region"]').attributes("aria-label")).toBe("Raw extraction Example_Tab2.tsv");
    expect(wrapper.get(".pane-head").text()).toContain("Tab2");
  });

  it("names a missing image in one line", () => {
    const wrapper = mountPane({
      summary: sourceSummary({ source: "Tab2", raw: "Example_Tab2.tsv", missing_image: "Example_Tab2.png" }),
      view: { ...view, image: null, image_url: null },
    });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".pane-missing").text()).toContain("No image: add Example_Tab2.png");
  });

  it("names each missing file and what to do about it in one text beside its icon", () => {
    /** The text of each note, which wraps as one paragraph in a narrow pane. */
    const notes = (wrapper: ReturnType<typeof mountPane>) =>
      wrapper.findAll(".pane-missing").map((note) => {
        expect(note.element.children).toHaveLength(2);
        return note.get(".pane-missing-text").text();
      });
    const table = mountPane({
      summary: sourceSummary({ source: "Tab3", missing_image: "Example_Tab3.png", missing_raw: "Example_Tab3.tsv" }),
      view: { ...view, source: "Tab3", image: null, image_url: null, raw_grid: null },
    });
    expect(notes(table)).toEqual([
      "No image: add Example_Tab3.png. Save it from the paper as a PNG image.",
      "No raw extraction: add Example_Tab3.tsv with Add table.",
    ]);
    const figure = mountPane({
      summary: sourceSummary({
        source: "Fig1",
        kind: "figure",
        image: "Example_Fig1.png",
        missing_raw: "Example_Fig1.wpd.json",
      }),
      view: { ...view, source: "Fig1", raw_grid: null },
    });
    expect(notes(figure)).toEqual([
      "No digitization: add Example_Fig1.wpd.json. Digitize it in WebPlotDigitizer and import it with pkdb digitize import.",
    ]);
  });

  it("toggles the zoom, which survives a storage that throws", async () => {
    const wrapper = mountPane();
    const [fit, full] = wrapper.findAll(".zoom button");
    expect(fit!.attributes("aria-pressed")).toBe("true");
    await full!.trigger("click");
    expect(full!.attributes("aria-pressed")).toBe("true");
    expect(fit!.attributes("aria-pressed")).toBe("false");
    expect(wrapper.get("img").classes()).toContain("source-image--full");
    expect(localStorage.getItem("pkdb-curation:source-zoom")).toBe("full");
    expect(mountPane().findAll(".zoom button")[1]!.attributes("aria-pressed")).toBe("true");

    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const blocked = mountPane();
    const buttons = blocked.findAll(".zoom button");
    expect(buttons[0]!.attributes("aria-pressed")).toBe("true");
    await buttons[1]!.trigger("click");
    expect(buttons[1]!.attributes("aria-pressed")).toBe("true");
    vi.restoreAllMocks();
  });
});

describe("problems of the source", () => {
  /** A problem of the raw extraction of a paper table. */
  const problem = (file: string): Problem => ({
    code: "raw_row_empty",
    severity: "warning",
    message: `${file} has an empty row.`,
    source: { file, row: 2 },
    acknowledgeable: false,
  });

  it("opens them again for the next source after the curator closed them", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    serveApi({
      "GET /local/state": snapshot(),
      [`GET ${EXAMPLE}`]: studyDetail({ problems: [problem("Example_Tab2.tsv"), problem("Example_Tab3.tsv")] }),
    });
    const study = useStudyStore();
    await study.open("caffeine", "Example");
    const tab3 = sourceSummary({ source: "Tab3", image: "Example_Tab3.png", raw: "Example_Tab3.tsv", raw_kind: "table" });
    const wrapper = mount(SourcePane, {
      props: { summary, view, loading: false, error: null, selected: null },
      global: { plugins: [pinia] },
    });
    const details = () => wrapper.get<HTMLDetailsElement>("details.source-problems").element;
    expect(wrapper.get(".source-problems").text()).toContain("Example_Tab2.tsv has an empty row.");
    expect(details().open).toBe(true);
    details().open = false;
    await wrapper.setProps({ summary: tab3, view: { ...view, source: "Tab3", image: "Example_Tab3.png" } });
    await flushPromises();
    expect(wrapper.get(".source-problems").text()).toContain("Example_Tab3.tsv has an empty row.");
    expect(details().open).toBe(true);
    study.close();
  });
});

describe("scrolling", () => {
  /** Gives the body of the pane a view of 300 px over `content` px scrolled to `top`, as a layout would. */
  function layout(wrapper: ReturnType<typeof mountPane>, content: number, top = 0): HTMLElement {
    const body = wrapper.get(".pane-body").element as HTMLElement;
    Object.defineProperty(body, "clientHeight", { configurable: true, value: 300 });
    Object.defineProperty(body, "scrollHeight", { configurable: true, value: content });
    Object.defineProperty(body, "scrollTop", { configurable: true, writable: true, value: top });
    return body;
  }

  it("fades out at the bottom while more of the pane follows below, and not at its end", async () => {
    const wrapper = mountPane();
    const body = layout(wrapper, 900);
    await wrapper.get(".pane-body").trigger("scroll");
    expect(wrapper.get(".pane-more").attributes("aria-hidden")).toBe("true");
    body.scrollTop = 600;
    await wrapper.get(".pane-body").trigger("scroll");
    expect(wrapper.find(".pane-more").exists()).toBe(false);
  });

  it("does not fade out a pane that fits", async () => {
    const wrapper = mountPane();
    layout(wrapper, 300);
    await wrapper.get(".pane-body").trigger("scroll");
    expect(wrapper.find(".pane-more").exists()).toBe(false);
  });

  it("keeps the content in one column inside the body that scrolls and takes the focus", () => {
    const wrapper = mountPane();
    expect(wrapper.get(".pane-body").attributes("tabindex")).toBe("0");
    expect(wrapper.find(".pane-body > .pane-content").exists()).toBe(true);
  });
});
