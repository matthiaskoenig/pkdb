import { describe, expect, it } from "vitest";
import { scheduleText } from "../../src/features/details/schedule";

describe("dosing schedules", () => {
  it("lists irregular administration times once with their unit", () => {
    expect(scheduleText({ time: [0, 12, 40], time_unit: "h" })).toBe(
      "0, 12, 40\u00a0h",
    );
    expect(scheduleText({ time: [0.5, 1.5], time_unit: "min" })).toBe(
      "0.5, 1.5\u00a0min",
    );
  });
  it("describes regular schedules by interval, number of doses and start", () => {
    expect(
      scheduleText({ time: 0, interval: 24, doses: 7, time_unit: "h" }),
    ).toBe("every 24\u00a0h, 7\u00a0doses from 0\u00a0h");
    expect(scheduleText({ time: 0, interval: 12, time_unit: "h" })).toBe(
      "every 12\u00a0h from 0\u00a0h",
    );
    expect(scheduleText({ interval: 24, doses: 7, time_unit: "h" })).toBe(
      "every 24\u00a0h, 7\u00a0doses",
    );
    expect(
      scheduleText({ time: 0, interval: 12, doses: 1, time_unit: "h" }),
    ).toBe("every 12\u00a0h, 1\u00a0dose from 0\u00a0h");
    expect(
      scheduleText({ time: 0, interval: 24, time_end: 168, time_unit: "h" }),
    ).toBe("every 24\u00a0h from 0\u00a0h to 168\u00a0h");
  });
  it("describes a continuous administration as a span", () => {
    expect(scheduleText({ time: 0, time_end: 24, time_unit: "h" })).toBe(
      "from 0\u00a0h to 24\u00a0h",
    );
  });
  it("keeps a single administration time and a zero start", () => {
    expect(scheduleText({ time: 0, time_unit: "h" })).toBe("0\u00a0h");
    expect(scheduleText({ time: [2], time_unit: "h" })).toBe("2\u00a0h");
    expect(scheduleText({ time: 0, interval: 24, doses: 3 })).toBe(
      "every 24, 3\u00a0doses from 0",
    );
  });
  it("reports nothing when no schedule is known", () => {
    expect(scheduleText({})).toBeUndefined();
    expect(scheduleText({ time: null, time_unit: "h" })).toBeUndefined();
    expect(scheduleText({ time: [], interval: null })).toBeUndefined();
    expect(scheduleText(null)).toBeUndefined();
    expect(scheduleText("0\u00a0h")).toBeUndefined();
  });
  it("rounds times to four significant digits", () => {
    expect(
      scheduleText({ time: [0.1 + 0.2, 12.000000000000002], time_unit: "h" }),
    ).toBe("0.3, 12\u00a0h");
    expect(
      scheduleText({
        time: 0.30000000000000004,
        interval: 1 / 3,
        doses: 2,
        time_unit: "h",
      }),
    ).toBe("every 0.3333\u00a0h, 2\u00a0doses from 0.3\u00a0h");
  });
});
