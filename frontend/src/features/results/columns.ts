import type { ResultTab } from "../search/model";
export interface Column {
  key: string;
  title: string;
  order?: string;
}
export const columns: Record<ResultTab, Column[]> = {
  studies: [
    { key: "sid", title: "Study", order: "sid" },
    { key: "name", title: "Name", order: "name" },
    { key: "reference", title: "Reference" },
    { key: "provenance", title: "Source" },
    { key: "licence", title: "Licence", order: "licence" },
    { key: "access", title: "Access", order: "access" },
  ],
  groups: [
    { key: "name", title: "Group", order: "name" },
    { key: "count", title: "Participants" },
    { key: "study", title: "Study", order: "study_sid" },
    { key: "characteristica", title: "Characteristics" },
  ],
  individuals: [
    { key: "name", title: "Individual", order: "name" },
    { key: "group", title: "Group" },
    { key: "study", title: "Study", order: "study_sid" },
    { key: "characteristica", title: "Characteristics" },
  ],
  interventions: [
    { key: "name", title: "Intervention", order: "name" },
    { key: "substance", title: "Substance", order: "substance" },
    { key: "value", title: "Value", order: "value" },
    { key: "unit", title: "Unit", order: "unit" },
    { key: "route", title: "Route", order: "route" },
    { key: "study", title: "Study", order: "study_sid" },
  ],
  measurements: [
    {
      key: "measurement_type",
      title: "Measurement",
      order: "measurement_type",
    },
    { key: "substance", title: "Substance", order: "substance" },
    { key: "value", title: "Value", order: "value" },
    { key: "mean", title: "Mean", order: "mean" },
    { key: "median", title: "Median", order: "median" },
    { key: "sd", title: "SD", order: "sd" },
    { key: "se", title: "SE", order: "se" },
    { key: "unit", title: "Unit", order: "unit" },
    { key: "subject", title: "Subject" },
    { key: "interventions", title: "Related interventions" },
    { key: "study", title: "Study", order: "study_sid" },
  ],
  timecourses: [
    { key: "name", title: "Timecourse", order: "name" },
    { key: "study", title: "Study", order: "study_sid" },
    { key: "dimensions", title: "Dimensions" },
  ],
  scatters: [
    { key: "name", title: "Scatter data", order: "name" },
    { key: "study", title: "Study", order: "study_sid" },
    { key: "dimensions", title: "Dimensions" },
  ],
};
export function validOrder(tab: ResultTab, order: string): boolean {
  return (
    order === "" ||
    columns[tab].some((column) => column.order === order.replace(/^-/u, ""))
  );
}
