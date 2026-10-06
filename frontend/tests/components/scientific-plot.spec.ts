import { beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { makeVuetify } from "../../src/plugins/vuetify";
import ScientificPlot from "../../src/features/plots/components/ScientificPlot.vue";
const engine = vi.hoisted(() => ({
  react: vi.fn(),
  purge: vi.fn(),
  Plots: { resize: vi.fn() },
}));
const loader = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("../../src/features/plots/plotly", () => ({ loadPlotly: loader.load }));
const points = [[{ pk: 1, time: 0, time_unit: "h", unit: "mg/l", mean: 0 }]];
beforeEach(() => {
  engine.react.mockReset().mockResolvedValue(undefined);
  engine.purge.mockReset();
  engine.Plots.resize.mockReset().mockResolvedValue(undefined);
  loader.load.mockReset().mockResolvedValue(engine);
});
it("exposes accessible values and log controls and releases the chart", async () => {
  const wrapper = mount(ScientificPlot, {
    props: { points, kind: "timecourse" },
  });
  await flushPromises();
  expect(engine.react).toHaveBeenCalledTimes(1);
  expect(wrapper.find("table").text()).toContain("0");
  await wrapper.findAll("input")[1]?.setValue(true);
  await flushPromises();
  expect(engine.react).toHaveBeenLastCalledWith(
    expect.any(HTMLElement),
    expect.any(Array),
    expect.objectContaining({
      yaxis: expect.objectContaining({ type: "log" }),
    }),
    expect.objectContaining({ modeBarButtonsToRemove: ["toImage"] }),
  );
  expect(wrapper.text()).toContain("Zero and negative values");
  wrapper.unmount();
  expect(engine.purge).toHaveBeenCalled();
});
it("does not create a chart if unmounted before lazy import resolves", async () => {
  let finish: ((value: typeof engine) => void) | undefined;
  loader.load.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const wrapper = mount(ScientificPlot, {
    props: { points, kind: "timecourse" },
  });
  await flushPromises();
  wrapper.unmount();
  finish?.(engine);
  await flushPromises();
  expect(engine.react).not.toHaveBeenCalled();
});
it("serializes replacement renders and cleans up a render finishing after unmount", async () => {
  let finish: (() => void) | undefined;
  engine.react.mockImplementationOnce(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  const wrapper = mount(ScientificPlot, {
    props: { points, kind: "timecourse" },
  });
  await flushPromises();
  await wrapper.setProps({
    points: [[{ pk: 2, time: 2, time_unit: "h", unit: "mg/l", mean: 10 }]],
  });
  await flushPromises();
  expect(engine.react).toHaveBeenCalledTimes(1);
  wrapper.unmount();
  finish?.();
  await flushPromises();
  expect(engine.react).toHaveBeenCalledTimes(1);
  expect(engine.purge).toHaveBeenCalledTimes(2);
});
it("names the trace by the timecourse label and tabulates geometric statistics", async () => {
  const wrapper = mount(ScientificPlot, {
    props: {
      kind: "timecourse",
      points: [
        [
          {
            pk: 7,
            time: 1,
            time_unit: "h",
            unit: "mg/l",
            gmean: 8,
            gsd: 2,
            gcv: 0.22595033203145737,
            label: "Plasma after 10 mg",
          },
        ],
      ],
    },
  });
  await flushPromises();
  expect(engine.react).toHaveBeenCalledWith(
    expect.any(HTMLElement),
    [
      expect.objectContaining({
        name: "Plasma after 10 mg",
        showlegend: true,
        y: [8],
        error_y: expect.objectContaining({
          symmetric: false,
          array: [8],
          arrayminus: [4],
        }),
      }),
    ],
    expect.objectContaining({
      yaxis: expect.objectContaining({
        title: { text: "geometric mean [mg/l]" },
      }),
    }),
    expect.any(Object),
  );
  const headers = wrapper.findAll("th").map((header) => header.text());
  expect(headers).toEqual(
    expect.arrayContaining([
      "Mean",
      "Median",
      "Geometric mean",
      "Geometric SD",
      "Geometric CV",
    ]),
  );
  expect(headers).not.toContain("Value");
  expect(wrapper.get("caption").text()).toBe(
    "Point values and their uncertainty; missing values are shown as -",
  );
  const cells = wrapper.findAll("tbody td").map((cell) => cell.text());
  expect(cells).toEqual(expect.arrayContaining(["8", "2", "22.6\u00a0%"]));
  wrapper.unmount();
});
it("rounds the table and the hover to four significant digits", async () => {
  const wrapper = mount(ScientificPlot, {
    props: {
      kind: "timecourse",
      points: [
        [
          {
            pk: 7,
            time: 0.30000000000000004,
            time_unit: "h",
            unit: "mg/l",
            mean: 0.009000000000000001,
            sd: 0.1111111111111111,
            cv: 0.07,
          },
        ],
      ],
    },
  });
  await flushPromises();
  const cells = wrapper.findAll("tbody td").map((cell) => cell.text());
  expect(cells).toEqual(
    expect.arrayContaining(["0.3", "0.009", "0.1111", "7\u00a0%"]),
  );
  expect(engine.react).toHaveBeenCalledWith(
    expect.any(HTMLElement),
    expect.any(Array),
    expect.objectContaining({
      xaxis: expect.objectContaining({ hoverformat: ".4~g" }),
      yaxis: expect.objectContaining({ hoverformat: ".4~g" }),
    }),
    expect.any(Object),
  );
  wrapper.unmount();
});
it("draws the chart on the surface of the light and the dark theme", async () => {
  const vuetify = makeVuetify();
  const wrapper = mount(ScientificPlot, {
    props: { points, kind: "timecourse" },
    global: { plugins: [vuetify] },
  });
  await flushPromises();
  expect(engine.react).toHaveBeenLastCalledWith(
    expect.any(HTMLElement),
    [
      expect.objectContaining({
        line: { color: "#176b70" },
        marker: { color: "#176b70" },
      }),
    ],
    expect.objectContaining({
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: { color: "#000" },
    }),
    expect.any(Object),
  );
  vuetify.theme.change("dark");
  await flushPromises();
  const layout = engine.react.mock.lastCall?.[2];
  expect(layout).toMatchObject({
    paper_bgcolor: "#192b31",
    plot_bgcolor: "#192b31",
  });
  expect(layout.font.color).not.toBe("#000");
  expect(layout.yaxis.gridcolor).toMatch(/^rgba\(/);
  expect(engine.react.mock.lastCall?.[1][0].line.color).toBe("#79d5d6");
  wrapper.unmount();
});
