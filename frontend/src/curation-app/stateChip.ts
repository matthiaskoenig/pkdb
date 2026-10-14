/**
 * The chip of a state in the header, such as File watching: Active or Connection: Offline. On the
 * teal app bar a warning or an error is a flat chip in the light amber or red of the bar with dark
 * text (the theme colors app-bar-warning and app-bar-error, themes.ts), and every other state is
 * a translucent white chip (tonal, without a color) in the white text of the bar: the colors of
 * the states have too little contrast on teal, and the label says the state. Elsewhere, as in the
 * menus and the collapsed header, a chip is tonal in the color of its state, with the text of the
 * surface (status-chip, styles.css).
 */
import type { Tone } from "../study-views/overview";

export interface StateChip {
  /** A theme color for the `color` of a VChip; none for a neutral chip. */
  color: string | undefined;
  variant: "flat" | "tonal";
  class: "status-chip" | "bar-chip";
}

/**
 * The chip of a state of `tone`, on the app bar when `bar`. No tone: a neutral state, or the last
 * known one while the local server does not answer.
 */
export function stateChip(tone: Tone, bar: boolean): StateChip {
  if (!bar) return { color: tone, variant: "tonal", class: "status-chip" };
  if (tone === "warning" || tone === "error") return { color: `app-bar-${tone}`, variant: "flat", class: "bar-chip" };
  return { color: undefined, variant: "tonal", class: "bar-chip" };
}
