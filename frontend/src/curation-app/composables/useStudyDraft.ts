/**
 * The draft of study.json of the open study, which the study store owns: the form, the document
 * that it was read from and its revision, the changed fields and the sections that show them,
 * Save over the revision, Discard with Undo, the conflict with a newer file on disk and Reload,
 * and which notes panels are open. The Metadata section edits the form, the Data section the
 * notes of the tables in it, and both show its save bar (StudySaveBar).
 *
 * The form follows study.json on disk while it has no unsaved edits. `reset` forgets the draft
 * when the study closes; the answer of a save that started before changes nothing.
 */
import { computed, getCurrentScope, onScopeDispose, ref, shallowRef, watch, type ComputedRef, type Ref } from "vue";
import { isNoUser, isRevisionConflict, isValidationError } from "../api/client";
import type {
  DocumentState,
  MetadataWrite,
  StudyDetail,
  StudyMetadata,
  TableKind,
  ValidationIssue,
} from "../api/types";
import {
  changedFields,
  clone,
  copyField,
  fieldText,
  fromForm,
  issuesByTarget,
  mergeOnReload,
  readStudyJson,
  targetLabel,
  toForm,
  unsavedSections,
  type FieldMark,
  type MetadataForm,
} from "../metadata";
import { kindsWithTable, notesKindOf, notesKindsOf } from "../notes";
import { failureOf, issuesFailure, NOTICE_MS, userHint, type ActionFailure, type Section } from "../study";
import { noteKinds } from "../tableKinds";
import { useChangedFields } from "./useChangedFields";
import { createNotice } from "./useNotice";

/** What the draft reads and writes. */
export interface DraftSource {
  /** The detail of the open study; null while none is open or it loads. */
  detail: () => StudyDetail | null;
  /** Writes study.json over `revision`; a stale revision rejects with a revision conflict. */
  save: (revision: string, metadata: StudyMetadata) => Promise<MetadataWrite>;
}

/** The sections that edit the draft and show its save bar. */
export type DraftSection = Extract<Section, "metadata" | "data">;

/** study.json changed on disk: its revision, and its content as a form, null when it is no JSON object. */
export interface DraftConflict {
  revision: string;
  theirs: MetadataForm | null;
}

export interface StudyDraft {
  /** The form; null while an invalid study.json shows its issues instead. */
  form: Ref<MetadataForm | null>;
  /** The document that the form started from; null for a new study.json. */
  base: Readonly<Ref<MetadataForm | null>>;
  /** Whether the app can write study.json: it has a revision to save over. */
  writable: ComputedRef<boolean>;
  dirty: ComputedRef<boolean>;
  /** The fields with unsaved changes, the keys of `changedFields(base, form)`. */
  changed: ComputedRef<string[]>;
  /** The sections with unsaved fields, whose tabs the study page marks. */
  unsaved: ComputedRef<Section[]>;
  saving: Readonly<Ref<boolean>>;
  /** A conflict with a readable study.json blocks Save until Reload. */
  canSave: ComputedRef<boolean>;
  /** The bar shows unsaved changes and the outcome of the last save, reload, discard or reference change. */
  barShown: ComputedRef<boolean>;
  /** A refused or failed save: why, and the issues that no field shows. Its alert closes it. */
  failure: Ref<ActionFailure | null>;
  /**
   * The failure of the last save as the bar of `section` shows it. A refused save asks to fix the
   * fields that the section marks, and lists the issues of the others with their fields: Data
   * shows the notes of `kind` above the selected table, Metadata the other fields of the form.
   */
  failureIn(section: DraftSection, kind?: TableKind | null): ActionFailure | null;
  /** The messages of a refused save by field. */
  errors: Readonly<Ref<ReadonlyMap<string, string[]>>>;
  /** Writes need a user: what to do about it. */
  noUser: Readonly<Ref<string | null>>;
  conflict: Readonly<Ref<DraftConflict | null>>;
  /** The fields that changed on disk at the last reload. */
  marks: Readonly<Ref<ReadonlyMap<string, FieldMark>>>;
  /** The disk values of the fields that changed on both sides at the last reload. */
  disk: ComputedRef<ReadonlyMap<string, string>>;
  /** The fields that changed on both sides at the last reload; null before a reload. Its alert closes it. */
  reloaded: Ref<string[] | null>;
  /** Why reference.json could not be refreshed after a save. Its alert closes it. */
  referenceError: Ref<string>;
  /** The notice of the last action that succeeded, for a few seconds. */
  notice: Readonly<Ref<string>>;
  /** Whether Undo brings back the edits of the last Discard. */
  undoable: ComputedRef<boolean>;
  /** The table kinds whose notes panels are open, kept while the study is open. */
  notesOpen: Readonly<Ref<ReadonlySet<TableKind>>>;
  /** Show `text` in the bar for a few seconds; an empty text clears it. */
  announce(text: string): void;
  save(): Promise<void>;
  /** Put the edits on top of study.json on disk and mark what changed there. */
  reload(): void;
  /** Drop the edits: the form shows study.json as the app last read it. */
  discard(): void;
  /** Bring back the form of the last Discard, over the revision it was read from. */
  undoDiscard(): void;
  /** Replace the edit of a field that changed on both sides with the version on disk. */
  useDisk(key: string): void;
  /** An invalid study.json: edit `start` as a new study.json. */
  startNew(start: MetadataForm): void;
  setNotesOpen(kind: TableKind, open: boolean): void;
  /** Forget the draft, as when the study closes. */
  reset(): void;
}

/** The form before the last Discard, which Undo restores for a few seconds or until the next edit. */
interface Discarded {
  form: MetadataForm;
  base: MetadataForm | null;
  revision: string | null;
  adopted: string | null | undefined;
  marks: ReadonlyMap<string, FieldMark>;
  reloaded: string[] | null;
}

export function useStudyDraft(source: DraftSource): StudyDraft {
  /** study.json as the app last read it. */
  const studyJson = computed(() => source.detail()?.metadata ?? null);
  /** The table kinds with notes in study.json, as the study page describes them. */
  const kinds = computed(() => {
    const detail = source.detail();
    return detail ? noteKinds(detail) : [];
  });
  /** The kinds that a table of the study has, whose notes the Data section shows. */
  const tabled = computed(() => {
    const detail = source.detail();
    return detail ? kindsWithTable(detail, kinds.value) : [];
  });

  /** The revision of study.json that a save goes over; null for a file that the app cannot write. */
  const revision = ref<string | null>(null);
  /** The revision that the form was last read from, to notice a new one in the detail. */
  let adopted: string | null | undefined;
  /** Counts the resets: a save that started before one changes nothing. */
  let generation = 0;
  const base = ref<MetadataForm | null>(null);
  const form = ref<MetadataForm | null>(null);
  const saving = ref(false);
  const failure = shallowRef<ActionFailure | null>(null);
  const errors = shallowRef<ReadonlyMap<string, string[]>>(new Map());
  const noUser = ref<string | null>(null);
  const conflict = shallowRef<DraftConflict | null>(null);
  const marks = shallowRef<ReadonlyMap<string, FieldMark>>(new Map());
  const reloaded = shallowRef<string[] | null>(null);
  const referenceError = ref("");
  const { notice, announce } = createNotice();
  const notesOpen = shallowRef<ReadonlySet<TableKind>>(new Set());
  const undo = shallowRef<Discarded | null>(null);
  let undoTimer: ReturnType<typeof setTimeout> | undefined;

  const writable = computed(() => revision.value !== null);
  /** The fields with unsaved changes, compared field by field. */
  const changed = useChangedFields(base, form);
  const unsaved = computed(() => unsavedSections(base.value, form.value, changed.value, tabled.value));
  const dirty = computed(() => unsaved.value.length > 0);
  const undoable = computed(() => undo.value !== null);
  const barShown = computed(
    () =>
      dirty.value ||
      saving.value ||
      conflict.value !== null ||
      failure.value !== null ||
      noUser.value !== null ||
      reloaded.value !== null ||
      referenceError.value !== "" ||
      notice.value !== "" ||
      undo.value !== null,
  );
  const canSave = computed(() => dirty.value && writable.value && !saving.value && !conflict.value?.theirs);
  const disk = computed<ReadonlyMap<string, string>>(() => {
    const theirs = base.value;
    const values = new Map<string, string>();
    if (theirs)
      for (const [key, mark] of marks.value) if (mark === "conflict") values.set(key, fieldText(theirs, key));
    return values;
  });

  function openNotes(opened: Iterable<TableKind>): void {
    const closed = [...opened].filter((kind) => !notesOpen.value.has(kind));
    if (closed.length) notesOpen.value = new Set([...notesOpen.value, ...closed]);
  }

  function setNotesOpen(kind: TableKind, open: boolean): void {
    const next = new Set(notesOpen.value);
    if (open) next.add(kind);
    else next.delete(kind);
    notesOpen.value = next;
  }

  function clearFeedback(): void {
    failure.value = null;
    errors.value = new Map();
    noUser.value = null;
    conflict.value = null;
    marks.value = new Map();
    reloaded.value = null;
  }

  /** Show `state` in the form, dropping the edits and the feedback of the last save. */
  function adopt(state: DocumentState<StudyMetadata>): void {
    adopted = state.revision;
    revision.value = state.revision;
    base.value = state.value ? toForm(state.value, kinds.value) : null;
    form.value = base.value ? clone(base.value) : null;
    clearFeedback();
  }

  // The form follows study.json on disk while it has no unsaved edits, also when the edits are
  // undone by hand after the file changed.
  watch(
    [studyJson, dirty, saving],
    ([state, edited, busy]) => {
      if (state && state.revision !== adopted && !edited && !busy) adopt(state);
    },
    { immediate: true },
  );

  // The notes of a kind open by themselves when study.json on disk gets an issue in them; a panel
  // that the curator closed stays closed while the same issues stay.
  const fileIssueKinds = computed(() =>
    notesKindsOf((studyJson.value?.issues ?? []).map((issue) => issue.field), kinds.value),
  );
  /** The kinds whose notes had an issue on disk at the last read, which opened then; a reset forgets them. */
  let issueKinds: TableKind[] = [];
  watch(
    fileIssueKinds,
    (now) => {
      openNotes(now.filter((kind) => !issueKinds.includes(kind)));
      issueKinds = now;
    },
    { immediate: true },
  );

  function useDisk(key: string): void {
    if (!form.value || !base.value) return;
    copyField(form.value, base.value, key);
    marks.value = new Map([...marks.value, [key, "disk"]]);
    reloaded.value = reloaded.value?.filter((field) => field !== key) ?? null;
  }

  /**
   * A refused save: the issues by field, which the sections mark, and the issues of no field,
   * which the bar lists. The notes with an issue open.
   */
  function refused(issues: ValidationIssue[], sent: MetadataForm): void {
    const grouped = issuesByTarget(sent, issues);
    errors.value = grouped.fields;
    failure.value = issuesFailure("study.json was not saved.", grouped.general);
    openNotes(notesKindsOf(grouped.fields.keys(), kinds.value));
  }

  /** Whether `section` shows the field `key` of the form: Data the notes of `kind`, Metadata the others. */
  function shownIn(key: string, section: DraftSection, kind: TableKind | null): boolean {
    if (section === "data") return kind !== null && notesKindOf(key, [kind]) !== null;
    return notesKindOf(key, tabled.value) === null;
  }

  function failureIn(section: DraftSection, kind: TableKind | null = null): ActionFailure | null {
    const value = failure.value;
    // Only a refused save has issues by field, which every save, reload and discard clears first.
    if (!value || !errors.value.size) return value;
    const fields = [...errors.value];
    const marked = fields.some(([key]) => shownIn(key, section, kind));
    const listed = fields
      .filter(([key]) => !shownIn(key, section, kind))
      .flatMap(([key, messages]) => messages.map((message) => `${targetLabel(key)}: ${message}`));
    return issuesFailure(marked ? `${value.text} Fix the marked fields.` : value.text, [...value.issues, ...listed]);
  }

  async function save(): Promise<void> {
    const current = form.value;
    const at = revision.value;
    if (!current || at === null || !canSave.value) return;
    const sent = clone(current);
    const metadata = fromForm(sent);
    const started = generation;
    saving.value = true;
    failure.value = null;
    errors.value = new Map();
    noUser.value = null;
    referenceError.value = "";
    announce("");
    try {
      const result = await source.save(at, metadata);
      if (started !== generation) return;
      const written = toForm(metadata, kinds.value);
      // Edits made while the save ran stay unsaved; otherwise the form shows what was written.
      if (form.value && changedFields(sent, form.value).length === 0) form.value = clone(written);
      base.value = written;
      revision.value = result.revision;
      adopted = result.revision;
      conflict.value = null;
      marks.value = new Map();
      reloaded.value = null;
      if (result.reference_error)
        referenceError.value = `study.json saved; reference.json could not be refreshed: ${result.reference_error}`;
      announce("study.json saved.");
    } catch (caught) {
      if (started !== generation) return;
      if (isRevisionConflict(caught))
        conflict.value = { revision: caught.body.revision, theirs: readStudyJson(caught.body.content, kinds.value) };
      else if (isValidationError(caught)) refused(caught.body.issues, sent);
      else if (isNoUser(caught)) noUser.value = userHint(caught);
      else failure.value = failureOf(caught, "study.json was not saved.");
    } finally {
      if (started === generation) saving.value = false;
    }
  }

  function reload(): void {
    const changed = conflict.value;
    if (!changed?.theirs || !form.value) return;
    const start = base.value ?? toForm({}, kinds.value);
    const { merged, conflicts } = mergeOnReload(start, form.value, changed.theirs);
    marks.value = new Map(
      changedFields(start, changed.theirs).map((key): [string, FieldMark] => [
        key,
        conflicts.includes(key) ? "conflict" : "disk",
      ]),
    );
    reloaded.value = conflicts;
    base.value = changed.theirs;
    form.value = merged;
    revision.value = changed.revision;
    adopted = changed.revision;
    conflict.value = null;
    failure.value = null;
    errors.value = new Map();
    openNotes(notesKindsOf(marks.value.keys(), kinds.value));
  }

  function discard(): void {
    const state = studyJson.value;
    if (!state || !form.value) return;
    const discarded: Discarded = {
      form: clone(form.value),
      base: base.value && clone(base.value),
      revision: revision.value,
      adopted,
      marks: marks.value,
      reloaded: reloaded.value,
    };
    adopt(state);
    undo.value = discarded;
    clearTimeout(undoTimer);
    undoTimer = setTimeout(() => (undo.value = null), NOTICE_MS);
    announce("Changes discarded.");
  }

  function undoDiscard(): void {
    const discarded = undo.value;
    if (!discarded) return;
    undo.value = null;
    clearTimeout(undoTimer);
    form.value = discarded.form;
    base.value = discarded.base;
    revision.value = discarded.revision;
    adopted = discarded.adopted;
    marks.value = discarded.marks;
    reloaded.value = discarded.reloaded;
    announce("Changes restored.");
  }

  // The next edit ends the undo of a Discard.
  watch(dirty, (value) => {
    if (value && undo.value) {
      undo.value = null;
      clearTimeout(undoTimer);
    }
  });

  function startNew(start: MetadataForm): void {
    form.value = start;
    base.value = null;
  }

  // The timers of the notice and of Undo stop with the store or the component that owns the draft.
  if (getCurrentScope())
    onScopeDispose(() => {
      clearTimeout(undoTimer);
      announce("");
    });

  function reset(): void {
    generation += 1;
    clearTimeout(undoTimer);
    revision.value = null;
    adopted = undefined;
    base.value = null;
    form.value = null;
    saving.value = false;
    clearFeedback();
    referenceError.value = "";
    announce("");
    undo.value = null;
    notesOpen.value = new Set();
    issueKinds = [];
  }

  return {
    form,
    base,
    writable,
    dirty,
    changed,
    unsaved,
    saving,
    canSave,
    barShown,
    failure,
    failureIn,
    errors,
    noUser,
    conflict,
    marks,
    disk,
    reloaded,
    referenceError,
    notice,
    undoable,
    notesOpen,
    announce,
    save,
    reload,
    discard,
    undoDiscard,
    useDisk,
    startNew,
    setNotesOpen,
    reset,
  };
}
