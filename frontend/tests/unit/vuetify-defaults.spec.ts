import { describe, expect, it } from "vitest";
import { COMPACT_DEFAULTS } from "../../src/study-views/density";
import { makeVuetify } from "../../src/plugins/vuetify";

describe("vuetify defaults", () => {
  it("keeps the website defaults and adds the compact ones only when asked", () => {
    const website = makeVuetify().defaults.value;
    expect(website?.VBtn).toEqual({ rounded: "lg", variant: "flat" });
    expect(website?.VTabs).toBeUndefined();
    const curation = makeVuetify({ defaults: COMPACT_DEFAULTS }).defaults.value;
    expect(curation?.VBtn).toEqual({ rounded: "lg", variant: "flat", size: "small" });
    expect(curation?.VSelect).toEqual({ variant: "outlined", density: "compact" });
    expect(curation?.VTabs).toEqual({ density: "compact" });
  });

  it("makes the switches, radios and checkboxes of the curation app compact", () => {
    const website = makeVuetify().defaults.value;
    expect(website?.VSwitch).toBeUndefined();
    expect(website?.VRadioGroup).toBeUndefined();
    const curation = makeVuetify({ defaults: COMPACT_DEFAULTS }).defaults.value;
    expect(curation?.VSwitch).toEqual({ density: "compact", hideDetails: true, size: "x-small" });
    expect(curation?.VRadioGroup).toEqual({ density: "compact" });
    expect(curation?.VRadio).toEqual({ density: "compact" });
    expect(curation?.VCheckboxBtn).toEqual({ density: "compact" });
  });

  it("adds the colors of another app only when asked", () => {
    expect(makeVuetify().theme.computedThemes.value.light!.colors["info-data"]).toBeUndefined();
    const extended = makeVuetify({
      themes: { light: { colors: { "info-data": "#6a3fb5" }, variables: { "info-cell-tint": "6%" } }, dark: { colors: {}, variables: {} } },
    }).theme.computedThemes.value;
    expect(extended.light!.colors["info-data"]).toBe("#6a3fb5");
    expect(extended.light!.colors.primary).toBe("#176b70");
    expect(extended.light!.variables["info-cell-tint"]).toBe("6%");
    expect(extended.dark!.colors.primary).toBe("#79d5d6");
  });
});
