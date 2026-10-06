import type { ResultTab } from "../search/model";
export interface Column {
  key: string;
  title: string;
  order?: string;
  // A value that reads as one unit, such as `2.5 ± 0.5 (SD)`, stays on one line.
  nowrap?: boolean;
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
    { key: "unit", title: "Unit", order: "unit" },
    { key: "statistics", title: "Value", order: "mean", nowrap: true },
    { key: "route", title: "Route", order: "route" },
    { key: "schedule", title: "Schedule" },
    { key: "study", title: "Study", order: "study_sid" },
  ],
  measurements: [
    {
      key: "measurement_type",
      title: "Measurement",
      order: "measurement_type",
    },
    { key: "substance", title: "Substance", order: "substance" },
    { key: "unit", title: "Unit", order: "unit" },
    { key: "statistics", title: "Value", order: "mean", nowrap: true },
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
