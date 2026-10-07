import { describe, expect, it } from "vitest";
import type { ValidationIssue } from "../../src/curation-app/api/types";
import {
  changedFields,
  fieldLabel,
  FIELD_KEYS,
  fromForm,
  issueMessage,
  issuesByTarget,
  issueTarget,
  mergeOnReload,
  readStudyJson,
  startForm,
  toForm,
} from "../../src/curation-app/metadata";
import { fullStudyMetadata, studyDetail, studyMetadata } from "./curation-fixtures";

function issue(field: string | null, message = `${field}: Input is invalid`): ValidationIssue {
  return { code: "invalid_study_json", severity: "error", message, field };
}

describe("toForm and fromForm", () => {
  it("round-trips a full study.json", () => {
    const value = fullStudyMetadata();
    expect(fromForm(toForm(value))).toEqual(value);
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
    expect(fromForm(toForm(value))).toEqual(value);
  });

  it("round-trips the defaults of a minimal study.json as the server reads it", () => {
    const value = studyMetadata();
    expect(fromForm(toForm(value))).toEqual(value);
  });

  it("drops blank entries, notes without content and empty identifiers like the canonical writer", () => {
    const form = toForm(fullStudyMetadata());
    form.reference = { pmid: " ", doi: "" };
    form.descriptions.push("", "  ");
    form.comments.push({ user: "mkoenig", text: " " });
    form.curators.push({ user: "", rating: 0 });
    form.collaborators.push("");
    form.notes.outputs = { descriptions: [""], comments: [] };
    form.notes.scatters = { descriptions: [], comments: [{ user: "janekg", text: "" }] };
    form.issue = null;
    form.release = null;

    const value = fromForm(form);

    expect(value).not.toHaveProperty("reference");
    expect(value).not.toHaveProperty("issue");
    expect(value).not.toHaveProperty("release");
    expect(value.descriptions).toEqual(["Plasma levels in µg/l."]);
    expect(value.comments).toEqual([{ user: "mkoenig", text: "Checked against the PDF." }]);
    expect(value.curators).toHaveLength(2);
    expect(value.collaborators).toEqual(["Jane Doe"]);
    expect(value.notes).toEqual({ timecourses: { descriptions: ["Digitized from Figure 1."], comments: [] } });
  });

  it("trims identifiers and user names, but keeps the text of descriptions", () => {
    const form = toForm(studyMetadata());
    form.reference = { pmid: " 123 ", doi: " 10.1000/x " };
    form.creator = " mkoenig ";
    form.descriptions = ["  indented"];
    const value = fromForm(form);
    expect(value.reference).toEqual({ pmid: "123", doi: "10.1000/x" });
    expect(value.creator).toBe("mkoenig");
    expect(value.descriptions).toEqual(["  indented"]);
  });

  it("keeps only the fields of the chosen provenance kind", () => {
    const form = toForm(fullStudyMetadata());
    form.provenance.kind = "manual_curation";
    form.provenance.source_key = "pkdb.manual";
    expect(fromForm(form).provenance).toEqual({ kind: "manual_curation", source_key: "pkdb.manual" });
  });

  it("reads any JSON value without failing, with the defaults of a new study.json", () => {
    const form = toForm({ creator: 7, curators: "x", licence: "maybe", notes: { outputs: "x" } });
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
    expect(readStudyJson(JSON.stringify(fullStudyMetadata()))?.creator).toBe("curator");
    expect(readStudyJson("{ not json")).toBeNull();
    expect(readStudyJson("[]")).toBeNull();
    expect(readStudyJson(null)).toBeNull();
  });
});

describe("changedFields", () => {
  it("lists the fields that differ, by their study.json path", () => {
    const base = toForm(fullStudyMetadata());
    const current = toForm(fullStudyMetadata());
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
    expect(FIELD_KEYS).toContain("reference.pmid");
    expect(FIELD_KEYS).toContain("notes.scatters.descriptions");
    expect(FIELD_KEYS.map(fieldLabel)).not.toContain(undefined);
    expect(fieldLabel("notes.outputs.comments")).toBe("Comments on outputs");
    expect(fieldLabel("provenance.run_id")).toBe("Run ID");
  });
});

describe("mergeOnReload", () => {
  it("keeps a local licence edit while taking a curator change from disk", () => {
    const base = toForm(fullStudyMetadata());
    const mine = toForm(fullStudyMetadata({ licence: "open" }));
    const theirs = toForm(
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
    const base = toForm(fullStudyMetadata());
    const mine = toForm(fullStudyMetadata({ licence: "open", descriptions: ["Mine."] }));
    const theirs = toForm(fullStudyMetadata({ access: "private", descriptions: ["Theirs."] }));

    const { merged, conflicts } = mergeOnReload(base, mine, theirs);

    expect(merged.descriptions).toEqual(["Mine."]);
    expect(merged.licence).toBe("open");
    expect(merged.access).toBe("private");
    expect(conflicts).toEqual(["descriptions"]);
  });

  it("sees no conflict when both sides made the same change", () => {
    const base = toForm(fullStudyMetadata());
    const same = toForm(fullStudyMetadata({ licence: "open" }));
    expect(mergeOnReload(base, same, toForm(fullStudyMetadata({ licence: "open" }))).conflicts).toEqual([]);
  });

  it("does not change its arguments", () => {
    const base = toForm(fullStudyMetadata());
    const mine = toForm(fullStudyMetadata({ licence: "open" }));
    const theirs = toForm(fullStudyMetadata({ creator: "janekg" }));
    const { merged } = mergeOnReload(base, mine, theirs);
    merged.descriptions.push("New.");
    expect(theirs.creator).toBe("janekg");
    expect(theirs.descriptions).toEqual(["Plasma levels in µg/l."]);
    expect(mine.creator).toBe("curator");
  });
});

describe("issueTarget", () => {
  const form = toForm(fullStudyMetadata());

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

  it("maps a list index of the sent study.json past the blank rows of the form", () => {
    const blank = toForm(fullStudyMetadata());
    blank.curators.unshift({ user: "", rating: 0 });
    expect(issueTarget(blank, "curators.1.user")).toBe("curators.2.user");
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
      issue("curators.1.rating", "curators.1.rating: Input should be less than or equal to 5"),
      issue("format", "format: Input should be 2"),
      issue(null, "study.json is not valid JSON"),
    ];
    const grouped = issuesByTarget(form, issues);
    expect(Object.fromEntries(grouped.fields)).toEqual({
      "curators.1.rating": ["Input should be less than or equal to 5"],
    });
    expect(grouped.general).toEqual(["format: Input should be 2", "study.json is not valid JSON"]);
    expect(issueMessage(issues[0]!)).toBe("Input should be less than or equal to 5");
    expect(issueMessage(issue("reference.doi", "reference.doi: Value error, 'doi' is not a valid DOI"))).toBe(
      "'doi' is not a valid DOI",
    );
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
