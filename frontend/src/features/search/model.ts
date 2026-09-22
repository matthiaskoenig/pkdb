export type Scope = "matching" | "studies";
export const tabs = [
  "studies",
  "groups",
  "individuals",
  "interventions",
  "measurements",
  "timecourses",
  "scatters",
] as const;
export type ResultTab = (typeof tabs)[number];
export interface Criteria {
  filters: Record<string, string[]>;
  subjects: { groups: boolean; individuals: boolean };
  licences: { open: boolean; closed: boolean };
  types: { output: boolean; timecourse: boolean; array: boolean };
  scope: Scope;
}
export interface ResultView {
  tab: ResultTab;
  page: number;
  pageSize: number;
  order: string;
  tableSearch: string;
}
export interface SearchLocation {
  criteria: Criteria;
  view: ResultView;
}
export const tabLabels: Record<ResultTab, string> = {
  studies: "Studies",
  groups: "Groups",
  individuals: "Individuals",
  interventions: "Interventions",
  measurements: "Measurements",
  timecourses: "Timecourses",
  scatters: "Scatter data",
};
export const scopeLabels: Record<Scope, string> = {
  matching: "Matching measurements and related records",
  studies: "All data from qualifying studies",
};
export const scopeHelp: Record<Scope, string> = {
  matching:
    "Measurement constraints select measurements; their related studies, subjects and interventions provide context. Not every related record or plotted point directly matches each filter.",
  studies:
    "Conditions may be satisfied by different records in a study. All data from qualifying studies is included more broadly; returned measurements need not jointly match every filter.",
};
