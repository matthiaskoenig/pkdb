// Narrow application surface for plotly.js-dist-min 4.1.1, not full library typings.
// https://plotly.com/javascript/plotlyjs-function-reference/
declare module "plotly.js-dist-min" {
  interface Engine {
    react(
      element: HTMLElement,
      data: import("../features/plots/types").Trace[],
      layout: import("../features/plots/types").PlotLayout,
      config: {
        responsive: boolean;
        displaylogo: boolean;
        displayModeBar: boolean;
        modeBarButtonsToRemove: string[];
      },
    ): Promise<unknown>;
    purge(element: HTMLElement): void;
    Plots: { resize(element: HTMLElement): Promise<unknown> };
  }
  const engine: Engine;
  export default engine;
}
