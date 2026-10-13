/**
 * What the curation app adds to the light and the dark theme of the website: the colors of the
 * classes of information (`info.ts`), and its amber.
 */
import type { ThemeExtension } from "../plugins/vuetify";
import { INFO_THEMES } from "./info";

type ThemeName = "light" | "dark";

/**
 * The amber of the app: `amber` for the warnings of the table grid and the navigator and for the
 * text and the border of the banner of unsaved changes, at least 3:1 on the surface and the page
 * and 4.5:1 on its tint; the theme's warning color is too light for that in the light theme.
 * `amber-tint` is the background of the banner. The page scrolls under the banner, so the tint
 * is opaque: in the dark theme the amber at 12 % over the background of the page.
 */
export const AMBER_COLORS: Record<ThemeName, Record<"amber" | "amber-tint", string>> = {
  light: { amber: "#8f5300", "amber-tint": "#fff4e0" },
  dark: { amber: "#ffb547", "amber-tint": "#2d3027" },
};

function theme(name: ThemeName): ThemeExtension {
  const info = INFO_THEMES[name];
  return { colors: { ...info.colors, ...AMBER_COLORS[name] }, variables: info.variables };
}

export const CURATION_THEMES: Record<ThemeName, ThemeExtension> = { light: theme("light"), dark: theme("dark") };
