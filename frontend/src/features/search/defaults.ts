import type { Criteria, ResultView } from "./model";
export function defaultCriteria(): Criteria {
  return {
    filters: {},
    subjects: { groups: true, individuals: true },
    licences: { open: true, closed: true },
    types: { output: true, timecourse: true, array: true },
    scope: "matching",
  };
}
export function defaultView(): ResultView {
  return { tab: "studies", page: 1, pageSize: 20, order: "", tableSearch: "" };
}
export function cloneCriteria(value: Criteria): Criteria {
  return {
    ...value,
    filters: Object.fromEntries(
      Object.entries(value.filters).map(([k, v]) => [k, [...v]]),
    ),
    subjects: { ...value.subjects },
    licences: { ...value.licences },
    types: { ...value.types },
  };
}
