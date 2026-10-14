import { describe, expect, it } from "vitest";
import { APP_BAR_COLORS, CURATION_THEMES } from "../../src/curation-app/themes";
import { makeVuetify } from "../../src/plugins/vuetify";
import { COMPACT_DEFAULTS } from "../../src/study-views/density";
import { INFO_THEMES } from "../../src/study-views/info";
import { CAUTION_COLORS, STUDY_BAND_COLORS, STUDY_VIEW_THEMES } from "../../src/study-views/themes";

describe("the themes of the study views", () => {
  it("have the colors and tints of the classes of information, the caution colors and the study band, and nothing of the app bar", () => {
    for (const name of ["light", "dark"] as const) {
      expect(STUDY_VIEW_THEMES[name].colors).toEqual({
        ...INFO_THEMES[name].colors,
        ...CAUTION_COLORS[name],
        ...STUDY_BAND_COLORS[name],
      });
      expect(STUDY_VIEW_THEMES[name].variables).toEqual(INFO_THEMES[name].variables);
      expect(Object.keys(STUDY_VIEW_THEMES[name].colors).filter((color) => color.includes("app-bar"))).toEqual([]);
    }
  });

  it("are the themes of the curation app without its app bar", () => {
    for (const name of ["light", "dark"] as const)
      expect(CURATION_THEMES[name].colors).toEqual({ ...STUDY_VIEW_THEMES[name].colors, ...APP_BAR_COLORS[name] });
  });

  it("give a page of the website the colors of the views and the compact sizes when it asks for them", () => {
    const vuetify = makeVuetify({ themes: STUDY_VIEW_THEMES, defaults: COMPACT_DEFAULTS });
    expect(vuetify.theme.computedThemes.value.light!.colors.caution).toBe(CAUTION_COLORS.light.caution);
    expect(vuetify.theme.computedThemes.value.dark!.colors["study-band"]).toBe(STUDY_BAND_COLORS.dark["study-band"]);
    expect(vuetify.defaults.value?.VBtn).toMatchObject({ size: "small" });
  });
});
