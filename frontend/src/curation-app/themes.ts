/**
 * What the curation app adds to the themes of the website: the colors of the study views
 * (`STUDY_VIEW_THEMES`) and of its app bar.
 */
import type { ThemeExtension } from "../plugins/vuetify";
import { STUDY_VIEW_THEMES, type ThemeName } from "../study-views/themes";

type AppBarColor =
  | "app-bar"
  | "on-app-bar"
  | "app-bar-state"
  | "app-bar-warning"
  | "on-app-bar-warning"
  | "app-bar-error"
  | "on-app-bar-error";

/** What the bar shows the same in both themes: its state layers and its warning and error chips. */
const BAR_STATES = {
  "app-bar-state": "#000000",
  "app-bar-warning": "#ffd08a",
  "on-app-bar-warning": "#2e1a00",
  "app-bar-error": "#ffb4ab",
  "on-app-bar-error": "#690005",
} as const;

/**
 * The app bar: teal with white text and icons (`on-app-bar`, also its focus ring and the tile of
 * the logo). In the light theme it is the primary color, 6.2:1 for white text; the primary of the
 * dark theme is a light teal (1.7:1), so the dark bar is a darker teal of the same hue, 8.3:1.
 * `app-bar-state` darkens a hovered, focused or open button of the bar under its text
 * (styles.css). A warning or an error on the bar is a chip in a light amber or red with dark text:
 * the warning and error colors of the themes have too little contrast on teal (stateChip.ts).
 */
export const APP_BAR_COLORS: Record<ThemeName, Record<AppBarColor, string>> = {
  light: { "app-bar": "#176b70", "on-app-bar": "#ffffff", ...BAR_STATES },
  dark: { "app-bar": "#13575b", "on-app-bar": "#ffffff", ...BAR_STATES },
};

function theme(name: ThemeName): ThemeExtension {
  const views = STUDY_VIEW_THEMES[name];
  return { colors: { ...views.colors, ...APP_BAR_COLORS[name] }, variables: views.variables };
}

export const CURATION_THEMES: Record<ThemeName, ThemeExtension> = { light: theme("light"), dark: theme("dark") };
