import { describe, expect, it } from "vitest";
import { hasNotes, kindsWithTable, notesKindOf, notesKindsOf } from "../../src/curation-app/notes";
import { NOTE_KINDS, tableEntry } from "./curation-fixtures";

describe("notesKindOf", () => {
  it("reads the table kind of a field of the notes of study.json", () => {
    expect(notesKindOf("notes.subjects.descriptions.0", NOTE_KINDS)).toBe("subjects");
    expect(notesKindOf("notes.outputs.comments.1.user", NOTE_KINDS)).toBe("outputs");
    expect(notesKindOf("notes.timecourses", NOTE_KINDS)).toBe("timecourses");
  });

  it("has none for another field, an unknown kind or a kind that is not listed", () => {
    expect(notesKindOf("descriptions.0", NOTE_KINDS)).toBeNull();
    expect(notesKindOf("notes.unknown.descriptions", NOTE_KINDS)).toBeNull();
    expect(notesKindOf("notesx.subjects", NOTE_KINDS)).toBeNull();
    expect(notesKindOf(null, NOTE_KINDS)).toBeNull();
    expect(notesKindOf(undefined, NOTE_KINDS)).toBeNull();
    expect(notesKindOf("notes.scatters.comments", ["subjects"])).toBeNull();
  });
});

describe("notesKindsOf", () => {
  it("lists each kind once, in the order of the kinds", () => {
    expect(
      notesKindsOf(["notes.outputs.descriptions.0", "creator", "notes.subjects.comments", "notes.outputs.comments"], NOTE_KINDS),
    ).toEqual(["subjects", "outputs"]);
    expect(notesKindsOf([], NOTE_KINDS)).toEqual([]);
  });
});

describe("kindsWithTable", () => {
  it("keeps the kinds that a table of the study has", () => {
    const study = {
      tables: [
        tableEntry("subjects.tsv", "subjects"),
        tableEntry("outputs_Tab2.tsv", "outputs"),
        tableEntry("outputs_Tab3.tsv", "outputs"),
        tableEntry("Example_Tab2.tsv", "raw"),
      ],
    };
    expect(kindsWithTable(study, NOTE_KINDS)).toEqual(["subjects", "outputs"]);
    expect(kindsWithTable({ tables: [] }, NOTE_KINDS)).toEqual([]);
  });
});

describe("hasNotes", () => {
  it("is true for a description or a comment, also one just added and empty", () => {
    expect(hasNotes({ descriptions: [""], comments: [] })).toBe(true);
    expect(hasNotes({ descriptions: [], comments: [{ user: "curator", text: "" }] })).toBe(true);
    expect(hasNotes({ descriptions: [], comments: [] })).toBe(false);
    expect(hasNotes(undefined)).toBe(false);
  });
});
