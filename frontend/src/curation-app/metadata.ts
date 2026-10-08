/**
 * The form of `study.json` in the metadata section: reading a document into the form, writing
 * the form back as the canonical writer would, the fields that changed, the three-way merge of
 * a reload, and the fields of the form that validation issues belong to.
 *
 * Fields are named by their path in `study.json`, such as `reference.pmid`, `curators` or
 * `notes.outputs.descriptions`. A list is one field: a merge takes it from one side as a whole.
 */
import {
  isRecord,
  type Comment,
  type DataImport,
  type Provenance,
  type Release,
  type SourceAsset,
  type StudyDetail,
  type StudyMetadata,
  type StudyReference,
  type TableKind,
  type ValidationIssue,
} from "./api/types";

export const TABLE_KINDS: readonly TableKind[] = [
  "subjects",
  "interventions",
  "characteristica",
  "outputs",
  "timecourses",
  "scatters",
];

export const TABLE_KIND_LABELS: Record<TableKind, string> = {
  subjects: "Subjects",
  interventions: "Interventions",
  characteristica: "Characteristica",
  outputs: "Outputs",
  timecourses: "Timecourses",
  scatters: "Scatters",
};

export type ProvenanceKind = Provenance["kind"];

export const PROVENANCE_LABELS: Record<ProvenanceKind, string> = {
  manual_curation: "Manual curation",
  automatic_curation: "Automatic curation",
  data_import: "Data import",
};

/** The source key of a manual curation that `study.json` leaves out. */
export const MANUAL_SOURCE_KEY = "pkdb.manual";

export interface CuratorRow {
  user: string;
  /** From 0 to 5 in half steps. */
  rating: number;
}

export interface NotesForm {
  descriptions: string[];
  comments: Comment[];
}

/** The provenance with the fields of every kind, so that switching the kind loses nothing. */
export interface ProvenanceForm {
  kind: ProvenanceKind;
  source_key: string;
  method: string;
  version: string;
  run_id: string;
  assets: SourceAsset[];
  /** A data import as read; the importer sets it, so the form only shows it. */
  data_import: DataImport | null;
}

export interface MetadataForm {
  reference: { pmid: string; doi: string };
  creator: string;
  curators: CuratorRow[];
  collaborators: string[];
  licence: StudyMetadata["licence"];
  access: StudyMetadata["access"];
  provenance: ProvenanceForm;
  /** Read only: set when the study is released. */
  issue: number | null;
  /** Read only: set when the study is released. */
  release: Release | null;
  descriptions: string[];
  comments: Comment[];
  notes: Record<TableKind, NotesForm>;
}

/** The fields of the form, in the order of the section. */
export const FIELD_KEYS: readonly string[] = [
  "reference.pmid",
  "reference.doi",
  "creator",
  "curators",
  "collaborators",
  "licence",
  "access",
  "provenance.kind",
  "provenance.source_key",
  "provenance.method",
  "provenance.version",
  "provenance.run_id",
  "provenance.assets",
  "provenance.data_import",
  "issue",
  "release",
  "descriptions",
  "comments",
  ...TABLE_KINDS.flatMap((kind) => [`notes.${kind}.descriptions`, `notes.${kind}.comments`]),
];

const LABELS: Record<string, string> = {
  "reference.pmid": "PMID",
  "reference.doi": "DOI",
  creator: "Creator",
  curators: "Curators",
  collaborators: "Collaborators",
  licence: "Licence",
  access: "Access",
  "provenance.kind": "Provenance",
  "provenance.source_key": "Source key",
  "provenance.method": "Method",
  "provenance.version": "Version",
  "provenance.run_id": "Run ID",
  "provenance.assets": "Assets",
  "provenance.data_import": "Data import",
  issue: "Issue",
  release: "Release",
  descriptions: "Descriptions",
  comments: "Comments",
};

/** How a field differs after a reload: changed on disk only, or on disk and in the form. */
export type FieldMark = "disk" | "conflict";

export const MARK_TEXT: Record<FieldMark, string> = {
  disk: "Changed on disk",
  conflict: "Changed on disk too. Your edit is kept.",
};

/** The name of a field for a sentence, such as `Comments on outputs`. */
export function fieldLabel(key: string): string {
  const notes = /^notes\.(\w+)\.(descriptions|comments)$/.exec(key);
  if (notes) return notes[2] === "descriptions" ? `Descriptions of ${notes[1]}` : `Comments on ${notes[1]}`;
  return LABELS[key] ?? key;
}

// Reading

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** An identifier; a PubMed ID written as a number keeps its digits. */
function identifier(value: unknown): string {
  return typeof value === "number" ? String(value) : text(value);
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function record(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function comments(value: unknown): Comment[] {
  return list(value).map((entry) => ({ user: text(record(entry).user), text: text(record(entry).text) }));
}

function assets(value: unknown): SourceAsset[] {
  return list(value).map((entry) => ({ url: text(record(entry).url), sha256: text(record(entry).sha256) }));
}

function isDataImport(value: Record<string, unknown>): value is Record<string, unknown> & DataImport {
  return value.kind === "data_import";
}

function provenanceForm(value: unknown): ProvenanceForm {
  const data = record(value);
  const kind: ProvenanceKind =
    data.kind === "automatic_curation" || data.kind === "data_import" ? data.kind : "manual_curation";
  return {
    kind,
    source_key: text(data.source_key) || (kind === "manual_curation" ? MANUAL_SOURCE_KEY : ""),
    method: text(data.method),
    version: text(data.version),
    run_id: text(data.run_id),
    assets: kind === "automatic_curation" ? assets(data.assets) : [],
    data_import: isDataImport(data) ? clone(data) : null,
  };
}

/** The form of a `study.json` value; it reads any JSON value, with defaults for what it lacks. */
export function toForm(value: unknown): MetadataForm {
  const data = record(value);
  const reference = record(data.reference);
  const release = record(data.release);
  const notes = record(data.notes);
  return {
    reference: { pmid: identifier(reference.pmid), doi: text(reference.doi) },
    creator: text(data.creator),
    curators: list(data.curators).map((entry) => {
      const curator = record(entry);
      return { user: text(curator.user), rating: typeof curator.rating === "number" ? curator.rating : 0 };
    }),
    collaborators: list(data.collaborators).map(text),
    licence: data.licence === "open" ? "open" : "closed",
    access: data.access === "public" ? "public" : "private",
    provenance: provenanceForm(data.provenance),
    issue: typeof data.issue === "number" ? data.issue : null,
    release: isRecord(data.release) ? { pkdb_id: text(release.pkdb_id), date: text(release.date) } : null,
    descriptions: list(data.descriptions).map(text),
    comments: comments(data.comments),
    notes: Object.fromEntries(
      TABLE_KINDS.map((kind) => {
        const entry = record(notes[kind]);
        return [kind, { descriptions: list(entry.descriptions).map(text), comments: comments(entry.comments) }];
      }),
    ) as Record<TableKind, NotesForm>,
  };
}

/** The form of the content of a 409 answer: the text of `study.json` on disk; null when it is no JSON object. */
export function readStudyJson(content: string | null): MetadataForm | null {
  if (content === null) return null;
  let value: unknown;
  try {
    value = JSON.parse(content);
  } catch {
    return null;
  }
  return isRecord(value) ? toForm(value) : null;
}

/**
 * The form of a new `study.json` for a folder whose `study.json` is invalid: the creator, the
 * curators, the issue and the release that the folder summary could read, and the identifiers of
 * `reference.json`. `author` is the creator when the summary names none.
 */
export function startForm(detail: StudyDetail, author: string): MetadataForm {
  const summary = detail.summary;
  const reference = detail.reference && !("error" in detail.reference) ? detail.reference : null;
  const form = toForm({});
  form.reference = { pmid: reference?.pmid ?? "", doi: reference?.doi ?? "" };
  form.creator = summary.creator ?? author;
  form.curators = (summary.curators ?? []).map((user) => ({ user, rating: 0 }));
  form.issue = summary.issue ?? null;
  form.release = summary.release ?? null;
  return form;
}

// Writing

// A row that was added and left empty: the model refuses an empty text or user name, so it is not
// written. Whitespace-only text is a value and stays.
const keptText = (entry: string) => entry !== "";
const keptComment = (row: Comment) => row.text !== "";
const keptCurator = (row: CuratorRow) => row.user !== "";
const keptAsset = (asset: SourceAsset) => asset.url !== "" || asset.sha256 !== "";

function writtenProvenance(form: ProvenanceForm): Provenance {
  if (form.kind === "data_import" && form.data_import) return clone(form.data_import);
  if (form.kind === "automatic_curation")
    return {
      kind: "automatic_curation",
      source_key: form.source_key,
      method: form.method,
      version: form.version,
      assets: form.assets.filter(keptAsset).map((asset) => ({ url: asset.url, sha256: asset.sha256 })),
      run_id: form.run_id,
    };
  return { kind: "manual_curation", source_key: form.source_key };
}

/**
 * The `study.json` value of the form, as the canonical writer would write it. Every value goes
 * as typed, also whitespace-only text, and validation names what it refuses at its field. Left
 * out are rows that were added and left empty, an empty PMID or DOI field, no issue, no release,
 * and the notes of a table kind without descriptions and comments.
 */
export function fromForm(form: MetadataForm): StudyMetadata {
  const reference: StudyReference = {};
  if (form.reference.pmid !== "") reference.pmid = form.reference.pmid;
  if (form.reference.doi !== "") reference.doi = form.reference.doi;
  const notes: StudyMetadata["notes"] = {};
  for (const kind of TABLE_KINDS) {
    const descriptions = form.notes[kind].descriptions.filter(keptText);
    const comments = form.notes[kind].comments.filter(keptComment).map((entry) => ({ ...entry }));
    if (descriptions.length || comments.length) notes[kind] = { descriptions, comments };
  }
  return {
    format: 2,
    ...(reference.pmid !== undefined || reference.doi !== undefined ? { reference } : {}),
    creator: form.creator,
    curators: form.curators.filter(keptCurator).map((row) => ({ user: row.user, rating: row.rating })),
    collaborators: form.collaborators.filter(keptText),
    licence: form.licence,
    access: form.access,
    provenance: writtenProvenance(form.provenance),
    ...(form.issue !== null ? { issue: form.issue } : {}),
    ...(form.release ? { release: { ...form.release } } : {}),
    descriptions: form.descriptions.filter(keptText),
    comments: form.comments.filter(keptComment).map((entry) => ({ ...entry })),
    notes,
  };
}

/**
 * The provenance for another kind. The source key of a manual curation does not carry over to
 * another kind, and an empty one becomes it again for a manual curation; a typed key stays.
 */
export function withKind(provenance: ProvenanceForm, kind: ProvenanceKind): ProvenanceForm {
  let source_key = provenance.source_key;
  if (kind !== "manual_curation" && source_key === MANUAL_SOURCE_KEY) source_key = "";
  if (kind === "manual_curation" && source_key === "") source_key = MANUAL_SOURCE_KEY;
  return { ...provenance, kind, source_key };
}

// Comparing and merging

/** A deep copy of a JSON value, such as a form. */
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

/** Whether two JSON values are equal; the order of object keys does not matter. */
function same(left: unknown, right: unknown): boolean {
  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) return false;
    return left.every((entry, index) => same(entry, right[index]));
  }
  if (isRecord(left) && isRecord(right)) {
    const keys = Object.keys(left);
    return keys.length === Object.keys(right).length && keys.every((key) => key in right && same(left[key], right[key]));
  }
  return left === right;
}

function valueAt(form: MetadataForm, key: string): unknown {
  let node: unknown = form;
  for (const part of key.split(".")) node = isRecord(node) ? node[part] : undefined;
  return node;
}

/** Sets the field `key` of `target` to a copy of the one of `source`, such as the disk version. */
export function copyField(target: MetadataForm, source: MetadataForm, key: string): void {
  const parts = key.split(".");
  const last = parts.pop();
  let node: unknown = target;
  for (const part of parts) node = isRecord(node) ? node[part] : undefined;
  if (isRecord(node) && last !== undefined) node[last] = clone(valueAt(source, key));
}

/** The fields whose values differ between `base` and `current`, in the order of `FIELD_KEYS`. */
export function changedFields(base: MetadataForm, current: MetadataForm): string[] {
  return FIELD_KEYS.filter((key) => !same(valueAt(base, key), valueAt(current, key)));
}

/**
 * The form after a reload: `theirs` (the document on disk) with the edits of `mine` on top. A
 * field that both sides changed differently keeps mine and is listed in `conflicts`. `base` is
 * the document that the form started from.
 */
export function mergeOnReload(
  base: MetadataForm,
  mine: MetadataForm,
  theirs: MetadataForm,
): { merged: MetadataForm; conflicts: string[] } {
  const theirChanges = new Set(changedFields(base, theirs));
  const merged = clone(theirs);
  const conflicts: string[] = [];
  for (const key of changedFields(base, mine)) {
    copyField(merged, mine, key);
    if (theirChanges.has(key) && !same(valueAt(mine, key), valueAt(theirs, key))) conflicts.push(key);
  }
  return { merged, conflicts };
}

/** At most this many characters of a value are shown in a sentence. */
const SHOWN = 160;

function shortened(text: string): string {
  return text.length > SHOWN ? `${text.slice(0, SHOWN)}...` : text;
}

/** The value of a field for a sentence, such as `mkoenig (3), janekg (4.5)` for the curators. */
export function fieldText(form: MetadataForm, key: string): string {
  const value = valueAt(form, key);
  if (key === "provenance.kind") return PROVENANCE_LABELS[form.provenance.kind];
  if (key === "provenance.data_import")
    return form.provenance.data_import
      ? `${form.provenance.data_import.importer} ${form.provenance.data_import.importer_version}`
      : "none";
  if (key === "release") return form.release ? `${form.release.pkdb_id} · released ${form.release.date}` : "none";
  if (key === "issue") return form.issue === null ? "none" : `#${form.issue}`;
  if (typeof value === "string") return value === "" ? "empty" : shortened(value);
  if (!Array.isArray(value)) return String(value);
  const entries = value.map((entry) => {
    if (!isRecord(entry)) return String(entry);
    if ("rating" in entry) return `${String(entry.user)} (${String(entry.rating)})`;
    if ("text" in entry) return `${String(entry.user)}: ${String(entry.text)}`;
    return String(entry.url);
  });
  return entries.length ? shortened(entries.join(key.endsWith("descriptions") ? " / " : ", ")) : "none";
}

/** The message of a field that changed on disk at a reload; a conflict names the disk value. */
export function markMessage(mark: FieldMark, disk: string | null): string {
  return mark === "conflict" && disk !== null ? `${MARK_TEXT.conflict} On disk: ${disk}` : MARK_TEXT[mark];
}

// Issues

/**
 * `<prefix>.<form index>` for the list index `part` of the written rows, which skip the rows left
 * empty; the list itself without an index; null for an unknown row.
 */
function row<T>(prefix: string, rows: readonly T[], kept: (row: T) => boolean, part: string | undefined): string | null {
  if (part === undefined) return prefix;
  if (!/^\d+$/.test(part)) return null;
  let written = -1;
  for (const [position, entry] of rows.entries()) {
    if (kept(entry)) written += 1;
    if (written === Number(part)) return `${prefix}.${position}`;
  }
  return null;
}

/**
 * The field of the form that shows an issue with the `field` of the API, such as
 * `curators.0.rating` or `provenance.automatic_curation.method`; null when the form has no field
 * for it, such as an issue of the whole file.
 */
export function issueTarget(form: MetadataForm, field: string | null | undefined): string | null {
  if (!field) return null;
  const [head, ...rest] = field.split(".");
  switch (head) {
    case "reference":
      return rest[0] === "doi" ? "reference.doi" : "reference.pmid";
    case "creator":
    case "licence":
    case "access":
    case "issue":
    case "release":
    case "collaborators":
      return head;
    case "curators": {
      const target = row("curators", form.curators, keptCurator, rest[0]);
      if (target === null || rest.length === 0) return target;
      return `${target}.${rest[1] === "rating" ? "rating" : "user"}`;
    }
    case "descriptions":
      return row("descriptions", form.descriptions, keptText, rest[0]);
    case "comments":
      return row("comments", form.comments, keptComment, rest[0]);
    case "provenance": {
      // The path names the kind of a tagged union: provenance.automatic_curation.method.
      const [, name, index, part] = rest;
      if (name === undefined) return "provenance.kind";
      if (form.provenance.kind === "data_import") return "provenance.data_import";
      if (name !== "assets") return `provenance.${name}`;
      const target = row("provenance.assets", form.provenance.assets, keptAsset, index);
      return target !== null && part !== undefined && index !== undefined ? `${target}.${part}` : target;
    }
    case "notes": {
      const [kind, name, index] = rest;
      const notes = TABLE_KINDS.find((candidate) => candidate === kind);
      if (notes === undefined) return null;
      if (name === "descriptions")
        return row(`notes.${notes}.descriptions`, form.notes[notes].descriptions, keptText, index);
      if (name === "comments") return row(`notes.${notes}.comments`, form.notes[notes].comments, keptComment, index);
      // The form writes every kind as an object, so an issue of a whole kind lists with the others.
      return null;
    }
    default:
      return null;
  }
}

/** The message of an issue without the path and the "Value error" that validation puts before it. */
export function issueMessage(issue: ValidationIssue): string {
  const prefix = issue.field ? `${issue.field}: ` : "";
  const message = prefix && issue.message.startsWith(prefix) ? issue.message.slice(prefix.length) : issue.message;
  return message.replace(/^Value error, /, "");
}

/** The messages of `issues` by the field of the form that shows them, and the messages of the others. */
export function issuesByTarget(
  form: MetadataForm,
  issues: ValidationIssue[],
): { fields: Map<string, string[]>; general: string[] } {
  const fields = new Map<string, string[]>();
  const general: string[] = [];
  for (const issue of issues) {
    const target = issueTarget(form, issue.field);
    if (target === null) general.push(issue.message);
    else fields.set(target, [...(fields.get(target) ?? []), issueMessage(issue)]);
  }
  return { fields, general };
}
