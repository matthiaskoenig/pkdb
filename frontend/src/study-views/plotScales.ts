/**
 * The scales of the plot of a figure and the reader's choice of them: the choice, else the choice
 * that the page kept (the curation app keeps them in the settings of its local server), else the
 * scales of the digitization, else linear.
 */
import { computed, ref, toValue, type ComputedRef, type MaybeRefOrGetter } from "vue";
import { digitizedScales, LINEAR_SCALES } from "./overlay";
import type { Axis, AxisScale, AxisScales, SourceView } from "./types";

/** The figure of the plot scales: `caffeine/Demo2020/Fig1`. */
export function plotFigure(study: string, source: string): string {
  return `${study}/${source}`;
}

export interface PlotScales {
  /** The scales of the plot: the choice of the reader, else the kept choice, else the digitization's, else linear. */
  scales: ComputedRef<AxisScales>;
  /** Choose the scale of an axis of the figure. */
  choose(axis: Axis, scale: AxisScale): void;
}

/** Where a page keeps the choices by figure beyond the page. */
export interface PlotScaleStore {
  kept(figure: string): AxisScales | undefined;
  keep(figure: string, scales: AxisScales): Promise<unknown>;
}

/**
 * The scales of the plot of the figure `view` of `study`. A choice applies at once and lasts for
 * the page; with a `store`, the store keeps it too, one choice after the other, so that it keeps
 * the last of two quick choices, and a choice that it cannot keep still applies.
 */
export function usePlotScaleChoice(
  study: MaybeRefOrGetter<string>,
  view: MaybeRefOrGetter<SourceView | null>,
  store: PlotScaleStore | null = null,
): PlotScales {
  const chosen = ref<Record<string, AxisScales>>({});
  const figure = computed(() => {
    const identity = toValue(study);
    const source = toValue(view)?.source;
    return identity && source ? plotFigure(identity, source) : null;
  });
  const scales = computed<AxisScales>(() => {
    const current = toValue(view);
    const fallback = current ? digitizedScales(current) : LINEAR_SCALES;
    const name = figure.value;
    if (name === null) return fallback;
    return chosen.value[name] ?? store?.kept(name) ?? fallback;
  });
  let saved: Promise<unknown> = Promise.resolve();

  function choose(axis: Axis, scale: AxisScale): void {
    const name = figure.value;
    if (name === null) return;
    const next = { ...scales.value, [axis]: scale };
    chosen.value = { ...chosen.value, [name]: next };
    if (store) saved = saved.then(() => store.keep(name, next)).catch(() => undefined);
  }

  return { scales, choose };
}
