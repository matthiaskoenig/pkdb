import type { Plugin } from "vite";

/**
 * The order of the cascade layers of both builds, the website and the curation app.
 *
 * A browser orders cascade layers by the first stylesheet that names them. The builds split the
 * styles into several files, and Vite links the files of shared chunks before the file of the
 * entry: on the website the file of VSelect, which names vuetify-components, vuetify-final and
 * vuetify-overrides, came before the main file, which names vuetify-core. Vuetify's reset
 * (`button { font: inherit }`) then won against the sizes of its buttons and chips on every page.
 * Vuetify asks for its order to be declared before any of its stylesheets
 * (https://vuetifyjs.com/en/styles/layers/), so each page declares the order first, in its head.
 *
 * Vuetify's layers and their nested layers, in the order of node_modules/vuetify/lib/styles/main.css
 * (tests/unit/cascade-layers.spec.ts compares them), then the layers of this frontend.
 */
export const CASCADE_LAYERS = [
  "vuetify-core.reset",
  "vuetify-core.base",
  "vuetify-components",
  "vuetify-overrides",
  "vuetify-utilities.theme-base",
  "vuetify-utilities.typography",
  "vuetify-utilities.helpers",
  "vuetify-utilities.theme-background",
  "vuetify-utilities.theme-foreground",
  "vuetify-final.transitions",
  "vuetify-final.trumps",
  // The sizes of the curation app on the study pages of the website (src/study-views/styles.css).
  "website-study-views",
] as const;

/** The layer statement; naming `a.b` declares `a` first, then `b` inside it. */
export const layerOrder = `@layer ${CASCADE_LAYERS.join(", ")};`;

/** Puts the layer statement at the top of the head of every page, before any stylesheet. */
export function cascadeLayers(): Plugin {
  return {
    name: "pkdb-cascade-layers",
    transformIndexHtml: () => [{ tag: "style", children: layerOrder, injectTo: "head-prepend" }],
  };
}
