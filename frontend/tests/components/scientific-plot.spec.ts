import { beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import ScientificPlot from "../../src/features/plots/components/ScientificPlot.vue";
const engine = vi.hoisted(() => ({
  react: vi.fn(),
  purge: vi.fn(),
  Plots: { resize: vi.fn() },
}));
const loader = vi.hoisted(() => ({ load: vi.fn() }));
vi.mock("../../src/features/plots/plotly", () => ({ loadPlotly: loader.load }));
const points = [[{ pk: 1, time: 0, time_unit: "h", unit: "mg/l", value: 0 }]];
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
    points: [[{ pk: 2, time: 2, time_unit: "h", unit: "mg/l", value: 10 }]],
  });
  await flushPromises();
  expect(engine.react).toHaveBeenCalledTimes(1);
  wrapper.unmount();
  finish?.();
  await flushPromises();
  expect(engine.react).toHaveBeenCalledTimes(1);
  expect(engine.purge).toHaveBeenCalledTimes(2);
});
