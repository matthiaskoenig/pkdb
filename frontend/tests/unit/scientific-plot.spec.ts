import { describe, expect, it } from "vitest";
import { plotModel } from "../../src/features/plots/types";
const point = (pk: number, fields: Record<string, unknown> = {}) => ({
  pk,
  time: 0,
  time_unit: "h",
  unit: "mg/l",
  mean: null,
  median: null,
  gmean: null,
  sd: null,
  se: null,
  cv: null,
  gsd: null,
  gcv: null,
  label: null,
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
          point(10, { mean: 2, unit: "mg", se: 0.2 }),
          point(11, { mean: 5, sd: 0.5 }),
        ],
        [point(20, { mean: 1, unit: "mg" }), point(21, { mean: 9 })],
      ],
      "scatter",
    );
    expect(result.traces[0]?.x).toEqual([2, 1]);
    expect(result.traces[0]?.y).toEqual([5, 9]);
    expect(result.traces[0]?.error_x?.array).toEqual([0.2, null]);
    expect(result.traces[0]?.error_y?.array).toEqual([0.5, null]);
    expect(result.xLabel).toBe("mean [mg]");
  });
  it("retains CV without misrepresenting it as dimensional error", () => {
    const result = plotModel(
      [[point(1, { mean: 10, cv: 0.25 })]],
      "timecourse",
    );
    expect(result.traces[0]?.error_y).toBeUndefined();
    expect(result.points[0]?.[0]?.cv).toBe(0.25);
    expect(result.notes.join(" ")).toContain(
      "not plotted as an absolute error",
    );
    const geometric = plotModel(
      [[point(1, { gmean: 10, gcv: 0.25 })]],
      "timecourse",
    );
    expect(geometric.traces[0]?.error_y).toBeUndefined();
    expect(geometric.notes.join(" ")).toContain(
      "Geometric coefficient of variation is retained in the data table",
    );
  });
  it("does not fill missing values from another statistic", () => {
    expect(
      plotModel(
        [[point(1, { mean: 0, median: 10 })], [point(2, { median: 20 })]],
        "timecourse",
      ).traces[0]?.y,
    ).toEqual([0, null]);
  });
  it("plots the mean, else the median, else the geometric mean", () => {
    const y = (fields: Record<string, unknown>) =>
      plotModel([[point(1, fields)]], "timecourse");
    expect(y({ mean: 1, median: 2, gmean: 3 }).yLabel).toBe("mean [mg/l]");
    expect(y({ median: 2, gmean: 3 }).traces[0]?.y).toEqual([2]);
    expect(y({ median: 2, gmean: 3 }).yLabel).toBe("median [mg/l]");
    expect(y({ gmean: 3 }).traces[0]?.y).toEqual([3]);
    expect(y({ gmean: 3 }).yLabel).toBe("geometric mean [mg/l]");
    expect(y({}).yLabel).toBe("Not reported [mg/l]");
  });
  it("draws arithmetic errors symmetrically from the SD, else the SE", () => {
    const error = plotModel(
      [[point(1, { mean: 5, sd: 1, se: 0.5 })]],
      "timecourse",
    ).traces[0]?.error_y;
    expect(error).toEqual({ type: "data", array: [1], visible: true });
    expect(
      plotModel([[point(1, { median: 5, se: 0.5 })]], "timecourse").traces[0]
        ?.error_y?.array,
    ).toEqual([0.5]);
  });
  it("draws the geometric SD as a multiplicative band around the geometric mean", () => {
    const result = plotModel(
      [
        [point(1, { time: 0, gmean: 10, gsd: 2 })],
        [point(2, { time: 1, gmean: 4, gsd: 1 })],
        [point(3, { time: 2, gmean: 4 })],
      ],
      "timecourse",
    );
    expect(result.traces[0]?.y).toEqual([10, 4, 4]);
    expect(result.traces[0]?.error_y).toEqual({
      type: "data",
      symmetric: false,
      array: [10, 0, null],
      arrayminus: [5, 0, null],
      visible: true,
    });
    expect(result.notes.join(" ")).toContain(
      "Y error bars: geometric mean divided and multiplied by the geometric SD.",
    );
  });
  it("draws no band for a geometric SD below 1 or without a geometric mean", () => {
    expect(
      plotModel([[point(1, { gmean: 4, gsd: 0.5 })]], "timecourse").traces[0]
        ?.error_y?.array,
    ).toEqual([null]);
    expect(
      plotModel([[point(1, { mean: 4, gsd: 2 })]], "timecourse").traces[0]
        ?.error_y,
    ).toBeUndefined();
  });
  it("labels a timecourse trace with the timecourse label", () => {
    const labelled = plotModel(
      [
        [point(1, { time: 0, mean: 1, label: "Plasma, 10 mg" })],
        [point(2, { time: 1, mean: 2, label: "Plasma, 10 mg" })],
      ],
      "timecourse",
    );
    expect(labelled.traces[0]?.name).toBe("Plasma, 10 mg");
    expect(labelled.traces[0]?.showlegend).toBe(true);
    const unlabelled = plotModel([[point(1, { mean: 1 })]], "timecourse");
    expect(unlabelled.traces[0]?.name).toBe("mean [mg/l]");
    expect(unlabelled.traces[0]?.showlegend).toBe(false);
  });
  it("keeps the series label with every point of the accessible table", () => {
    const result = plotModel(
      [[point(1, { gmean: 2, gsd: 1.5, gcv: 0.4, label: "A" })]],
      "timecourse",
    );
    expect(result.points[0]?.[0]).toMatchObject({
      gmean: 2,
      gsd: 1.5,
      gcv: 0.4,
      label: "A",
    });
  });
  it("rejects malformed dimensions, nonfinite numbers and mixed units", () => {
    expect(() => plotModel([[point(1)]], "scatter")).toThrow("dimensions");
    expect(() =>
      plotModel([[point(1, { mean: Infinity })]], "timecourse"),
    ).toThrow("non-finite");
    expect(() =>
      plotModel([[point(1)], [point(2, { unit: "mmol/l" })]], "timecourse"),
    ).toThrow("mixed units");
    expect(() =>
      plotModel([[point(1)], [point(2, { time_unit: "min" })]], "timecourse"),
    ).toThrow("mixed time units");
  });
});
