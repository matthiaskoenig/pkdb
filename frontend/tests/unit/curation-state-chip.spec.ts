import { describe, expect, it } from "vitest";
import { stateChip } from "../../src/curation-app/stateChip";

describe("stateChip", () => {
  it("is tonal in the color of its state, with the text of the surface, off the app bar", () => {
    expect(stateChip("success", false)).toEqual({ color: "success", variant: "tonal", class: "status-chip" });
    expect(stateChip("error", false)).toEqual({ color: "error", variant: "tonal", class: "status-chip" });
    expect(stateChip(undefined, false)).toEqual({ color: undefined, variant: "tonal", class: "status-chip" });
  });

  it("shows a warning or an error on the app bar in the light amber or red of the bar", () => {
    expect(stateChip("warning", true)).toEqual({ color: "app-bar-warning", variant: "flat", class: "bar-chip" });
    expect(stateChip("error", true)).toEqual({ color: "app-bar-error", variant: "flat", class: "bar-chip" });
  });

  it("shows every other state on the app bar, and the last known one of a server that does not answer, in translucent white", () => {
    for (const tone of ["success", "info", undefined] as const)
      expect(stateChip(tone, true)).toEqual({ color: undefined, variant: "tonal", class: "bar-chip" });
  });
});
