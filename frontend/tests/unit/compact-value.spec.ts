import { describe, expect, it } from "vitest";
import { compactValue } from "../../src/features/results/statistics";

const nb = " ";
describe("compact statistic with its spread", () => {
  it("shows a mean with its SD, else its SE, else its CV", () => {
    expect(compactValue({ mean: 2.5, sd: 0.5 })).toBe(
      `2.5${nb}±${nb}0.5${nb}(SD)`,
    );
    expect(compactValue({ mean: 2.5, sd: 0.5, se: 0.25, cv: 0.2 })).toBe(
      `2.5${nb}±${nb}0.5${nb}(SD)`,
    );
    expect(compactValue({ mean: 2.5, se: 0.25 })).toBe(
      `2.5${nb}±${nb}0.25${nb}(SE)`,
    );
    expect(compactValue({ mean: 2.5, cv: 0.226 })).toBe(
      `2.5${nb}(CV${nb}22.6${nb}%)`,
    );
    expect(compactValue({ mean: 0 })).toBe("0");
  });
  it("shows a geometric mean with its GSD as a factor, else its GCV", () => {
    expect(compactValue({ gmean: 2.7, gsd: 1.3 })).toBe(
      `2.7${nb}×/÷${nb}1.3${nb}(GSD)`,
    );
    expect(compactValue({ gmean: 2.7, gsd: 1.3, gcv: 0.3 })).toBe(
      `2.7${nb}×/÷${nb}1.3${nb}(GSD)`,
    );
    expect(compactValue({ gmean: 2.7, gcv: 0.2259 })).toBe(
      `geometric mean 2.7${nb}(GCV${nb}22.59${nb}%)`,
    );
    expect(compactValue({ gmean: 2.7 })).toBe("geometric mean 2.7");
  });
  it("shows a median with its range", () => {
    expect(compactValue({ median: 2.8, min: 1.9, max: 4.1 })).toBe(
      "median 2.8 [1.9-4.1]",
    );
    expect(compactValue({ median: 2.8 })).toBe("median 2.8");
    expect(compactValue({ mean: 2, min: -1.5, max: 4 })).toBe("2 [-1.5 to 4]");
    expect(compactValue({ minimum: 1, maximum: 3 })).toBe("[1-3]");
  });
  it("prefers the mean over the median over the geometric mean", () => {
    expect(compactValue({ mean: 1, median: 2, gmean: 3 })).toBe("1");
    expect(compactValue({ median: 2, gmean: 3 })).toBe("median 2");
  });
  it("rounds to four significant digits and shows a choice or a dash", () => {
    expect(compactValue({ mean: 0.009000000000000001, sd: 0.001 })).toBe(
      `0.009${nb}±${nb}0.001${nb}(SD)`,
    );
    expect(compactValue({ choice: { name: "female" } })).toBe("female");
    expect(compactValue({ choice: "Y" })).toBe("Y");
    expect(compactValue({ mean: null, median: null, choice: null })).toBe("-");
    expect(compactValue({})).toBe("-");
  });
});
