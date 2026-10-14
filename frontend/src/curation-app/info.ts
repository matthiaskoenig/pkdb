/**
 * The classes of information of the tables of a study, by which the Data section groups and
 * marks them: the subjects with their characteristica, the interventions, the data of the
 * paper, and the raw extractions of its tables as printed. `infoColor` is the one place that
 * names their theme colors: the rows pane tints the columns of a table by what they name
 * (TableGrid), the navigator marks its tables with them, and `infoOutlined` says which class is
 * marked by an outline because its tables have no tint.
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

/** Whether a class is marked by an outline in its color instead of a fill: the raw extractions, whose tables have no tint. */
export function infoOutlined(info: InfoClass): boolean {
  return info === "raw";
}

type ThemeName = "light" | "dark";

/** Blue, green and two greys in each theme: a neutral grey for the data, a teal grey for the raw extractions. */
const HEX: Record<ThemeName, Record<InfoClass, string>> = {
  light: { subjects: "#1d5fb8", interventions: "#2e7d32", data: "#616161", raw: "#5f6b6d" },
  dark: { subjects: "#8ab4f8", interventions: "#81c995", data: "#a8a8a8", raw: "#aab6b8" },
};

/**
 * How strongly a column tints its header cell and its cells over the surface. The data take
 * their own, stronger tint in the light theme: a neutral grey at 6 % is about the grey of the
 * page (#f5f7f7); at 12 % its cells differ from the page more than the white surface does. The
 * raw extractions have no tint.
 */
const TINTS: Record<ThemeName, Record<"head" | "cell" | "data-head" | "data-cell", string>> = {
  light: { head: "16%", cell: "6%", "data-head": "22%", "data-cell": "12%" },
  dark: { head: "20%", cell: "7%", "data-head": "20%", "data-cell": "7%" },
};

function theme(name: ThemeName): ThemeExtension {
  const tints = TINTS[name];
  return {
    colors: Object.fromEntries(INFO_CLASSES.map((info) => [infoColor(info), HEX[name][info]])),
    variables: {
      "info-head-tint": tints.head,
      "info-cell-tint": tints.cell,
      "info-data-head-tint": tints["data-head"],
      "info-data-cell-tint": tints["data-cell"],
    },
  };
}

/**
 * What the curation app adds to the themes of the website: the colors of the classes, and their
 * tints as the CSS variables `--v-info-head-tint` and `--v-info-cell-tint`, and for the data
 * `--v-info-data-head-tint` and `--v-info-data-cell-tint`.
 */
export const INFO_THEMES: Record<ThemeName, ThemeExtension> = { light: theme("light"), dark: theme("dark") };
