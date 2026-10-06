import { describe, it, expect } from "vitest";
import { cellText } from "../../src/features/results/cells";
import type { ApiRecord } from "../../src/api/contracts";
import { columns, validOrder } from "../../src/features/results/columns";
describe("scientific result cells", () => {
  it("labels all acquisition types and their source", () => {
    expect(cellText({ provenance: { kind: "data_import", source_key: "osp.observed-data", release: "v1.9" } }, "provenance")).toBe("Automatic import · osp.observed-data · v1.9");
    expect(cellText({ provenance: { kind: "manual_curation", source_key: "pkdb.manual" } }, "provenance")).toBe("Manual curation · pkdb.manual");
    expect(cellText({ provenance: { kind: "automatic_curation", source_key: "pipeline" } }, "provenance")).toBe("Automatic curation · pipeline");
    expect(cellText({}, "provenance")).toBe("-");
  });
  it("shows one dash for every empty cell of every table", () => {
    const gaps: ApiRecord = {
      pk: 3,
      name: "D3",
      substance: null,
      route: null,
      unit: null,
      mean: null,
      interventions: [],
      group: null,
      study: null,
      provenance: null,
      array: [],
      characteristica: [],
      reference: null,
    };
    expect(
      columns.interventions.map((column) => cellText(gaps, column.key)),
    ).toEqual(["D3", "-", "-", "-", "-", "-", "-"]);
    for (const tab of Object.keys(columns) as (keyof typeof columns)[])
      for (const column of columns[tab])
        if (column.key !== "name")
          expect(cellText(gaps, column.key)).not.toContain("Not reported");
    expect(cellText(gaps, "interventions")).toBe("-");
    expect(cellText(gaps, "subject")).toBe("-");
    expect(cellText(gaps, "dimensions")).toBe("-");
    expect(cellText(gaps, "characteristica")).toBe("-");
  });
  it("keeps a measured zero and shows a missing statistic as a dash", () => {
    expect(cellText({ mean: 0 }, "statistics")).toBe("0");
    expect(cellText({ mean: null }, "statistics")).toBe("-");
    expect(cellText({ unit: null }, "unit")).toBe("-");
    expect(cellText({ unit: "mg/l" }, "unit")).toBe("mg/l");
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
  it("shows the value of a row with its spread in one cell", () => {
    const nb = "\u00a0";
    expect(cellText({ mean: 2.5, sd: 0.5, unit: "mg" }, "statistics")).toBe(
      `2.5${nb}±${nb}0.5${nb}(SD)`,
    );
    expect(cellText({ gmean: 2.7, gsd: 1.3 }, "statistics")).toBe(
      `2.7${nb}×/÷${nb}1.3${nb}(GSD)`,
    );
    expect(cellText({ median: 2.8, min: 1.9, max: 4.1 }, "statistics")).toBe(
      "median 2.8 [1.9-4.1]",
    );
    expect(cellText({ mean: 0.009000000000000001 }, "statistics")).toBe(
      "0.009",
    );
  });
  it("names a study format 2 study by its identifier and a format 1 study by its name", () => {
    expect(
      cellText(
        { study: { sid: "caffeine/Harder1988", name: "Harder1988" } },
        "study",
      ),
    ).toBe("caffeine/Harder1988");
    expect(cellText({ study_sid: "caffeine/Harder1988" }, "study")).toBe(
      "caffeine/Harder1988",
    );
    expect(
      cellText({ study: { sid: "PKDB00057", name: "Abernethy1982" } }, "study"),
    ).toBe("Abernethy1982");
  });
  it("lists related interventions and a dash when there are none", () => {
    expect(
      cellText({ interventions: [{ name: "D1" }, { name: "D2" }] }, "interventions"),
    ).toBe("D1, D2");
    expect(cellText({ interventions: [] }, "interventions")).toBe("-");
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
    expect(shown({ mean: 30.123456, unit: "year" })).toBe("Age 30.12 year");
    expect(shown({ gmean: null, choice: { name: "Female" }, unit: null })).toBe(
      "Age Female",
    );
    expect(shown({})).toBe("Age -");
  });
  it("shows dosing schedules without breaking a number from its unit", () => {
    expect(
      cellText({ time: [0, 12, 40], time_unit: "h" }, "schedule"),
    ).toBe("0, 12, 40\u00a0h");
    expect(
      cellText(
        { time: 0, interval: 24, doses: 7, time_unit: "h" },
        "schedule",
      ),
    ).toBe("every 24\u00a0h, 7\u00a0doses from 0\u00a0h");
    expect(cellText({ time: null }, "schedule")).toBe("-");
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
  it("sorts the value column by the value of a row and no longer by value", () => {
    expect(validOrder("measurements", "central_value")).toBe(true);
    expect(validOrder("measurements", "-central_value")).toBe(true);
    expect(validOrder("interventions", "-central_value")).toBe(true);
    for (const order of ["value", "mean", "gmean", "gsd", "cv", "statistics"])
      expect(validOrder("measurements", order)).toBe(false);
    expect(validOrder("interventions", "value")).toBe(false);
    expect(validOrder("interventions", "schedule")).toBe(false);
  });
  it("puts the unit before one value column and keeps subject and study last", () => {
    const keys = (tab: "measurements" | "interventions") =>
      columns[tab].map((column) => column.key);
    expect(keys("measurements")).toEqual([
      "measurement_type",
      "substance",
      "unit",
      "statistics",
      "subject",
      "interventions",
      "study",
    ]);
    expect(keys("interventions").slice(0, 4)).toEqual([
      "name",
      "substance",
      "unit",
      "statistics",
    ]);
    expect(keys("interventions")).toContain("schedule");
    const value = columns.measurements.find((c) => c.key === "statistics");
    expect(value).toMatchObject({
      title: "Value",
      order: "central_value",
      nowrap: true,
    });
  });
});
