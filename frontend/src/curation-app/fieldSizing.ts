/**
 * Whether the browser sizes text areas by their content (CSS `field-sizing`). Where it does not,
 * such as Firefox today, text areas grow with Vuetify's `auto-grow`, which measures them instead.
 */
export function sizesFieldsByContent(): boolean {
  return typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
}

/** The most rows that a growing text area takes before it scrolls. */
export const GROW_ROWS = 10;
