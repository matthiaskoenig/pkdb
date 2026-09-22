import { defaultCriteria } from "./defaults";
import type { Criteria } from "./model";

export interface SearchExample {
  id: string;
  title: string;
  description: string;
  criteria: () => Criteria;
}
export const searchExamples: readonly SearchExample[] = [
  {
    id: "single-study",
    title: "Explore Abernethy1982",
    description:
      "Select study PKDB00198 and include all data from the qualifying study. Availability depends on current data and your access.",
    criteria: () => ({
      ...defaultCriteria(),
      scope: "studies",
      filters: { studies__sid__in: ["PKDB00198"] },
    }),
  },
  {
    id: "midazolam-human",
    title: "Midazolam half-life in human subjects",
    description:
      "Select half-life measurements linked to midazolam interventions and subjects with the Homo sapiens characteristic. Related interventions and plotted context can extend beyond these matches.",
    criteria: () => ({
      ...defaultCriteria(),
      filters: {
        interventions__substance_sid__in: ["midazolam"],
        outputs__measurement_type_sid__in: ["thalf"],
        subjects__choice_sid__in: ["homo-sapiens"],
      },
    }),
  },
  {
    id: "midazolam-healthy",
    title: "Midazolam half-life in healthy subjects",
    description:
      "Select half-life measurements linked to midazolam interventions and subjects marked healthy. This does not also require human subjects: multiple characteristic choices use OR, not AND.",
    criteria: () => ({
      ...defaultCriteria(),
      filters: {
        interventions__substance_sid__in: ["midazolam"],
        outputs__measurement_type_sid__in: ["thalf"],
        subjects__choice_sid__in: ["healthy-yes"],
      },
    }),
  },
];
