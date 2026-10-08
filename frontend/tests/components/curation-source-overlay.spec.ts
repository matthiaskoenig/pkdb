import { beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { afterEach } from "vitest";
import type { SourceView } from "../../src/curation-app/api/types";
import type SourceOverlayComponent from "../../src/curation-app/components/SourceOverlay.vue";
import type { OverlayTrace } from "../../src/curation-app/overlay";
import sourceFixture from "../fixtures/curation-contract/source-fig1.json";

enableAutoUnmount(afterEach);

type Click = (event: { points: { customdata?: unknown; x?: unknown; y?: unknown }[] }) => void;

const handlers = vi.hoisted(() => new Map<string, Click>());
const engine = vi.hoisted(() => ({
  react: vi.fn(),
  purge: vi.fn(),
  Plots: { resize: vi.fn() },
}));
const loader = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("../../src/features/plots/plotly", () => ({ loadPlotly: loader.load }));

const EXAMPLE = "/local/studies/caffeine/Example";

let SourceOverlay: typeof SourceOverlayComponent;

const view: SourceView = {
  source: "Fig1",
  image: "Example_Fig1.png",
  image_url: `${EXAMPLE}/files/Example_Fig1.png`,
  image_size: [800, 600],
  raw_grid: null,
  digitization: "Example_Fig1.wpd.json",
  mapped: [
    {
      file: "timecourses_Fig1.tsv",
      kind: "timecourses",
      header: ["label", "time", "time_unit", "mean", "unit"],
      rows: [
        [2, ["caf_plasma_D150", "0.5", "h", "2.419", "µg/ml"]],
        [3, ["caf_plasma_D75", "0.5", "h", "1.20", "µg/ml"]],
      ],
      shared: false,
    },
  ],
  overlay: [
    {
      series: "caf_plasma_D150",
      role: "raw",
      px: 120,
      py: 300,
      x: 0.5,
      y: 2.42,
      file: "Example_Fig1.wpd.json",
      line: null,
      error_px: null,
      x_text: "0.5",
      y_text: "2.42",
      error_bar_end: false,
    },
    {
      series: "caf_plasma_D150",
      role: "mapped",
      px: 120,
      py: 301,
      x: 0.5,
      y: 2.419,
      file: "timecourses_Fig1.tsv",
      line: 2,
      error_px: null,
      x_text: "0.5",
      y_text: "2.419",
      error_bar_end: false,
    },
  ],
  unmatched: ["caf_plasma_D75"],
  layout: "overlay",
  points: [
    {
      series: "caf_plasma_D150",
      kind: "timecourses",
      file: "timecourses_Fig1.tsv",
      line: 2,
      x: 0.5,
      y: 2.419,
      error_bar: null,
      x_text: "0.5",
      y_text: "2.419",
    },
    {
      series: "caf_plasma_D75",
      kind: "timecourses",
      file: "timecourses_Fig1.tsv",
      line: 3,
      x: 0.5,
      y: 1.2,
      error_bar: null,
      x_text: "0.5",
      y_text: "1.20",
    },
  ],
  series: [
    { name: "caf_plasma_D150", color: "#2a78d6", dark_color: "#3987e5", x_label: "time (h)", y_label: "c (µg/ml)" },
    { name: "caf_plasma_D75", color: "#d65a24", dark_color: "#d95926", x_label: "time (h)", y_label: "c (µg/ml)" },
  ],
};

beforeEach(async () => {
  // The import state of Plotly is shared by the plots of the page; each test starts with a new page.
  vi.resetModules();
  ({ default: SourceOverlay } = await import("../../src/curation-app/components/SourceOverlay.vue"));
  handlers.clear();
  engine.react.mockReset().mockImplementation(async (element: HTMLElement) =>
    Object.assign(element, { on: (event: string, handler: Click) => handlers.set(event, handler) }),
  );
  engine.purge.mockReset();
  engine.Plots.resize.mockReset().mockResolvedValue(undefined);
  loader.load.mockReset().mockResolvedValue(engine);
});

describe("SourceOverlay", () => {
  it("draws the overlay on the image in an image with a name, a legend and a data table", async () => {
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    expect(engine.react).toHaveBeenCalledTimes(1);
    const [element, traces, layout, config] = engine.react.mock.calls[0]!;
    const host = wrapper.get('[role="img"]');
    expect(element).toBe(host.element);
    expect(host.attributes("aria-label")).toBe(
      "Figure Fig1 with 1 digitized point and 1 mapped row of the series caf_plasma_D150",
    );
    expect(traces).toEqual(expect.arrayContaining([expect.objectContaining({ meta: "mapped caf_plasma_D150" })]));
    expect(layout).toEqual(expect.objectContaining({ images: [expect.objectContaining({ sizex: 800, sizey: 600 })] }));
    expect(config).toEqual(expect.objectContaining({ displayModeBar: false, responsive: true }));

    const legend = wrapper.get(".overlay-legend");
    expect(legend.findAll("li").map((item) => item.text())).toEqual(["caf_plasma_D150"]);
    expect(legend.get(".overlay-swatch").attributes("style")).toContain("background-color");

    const details = wrapper.get("details");
    expect(details.get("summary").text()).toBe("Data of the plot");
    const rows = details.findAll("tbody tr").map((row) => row.findAll("th, td").map((cell) => cell.text()));
    expect(rows).toEqual([
      ["caf_plasma_D150", "Digitized", "0.5", "2.42", "Example_Fig1.wpd.json", "-"],
      ["caf_plasma_D150", "Mapped", "0.5", "2.419", "timecourses_Fig1.tsv", "2"],
    ]);
  });

  it("names and keys the digitized error bar ends of a real source view, and selects their rows", async () => {
    // The source view of Fig1 of the e2e fixture, a contract fixture of the local API.
    const real = sourceFixture as unknown as SourceView;
    const wrapper = mount(SourceOverlay, { props: { view: real } });
    await flushPromises();
    expect(wrapper.get('[role="img"]').attributes("aria-label")).toBe(
      "Figure Fig1 with 17 digitized points, 18 digitized error bar ends and 18 mapped rows " +
        "of the series caf_plasma_100mg, caf_plasma_200mg",
    );
    expect(wrapper.get(".overlay-key").text()).toContain("Digitized error bar");
    const kinds = wrapper.findAll("details tbody tr").map((row) => row.findAll("td")[0]?.text());
    expect(kinds.filter((kind) => kind === "Digitized error bar")).toHaveLength(18);

    // A click on the end of the error bar of line 6 selects line 6.
    const traces = engine.react.mock.calls[0]![1] as OverlayTrace[];
    const bars = traces.find((trace) => trace.meta === "raw-bar caf_plasma_100mg")!;
    handlers.get("plotly_click")?.({ points: [{ customdata: bars.customdata?.[4], x: bars.x[4], y: bars.y[4] }] });
    expect(wrapper.emitted("select-row")).toEqual([[{ file: "timecourses_Fig1.tsv", line: 6 }]]);
  });

  it("reserves the size of the image before Plotly draws, and shows the legend after", async () => {
    let draw: ((value: typeof engine) => void) | undefined;
    loader.load.mockReturnValue(new Promise((resolve) => (draw = resolve)));
    const wrapper = mount(SourceOverlay, { props: { view } });
    expect(wrapper.get('[role="img"]').attributes("style")).toContain("aspect-ratio: 800 / 600");
    // The frame and the image without the overlay are at most as wide as the image.
    expect(wrapper.get(".source-overlay").attributes("style")).toContain("--figure-width: 800px");
    expect(wrapper.find(".overlay-legend").exists()).toBe(false);
    draw?.(engine);
    await flushPromises();
    expect(wrapper.find(".overlay-legend").exists()).toBe(true);
  });

  it("emits the file and line of a clicked mapped point, also through the digitized point on it", async () => {
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    const click = handlers.get("plotly_click");
    expect(click).toBeDefined();
    const raw = ["Example_Fig1.wpd.json", null, "caf_plasma_D150", "0.5", "2.42"];
    click?.({ points: [{ customdata: raw, x: 400, y: 100 }] });
    expect(wrapper.emitted("select-row")).toBeUndefined();
    click?.({ points: [{ customdata: ["timecourses_Fig1.tsv", 2, "caf_plasma_D150", "0.5", "2.419"], x: 120, y: 301 }] });
    click?.({ points: [{ customdata: raw, x: 120, y: 300 }] });
    expect(wrapper.emitted("select-row")).toEqual([
      [{ file: "timecourses_Fig1.tsv", line: 2 }],
      [{ file: "timecourses_Fig1.tsv", line: 2 }],
    ]);
  });

  it("shows a pointer only over a point that selects a row, and keeps the classes that Plotly adds", async () => {
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    // Plotly marks its element with classes; its styles and its sizing depend on them.
    wrapper.get('[role="img"]').element.classList.add("js-plotly-plot");
    const host = () => wrapper.get(".overlay-frame");
    handlers.get("plotly_hover")?.({
      points: [{ customdata: ["timecourses_Fig1.tsv", 2, "caf_plasma_D150", "0.5", "2.419"], x: 120, y: 301 }],
    });
    await flushPromises();
    expect(host().classes()).toContain("overlay-frame--pointer");
    handlers.get("plotly_unhover")?.({ points: [] });
    await flushPromises();
    expect(host().classes()).not.toContain("overlay-frame--pointer");
    handlers.get("plotly_hover")?.({
      points: [{ customdata: ["Example_Fig1.wpd.json", null, "caf_plasma_D150", "0.5", "2.42"], x: 400, y: 100 }],
    });
    await flushPromises();
    expect(host().classes()).not.toContain("overlay-frame--pointer");
    await wrapper.setProps({ highlight: "caf_plasma_D150" });
    await flushPromises();
    expect(wrapper.get('[role="img"]').classes()).toContain("js-plotly-plot");
  });

  it("listens to clicks once across renders", async () => {
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    const first = handlers.get("plotly_click");
    await wrapper.setProps({ highlight: "caf_plasma_D150" });
    await flushPromises();
    expect(engine.react).toHaveBeenCalledTimes(2);
    expect(handlers.get("plotly_click")).toBe(first);
  });

  it("fades the other series of an emphasized series and says when it is not digitized", async () => {
    const wrapper = mount(SourceOverlay, { props: { view, highlight: "caf_plasma_D75" } });
    await flushPromises();
    expect(wrapper.text()).toContain("caf_plasma_D75 is not digitized.");
    await wrapper.setProps({ highlight: "caf_plasma_D150" });
    await flushPromises();
    expect(wrapper.text()).not.toContain("is not digitized");
    expect(wrapper.get(".overlay-legend li").classes()).toContain("overlay-legend-item--emphasized");
  });

  it("shows a failed import of Plotly with Retry and Reload, and imports it again on Retry", async () => {
    loader.load.mockRejectedValueOnce(new TypeError("Failed to fetch dynamically imported module"));
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    expect(wrapper.text()).toContain("The plot could not be loaded.");
    // Chrome keeps a failed import until the page reloads, so a reload is offered at once.
    expect(wrapper.findAll("button").map((button) => button.text())).toEqual(["Retry", "Reload the page"]);
    expect(engine.react).not.toHaveBeenCalled();
    await wrapper.findAll("button")[0]!.trigger("click");
    await flushPromises();
    expect(loader.load).toHaveBeenCalledTimes(2);
    expect(engine.react).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).not.toContain("could not be loaded");
    expect(wrapper.get(".overlay-frame").isVisible()).toBe(true);
  });

  it("shows the image of the figure instead of an empty frame while the plot cannot be drawn", async () => {
    loader.load.mockRejectedValue(new TypeError("Failed to fetch dynamically imported module"));
    const wrapper = mount(SourceOverlay, { props: { view }, attachTo: document.body });
    await flushPromises();
    expect(wrapper.get(".overlay-frame").isVisible()).toBe(false);
    const image = wrapper.get(".overlay-fallback img");
    expect(image.attributes("src")).toBe(`${EXAMPLE}/files/Example_Fig1.png`);
    expect(image.attributes("alt")).toBe("Image of Fig1");
    for (const part of [".overlay-legend", ".overlay-key"]) expect(wrapper.find(part).exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Click a cross");
    // The data stay readable.
    expect(wrapper.findAll("details tbody tr")).toHaveLength(2);
  });

  it("suggests a reload when the import fails again, as Chrome keeps a failed import until a reload", async () => {
    loader.load.mockRejectedValue(new TypeError("Failed to fetch dynamically imported module"));
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    expect(wrapper.text()).not.toContain("Reload the page to try again");
    await wrapper.findAll("button")[0]!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("The plot could not be loaded again. Reload the page to try again.");
    expect(wrapper.findAll("button").map((button) => button.text())).toEqual(["Retry", "Reload the page"]);
  });

  it("draws every plot that waits for Plotly after one Retry", async () => {
    loader.load.mockRejectedValueOnce(new TypeError("Failed")).mockRejectedValueOnce(new TypeError("Failed"));
    const overlay = mount(SourceOverlay, { props: { view } });
    const plot = mount(SourceOverlay, { props: { view, mode: "plot" } });
    await flushPromises();
    expect(overlay.text()).toContain("The plot could not be loaded.");
    expect(plot.text()).toContain("The plot could not be loaded.");
    await overlay.findAll("button")[0]!.trigger("click");
    await flushPromises();
    expect(engine.react).toHaveBeenCalledTimes(2);
    expect(plot.text()).not.toContain("could not be loaded");
  });

  it("plots the mapped rows of the series without a dataset in plot mode", async () => {
    const wrapper = mount(SourceOverlay, { props: { view, mode: "plot" } });
    await flushPromises();
    const [, traces, layout] = engine.react.mock.calls[0]!;
    expect(traces).toEqual([expect.objectContaining({ meta: "plot caf_plasma_D75", x: [0.5], y: [1.2] })]);
    expect(layout).not.toHaveProperty("images");
    expect(wrapper.get('[role="img"]').attributes("aria-label")).toBe(
      "Plot of 1 mapped row of Fig1 of the series caf_plasma_D75",
    );
    // The color of the source view; jsdom writes colors as rgb().
    expect(wrapper.get(".overlay-legend .overlay-swatch").attributes("style")).toContain(
      "background-color: rgb(214, 90, 36)",
    );
  });

  it("draws the plot when the source view puts the image and the plot side by side", async () => {
    const wrapper = mount(SourceOverlay, {
      props: { view: { ...view, digitization: null, overlay: [], layout: "side_by_side" } },
    });
    await flushPromises();
    const [, , layout] = engine.react.mock.calls[0]!;
    expect(layout).not.toHaveProperty("images");
    expect(wrapper.get('[role="img"]').attributes("aria-label")).toContain("Plot of");
  });

  it("follows the size of its element: Plotly resizes, and the marks shrink with the image", async () => {
    let resized: ((entries: { contentRect: { width: number } }[]) => void) | undefined;
    const original = globalThis.ResizeObserver;
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: typeof resized) {
          resized = callback;
        }
        observe() {}
        disconnect() {}
      },
    );
    try {
      mount(SourceOverlay, { props: { view } });
      await flushPromises();
      const size = () => {
        const traces = engine.react.mock.lastCall?.[1] as { meta: string; marker?: { size: number } }[];
        return traces.find((trace) => trace.meta === "mapped caf_plasma_D150")?.marker?.size;
      };
      expect(size()).toBe(11);
      resized?.([{ contentRect: { width: 400 } }]);
      await flushPromises();
      expect(engine.Plots.resize).toHaveBeenCalled();
      expect(size()).toBeCloseTo(6.6);
    } finally {
      vi.stubGlobal("ResizeObserver", original);
    }
  });

  it("releases the plot when it unmounts", async () => {
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    wrapper.unmount();
    expect(engine.purge).toHaveBeenCalledTimes(1);
  });
});
