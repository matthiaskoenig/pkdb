import { describe, expect, it } from "vitest";
import { INFO_THEMES } from "../../src/study-views/info";
import { CURATION_THEMES } from "../../src/curation-app/themes";
import { makeVuetify } from "../../src/plugins/vuetify";

type Rgb = [number, number, number];

/** The channels of `#rrggbb` or `#rgb`. */
function rgb(color: unknown): Rgb {
  const short = String(color).replace("#", "");
  const hex = short.length === 3 ? [...short].map((digit) => digit + digit).join("") : short;
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

/** `color` at `share` over `base`, as a tint or a translucent layer paints. */
function mix(color: Rgb, share: number, base: Rgb): Rgb {
  return color.map((value, index) => value * share + base[index]! * (1 - share)) as Rgb;
}

const themes = makeVuetify({ themes: CURATION_THEMES }).theme.computedThemes.value;

describe("the themes of the curation app", () => {
  it("keep the colors and tints of the classes of information", () => {
    for (const name of ["light", "dark"] as const) {
      expect(themes[name]!.colors).toMatchObject(INFO_THEMES[name].colors);
      expect(themes[name]!.variables).toMatchObject(INFO_THEMES[name].variables);
    }
  });

  it("add the amber of the app and its tint, in the dark theme a tint of 12 % over the page", () => {
    expect([themes.light!.colors.caution, themes.light!.colors["caution-tint"]]).toEqual(["#8f5300", "#fff4e0"]);
    expect([themes.dark!.colors.caution, themes.dark!.colors["caution-tint"]]).toEqual(["#ffb547", "#2d3027"]);
    const amber = rgb(themes.dark!.colors.caution);
    const page = rgb(themes.dark!.colors.background);
    const tint = amber.map((value, index) => Math.round(value * 0.12 + page[index]! * 0.88));
    expect(rgb(themes.dark!.colors["caution-tint"])).toEqual(tint);
  });

  it.each(["light", "dark"] as const)("keep 4.5:1 for the amber text on its tint, and 3:1 for amber marks, in the %s theme", (name) => {
    const { colors } = themes[name]!;
    const amber = rgb(colors.caution);
    expect(contrast(amber, rgb(colors["caution-tint"]))).toBeGreaterThanOrEqual(4.5);
    // The border of the banner on the page, the warnings of the navigator and the grid on the surface.
    expect(contrast(amber, rgb(colors.background))).toBeGreaterThanOrEqual(3);
    expect(contrast(amber, rgb(colors.surface))).toBeGreaterThanOrEqual(3);
    // Undo, a text button in the primary color.
    expect(contrast(rgb(colors.primary), rgb(colors["caution-tint"]))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(["light", "dark"] as const)(
    "keep 4.5:1 for the text of medium emphasis of the banner without unsaved changes, and for its shortcut, in the %s theme",
    (name) => {
      const { colors, variables } = themes[name]!;
      const opacity = Number(variables["medium-emphasis-opacity"]);
      expect(opacity).toBeGreaterThan(0);
      /** The text color on-surface at the medium opacity over `background`. */
      const medium = (background: Rgb) =>
        rgb(colors["on-surface"]).map((value, index) => Math.round(value * opacity + background[index]! * (1 - opacity))) as Rgb;
      // No unsaved changes to study.json, on the surface, and the Ctrl+S hint beside Save.
      const surface = rgb(colors.surface);
      expect(contrast(medium(surface), surface)).toBeGreaterThanOrEqual(4.5);
      // The Ctrl+S hint on the amber tint while there are unsaved changes.
      const tint = rgb(colors["caution-tint"]);
      expect(contrast(medium(tint), tint)).toBeGreaterThanOrEqual(4.5);
    },
  );
});

describe("the app bar and the study band of the curation app", () => {
  it("make the bar the light primary in the light theme and a darker teal in the dark theme, with white text, and leave the website as it is", () => {
    expect(themes.light!.colors["app-bar"]).toBe("#176b70");
    expect(themes.light!.colors["app-bar"]).toBe(themes.light!.colors.primary);
    expect(themes.dark!.colors["app-bar"]).toBe("#13575b");
    for (const name of ["light", "dark"] as const) {
      expect(themes[name]!.colors).toMatchObject({
        "on-app-bar": "#ffffff",
        "app-bar-state": "#000000",
        "app-bar-warning": "#ffd08a",
        "on-app-bar-warning": "#2e1a00",
        "app-bar-error": "#ffb4ab",
        "on-app-bar-error": "#690005",
      });
    }
    // White text would have 1.7:1 on the light teal primary of the dark theme.
    expect(contrast(rgb("#ffffff"), rgb(themes.dark!.colors.primary))).toBeLessThan(2);
    // The website has none of these colors.
    const website = makeVuetify().theme.computedThemes.value;
    expect(website.light!.colors["app-bar"]).toBeUndefined();
    expect(website.dark!.colors["study-band"]).toBeUndefined();
  });

  it.each(["light", "dark"] as const)("keep 4.5:1 for the text and the chips of the bar in the %s theme", (name) => {
    const { colors, variables } = themes[name]!;
    const bar = rgb(colors["app-bar"]);
    const white = rgb(colors["on-app-bar"]);
    // The name, the labels, the icons and the user; the focus ring and the tile of the logo need 3:1.
    expect(contrast(white, bar), "text on the bar").toBeGreaterThanOrEqual(4.5);
    // A state without a warning, and Set user: white text on the white of a tonal chip or button.
    const tonal = mix(white, Number(variables["activated-opacity"]), bar);
    expect(contrast(white, tonal), "translucent white chip").toBeGreaterThanOrEqual(4.5);
    for (const tone of ["warning", "error"] as const) {
      const tint = rgb(colors[`app-bar-${tone}`]);
      expect(contrast(rgb(colors[`on-app-bar-${tone}`]), tint), `text of the ${tone} chip`).toBeGreaterThanOrEqual(4.5);
      // The chip stands out from the bar, and so does the warning icon of a missing user: 3:1.
      expect(contrast(tint, bar), `${tone} chip on the bar`).toBeGreaterThanOrEqual(3);
    }
  });

  it.each(["light", "dark"] as const)(
    "darken the bar under the white text of a hovered, focused or open button in the %s theme, so that it keeps its contrast at rest",
    (name) => {
      const { colors, variables } = themes[name]!;
      const bar = rgb(colors["app-bar"]);
      const white = rgb(colors["on-app-bar"]);
      const state = rgb(colors["app-bar-state"]);
      const activated = Number(variables["activated-opacity"]);
      const rest = contrast(white, mix(white, activated, bar));
      // Twice Vuetify's opacities (styles.css): hovered, focused or open, and open while hovered or focused.
      const layers = [variables["hover-opacity"], variables["focus-opacity"], variables["activated-opacity"]]
        .map((opacity) => Number(opacity))
        .flatMap((opacity) => [2 * opacity, 2 * (opacity + activated)]);
      for (const layer of layers) {
        const under = mix(state, layer, bar);
        expect(contrast(white, under), `text over a layer of ${layer}`).toBeGreaterThanOrEqual(contrast(white, bar));
        expect(contrast(white, mix(white, activated, under)), `chip over a layer of ${layer}`).toBeGreaterThanOrEqual(rest);
      }
    },
  );

  it("tint the study band with the primary at 8 % over the surface of each theme", () => {
    for (const name of ["light", "dark"] as const) {
      const { colors } = themes[name]!;
      const band = mix(rgb(colors.primary), 0.08, rgb(colors.surface)).map((value) => Math.round(value));
      expect(rgb(colors["study-band"])).toEqual(band);
      expect(colors["study-band"]).not.toBe(colors.surface);
      expect(colors["study-band"]).not.toBe(colors.background);
    }
    expect([themes.light!.colors["study-band"], themes.dark!.colors["study-band"]]).toEqual(["#ecf3f4", "#21393e"]);
  });

  it.each(["light", "dark"] as const)("keep 4.5:1 for the text and the controls on the study band in the %s theme", (name) => {
    const { colors, variables } = themes[name]!;
    const band = rgb(colors["study-band"]);
    const text = rgb(colors["on-surface"]);
    const primary = rgb(colors.primary);
    const activated = Number(variables["activated-opacity"]);
    expect(contrast(mix(text, Number(variables["high-emphasis-opacity"]), band), band), "text").toBeGreaterThanOrEqual(4.5);
    // The label Review, the dot after the title, the facts at the end of the tab line.
    expect(contrast(mix(text, Number(variables["medium-emphasis-opacity"]), band), band), "medium text").toBeGreaterThanOrEqual(4.5);
    // Open tables and Validate: primary text on a tonal button; the PMID link; the line under the active tab.
    expect(contrast(primary, mix(primary, activated, band)), "tonal button").toBeGreaterThanOrEqual(4.5);
    expect(contrast(primary, band), "link").toBeGreaterThanOrEqual(4.5);
    // The chips of the release, the sync status and the problems: the text of the surface on their tint,
    // a stronger one for errors in the dark theme (styles.css).
    for (const tone of ["success", "info", "warning", "error"] as const) {
      const opacity = name === "dark" && tone === "error" ? 0.24 : activated;
      expect(contrast(text, mix(rgb(colors[tone]), opacity, band)), `${tone} chip`).toBeGreaterThanOrEqual(4.5);
    }
  });
});
