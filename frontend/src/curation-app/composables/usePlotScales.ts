import { computed, ref, toValue, type ComputedRef, type MaybeRefOrGetter } from "vue";
import type { Axis, AxisScale, AxisScales, SourceView } from "../../study-views/types";
import { digitizedScales, LINEAR_SCALES } from "../../study-views/overlay";
import { useOverviewStore } from "../stores/overview";

/** The figure of the plot scales of the local server: `caffeine/Demo2020/Fig1`. */
export function plotFigure(study: string, source: string): string {
  return `${study}/${source}`;
}

export interface UsePlotScales {
  /** The scales of the plot: the choice of the curator, else the digitization's, else linear. */
  scales: ComputedRef<AxisScales>;
  /** Choose the scale of an axis of the figure; the local server keeps both scales of the figure. */
  choose(axis: Axis, scale: AxisScale): void;
}

/**
 * The scales of the plot of the figure `view` of `study`, and the choice of the curator. The
 * local server keeps the choices with its settings (`plot_scales` of its state), like the theme,
 * as the browser forgets what it stores whenever `pkdb curate` starts on a new port.
 */
export function usePlotScales(
  study: MaybeRefOrGetter<string>,
  view: MaybeRefOrGetter<SourceView | null>,
): UsePlotScales {
  const overview = useOverviewStore();
  /** The choices of this page by figure: they apply at once, and until a reload when the server cannot keep them. */
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
    return chosen.value[name] ?? overview.snapshot?.plot_scales[name] ?? fallback;
  });

  /**
   * The last save: each save waits for the one before, so that the local server keeps the last of
   * two quick choices. A failed save does not stop the next one.
   */
  let saved: Promise<unknown> = Promise.resolve();

  function choose(axis: Axis, scale: AxisScale): void {
    const name = figure.value;
    if (name === null) return;
    const next = { ...scales.value, [axis]: scale };
    chosen.value = { ...chosen.value, [name]: next };
    // The scales apply also when the local server cannot keep them, until the page is reloaded.
    saved = saved.then(() => overview.configure({ plot_scale: { figure: name, ...next } })).catch(() => undefined);
  }

  return { scales, choose };
}
