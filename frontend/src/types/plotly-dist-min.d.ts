// Narrow application surface for plotly.js-dist-min 4.1.1, not full library typings.
// https://plotly.com/javascript/plotlyjs-function-reference/
declare module "plotly.js-dist-min" {
  /** A point of a plotly_click or plotly_hover event: its customdata and its position in data units. */
  interface PlotEventPoint {
    customdata?: unknown;
    x?: unknown;
    y?: unknown;
  }
  /** The element of a plot: Plotly adds its event methods. */
  interface PlotElement extends HTMLElement {
    on(
      event: "plotly_click" | "plotly_hover" | "plotly_unhover",
      handler: (event: { points: PlotEventPoint[] }) => void,
    ): void;
  }
  interface Engine {
    react(
      element: HTMLElement,
      data:
        | import("../features/plots/types").Trace[]
        | import("../features/home/chart").OverviewTrace[]
        | import("../curation-app/overlay").OverlayTrace[],
      layout:
        | import("../features/plots/types").PlotLayout
        | import("../features/home/chart").OverviewLayout
        | import("../curation-app/overlay").OverlayLayout,
      config: {
        responsive: boolean;
        displaylogo: boolean;
        displayModeBar: boolean;
        modeBarButtonsToRemove: string[];
        doubleClick?: false;
        showTips?: boolean;
      },
    ): Promise<PlotElement>;
    purge(element: HTMLElement): void;
    Plots: { resize(element: HTMLElement): Promise<unknown> };
  }
  const engine: Engine;
  export default engine;
}
