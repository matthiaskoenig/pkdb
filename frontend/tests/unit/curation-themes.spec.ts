import { describe, expect, it } from "vitest";
import { INFO_THEMES } from "../../src/curation-app/info";
import { CURATION_THEMES } from "../../src/curation-app/themes";
import { makeVuetify } from "../../src/plugins/vuetify";

type Rgb = [number, number, number];

/** The channels of `#rrggbb`. */
function rgb(color: unknown): Rgb {
  const hex = String(color).replace("#", "");
  return [0, 2, 4].map((start) => Number.parseInt(hex.slice(start, start + 2), 16)) as Rgb;
}

/** The contrast ratio of two colors (WCAG 2). */
function contrast(first: Rgb, second: Rgb): number {
  const luminance = (color: Rgb) => {
    const [red, green, blue] = color.map((value) => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * red! + 0.7152 * green! + 0.0722 * blue!;
  };
  const [light, dark] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (light! + 0.05) / (dark! + 0.05);
}

const themes = makeVuetify({ themes: CURATION_THEMES }).theme.computedThemes.value;

describe("the themes of the curation app", () => {
  it("keep the colors and tints of the classes of information", () => {
    for (const name of ["light", "dark"] as const) {
      expect(themes[name]!.colors).toMatchObject(INFO_THEMES[name].colors);
      expect(themes[name]!.variables).toMatchObject(INFO_THEMES[name].variables);
    }
  });

  it("add the amber of unsaved changes, in the dark theme a tint of 12 % over the page", () => {
    expect([themes.light!.colors.unsaved, themes.light!.colors["unsaved-tint"]]).toEqual(["#8f5300", "#fff4e0"]);
    expect([themes.dark!.colors.unsaved, themes.dark!.colors["unsaved-tint"]]).toEqual(["#ffb547", "#2d3027"]);
    const amber = rgb(themes.dark!.colors.unsaved);
    const page = rgb(themes.dark!.colors.background);
    const tint = amber.map((value, index) => Math.round(value * 0.12 + page[index]! * 0.88));
    expect(rgb(themes.dark!.colors["unsaved-tint"])).toEqual(tint);
  });

  it.each(["light", "dark"] as const)("keep 4.5:1 for the amber text on its tint, and 3:1 for the border, in the %s theme", (name) => {
    const { colors } = themes[name]!;
    const amber = rgb(colors.unsaved);
    expect(contrast(amber, rgb(colors["unsaved-tint"]))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(amber, rgb(colors.background))).toBeGreaterThanOrEqual(3);
    // Undo, a text button in the primary color.
    expect(contrast(rgb(colors.primary), rgb(colors["unsaved-tint"]))).toBeGreaterThanOrEqual(4.5);
  });
});
