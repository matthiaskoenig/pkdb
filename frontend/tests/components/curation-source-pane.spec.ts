import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { SourceView } from "../../src/curation-app/api/types";
import SourcePane from "../../src/curation-app/components/SourcePane.vue";
import { sourceSummary } from "../unit/curation-fixtures";

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
