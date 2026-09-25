export interface OverviewTrace {
  type: "bar" | "scatter";
  name: string;
  x: (number | string)[];
  y: number[];
  mode?: "lines+markers";
  marker?: { color: string };
}
export interface OverviewLayout {
  autosize: boolean;
  height: number;
  xaxis: { title: { text: string }; type: "linear" | "category"; dtick?: number; tickformat?: string; automargin: boolean };
  yaxis: { title: { text: string }; rangemode: "tozero"; automargin: boolean; dtick?: number };
  margin: { l: number; r: number; t: number; b: number };
  paper_bgcolor: string;
  plot_bgcolor: string;
  font: { color: string };
  barmode: "stack";
  legend: { orientation: "h"; x: number; y: number; yanchor: "top" };
  uirevision: string;
}
