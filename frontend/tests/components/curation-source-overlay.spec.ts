import { beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { afterEach } from "vitest";
import type { SourceView } from "../../src/curation-app/api/types";
import type SourceOverlayComponent from "../../src/curation-app/components/SourceOverlay.vue";
import { SERIES_COLORS } from "../../src/curation-app/overlay";

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
        [3, ["caf_plasma_D75", "0.5", "h", "1.2", "µg/ml"]],
      ],
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
    },
  ],
  unmatched: ["caf_plasma_D75"],
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

  it("reserves the size of the image before Plotly draws", () => {
    loader.load.mockReturnValue(new Promise(() => undefined));
    const wrapper = mount(SourceOverlay, { props: { view } });
    const style = wrapper.get('[role="img"]').attributes("style") ?? "";
    expect(style).toContain("aspect-ratio: 800 / 600");
    expect(style).toContain("max-width: 800px");
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

  it("shows a failed import of Plotly and imports it again on Retry", async () => {
    loader.load.mockRejectedValueOnce(new TypeError("Failed to fetch dynamically imported module"));
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    expect(wrapper.text()).toContain("The plot could not be loaded.");
    expect(engine.react).not.toHaveBeenCalled();
    await wrapper.get("button").trigger("click");
    await flushPromises();
    expect(loader.load).toHaveBeenCalledTimes(2);
    expect(engine.react).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).not.toContain("could not be loaded");
  });

  it("suggests a reload when the import fails again, as Chrome keeps a failed import until a reload", async () => {
    loader.load.mockRejectedValue(new TypeError("Failed to fetch dynamically imported module"));
    const wrapper = mount(SourceOverlay, { props: { view } });
    await flushPromises();
    expect(wrapper.text()).not.toContain("Reload the page");
    await wrapper.get("button").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("The plot could not be loaded. Reload the page to try again.");
    expect(wrapper.findAll("button").map((button) => button.text())).toEqual(["Reload the page"]);
  });

  it("draws every plot that waits for Plotly after one Retry", async () => {
    loader.load.mockRejectedValueOnce(new TypeError("Failed")).mockRejectedValueOnce(new TypeError("Failed"));
    const overlay = mount(SourceOverlay, { props: { view } });
    const plot = mount(SourceOverlay, { props: { view, mode: "plot" } });
    await flushPromises();
    expect(overlay.text()).toContain("The plot could not be loaded.");
    expect(plot.text()).toContain("The plot could not be loaded.");
    await overlay.get("button").trigger("click");
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
    expect(wrapper.get(".overlay-legend .overlay-swatch").attributes("style")).toContain(
      // jsdom writes colors as rgb().
      "background-color: rgb(235, 104, 52)",
    );
    expect(SERIES_COLORS.light[1]).toBe("#eb6834");
  });

  it("draws the plot beside the image when the figure is not calibrated", async () => {
    const wrapper = mount(SourceOverlay, { props: { view: { ...view, digitization: null, overlay: [] } } });
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
