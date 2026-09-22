import { describe, expect, it } from "vitest";
import { plotModel } from "../../src/features/plots/types";
const point = (pk: number, fields: Record<string, unknown> = {}) => ({
  pk,
  time: 0,
  time_unit: "h",
  unit: "mg/l",
  value: null,
  mean: null,
  median: null,
  sd: null,
  se: null,
  cv: null,
  ...fields,
});

describe("scientific plot semantics", () => {
  it("sorts time with its statistics and uncertainty, retaining zero and missing values", () => {
    const input = [
      [point(2, { time: 2, mean: 1e-9, sd: 0.1 })],
      [point(1, { time: 0, mean: 0, sd: 0 })],
      [point(3, { time: 3 })],
    ];
    const result = plotModel(input, "timecourse");
    expect(result.traces[0]?.x).toEqual([0, 2, 3]);
    expect(result.traces[0]?.y).toEqual([0, 1e-9, null]);
    expect(result.traces[0]?.error_y?.array).toEqual([0, 0.1, null]);
    expect(result.traces[0]?.connectgaps).toBe(false);
    expect(result.xLabel).toBe("Time [h]");
    expect(result.yLabel).toBe("mean [mg/l]");
    expect(input[0]?.[0]?.pk).toBe(2);
  });
  it("preserves paired scatter observations and independent axis units", () => {
    const result = plotModel(
      [
        [
          point(10, { value: 2, unit: "mg", se: 0.2 }),
          point(11, { value: 5, sd: 0.5 }),
        ],
        [point(20, { value: 1, unit: "mg" }), point(21, { value: 9 })],
      ],
      "scatter",
    );
    expect(result.traces[0]?.x).toEqual([2, 1]);
    expect(result.traces[0]?.y).toEqual([5, 9]);
    expect(result.traces[0]?.error_x?.array).toEqual([0.2, null]);
    expect(result.traces[0]?.error_y?.array).toEqual([0.5, null]);
    expect(result.xLabel).toBe("value [mg]");
  });
  it("retains CV without misrepresenting it as dimensional error", () => {
    const result = plotModel([[point(1, { mean: 10, cv: 25 })]], "timecourse");
    expect(result.traces[0]?.error_y).toBeUndefined();
    expect(result.points[0]?.[0]?.cv).toBe(25);
    expect(result.notes.join(" ")).toContain(
      "not plotted as an absolute error",
    );
  });
  it("does not fill missing individual values from aggregate means", () => {
    expect(
      plotModel(
        [[point(1, { value: 0, mean: 10 })], [point(2, { mean: 20 })]],
        "timecourse",
      ).traces[0]?.y,
    ).toEqual([0, null]);
  });
  it("rejects malformed dimensions, nonfinite numbers and mixed units", () => {
    expect(() => plotModel([[point(1)]], "scatter")).toThrow("dimensions");
    expect(() =>
      plotModel([[point(1, { value: Infinity })]], "timecourse"),
    ).toThrow("non-finite");
    expect(() =>
      plotModel([[point(1)], [point(2, { unit: "mmol/l" })]], "timecourse"),
    ).toThrow("mixed units");
    expect(() =>
      plotModel([[point(1)], [point(2, { time_unit: "min" })]], "timecourse"),
    ).toThrow("mixed time units");
  });
});
