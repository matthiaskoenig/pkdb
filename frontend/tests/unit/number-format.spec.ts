import { describe, expect, it } from "vitest";
import {
  formatNumber,
  formatPercent,
  statisticText,
} from "../../src/features/results/format";

describe("statistic number format", () => {
  it("keeps at most four significant digits without float noise", () => {
    expect(formatNumber(0.009000000000000001)).toBe("0.009");
    expect(formatNumber(0.1111111111111111)).toBe("0.1111");
    expect(formatNumber(0.22595033203145737)).toBe("0.226");
    expect(formatNumber(0.002125)).toBe("0.002125");
    expect(formatNumber(1.60380788)).toBe("1.604");
    expect(formatNumber(123456)).toBe("123500");
    expect(formatNumber(2)).toBe("2");
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(-1.23456)).toBe("-1.235");
    expect(formatNumber(1e-9)).toBe("1e-9");
  });
  it("shows fractions as percent with a sign", () => {
    expect(formatPercent(0.226)).toBe("22.6 %");
    expect(formatPercent(0.22595033203145737)).toBe("22.6 %");
    expect(formatPercent(0.07)).toBe("7 %");
    expect(formatPercent(0)).toBe("0 %");
  });
  it("formats only statistics and keeps identifiers and counts", () => {
    expect(statisticText("mean", 0.009000000000000001)).toBe("0.009");
    expect(statisticText("gsd", 1.60380788)).toBe("1.604");
    expect(statisticText("cv", 0.5)).toBe("50 %");
    expect(statisticText("gcv", 0.4227)).toBe("42.27 %");
    expect(statisticText("time", 0.30000000000000004)).toBe("0.3");
    expect(statisticText("time_end", 24.000000000000004)).toBe("24");
    expect(statisticText("interval", 1 / 3)).toBe("0.3333");
    expect(statisticText("pk", 123456)).toBeUndefined();
    expect(statisticText("count", 12345)).toBeUndefined();
    expect(statisticText("mean", null)).toBeUndefined();
    expect(statisticText("mean", "2")).toBeUndefined();
  });
});
