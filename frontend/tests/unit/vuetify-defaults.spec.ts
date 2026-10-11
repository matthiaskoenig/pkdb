import { describe, expect, it } from "vitest";
import { COMPACT_DEFAULTS } from "../../src/curation-app/density";
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
});
