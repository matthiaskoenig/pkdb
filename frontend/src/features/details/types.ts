export type DetailRecord = Record<string, unknown>;

export function isRecord(value: unknown): value is DetailRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function record(value: unknown): DetailRecord {
  if (!isRecord(value))
    throw new Error("The server returned an invalid detail record.");
  return value;
}

export function records(value: unknown): DetailRecord[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

export function text(value: unknown): string {
  if (value === null || value === undefined || value === "")
    return "Not reported";
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (isRecord(value))
    return text(value.label ?? value.name ?? value.sid ?? value.pk);
  return "Not reported";
}

export function label(key: string): string {
  const labels: Record<string, string> = {
    pk: "Record ID",
    sid: "Identifier",
    sd: "Standard deviation",
    se: "Standard error",
    cv: "Coefficient of variation",
    normed: "Normalized",
    characteristica: "Characteristics",
    output_count: "Whole-study measurement count",
    group_count: "Whole-study group count",
    individual_count: "Whole-study individual count",
    intervention_count: "Whole-study intervention count",
    timecourse_count: "Whole-study timecourse count",
    scatter_count: "Whole-study scatter count",
    output_calculated_count: "Whole-study calculated measurement count",
  };
  return (
    labels[key] ??
    key.replaceAll("_", " ").replace(/^./, (first) => first.toUpperCase())
  );
}

export function externalUrl(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export function detailPath(
  entity: string,
  identifier: string | number,
): string {
  const aliases: Record<string, string> = {
    study: "studies",
    group: "groups",
    individual: "individuals",
    intervention: "interventions",
    output: "outputs",
    measurements: "outputs",
    timecourses: "subsets",
    scatters: "subsets",
    reference: "references",
    info_node: "info_nodes",
  };
  const resource = aliases[entity] ?? entity;
  if (
    ![
      "studies",
      "groups",
      "individuals",
      "interventions",
      "outputs",
      "subsets",
      "references",
      "info_nodes",
    ].includes(resource)
  )
    throw new Error("Unsupported detail type.");
  if (!String(identifier)) throw new Error("A record identifier is required.");
  return `/api/v1/${resource}/${encodeURIComponent(identifier)}/`;
}

export interface Relation {
  entity: string;
  identifier: string | number;
  title: string;
}
export function relations(data: DetailRecord): Relation[] {
  const result: Relation[] = [];
  const fields: Record<string, string> = {
    study: "studies",
    group: "groups",
    parent: "groups",
    individual: "individuals",
    reference: "references",
    interventions: "interventions",
    parents: "info_nodes",
    substance: "info_nodes",
    tissue: "info_nodes",
    method: "info_nodes",
    measurement_type: "info_nodes",
    route: "info_nodes",
    form: "info_nodes",
    application: "info_nodes",
    choice: "info_nodes",
  };
  for (const [field, entity] of Object.entries(fields)) {
    const value = data[field];
    const items = Array.isArray(value) ? value : [value];
    for (const item of items) {
      if (!isRecord(item)) continue;
      const identifier = item.sid ?? item.pk;
      if (typeof identifier === "string" || typeof identifier === "number")
        result.push({
          entity,
          identifier,
          title: `${label(field)}: ${text(item)}`,
        });
    }
  }
  return result;
}
