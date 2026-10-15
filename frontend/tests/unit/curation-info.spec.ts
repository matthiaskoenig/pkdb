import { describe, expect, it } from "vitest";
import { INFO_CLASSES, INFO_HEADINGS, INFO_THEMES, infoColor, infoOutlined, infoStyle } from "../../src/curation-app/info";
import type { InfoClass } from "../../src/curation-app/api/types";
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

/** The color difference of two colors, the distance in CIELAB (CIE76); about 2.3 is the smallest difference that the eye sees. */
function deltaE(first: Rgb, second: Rgb): number {
  const lab = (color: Rgb) => {
    const [red, green, blue] = color.map((value) => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
    const f = (value: number) => (value > 0.008856 ? Math.cbrt(value) : 7.787 * value + 16 / 116);
    const x = f((0.4124 * red! + 0.3576 * green! + 0.1805 * blue!) / 0.95047);
    const y = f(0.2126 * red! + 0.7152 * green! + 0.0722 * blue!);
    const z = f((0.0193 * red! + 0.1192 * green! + 0.9505 * blue!) / 1.08883);
    return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
  };
  const [a, b] = [lab(first), lab(second)];
  return Math.hypot(a[0]! - b[0]!, a[1]! - b[1]!, a[2]! - b[2]!);
}

const percent = (value: string | number | undefined) => Number.parseFloat(String(value)) / 100;
const themes = makeVuetify({ themes: INFO_THEMES }).theme.computedThemes.value;

/** The theme variables of the tints of the header and the cells of a column of each class; the raw extractions have none. */
const TINTS: Partial<Record<InfoClass, [string, string]>> = {
  subjects: ["info-head-tint", "info-cell-tint"],
  interventions: ["info-head-tint", "info-cell-tint"],
  data: ["info-data-head-tint", "info-data-cell-tint"],
};

describe("colors of the classes of information", () => {
  it("names the theme color of each class in one place, and outlines only the raw extractions", () => {
    expect(INFO_CLASSES.map(infoColor)).toEqual(["info-subjects", "info-interventions", "info-data", "info-raw"]);
    expect(INFO_CLASSES.map((info) => INFO_HEADINGS[info])).toEqual(["Subjects", "Interventions", "Data", "Raw extractions"]);
    expect(infoStyle("data")).toEqual({ "--info": "var(--v-theme-info-data)" });
    expect(INFO_CLASSES.filter(infoOutlined)).toEqual(["raw"]);
  });

  it("adds the colors and the tints to the light and the dark theme: the data in a neutral grey", () => {
    const colors = (name: "light" | "dark") => INFO_CLASSES.map((info) => themes[name]!.colors[infoColor(info)]);
    expect(colors("light")).toEqual(["#1d5fb8", "#2e7d32", "#616161", "#5f6b6d"]);
    expect(colors("dark")).toEqual(["#8ab4f8", "#81c995", "#a8a8a8", "#aab6b8"]);
    const tints = (name: "light" | "dark") =>
      ["info-head-tint", "info-cell-tint", "info-data-head-tint", "info-data-cell-tint"].map(
        (variable) => themes[name]!.variables[variable],
      );
    expect(tints("light")).toEqual(["16%", "6%", "22%", "12%"]);
    expect(tints("dark")).toEqual(["20%", "7%", "26%", "17%"]);
  });

  it.each(["light", "dark"] as const)("keeps 4.5:1 for the text on every tint of the %s theme", (name) => {
    const { colors, variables } = themes[name]!;
    const surface = rgb(colors.surface!);
    const onSurface = rgb(colors["on-surface"]!);
    const high = Number(variables["high-emphasis-opacity"]);
    const medium = Number(variables["medium-emphasis-opacity"]);
    // `study`, `source` and the line numbers: the medium emphasis on the surface, without a tint.
    expect(contrast(mix(onSurface, medium, surface), surface), "muted text").toBeGreaterThanOrEqual(4.5);
    for (const info of INFO_CLASSES) {
      const color = rgb(colors[infoColor(info)]!);
      // A tonal chip lays its color at the activated opacity under text in the surface's text color.
      const chip = mix(color, Number(variables["activated-opacity"]), surface);
      expect(contrast(onSurface, chip), `chip text of ${info}`).toBeGreaterThanOrEqual(4.5);
      // The bar of the navigator, and the outline of a raw extraction, are no text: 3:1 against the surface.
      expect(contrast(color, surface), `bar of ${info}`).toBeGreaterThanOrEqual(3);
      const tint = TINTS[info];
      if (!tint) continue;
      const head = mix(color, percent(variables[tint[0]]), surface);
      const cell = mix(color, percent(variables[tint[1]]), surface);
      // The header row, and a hovered row, which takes the tint of the header.
      expect(contrast(mix(onSurface, high, head), head), `header text of ${info}`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(mix(onSurface, high, cell), cell), `cell text of ${info}`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it.each(["light", "dark"] as const)("tints the data cells apart from the page of the %s theme, more than the surface stands apart", (name) => {
    const { colors, variables } = themes[name]!;
    const surface = rgb(colors.surface!);
    const page = rgb(colors.background!);
    const cell = mix(rgb(colors["info-data"]!), percent(variables["info-data-cell-tint"]), surface);
    expect(contrast(cell, page)).toBeGreaterThan(contrast(surface, page));
  });

  it.each([
    ["light", 4],
    ["dark", 6],
  ] as const)("keeps the data cells of the %s theme clearly apart from the subjects and interventions cells (dE of %d at least)", (name, minimum) => {
    const { colors, variables } = themes[name]!;
    const surface = rgb(colors.surface!);
    const cell = (info: "subjects" | "interventions" | "data") =>
      mix(rgb(colors[infoColor(info)]!), percent(variables[info === "data" ? "info-data-cell-tint" : "info-cell-tint"]), surface);
    expect(deltaE(cell("data"), cell("subjects"))).toBeGreaterThanOrEqual(minimum);
    expect(deltaE(cell("data"), cell("interventions"))).toBeGreaterThanOrEqual(minimum);
  });
});
