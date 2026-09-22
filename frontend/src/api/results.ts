import { api } from "./client";
import { parsePage } from "./contracts";
import type { ResultView, ResultTab } from "../features/search/model";
export const endpoints: Record<ResultTab, string> = {
  studies: "studies",
  groups: "groups",
  individuals: "individuals",
  interventions: "interventions",
  measurements: "outputs",
  timecourses: "subsets",
  scatters: "subsets",
};
export async function fetchRows(
  uuid: string,
  view: ResultView,
  signal: AbortSignal,
) {
  const p = new URLSearchParams({
    uuid,
    page: String(view.page),
    page_size: String(view.pageSize),
  });
  if (view.order) p.set("ordering", view.order);
  if (view.tableSearch) p.set("search_multi_match", view.tableSearch);
  if (view.tab === "timecourses" || view.tab === "scatters")
    p.set("data_type", view.tab === "timecourses" ? "timecourse" : "scatter");
  return parsePage(
    (await api.get<unknown>(`/api/v1/${endpoints[view.tab]}/?${p}`, { signal }))
      .data,
  );
}
