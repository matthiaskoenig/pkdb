import { describe, it, expect } from "vitest";
import { cellText } from "../../src/features/results/cells";
import { columns, validOrder } from "../../src/features/results/columns";
describe("scientific result cells", () => {
  it("labels all acquisition types and their source", () => {
    expect(cellText({ provenance: { kind: "data_import", source_key: "osp.observed-data", release: "v1.9" } }, "provenance")).toBe("Automatic import · osp.observed-data · v1.9");
    expect(cellText({ provenance: { kind: "manual_curation", source_key: "pkdb.manual" } }, "provenance")).toBe("Manual curation · pkdb.manual");
    expect(cellText({ provenance: { kind: "automatic_curation", source_key: "pipeline" } }, "provenance")).toBe("Automatic curation · pipeline");
    expect(cellText({}, "provenance")).toBe("Not reported");
  });
  it("distinguishes measured zero, null, precision and characteristic context", () => {
    expect(cellText({ mean: 0 }, "mean")).toBe("0");
    expect(cellText({ mean: null }, "mean")).toBe("Not reported");
    expect(cellText({ gmean: 0.002125 }, "gmean")).toBe("0.002125");
    expect(
      cellText(
        {
          characteristica: [
            { measurement_type: { name: "Age" }, mean: 0, unit: "year" },
          ],
        },
        "characteristica",
      ),
    ).toBe("Age 0 year");
  });
  it("shows the first reported of mean, median, geometric mean and choice", () => {
    const shown = (statistics: Record<string, unknown>) =>
      cellText(
        {
          characteristica: [
            { measurement_type: { name: "Age" }, unit: "year", ...statistics },
          ],
        } as never,
        "characteristica",
      );
    expect(shown({ mean: 0, median: 3, gmean: 4 })).toBe("Age 0 year");
    expect(shown({ mean: null, median: 3, gmean: 4 })).toBe("Age 3 year");
    expect(shown({ mean: null, median: null, gmean: 4 })).toBe("Age 4 year");
    expect(shown({ gmean: null, choice: { name: "Female" }, unit: null })).toBe(
      "Age Female",
    );
    expect(shown({})).toBe("Age Not reported year");
  });
  it("shows dosing schedules and keeps the other statistics apart", () => {
    expect(
      cellText({ time: [0, 12, 40], time_unit: "h" }, "schedule"),
    ).toBe("0, 12, 40 h");
    expect(
      cellText(
        { time: 0, interval: 24, doses: 7, time_unit: "h" },
        "schedule",
      ),
    ).toBe("every 24 h, 7 doses from 0 h");
    expect(cellText({ time: null }, "schedule")).toBe("Not reported");
    expect(cellText({ gsd: 1.5 }, "gsd")).toBe("1.5");
  });
  it("shows actual subset dimensions and units without inferring an absent dimensions field", () => {
    expect(
      cellText(
        {
          array: [
            [
              {
                measurement_type: { name: "Concentration" },
                substance: { name: "Drug" },
                unit: "gram / liter",
                mean: 0,
              },
            ],
          ],
        },
        "dimensions",
      ),
    ).toBe("Concentration Drug [gram / liter]");
  });
  it("does not offer unsupported participant-count sorting", () => {
    expect(validOrder("groups", "count")).toBe(false);
  });
  it("sorts by the statistics of format 2 and no longer by value", () => {
    for (const order of ["mean", "gmean", "-gsd", "gcv", "cv"])
      expect(validOrder("measurements", order)).toBe(true);
    expect(validOrder("interventions", "-mean")).toBe(true);
    expect(validOrder("measurements", "value")).toBe(false);
    expect(validOrder("interventions", "value")).toBe(false);
    expect(validOrder("interventions", "schedule")).toBe(false);
  });
  it("titles the statistic columns consistently", () => {
    const titles = Object.fromEntries(
      columns.measurements.map((column) => [column.key, column.title]),
    );
    expect(titles).toMatchObject({
      mean: "Mean",
      gmean: "Geometric mean",
      gsd: "Geometric SD",
      gcv: "Geometric CV",
    });
    expect(titles.value).toBeUndefined();
    expect(columns.interventions.map((column) => column.key)).toContain(
      "schedule",
    );
  });
});
