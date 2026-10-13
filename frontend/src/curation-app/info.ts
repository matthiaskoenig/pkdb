/**
 * The classes of information of the tables of a study, by which the Data section groups and
 * colors them: the subjects with their characteristica, the interventions, the data of the
 * paper, and the raw extractions of its tables as printed. `infoColor` is the one place that
 * names their theme colors; the rows pane tints its table in them, the navigator marks its
 * tables with them.
 */
import type { InfoClass } from "./api/types";
import type { ThemeExtension } from "../plugins/vuetify";

/** The classes in the order of the navigator. */
export const INFO_CLASSES: readonly InfoClass[] = ["subjects", "interventions", "data", "raw"];

/** The heading of the tables of each class in the navigator and the Table select. */
export const INFO_HEADINGS: Record<InfoClass, string> = {
  subjects: "Subjects",
  interventions: "Interventions",
  data: "Data",
  raw: "Raw extractions",
};

const COLORS: Record<InfoClass, string> = {
  subjects: "info-subjects",
  interventions: "info-interventions",
  data: "info-data",
  raw: "info-raw",
};

/** The theme color of a class, such as `info-data`, for the `color` of a Vuetify component. */
export function infoColor(info: InfoClass): string {
  return COLORS[info];
}

/** The CSS variable `--info`: the RGB of the theme color of a class, which `rgb(var(--info))` paints. */
export function infoStyle(info: InfoClass): Record<string, string> {
  return { "--info": `var(--v-theme-${infoColor(info)})` };
}

type ThemeName = "light" | "dark";

/** Blue, green, violet and grey in each theme. */
const HEX: Record<ThemeName, Record<InfoClass, string>> = {
  light: { subjects: "#1d5fb8", interventions: "#2e7d32", data: "#6a3fb5", raw: "#5f6b6d" },
  dark: { subjects: "#8ab4f8", interventions: "#81c995", data: "#c5a5f5", raw: "#aab6b8" },
};

/** How strongly a table tints its header row and its cells over the surface. */
const TINTS: Record<ThemeName, { head: string; cell: string }> = {
  light: { head: "16%", cell: "6%" },
  dark: { head: "20%", cell: "7%" },
};

function theme(name: ThemeName): ThemeExtension {
  return {
    colors: Object.fromEntries(INFO_CLASSES.map((info) => [infoColor(info), HEX[name][info]])),
    variables: { "info-head-tint": TINTS[name].head, "info-cell-tint": TINTS[name].cell },
  };
}

/**
 * What the curation app adds to the themes of the website: the colors of the classes, and their
 * tints as the CSS variables `--v-info-head-tint` and `--v-info-cell-tint`.
 */
export const INFO_THEMES: Record<ThemeName, ThemeExtension> = { light: theme("light"), dark: theme("dark") };
