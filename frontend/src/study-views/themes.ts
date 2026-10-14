/**
 * The colors that the study views add to the light and the dark theme of a page: the amber caution
 * color and the tint of the study band. `info.ts` has the colors of the classes of information;
 * `STUDY_VIEW_THEMES` has them all.
 */
import type { ThemeExtension } from "../plugins/vuetify";
import { INFO_THEMES } from "./info";

export type ThemeName = "light" | "dark";

/**
 * The amber of the app: `caution` for the warnings of the table grid and the navigator and for the
 * text and the border of the banner of unsaved changes, at least 3:1 on the surface and the page
 * and 4.5:1 on its tint; the theme's warning color is too light for that in the light theme.
 * `caution-tint` is the background of the banner. The page scrolls under the banner, so the tint
 * is opaque: in the dark theme the amber at 12 % over the background of the page.
 */
export const CAUTION_COLORS: Record<ThemeName, Record<"caution" | "caution-tint", string>> = {
  light: { caution: "#8f5300", "caution-tint": "#fff4e0" },
  dark: { caution: "#ffb547", "caution-tint": "#2d3027" },
};

/**
 * The study band, the header of a study and its tabs: the primary color of the theme at 8 % over
 * its surface, which sets the band apart from the white cards of the section below it.
 */
export const STUDY_BAND_COLORS: Record<ThemeName, Record<"study-band", string>> = {
  light: { "study-band": "#ecf3f4" },
  dark: { "study-band": "#21393e" },
};

function theme(name: ThemeName): ThemeExtension {
  const info = INFO_THEMES[name];
  return {
    colors: { ...info.colors, ...CAUTION_COLORS[name], ...STUDY_BAND_COLORS[name] },
    variables: info.variables,
  };
}

/**
 * What the study views add to the light and the dark theme of a page: the colors of the classes
 * of information with their tints, the amber caution color and the study band. Named colors and
 * variables that change nothing else of the page.
 */
export const STUDY_VIEW_THEMES: Record<ThemeName, ThemeExtension> = { light: theme("light"), dark: theme("dark") };
