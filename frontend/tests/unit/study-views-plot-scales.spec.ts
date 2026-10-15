import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { plotFigure, usePlotScaleChoice, type PlotScaleStore } from "../../src/study-views/plotScales";
import type { AxisScales, SourceView } from "../../src/study-views/types";

/** The view of the figure `source` without points; `logY` as its digitization draws y. */
function view(source: string, logY = false): SourceView {
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
    log_y: logY,
  };
}

describe("the scales of the plot of a figure", () => {
  it("follow the digitization, then the reader's choice, which lasts for the page, per figure", () => {
    const shown = ref<SourceView | null>(view("Fig1", true));
    const { scales, choose } = usePlotScaleChoice("caffeine/Example", shown);
    expect(scales.value).toEqual({ x: "linear", y: "log" });
    choose("y", "linear");
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
    shown.value = view("Fig2");
    choose("x", "log");
    expect(scales.value).toEqual({ x: "log", y: "linear" });
    shown.value = view("Fig1", true);
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
    shown.value = null;
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
  });

  it("start from the choice that the page kept and keep every new choice in order", async () => {
    const kept: Record<string, AxisScales> = { [plotFigure("caffeine/Example", "Fig1")]: { x: "log", y: "log" } };
    const calls: string[] = [];
    const store: PlotScaleStore = {
      kept: (figure) => kept[figure],
      keep: async (figure, scales) => {
        calls.push(`${figure} ${scales.x} ${scales.y}`);
      },
    };
    const { scales, choose } = usePlotScaleChoice("caffeine/Example", view("Fig1"), store);
    expect(scales.value).toEqual({ x: "log", y: "log" });
    choose("x", "linear");
    choose("y", "linear");
    await vi.waitFor(() =>
      expect(calls).toEqual(["caffeine/Example/Fig1 linear log", "caffeine/Example/Fig1 linear linear"]),
    );
  });

  it("apply a choice that the page could not keep", async () => {
    const store: PlotScaleStore = { kept: () => undefined, keep: () => Promise.reject(new Error("offline")) };
    const { scales, choose } = usePlotScaleChoice("caffeine/Example", view("Fig1"), store);
    choose("y", "log");
    await Promise.resolve();
    expect(scales.value).toEqual({ x: "linear", y: "log" });
  });
});
