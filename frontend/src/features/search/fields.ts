export type FilterGroup =
  "Studies" | "Subjects" | "Interventions" | "Measurements";
export interface FilterField {
  key: string;
  label: string;
  group: FilterGroup;
  endpoint: string;
  kind?: string;
  idKey: "sid" | "username" | "name";
  help: string;
}
export const fields: readonly FilterField[] = [
  {
    key: "studies__sid__in",
    label: "Studies",
    group: "Studies",
    endpoint: "studies",
    idKey: "sid",
    help: "Choose studies by their stable identifiers.",
  },
  {
    key: "studies__reference_name__in",
    label: "References",
    group: "Studies",
    endpoint: "references",
    idKey: "name",
    help: "Reference names are the identifiers accepted by the current reference filter.",
  },
  {
    key: "studies__creator__in",
    label: "Creators",
    group: "Studies",
    endpoint: "studies",
    idKey: "username",
    help: "Enter an exact username. Suggestions are sampled from visible studies.",
  },
  {
    key: "studies__curators__in",
    label: "Curators",
    group: "Studies",
    endpoint: "studies",
    idKey: "username",
    help: "Enter an exact curator username. Suggestions are sampled from visible studies.",
  },
  {
    key: "subjects__choice_sid__in",
    label: "Subject characteristics",
    group: "Subjects",
    endpoint: "info_nodes",
    kind: "choice",
    idKey: "sid",
    help: "Characteristic choices apply to groups and/or individuals selected below. Choice and type must match the same effective characteristic.",
  },
  {
    key: "subjects__measurement_type_sid__in",
    label: "Characteristic types",
    group: "Subjects",
    endpoint: "info_nodes",
    kind: "measurement_type",
    idKey: "sid",
    help: "Use a characteristic type with a choice to constrain the same effective characteristic row.",
  },
  ...(
    ["substance", "route", "measurement_type", "application", "form"] as const
  ).map((kind) => ({
    key: `interventions__${kind}_sid__in`,
    label: {
      substance: "Intervention substances",
      route: "Routes",
      measurement_type: "Intervention types",
      application: "Applications",
      form: "Dose forms",
    }[kind],
    group: "Interventions" as const,
    endpoint: "info_nodes",
    kind,
    idKey: "sid" as const,
    help: "Conditions within this group apply to the same intervention. Returned related interventions can provide additional context.",
  })),
  ...(["substance", "tissue", "measurement_type", "method"] as const).map(
    (kind) => ({
      key: `outputs__${kind}_sid__in`,
      label: {
        substance: "Measured substances",
        tissue: "Tissues",
        measurement_type: "Measurement types",
        method: "Methods",
      }[kind],
      group: "Measurements" as const,
      endpoint: "info_nodes",
      kind,
      idKey: "sid" as const,
      help: "Conditions select normalized measurements. Timecourse and scatter records can include additional contextual points.",
    }),
  ),
];
export const fieldKeys = new Set(fields.map((field) => field.key));
