export interface PlotColors {
  surface: string;
  text: string;
  muted: string;
  grid: string;
  primary: string;
}
function channels(color: string): [number, number, number] | undefined {
  const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/iu.exec(color)?.[1];
  if (!hex) return undefined;
  const full =
    hex.length === 3 ? [...hex].map((digit) => digit + digit).join("") : hex;
  const value = Number.parseInt(full, 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}
export function withAlpha(color: string, alpha: number): string {
  const rgb = channels(color);
  return rgb ? `rgba(${rgb.join(", ")}, ${alpha})` : color;
}
// The chart sits on the surface of the page theme with its text and grid, so
// it is as readable in the dark theme as in the light one.
export function plotColors(theme: Record<string, unknown>): PlotColors {
  const color = (name: string, fallback: string) => {
    const value = theme[name];
    return typeof value === "string" ? value : fallback;
  };
  const text = color("on-surface", "#000000");
  return {
    surface: color("surface", "#ffffff"),
    text,
    muted: withAlpha(text, 0.7),
    grid: withAlpha(text, 0.12),
    primary: color("primary", "#176b70"),
  };
}
