import { reactive } from "vue";
import { cspNonce } from "./csp";
import { loadPlotly } from "../features/plots/plotly";

/**
 * The style elements that Plotly creates when it is imported, by id: its global rules, and the
 * rules of the map library inside the bundle (plotly.js-dist-min 4.1.1), which the app does not
 * use. The CSP of the local server refuses style elements without its nonce, and Plotly reuses an
 * element that exists: it inserts its rules into the stylesheet of the element with the CSSOM,
 * which the CSP allows.
 */
const PLOTLY_STYLES = ["plotly.js-style-global", "9f215cf04c5486422605d13261cb87401f4e7763b6296af81e98efbc0130da53"];

/**
 * The import of Plotly, shared by the plots of the page. `failed again` is a failure after a
 * retry: Chrome keeps a failed import of a module until the page reloads, so a retry cannot
 * help then. `attempt` counts the retries, which every plot that waits for Plotly follows.
 */
export const plotlyImport = reactive<{ state: "idle" | "loaded" | "failed" | "failed again"; attempt: number }>({
  state: "idle",
  attempt: 0,
});
let retried = false;

/** Draw every plot again, and import Plotly again in every plot that waits for it. */
export function retryPlotly(): void {
  if (plotlyImport.state !== "loaded") retried = true;
  plotlyImport.attempt += 1;
}

/** Import Plotly after creating its style elements with the nonce of the page. */
export async function loadNoncedPlotly(): ReturnType<typeof loadPlotly> {
  const nonce = cspNonce();
  for (const id of PLOTLY_STYLES) {
    if (document.getElementById(id)) continue;
    const style = document.createElement("style");
    style.id = id;
    if (nonce) style.setAttribute("nonce", nonce);
    document.head.append(style);
  }
  try {
    const engine = await loadPlotly();
    plotlyImport.state = "loaded";
    retried = false;
    return engine;
  } catch (caught) {
    plotlyImport.state = retried ? "failed again" : "failed";
    throw caught;
  }
}
