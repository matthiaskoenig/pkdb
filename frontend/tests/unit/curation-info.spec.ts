import { describe, expect, it } from "vitest";
import { INFO_CLASSES, INFO_HEADINGS, INFO_THEMES, infoColor, infoStyle } from "../../src/curation-app/info";
import { makeVuetify } from "../../src/plugins/vuetify";

type Rgb = [number, number, number];

/** The channels of `#rgb` or `#rrggbb`. */
function rgb(color: unknown): Rgb {
  const hex = String(color).replace("#", "");
  const full = hex.length === 3 ? [...hex].map((digit) => digit + digit).join("") : hex;
  return [0, 2, 4].map((start) => Number.parseInt(full.slice(start, start + 2), 16)) as Rgb;
}

/** `color` at `share` over `base`, as a tint or a translucent text paints. */
function mix(color: Rgb, share: number, base: Rgb): Rgb {
  return color.map((value, index) => value * share + base[index]! * (1 - share)) as Rgb;
}

function luminance(color: Rgb): number {
  const [red, green, blue] = color.map((value) => {
    const channel = value / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * red! + 0.7152 * green! + 0.0722 * blue!;
}

/** The contrast ratio of two colors (WCAG 2). */
function contrast(first: Rgb, second: Rgb): number {
  const [light, dark] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (light! + 0.05) / (dark! + 0.05);
}

const percent = (value: string | number | undefined) => Number.parseFloat(String(value)) / 100;
const themes = makeVuetify({ themes: INFO_THEMES }).theme.computedThemes.value;

describe("colors of the classes of information", () => {
  it("names the theme color of each class in one place", () => {
    expect(INFO_CLASSES.map(infoColor)).toEqual(["info-subjects", "info-interventions", "info-data", "info-raw"]);
    expect(INFO_CLASSES.map((info) => INFO_HEADINGS[info])).toEqual(["Subjects", "Interventions", "Data", "Raw extractions"]);
    expect(infoStyle("data")).toEqual({ "--info": "var(--v-theme-info-data)" });
  });

  it("adds the colors and the tints to the light and the dark theme", () => {
    const colors = (name: "light" | "dark") => INFO_CLASSES.map((info) => themes[name]!.colors[infoColor(info)]);
    expect(colors("light")).toEqual(["#1d5fb8", "#2e7d32", "#6a3fb5", "#5f6b6d"]);
    expect(colors("dark")).toEqual(["#8ab4f8", "#81c995", "#c5a5f5", "#aab6b8"]);
    const tints = (name: "light" | "dark") => [themes[name]!.variables["info-head-tint"], themes[name]!.variables["info-cell-tint"]];
    expect(tints("light")).toEqual(["16%", "6%"]);
    expect(tints("dark")).toEqual(["20%", "7%"]);
  });

  it.each(["light", "dark"] as const)("keeps 4.5:1 for the text on every tint of the %s theme", (name) => {
    const { colors, variables } = themes[name]!;
    const surface = rgb(colors.surface!);
    const onSurface = rgb(colors["on-surface"]!);
    const high = Number(variables["high-emphasis-opacity"]);
    const medium = Number(variables["medium-emphasis-opacity"]);
    for (const info of INFO_CLASSES) {
      const color = rgb(colors[infoColor(info)]!);
      // A tonal chip lays its color at the activated opacity under text in the surface's text color.
      const chip = mix(color, Number(variables["activated-opacity"]), surface);
      const head = mix(color, percent(variables["info-head-tint"]), surface);
      const cell = mix(color, percent(variables["info-cell-tint"]), surface);
      expect(contrast(onSurface, chip), `chip text of ${info}`).toBeGreaterThanOrEqual(4.5);
      // The header row, and a hovered row, which takes the tint of the header.
      expect(contrast(mix(onSurface, high, head), head), `header text of ${info}`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(mix(onSurface, high, cell), cell), `cell text of ${info}`).toBeGreaterThanOrEqual(4.5);
      // The line numbers are in the medium emphasis.
      expect(contrast(mix(onSurface, medium, cell), cell), `line numbers of ${info}`).toBeGreaterThanOrEqual(4.5);
      // The bar of the navigator is no text: 3:1 against the surface.
      expect(contrast(color, surface), `bar of ${info}`).toBeGreaterThanOrEqual(3);
    }
  });
});
