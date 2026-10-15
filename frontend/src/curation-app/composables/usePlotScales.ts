import type { MaybeRefOrGetter } from "vue";
import { usePlotScaleChoice, type PlotScales } from "../../study-views/plotScales";
import type { SourceView } from "../../study-views/types";
import { useOverviewStore } from "../stores/overview";

/**
 * The scales of the plot of the figure `view` of `study`, and the choice of the curator. The
 * local server keeps the choices with its settings (`plot_scales` of its state), like the theme,
 * as the browser forgets what it stores whenever `pkdb curate` starts on a new port.
 */
export function usePlotScales(study: MaybeRefOrGetter<string>, view: MaybeRefOrGetter<SourceView | null>): PlotScales {
  const overview = useOverviewStore();
  return usePlotScaleChoice(study, view, {
    kept: (figure) => overview.snapshot?.plot_scales[figure],
    keep: (figure, scales) => overview.configure({ plot_scale: { figure, ...scales } }),
  });
}
