import { describe, it, expect } from "vitest";
import { cellText } from "../../src/features/results/cells";
import { validOrder } from "../../src/features/results/columns";
describe("scientific result cells", () => {
  it("distinguishes measured zero, null, precision and characteristic context", () => {
    expect(cellText({ value: 0 }, "value")).toBe("0");
    expect(cellText({ value: null }, "value")).toBe("Not reported");
    expect(cellText({ mean: 0.002125 }, "mean")).toBe("0.002125");
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
});
