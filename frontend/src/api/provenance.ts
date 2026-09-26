/** Human-readable acquisition provenance shared by study lists and details. */
export function provenanceText(value: unknown): string {
  if (!value || typeof value !== "object") return "Not reported";
  const provenance = value as Record<string, unknown>;
  const labels: Record<string, string> = {
    manual_curation: "Manual curation",
    data_import: "Automatic import",
    automatic_curation: "Automatic curation",
  };
  const kind = typeof provenance.kind === "string" ? labels[provenance.kind] : undefined;
  if (!kind) return "Not reported";
  return [kind, provenance.source_key, provenance.release]
    .filter((part): part is string => typeof part === "string" && part.length > 0)
    .join(" · ");
}
