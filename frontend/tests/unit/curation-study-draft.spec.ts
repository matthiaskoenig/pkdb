import { afterEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, shallowRef, type EffectScope } from "vue";
import { ApiError } from "../../src/curation-app/api/client";
import type { MetadataWrite, StudyDetail, StudyMetadata, ValidationIssue } from "../../src/curation-app/api/types";
import { useStudyDraft, type StudyDraft } from "../../src/curation-app/composables/useStudyDraft";
import { changedFields, toForm } from "../../src/curation-app/metadata";
import { NOTICE_MS } from "../../src/curation-app/study";
import { fullStudyMetadata, NOTE_KINDS, studyDetail } from "./curation-fixtures";

/** The detail of caffeine/Example with `metadata` as its study.json at `revision`; null for an invalid one. */
function withMetadata(
  metadata: StudyMetadata | null,
  revision: string | null = "study-1",
  issues: ValidationIssue[] = [],
): StudyDetail {
  return studyDetail({ metadata: { revision, value: metadata, issues } });
}

/** An issue of study.json as the library gives it: the message names the field, the detail does not. */
function issue(field: string, detail: string): ValidationIssue {
  return { code: "invalid_study_json", severity: "error", message: `${field}: ${detail}`, field, context: { detail } };
}

let scope: EffectScope | undefined;
const detail = shallowRef<StudyDetail | null>(null);
/** The writes of study.json in the order of the saves. */
let writes: { revision: string; metadata: StudyMetadata }[] = [];
/** How the local server answers a write; a test replaces it. */
let answer: (revision: string, metadata: StudyMetadata) => Promise<MetadataWrite>;

/** Writes study.json as the local server would: the detail has the new revision afterwards. */
async function written(_revision: string, metadata: StudyMetadata): Promise<MetadataWrite> {
  const revision = `study-${writes.length + 1}`;
  detail.value = withMetadata(metadata, revision);
  return { revision, reference: null, reference_error: null };
}

/** The draft of the study `value`, after it read its study.json. */
async function draftOf(value: StudyDetail | null = withMetadata(fullStudyMetadata())): Promise<StudyDraft> {
  detail.value = value;
  writes = [];
  answer = written;
  scope = effectScope();
  const draft = scope.run(() =>
    useStudyDraft({
      detail: () => detail.value,
      save: (revision, metadata) => {
        writes.push({ revision, metadata });
        return answer(revision, metadata);
      },
    }),
  )!;
  await nextTick();
  return draft;
}

afterEach(() => {
  scope?.stop();
  vi.useRealTimers();
});

describe("useStudyDraft", () => {
  it("reads study.json of the open study and follows it on disk while it has no unsaved edits", async () => {
    const draft = await draftOf();
    expect(draft.form.value?.creator).toBe("curator");
    expect(draft.dirty.value).toBe(false);
    expect(draft.writable.value).toBe(true);

    detail.value = withMetadata(fullStudyMetadata({ licence: "open" }), "study-2");
    await nextTick();
    expect(draft.form.value?.licence).toBe("open");

    // Edits keep the form; undoing them by hand shows the newer file.
    draft.form.value!.creator = "janekg";
    detail.value = withMetadata(fullStudyMetadata({ licence: "open", creator: "mkoenig" }), "study-3");
    await nextTick();
    expect(draft.form.value?.creator).toBe("janekg");
    draft.form.value!.creator = "curator";
    await nextTick();
    expect(draft.form.value?.creator).toBe("mkoenig");
    expect(draft.bannerShown.value).toBe(false);
  });

  it("names the changed fields by the section that shows them", async () => {
    const draft = await draftOf();
    draft.form.value!.notes.outputs.descriptions.push("More.");
    expect(draft.unsaved.value).toEqual(["data"]);
    // studyDetail has no scatters table: Metadata shows their notes.
    draft.form.value!.notes.scatters.comments.push({ user: "curator", text: "Figure 3." });
    expect(draft.unsaved.value).toEqual(["metadata", "data"]);
    expect(draft.dirty.value).toBe(true);
    expect(draft.bannerShown.value).toBe(true);
    expect(draft.canSave.value).toBe(true);
  });

  it("lists the changed fields, as changedFields names them", async () => {
    const draft = await draftOf();
    expect(draft.changed.value).toEqual([]);
    draft.form.value!.creator = "janekg";
    draft.form.value!.notes.outputs.descriptions.push("More.");
    expect(draft.changed.value).toEqual(changedFields(draft.base.value!, draft.form.value!));
    expect(draft.changed.value).toEqual(expect.arrayContaining(["creator", "notes.outputs.descriptions"]));
  });

  it("saves over the revision it was read from and keeps the edits made while the save ran", async () => {
    const draft = await draftOf();
    let finish: () => void = () => undefined;
    answer = (revision, metadata) =>
      new Promise((resolve) => (finish = () => resolve(written(revision, metadata))));
    draft.form.value!.reference.doi = "10.1000/xyz";
    const saved = draft.save();
    expect(draft.saving.value).toBe(true);
    expect(draft.canSave.value).toBe(false);
    draft.form.value!.notes.subjects.descriptions.push("Typed during the save.");
    finish();
    await saved;

    expect(writes).toHaveLength(1);
    expect(writes[0]?.revision).toBe("study-1");
    expect(writes[0]?.metadata.reference).toEqual({ pmid: "2895442", doi: "10.1000/xyz" });
    expect(writes[0]?.metadata.notes.subjects).toBeUndefined();
    // The edit made during the save stays unsaved, and the next save goes over the new revision.
    expect(draft.form.value?.notes.subjects.descriptions).toEqual(["Typed during the save."]);
    expect(draft.unsaved.value).toEqual(["data"]);
    expect(draft.notice.value).toBe("study.json saved.");
    answer = written;
    await draft.save();
    expect(writes[1]?.revision).toBe("study-2");
  });

  it("says when reference.json could not be refreshed after the save", async () => {
    const draft = await draftOf();
    answer = async (revision, metadata) => ({ ...(await written(revision, metadata)), reference_error: "PubMed is offline" });
    draft.form.value!.reference.pmid = "999";
    await draft.save();
    expect(draft.referenceError.value).toBe("study.json saved; reference.json could not be refreshed: PubMed is offline");
  });

  it("lists the changed fields in the order of the form", async () => {
    const draft = await draftOf();
    expect(draft.changed.value).toEqual([]);
    draft.form.value!.notes.outputs.descriptions.push("Read from Table 2.");
    draft.form.value!.provenance.source_key = "pkdb.edited";
    await nextTick();
    expect(draft.changed.value).toEqual(["provenance.source_key", "notes.outputs.descriptions"]);
    expect(draft.unsaved.value).toEqual(["metadata", "data"]);
  });

  it("lists for a new study.json the fields that it sets", async () => {
    const draft = await draftOf(withMetadata(null));
    expect(draft.changed.value).toEqual([]);
    draft.startNew(toForm({ creator: "curator" }, NOTE_KINDS));
    await nextTick();
    expect(draft.changed.value).toEqual(["creator"]);
    expect(draft.unsaved.value).toEqual(["metadata"]);
  });

  it("lists every issue of a refused save with its field in a section that shows no field", async () => {
    const draft = await draftOf();
    answer = () =>
      Promise.reject(
        new ApiError(422, {
          error: "Invalid study.json",
          issues: [
            issue("reference.pmid", "A PubMed ID has only digits."),
            issue("notes.outputs.descriptions.0", "Enter some text or remove this entry."),
          ],
        }),
      );
    draft.form.value!.reference.pmid = "abc";
    draft.form.value!.notes.outputs.descriptions[0] = " ";
    await draft.save();
    expect(draft.failureIn("review")).toMatchObject({
      text: "study.json was not saved.",
      issues: ["PMID: A PubMed ID has only digits.", "Descriptions of outputs: Enter some text or remove this entry."],
    });
  });

  it("marks the fields of a refused save, lists in each section the issues of the fields it does not show, and opens their notes", async () => {
    const draft = await draftOf();
    answer = () =>
      Promise.reject(
        new ApiError(422, {
          error: "Invalid study.json",
          issues: [
            issue("notes.outputs.descriptions.0", "Enter some text or remove this entry."),
            issue("notes.scatters.descriptions.0", "Enter some text or remove this entry."),
            { code: "invalid_study_json", severity: "error", message: "format: Input should be 2", field: "format" },
          ],
        }),
      );
    draft.form.value!.notes.outputs.descriptions[0] = " ";
    // studyDetail has no scatters table: Metadata shows their notes, and the issue at its field.
    draft.form.value!.notes.scatters.descriptions.push(" ");
    await draft.save();

    expect(draft.errors.value.get("notes.outputs.descriptions.0")).toEqual(["Enter some text or remove this entry."]);
    expect(draft.errors.value.get("notes.scatters.descriptions.0")).toEqual(["Enter some text or remove this entry."]);
    expect(draft.failure.value?.text).toBe("study.json was not saved.");
    expect(draft.failure.value?.issues).toEqual(["format: Input should be 2"]);
    // Metadata shows the notes of a kind without a table; Data the notes of the selected table.
    expect(draft.failureIn("metadata")).toMatchObject({
      text: "study.json was not saved. Fix the marked fields.",
      issues: ["format: Input should be 2", "Descriptions of outputs: Enter some text or remove this entry."],
    });
    expect(draft.failureIn("data", "outputs")).toMatchObject({
      text: "study.json was not saved. Fix the marked fields.",
      issues: ["format: Input should be 2", "Descriptions of scatters: Enter some text or remove this entry."],
    });
    expect(draft.failureIn("data", "subjects")).toMatchObject({
      text: "study.json was not saved.",
      issues: [
        "format: Input should be 2",
        "Descriptions of outputs: Enter some text or remove this entry.",
        "Descriptions of scatters: Enter some text or remove this entry.",
      ],
    });
    expect([...draft.notesOpen.value]).toEqual(["outputs", "scatters"]);
    expect(draft.form.value?.notes.outputs.descriptions).toEqual([" "]);
  });

  it("blocks Save on a changed study.json until Reload puts the edits on top, marks the fields and opens their notes", async () => {
    const draft = await draftOf();
    const disk = fullStudyMetadata({
      creator: "janekg",
      notes: { ...fullStudyMetadata().notes, subjects: { descriptions: ["From disk."], comments: [] } },
    });
    answer = () =>
      Promise.reject(
        new ApiError(409, { error: "changed", file: "study.json", revision: "study-2", content: JSON.stringify(disk) }),
      );
    draft.form.value!.licence = "open";
    await draft.save();
    expect(draft.conflict.value?.revision).toBe("study-2");
    expect(draft.canSave.value).toBe(false);

    draft.reload();
    expect(draft.form.value?.licence).toBe("open");
    expect(draft.form.value?.creator).toBe("janekg");
    expect(draft.marks.value.get("creator")).toBe("disk");
    expect(draft.marks.value.get("notes.subjects.descriptions")).toBe("disk");
    expect(draft.reloaded.value).toEqual([]);
    expect([...draft.notesOpen.value]).toEqual(["subjects"]);
    expect(draft.conflict.value).toBeNull();
    expect(draft.canSave.value).toBe(true);

    answer = written;
    await draft.save();
    expect(writes.at(-1)).toMatchObject({ revision: "study-2", metadata: { licence: "open", creator: "janekg" } });
  });

  it("keeps Save on a changed study.json that is no JSON object, which cannot be merged", async () => {
    const draft = await draftOf();
    answer = () =>
      Promise.reject(new ApiError(409, { error: "changed", file: "study.json", revision: "study-2", content: "{ broken" }));
    draft.form.value!.licence = "open";
    await draft.save();
    expect(draft.conflict.value).toEqual({ revision: "study-2", theirs: null });
    expect(draft.canSave.value).toBe(true);
    expect(draft.form.value?.licence).toBe("open");

    // Reload has nothing to merge; the next save goes over the revision the form was read from.
    draft.reload();
    expect(draft.conflict.value).not.toBeNull();
    answer = written;
    await draft.save();
    expect(writes.at(-1)?.revision).toBe("study-1");
    expect(draft.conflict.value).toBeNull();
  });

  it("replaces the edit of a field changed on both sides with the version on disk", async () => {
    const draft = await draftOf();
    const disk = fullStudyMetadata({ creator: "janekg", licence: "open" });
    answer = () =>
      Promise.reject(
        new ApiError(409, { error: "changed", file: "study.json", revision: "study-2", content: JSON.stringify(disk) }),
      );
    draft.form.value!.creator = "mkoenig";
    await draft.save();
    draft.reload();
    expect(draft.form.value?.creator).toBe("mkoenig");
    expect(draft.reloaded.value).toEqual(["creator"]);
    expect(draft.marks.value.get("creator")).toBe("conflict");
    expect([...draft.disk.value]).toEqual([["creator", "janekg"]]);

    draft.useDisk("creator");
    expect(draft.form.value?.creator).toBe("janekg");
    expect(draft.marks.value.get("creator")).toBe("disk");
    expect(draft.disk.value.size).toBe(0);
    expect(draft.reloaded.value).toEqual([]);
    expect(draft.dirty.value).toBe(false);
  });

  it("keeps what the local server said about a save that failed", async () => {
    const draft = await draftOf();
    answer = () =>
      Promise.reject(
        new ApiError(500, {
          error: "Could not save study.json of caffeine/Example.",
          code: "unexpected",
          detail: "OSError: disk full",
          action: "Save study.json (POST /local/studies/metadata)",
          request_id: "3f9c2a71",
          time: "2026-10-12T10:00:00+02:00",
        }),
      );
    draft.form.value!.creator = "janekg";
    await draft.save();
    expect(draft.failure.value?.text).toBe("Could not save study.json of caffeine/Example.");
    expect(draft.failure.value?.details?.requestId).toBe("3f9c2a71");
    expect(draft.form.value?.creator).toBe("janekg");
    expect(draft.saving.value).toBe(false);
  });

  it("asks to set the user when a save needs one", async () => {
    const draft = await draftOf();
    answer = () =>
      Promise.reject(new ApiError(403, { error: "no_user", message: "Set a user with --user or in the settings." }));
    draft.form.value!.creator = "janekg";
    await draft.save();
    expect(draft.noUser.value).toBe("Set your PK-DB user in Connection settings.");
  });

  it("discards the edits, and Undo brings them back for a few seconds or until the next edit", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const draft = await draftOf();
    draft.form.value!.creator = "janekg";
    draft.discard();
    expect(draft.form.value?.creator).toBe("curator");
    expect(draft.undoable.value).toBe(true);
    expect(draft.notice.value).toBe("Changes discarded.");

    draft.undoDiscard();
    expect(draft.form.value?.creator).toBe("janekg");
    expect(draft.undoable.value).toBe(false);

    // The next edit ends the undo.
    draft.discard();
    draft.form.value!.licence = "open";
    await nextTick();
    expect(draft.undoable.value).toBe(false);

    // So do a few seconds.
    draft.discard();
    expect(draft.undoable.value).toBe(true);
    vi.advanceTimersByTime(NOTICE_MS);
    expect(draft.undoable.value).toBe(false);
    expect(draft.bannerShown.value).toBe(false);
  });

  it("brings back the edits over the revision they were read from when Undo follows a change on disk", async () => {
    const draft = await draftOf();
    draft.form.value!.creator = "janekg";
    detail.value = withMetadata(fullStudyMetadata({ licence: "open" }), "study-2");
    await nextTick();
    draft.discard();
    expect(draft.form.value?.licence).toBe("open");
    expect(draft.form.value?.creator).toBe("curator");

    draft.undoDiscard();
    await nextTick();
    expect(draft.form.value?.creator).toBe("janekg");
    expect(draft.form.value?.licence).toBe("closed");
    expect(draft.dirty.value).toBe(true);
    await draft.save();
    expect(writes.at(-1)?.revision).toBe("study-1");
  });

  it("stops the timers of its notice and of Undo when its scope ends", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const draft = await draftOf();
    draft.form.value!.creator = "janekg";
    draft.discard();
    expect(vi.getTimerCount()).toBe(2);
    scope?.stop();
    expect(vi.getTimerCount()).toBe(0);
    expect(draft.notice.value).toBe("");
  });

  it("starts a new study.json over the revision of an invalid one", async () => {
    const draft = await draftOf(withMetadata(null, "broken-1"));
    expect(draft.form.value).toBeNull();
    expect(draft.writable.value).toBe(true);
    draft.startNew(toForm(fullStudyMetadata(), NOTE_KINDS));
    expect(draft.unsaved.value).toEqual(["metadata"]);
    await draft.save();
    expect(writes).toEqual([{ revision: "broken-1", metadata: expect.objectContaining({ creator: "curator" }) }]);
  });

  it("ignores a save that ends after the study closed", async () => {
    const draft = await draftOf();
    let finish: () => void = () => undefined;
    answer = () =>
      new Promise((resolve) => (finish = () => resolve({ revision: "study-2", reference: null, reference_error: null })));
    draft.form.value!.creator = "janekg";
    const saved = draft.save();

    draft.reset();
    detail.value = studyDetail({
      id: "caffeine/Other",
      metadata: { revision: "other-1", value: fullStudyMetadata({ creator: "mkoenig" }), issues: [] },
    });
    await nextTick();
    finish();
    await saved;

    expect(draft.form.value?.creator).toBe("mkoenig");
    expect(draft.dirty.value).toBe(false);
    expect(draft.saving.value).toBe(false);
    expect(draft.notice.value).toBe("");
    answer = written;
    draft.form.value!.creator = "janekg";
    await draft.save();
    expect(writes.at(-1)?.revision).toBe("other-1");
  });

  it("opens the notes of a kind once when study.json on disk has an issue in them", async () => {
    const broken = withMetadata(null, "broken-1", [
      issue("notes.subjects.comments.0.user", "A user name has no spaces."),
      issue("creator", "Enter a user name."),
    ]);
    const draft = await draftOf(broken);
    expect(draft.form.value).toBeNull();
    expect([...draft.notesOpen.value]).toEqual(["subjects"]);

    // Closed by the curator, it stays closed while the same issues stay.
    draft.setNotesOpen("subjects", false);
    detail.value = { ...broken, files_version: "files-2" };
    await nextTick();
    expect(draft.notesOpen.value.size).toBe(0);
  });

  it("opens the notes with an issue on disk again for the next study", async () => {
    const issues = [issue("notes.subjects.comments.0.user", "A user name has no spaces.")];
    const draft = await draftOf(withMetadata(null, "broken-1", issues));
    draft.reset();
    detail.value = studyDetail({ id: "caffeine/Other", metadata: { revision: "other-1", value: null, issues } });
    await nextTick();
    expect([...draft.notesOpen.value]).toEqual(["subjects"]);
  });

  it("forgets the form, the feedback and the open notes when reset", async () => {
    const draft = await draftOf();
    draft.form.value!.creator = "janekg";
    draft.setNotesOpen("outputs", true);
    draft.announce("Something.");
    draft.reset();
    expect(draft.form.value).toBeNull();
    expect(draft.dirty.value).toBe(false);
    expect(draft.notesOpen.value.size).toBe(0);
    expect(draft.notice.value).toBe("");
    expect(draft.bannerShown.value).toBe(false);
  });
});
