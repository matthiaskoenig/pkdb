export async function loadPlotly() {
  return (await import("plotly.js-dist-min")).default;
}
