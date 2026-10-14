/**
 * The metadata of a study as text, for the read-only view (MetadataView.vue) and the form of the
 * curation app (MetadataSection.vue): the labels of the provenance, the reference as a title,
 * authors and source, whether reference.json matches study.json, and the facts of an automatic
 * curation or a data import.
 */
import type { Tone } from "./overview";
import type { Provenance, ReferenceSummary } from "./types";

export type ProvenanceKind = Provenance["kind"];

export const PROVENANCE_LABELS: Record<ProvenanceKind, string> = {
  manual_curation: "Manual curation",
  automatic_curation: "Automatic curation",
  data_import: "Data import",
};

/** A fact of a card: its name, its text, and the page that it links to. */
export interface Fact {
  name: string;
  value: string;
  href?: string;
}

export type ReferenceView =
  | { kind: "none" }
  | { kind: "error"; text: string }
  | { kind: "reference"; title: string | null; authors: string; source: string };

/** The reference of a study as text: its title, at most six authors, and its journal with its date. */
export function referenceView(value: ReferenceSummary | null): ReferenceView {
  if (value === null) return { kind: "none" };
  if ("error" in value) return { kind: "error", text: value.error };
  const authors = value.authors;
  return {
    kind: "reference",
    title: value.title,
    authors:
      authors.length > 6 ? `${authors.slice(0, 6).join(", ")}, et al. (${authors.length} authors)` : authors.join(", "),
    source: [value.journal, value.publication_date].filter(Boolean).join(" · "),
  };
}

/** Whether reference.json has the identifiers of study.json, as its chip says it. */
export function referenceMatch(value: boolean | null): { label: string; tone: Tone } {
  if (value === true) return { label: "reference.json matches", tone: "success" };
  if (value === false) return { label: "reference.json does not match study.json", tone: "warning" };
  return { label: "No identifiers", tone: undefined };
}

/** The facts of an automatic curation or a data import; a field that the page left out or left empty shows nothing. */
export function provenanceFacts(provenance: Provenance): Fact[] {
  const facts: [string, string | undefined][] =
    provenance.kind === "automatic_curation"
      ? [
          ["Method", provenance.method],
          ["Version", provenance.version],
          ["Run ID", provenance.run_id],
        ]
      : provenance.kind === "data_import"
        ? [
            ["Importer", [provenance.importer, provenance.importer_version].filter(Boolean).join(" ")],
            ["Source", provenance.source_key],
            ["Release", provenance.release],
            ["Evidence", [provenance.evidence_kind, provenance.reference_scope].filter(Boolean).join(", ")],
          ]
        : [];
  return facts.filter((fact): fact is [string, string] => Boolean(fact[1])).map(([name, value]) => ({ name, value }));
}
