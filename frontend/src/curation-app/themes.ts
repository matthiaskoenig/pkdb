/**
 * What the curation app adds to the light and the dark theme of the website: the colors of the
 * classes of information (`info.ts`), and the amber of unsaved changes, which the banner of the
 * draft of study.json shows (`UnsavedBanner.vue`).
 */
import type { ThemeExtension } from "../plugins/vuetify";
import { INFO_THEMES } from "./info";

type ThemeName = "light" | "dark";

/**
 * The amber of unsaved changes: `unsaved` for the text and the border, `unsaved-tint` for the
 * background. The theme's warning color is too light for text in the light theme. The page
 * scrolls under the banner, so the tint is opaque: in the dark theme the amber at 12 % over the
 * background of the page.
 */
export const UNSAVED_COLORS: Record<ThemeName, Record<"unsaved" | "unsaved-tint", string>> = {
  light: { unsaved: "#8f5300", "unsaved-tint": "#fff4e0" },
  dark: { unsaved: "#ffb547", "unsaved-tint": "#2d3027" },
};

function theme(name: ThemeName): ThemeExtension {
  const info = INFO_THEMES[name];
  return { colors: { ...info.colors, ...UNSAVED_COLORS[name] }, variables: info.variables };
}

export const CURATION_THEMES: Record<ThemeName, ThemeExtension> = { light: theme("light"), dark: theme("dark") };
