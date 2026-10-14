import { describe, expect, it } from "vitest";
import type { TableKind, ValidationIssue } from "../../src/study-views/types";
import {
  changedFields,
  changedLabels,
  clone,
  copyField,
  fieldLabel,
  fieldText,
  fieldKeys,
  fromForm,
  issueMessage,
  issuesByTarget,
  issueTarget,
  MARK_TEXT,
  markMessages,
  mergeOnReload,
  messagesAt,
  NO_MESSAGES,
  type MetadataForm,
  readStudyJson,
  shortList,
  startForm,
  targetLabel,
  toForm,
  unsavedSections,
  withKind,
} from "../../src/curation-app/metadata";
import { kindLabel } from "../../src/curation-app/tableKinds";
import { NOTE_KINDS, TABLE_KIND_ENTRIES, fullStudyMetadata, studyDetail, studyMetadata } from "./curation-fixtures";

/** The form of a study.json value with the notes of every table kind of the study page. */
function formOf(value: unknown): MetadataForm {
  return toForm(value, NOTE_KINDS);
}

/** An issue of study.json as the library gives it: the message names the field, the detail does not. */
function issue(field: string | null, detail = "Input is invalid"): ValidationIssue {
  if (field === null) return { code: "invalid_study_json", severity: "error", message: detail, field };
  return { code: "invalid_study_json", severity: "error", message: `${field}: ${detail}`, field, context: { detail } };
}

describe("toForm and fromForm", () => {
  it("round-trips a full study.json", () => {
    const value = fullStudyMetadata();
    expect(fromForm(formOf(value))).toEqual(value);
  });

  it("round-trips study.json of a data import, which the form keeps as read", () => {
    const value = studyMetadata({
      provenance: {
        kind: "data_import",
        source_key: "pkdb.import",
        release: "2026.1",
        revision: "abc",
        importer: "importer",
        importer_version: "1.0",
        assets: [{ url: "https://example.org/data.zip", sha256: "b".repeat(64) }],
        dataset_ids: ["d1"],
        evidence_kind: "observed",
        reference_scope: "primary_publication",
      },
    });
    expect(fromForm(formOf(value))).toEqual(value);
  });

  it("round-trips the defaults of a minimal study.json as the server reads it", () => {
    const value = studyMetadata();
    expect(fromForm(formOf(value))).toEqual(value);
  });

  it("drops rows left empty, notes without content and absent values", () => {
    const form = formOf(fullStudyMetadata());
    form.reference = { pmid: "", doi: "" };
    form.descriptions.push("");
    form.comments.push({ user: "mkoenig", text: "" });
    form.curators.push({ user: "", rating: 0 });
    form.collaborators.push("");
    form.provenance.assets.push({ url: "", sha256: "" });
    form.notes.outputs = { descriptions: [], comments: [] };
    form.notes.scatters = { descriptions: [""], comments: [{ user: "janekg", text: "" }] };
    form.issue = null;
    form.release = null;

    const value = fromForm(form);

    expect(value).not.toHaveProperty("reference");
    expect(value).not.toHaveProperty("issue");
    expect(value).not.toHaveProperty("release");
    // The model refuses an empty text, so a row that was added and left empty is not written.
    expect(value.descriptions).toEqual(["Plasma levels in µg/l."]);
    expect(value.comments).toEqual([{ user: "mkoenig", text: "Checked against the PDF." }]);
    expect(value.curators).toHaveLength(2);
    expect(value.collaborators).toEqual(["Jane Doe"]);
    expect(value.provenance).toMatchObject({ assets: [{ url: "https://example.org/Harder1988.pdf" }] });
    expect(value.notes).toEqual({ timecourses: { descriptions: ["Digitized from Figure 1."], comments: [] } });
  });

  it("keeps every value as typed, also whitespace-only and padded text", () => {
    const value = fullStudyMetadata({
      reference: { pmid: " 123 ", doi: " 10.1000/x " },
      creator: " mkoenig ",
      curators: [{ user: " janekg", rating: 2.5 }],
      collaborators: [" Jane Doe ", "   "],
      descriptions: ["   ", "  indented", "trailing  "],
      comments: [{ user: "mkoenig", text: "  " }],
      notes: { outputs: { descriptions: [" "], comments: [{ user: "janekg", text: " padded " }] } },
    });
    expect(fromForm(formOf(value))).toEqual(value);
  });

  it("keeps only the fields of the chosen provenance kind", () => {
    const form = formOf(fullStudyMetadata());
    form.provenance.kind = "manual_curation";
    form.provenance.source_key = "pkdb.manual";
    expect(fromForm(form).provenance).toEqual({ kind: "manual_curation", source_key: "pkdb.manual" });
  });

  it("reads any JSON value without failing, with the defaults of a new study.json", () => {
    const form = formOf({ creator: 7, curators: "x", licence: "maybe", notes: { outputs: "x" } });
    expect(form.creator).toBe("");
    expect(form.curators).toEqual([]);
    expect(form.licence).toBe("closed");
    expect(form.access).toBe("private");
    expect(form.provenance.kind).toBe("manual_curation");
    expect(form.notes.outputs).toEqual({ descriptions: [], comments: [] });
  });
});

describe("readStudyJson", () => {
  it("reads the content of a 409 answer, or null when it is no JSON object", () => {
    expect(readStudyJson(JSON.stringify(fullStudyMetadata()), NOTE_KINDS)?.creator).toBe("curator");
    expect(readStudyJson("{ not json", NOTE_KINDS)).toBeNull();
    expect(readStudyJson("[]", NOTE_KINDS)).toBeNull();
    expect(readStudyJson(null, NOTE_KINDS)).toBeNull();
  });
});

describe("changedFields", () => {
  it("lists the fields that differ, by their study.json path", () => {
    const base = formOf(fullStudyMetadata());
    const current = formOf(fullStudyMetadata());
    expect(changedFields(base, current)).toEqual([]);

    current.licence = "open";
    current.curators[1]!.rating = 5;
    current.provenance.method = "claude-opus-5-6";
    current.notes.outputs.comments = [];
    expect(changedFields(base, current)).toEqual([
      "curators",
      "licence",
      "provenance.method",
      "notes.outputs.comments",
    ]);
  });

  it("knows every field of the form, with a label", () => {
    const keys = fieldKeys(formOf(fullStudyMetadata()));
    expect(keys).toContain("reference.pmid");
    expect(keys).toContain("notes.scatters.descriptions");
    expect(keys.map(fieldLabel)).not.toContain(undefined);
    expect(fieldLabel("notes.outputs.comments")).toBe("Comments on outputs");
    expect(fieldLabel("provenance.run_id")).toBe("Run ID");
  });

  it("names the field that shows the target of an issue", () => {
    expect(targetLabel("reference.pmid")).toBe("PMID");
    expect(targetLabel("curators.0.user")).toBe("Curators");
    expect(targetLabel("descriptions.1")).toBe("Descriptions");
    expect(targetLabel("provenance.assets.0.url")).toBe("Assets");
    expect(targetLabel("notes.outputs.descriptions.1")).toBe("Descriptions of outputs");
    expect(targetLabel("constructor")).toBe("constructor");
  });
});

describe("mergeOnReload", () => {
  it("keeps a local licence edit while taking a curator change from disk", () => {
    const base = formOf(fullStudyMetadata());
    const mine = formOf(fullStudyMetadata({ licence: "open" }));
    const theirs = formOf(
      fullStudyMetadata({
        curators: [
          { user: "mkoenig", rating: 3 },
          { user: "janekg", rating: 5 },
        ],
      }),
    );

    const { merged, conflicts } = mergeOnReload(base, mine, theirs);

    expect(merged.licence).toBe("open");
    expect(merged.curators[1]).toEqual({ user: "janekg", rating: 5 });
    expect(conflicts).toEqual([]);
    expect(changedFields(theirs, merged)).toEqual(["licence"]);
  });

  it("keeps mine for a field changed on both sides and lists it in conflicts", () => {
    const base = formOf(fullStudyMetadata());
    const mine = formOf(fullStudyMetadata({ licence: "open", descriptions: ["Mine."] }));
    const theirs = formOf(fullStudyMetadata({ access: "private", descriptions: ["Theirs."] }));

    const { merged, conflicts } = mergeOnReload(base, mine, theirs);

    expect(merged.descriptions).toEqual(["Mine."]);
    expect(merged.licence).toBe("open");
    expect(merged.access).toBe("private");
    expect(conflicts).toEqual(["descriptions"]);
  });

  it("sees no conflict when both sides made the same change", () => {
    const base = formOf(fullStudyMetadata());
    const same = formOf(fullStudyMetadata({ licence: "open" }));
    expect(mergeOnReload(base, same, formOf(fullStudyMetadata({ licence: "open" }))).conflicts).toEqual([]);
  });

  it("does not change its arguments", () => {
    const base = formOf(fullStudyMetadata());
    const mine = formOf(fullStudyMetadata({ licence: "open" }));
    const theirs = formOf(fullStudyMetadata({ creator: "janekg" }));
    const { merged } = mergeOnReload(base, mine, theirs);
    merged.descriptions.push("New.");
    expect(theirs.creator).toBe("janekg");
    expect(theirs.descriptions).toEqual(["Plasma levels in µg/l."]);
    expect(mine.creator).toBe("curator");
  });
});

describe("issueTarget", () => {
  const form = formOf(fullStudyMetadata());

  it("maps the field of an issue to the field of the form", () => {
    expect(issueTarget(form, "creator")).toBe("creator");
    expect(issueTarget(form, "reference")).toBe("reference.pmid");
    expect(issueTarget(form, "reference.doi")).toBe("reference.doi");
    expect(issueTarget(form, "curators.1.rating")).toBe("curators.1.rating");
    expect(issueTarget(form, "curators.0")).toBe("curators.0.user");
    expect(issueTarget(form, "collaborators.0")).toBe("collaborators");
    expect(issueTarget(form, "provenance.automatic_curation.method")).toBe("provenance.method");
    expect(issueTarget(form, "provenance.automatic_curation.assets.0.sha256")).toBe("provenance.assets.0.sha256");
    expect(issueTarget(form, "provenance.automatic_curation.assets")).toBe("provenance.assets");
    expect(issueTarget(form, "provenance")).toBe("provenance.kind");
    expect(issueTarget(form, "release.pkdb_id")).toBe("release");
    expect(issueTarget(form, "comments.0.user")).toBe("comments.0");
    expect(issueTarget(form, "notes.outputs.comments.0.text")).toBe("notes.outputs.comments.0");
    expect(issueTarget(form, "notes.timecourses.descriptions.0")).toBe("notes.timecourses.descriptions.0");
  });

  it("maps a list index of the sent study.json past the rows left empty", () => {
    const blank = formOf(fullStudyMetadata());
    blank.curators.unshift({ user: "", rating: 0 });
    expect(issueTarget(blank, "curators.1.user")).toBe("curators.2.user");
    // Whitespace-only text is sent, so its row keeps its index.
    blank.descriptions = ["", " ", "Doses."];
    expect(issueTarget(blank, "descriptions.0")).toBe("descriptions.1");
    expect(issueTarget(blank, "descriptions.1")).toBe("descriptions.2");
  });

  it("has no field for an issue of the whole file or an unknown path", () => {
    expect(issueTarget(form, null)).toBeNull();
    expect(issueTarget(form, "format")).toBeNull();
    expect(issueTarget(form, "curators.9.user")).toBeNull();
    expect(issueTarget(form, "notes.outputs")).toBeNull();
    expect(issueTarget(form, "notes.figures.descriptions.0")).toBeNull();
  });

  it("groups the messages by field, without the path, and lists the others", () => {
    const issues = [
      issue("curators.1.rating", "Input should be less than or equal to 5"),
      issue("format", "Input should be 2"),
      issue(null, "study.json is not valid JSON"),
    ];
    const grouped = issuesByTarget(form, issues);
    expect(Object.fromEntries(grouped.fields)).toEqual({
      "curators.1.rating": ["Input should be less than or equal to 5"],
    });
    expect(grouped.general).toEqual(["format: Input should be 2", "study.json is not valid JSON"]);
  });

  it("shows the message of the library without its field", () => {
    expect(issueMessage(issue("curators.1.rating", "Input should be less than or equal to 5"))).toBe(
      "Input should be less than or equal to 5",
    );
    // The detail of the library is the message, also when it names the field itself.
    expect(issueMessage(issue("reference", "reference: give a pmid or a doi"))).toBe("reference: give a pmid or a doi");
    // An issue without a detail keeps its whole message.
    const whole: ValidationIssue = { code: "invalid_study_json", severity: "error", message: "creator: Bad", field: "creator" };
    expect(issueMessage(whole)).toBe("creator: Bad");
  });
});

describe("withKind", () => {
  it("drops the source key of a manual curation for another kind and keeps a typed one", () => {
    const manual = formOf(studyMetadata()).provenance;
    expect(withKind(manual, "automatic_curation")).toMatchObject({ kind: "automatic_curation", source_key: "" });
    expect(withKind({ ...manual, source_key: "lab.notes" }, "automatic_curation").source_key).toBe("lab.notes");
    const automatic = withKind(manual, "automatic_curation");
    expect(withKind(automatic, "manual_curation")).toEqual(manual);
    expect(withKind({ ...automatic, source_key: "pkdb.ai" }, "manual_curation").source_key).toBe("pkdb.ai");
  });
});

describe("disk versions after a reload", () => {
  it("describes the value of a field for a sentence", () => {
    const form = formOf(fullStudyMetadata());
    expect(fieldText(form, "creator")).toBe("curator");
    expect(fieldText(form, "curators")).toBe("mkoenig (3), janekg (4.5)");
    expect(fieldText(form, "collaborators")).toBe("Jane Doe");
    expect(fieldText(form, "provenance.kind")).toBe("Automatic curation");
    expect(fieldText(form, "provenance.assets")).toBe("https://example.org/Harder1988.pdf");
    expect(fieldText(form, "descriptions")).toBe("Plasma levels in µg/l.");
    expect(fieldText(form, "notes.outputs.comments")).toBe("janekg: AUC rounded.");
    expect(fieldText(form, "release")).toBe("PKDB00198 · released 2026-09-28");
    expect(fieldText(formOf(studyMetadata()), "reference.doi")).toBe("empty");
    expect(fieldText(formOf(studyMetadata()), "descriptions")).toBe("none");
  });

  it("takes one field of the disk version into the form", () => {
    const mine = formOf(fullStudyMetadata({ creator: "mkoenig", licence: "open" }));
    const theirs = formOf(fullStudyMetadata({ creator: "janekg", curators: [] }));
    copyField(mine, theirs, "creator");
    expect(mine.creator).toBe("janekg");
    expect(mine.licence).toBe("open");
    expect(mine.curators).toHaveLength(2);
    theirs.creator = "changed";
    expect(mine.creator).toBe("janekg");
  });
});

describe("startForm", () => {
  it("starts a new study.json from the fields that the folder summary could read", () => {
    const detail = studyDetail({
      metadata: { revision: "broken-1", value: null, issues: [issue(null, "study.json is not valid JSON")] },
      summary: { ...studyDetail().summary, creator: "curator", curators: ["mkoenig"], issue: 2190, release: null },
      reference: {
        sid: "123",
        pmid: "123",
        doi: null,
        title: "Caffeine",
        journal: null,
        abstract: null,
        publication_date: null,
        authors: [],
      },
    });
    const form = startForm(detail, "janekg");
    expect(fromForm(form)).toEqual({
      format: 2,
      reference: { pmid: "123" },
      creator: "curator",
      curators: [{ user: "mkoenig", rating: 0 }],
      collaborators: [],
      licence: "closed",
      access: "private",
      provenance: { kind: "manual_curation", source_key: "pkdb.manual" },
      issue: 2190,
      descriptions: [],
      comments: [],
      notes: {},
    });
    expect(startForm(studyDetail({ summary: {} }), "janekg").creator).toBe("janekg");
  });
});

describe("unsavedSections", () => {
  const base = () => toForm(fullStudyMetadata(), NOTE_KINDS);

  it("names Metadata for the fields of the study and Data for the notes of a kind with a table", () => {
    const notes = clone(base());
    notes.notes.outputs.descriptions.push("More.");
    expect(unsavedSections(base(), notes, changedFields(base(), notes), ["outputs"])).toEqual(["data"]);
    const both = clone(notes);
    both.creator = "janekg";
    expect(unsavedSections(base(), both, changedFields(base(), both), ["outputs"])).toEqual(["metadata", "data"]);
    expect(unsavedSections(base(), clone(base()), [], ["outputs"])).toEqual([]);
  });

  it("names Metadata for the notes of a kind without a table, which Metadata shows", () => {
    const notes = clone(base());
    notes.notes.scatters.descriptions.push("From Figure 3.");
    expect(unsavedSections(base(), notes, changedFields(base(), notes), ["subjects", "outputs"])).toEqual(["metadata"]);
  });

  it("names Metadata for a new study.json, and nothing without a form", () => {
    expect(unsavedSections(null, toForm({}, NOTE_KINDS), [], NOTE_KINDS)).toEqual(["metadata"]);
    expect(unsavedSections(base(), null, [], NOTE_KINDS)).toEqual([]);
  });
});

describe("messages", () => {
  it("gives every field without messages the same frozen array", () => {
    const errors = new Map([["creator", ["Unknown user."]]]);
    expect(messagesAt(errors, "licence")).toBe(NO_MESSAGES);
    expect(messagesAt(errors, "access")).toBe(messagesAt(errors, "licence"));
    expect(Object.isFrozen(NO_MESSAGES)).toBe(true);
    expect(messagesAt(errors, "creator")).toBe(errors.get("creator"));
  });

  it("keeps one array per marked field", () => {
    const messages = markMessages(new Map([["licence", "disk" as const]]), new Map());
    expect(messages.get("licence")).toEqual([MARK_TEXT.disk]);
    expect(messages.get("access")).toBeUndefined();
  });
});

describe("the names of the changed fields", () => {
  const label = (kind: TableKind) => kindLabel({ table_kinds: TABLE_KIND_ENTRIES }, kind);

  it("names a field of the study by its label, and the notes of a kind once", () => {
    expect(
      changedLabels(["provenance.source_key", "notes.outputs.descriptions", "notes.outputs.comments"], label),
    ).toEqual(["Source key", "Notes of the outputs"]);
    expect(changedLabels(["reference.pmid", "notes.subjects.comments", "comments"], label)).toEqual([
      "PMID",
      "Notes of the subjects",
      "Comments",
    ]);
  });

  it("lists three names and counts the others", () => {
    expect(shortList([])).toBe("");
    expect(shortList(["PMID"])).toBe("PMID");
    expect(shortList(["PMID", "DOI", "Creator"])).toBe("PMID, DOI, Creator");
    expect(shortList(["PMID", "DOI", "Creator", "Curators"])).toBe("PMID, DOI, Creator and 1 more");
    expect(shortList(["PMID", "DOI", "Creator", "Curators", "Licence"])).toBe("PMID, DOI, Creator and 2 more");
  });
});
