<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VChip,
  VDialog,
  VExpansionPanel,
  VExpansionPanels,
  VExpansionPanelText,
  VExpansionPanelTitle,
  VForm,
  VRadio,
  VRadioGroup,
  VSelect,
  VSpacer,
  VTextField,
} from "vuetify/components";
import { isNoUser, isRevisionConflict, isValidationError } from "../api/client";
import type { DocumentState, Profile, StudyMetadata, TableKind, ValidationIssue } from "../api/types";
import DiskVersion from "../components/DiskVersion.vue";
import NotesFields from "../components/NotesFields.vue";
import PeopleFields from "../components/PeopleFields.vue";
import ReferenceDialog from "../components/ReferenceDialog.vue";
import UserHint from "../components/UserHint.vue";
import { useNotice } from "../composables/useNotice";
import { sectionHeading, useReturnFocus } from "../composables/useReturnFocus";
import {
  changedFields,
  clone,
  copyField,
  fieldLabel,
  fieldText,
  fromForm,
  issuesByTarget,
  markMessage,
  mergeOnReload,
  PROVENANCE_LABELS,
  readStudyJson,
  startForm,
  TABLE_KIND_LABELS,
  TABLE_KINDS,
  toForm,
  withKind,
  type FieldMark,
  type MetadataForm,
  type ProvenanceKind,
} from "../metadata";
import { issueUrl, plural } from "../overview";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { knownProfiles, messageOf, NOTICE_MS, releaseLabel, userHint } from "../study";

/**
 * The form of study.json. Saves are explicit and go over the revision that the form was read
 * from: a file changed on disk meanwhile is a conflict, and Reload puts the edits on top of the
 * new version. Leaving with unsaved edits asks first.
 */
const emit = defineEmits<{ unsaved: [value: boolean] }>();

const study = useStudyStore();
const overview = useOverviewStore();
const ids = {
  reference: useId(),
  people: useId(),
  access: useId(),
  release: useId(),
  notes: useId(),
  tables: useId(),
  leave: useId(),
};

const detail = computed(() => study.detail);
/** study.json as the app last read it. */
const studyJson = computed(() => detail.value?.metadata ?? null);

/** The revision of study.json that a save goes over; null for a file that the app cannot write. */
const revision = ref<string | null>(null);
/** The revision that the form was last read from, to notice a new one in the detail. */
let adopted: string | null | undefined;
/** The document that the form started from; null for an invalid study.json. */
const base = ref<MetadataForm | null>(null);
/** The form; null while an invalid study.json shows its issues instead. */
const form = ref<MetadataForm | null>(null);

const saving = ref(false);
/** A refused save: why, and the issues that no field shows. */
const failure = ref<{ text: string; issues: string[] } | null>(null);
/** The messages of a refused save by field. */
const errors = ref<ReadonlyMap<string, string[]>>(new Map());
/** Writes need a user: what to do about it. */
const noUser = ref<string | null>(null);
/** study.json changed on disk: its revision and its content as a form, null when it is no JSON object. */
const conflict = ref<{ revision: string; theirs: MetadataForm | null } | null>(null);
/** The fields that changed on disk at the last reload. */
const marks = ref<ReadonlyMap<string, FieldMark>>(new Map());
/** The fields that changed on both sides at the last reload; null before a reload. */
const reloaded = ref<string[] | null>(null);
const referenceError = ref("");
const { notice, announce } = useNotice();
const referenceOpen = ref(false);
const openPanels = ref<TableKind[]>([]);

/** The form before the last Discard, which Undo restores for a few seconds or until the next edit. */
interface Discarded {
  form: MetadataForm;
  base: MetadataForm | null;
  revision: string | null;
  adopted: string | null | undefined;
  marks: ReadonlyMap<string, FieldMark>;
  reloaded: string[] | null;
}
const undo = ref<Discarded | null>(null);
let undoTimer: ReturnType<typeof setTimeout> | undefined;

const writable = computed(() => revision.value !== null);
const dirty = computed(
  () => form.value !== null && (base.value === null || changedFields(base.value, form.value).length > 0),
);
/** The bar shows unsaved changes and the outcome of the last save, reload or reference change. */
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
/** A conflict with a readable study.json blocks Save until Reload. */
const canSave = computed(() => dirty.value && writable.value && !saving.value && !conflict.value?.theirs);

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
  base.value = state.value ? toForm(state.value) : null;
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

watch(dirty, (value) => emit("unsaved", value), { immediate: true });

// Profiles: the roster, and the people of the study who are not in it.
const roster = ref<Profile[]>([]);
onMounted(() => {
  study.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the roster the fields offer the people of the study.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));
const author = computed(() => overview.snapshot?.author.user ?? null);

// Reference
const savedIdentifiers = computed(() => detail.value?.metadata.value?.reference ?? {});
const identifiersChanged = computed(
  () =>
    form.value !== null &&
    (form.value.reference.pmid.trim() !== (savedIdentifiers.value.pmid ?? "") ||
      form.value.reference.doi.trim() !== (savedIdentifiers.value.doi ?? "")),
);
const match = computed(() => {
  const value = detail.value?.reference_match ?? null;
  if (value === true) return { label: "reference.json matches", tone: "success" };
  if (value === false) return { label: "reference.json does not match study.json", tone: "warning" };
  return { label: "No identifiers", tone: undefined };
});
const reference = computed(() => {
  const value = detail.value?.reference ?? null;
  if (value === null) return { kind: "none" as const };
  if ("error" in value) return { kind: "error" as const, text: value.error };
  const authors = value.authors;
  return {
    kind: "reference" as const,
    title: value.title,
    authors:
      authors.length > 6
        ? `${authors.slice(0, 6).join(", ")}, et al. (${authors.length} authors)`
        : authors.join(", "),
    source: [value.journal, value.publication_date].filter(Boolean).join(" · "),
  };
});

function useDoi(doi: string): void {
  if (!form.value) return;
  form.value.reference = { pmid: "", doi };
  announce(`DOI ${doi} is in the form. Save study.json to fetch its reference.`);
}

// Access and provenance
const kindItems = computed(() =>
  (["manual_curation", "automatic_curation", "data_import"] as const)
    .filter((kind) => kind !== "data_import" || form.value?.provenance.kind === "data_import")
    .map((kind) => ({ title: PROVENANCE_LABELS[kind], value: kind })),
);
const imported = computed(() => form.value?.provenance.data_import ?? null);
const issueLink = computed(() =>
  detail.value && form.value?.issue
    ? issueUrl(
        { issue: detail.value.issue, summary: { ...detail.value.summary, issue: form.value.issue } },
        overview.snapshot?.github.repository ?? "",
      )
    : null,
);

// Fields

function errorsAt(key: string): string[] {
  return errors.value.get(key) ?? [];
}

/** The disk values of the fields that changed on both sides at the last reload. */
const disk = computed(() => {
  const theirs = base.value;
  const values = new Map<string, string>();
  if (theirs)
    for (const [key, mark] of marks.value) if (mark === "conflict") values.set(key, fieldText(theirs, key));
  return values;
});

function markAt(key: string): string[] {
  const mark = marks.value.get(key);
  return mark ? [markMessage(mark, disk.value.get(key) ?? null)] : [];
}

/** Replace the edit of a field that changed on both sides with the version on disk. */
function useDisk(key: string): void {
  if (!form.value || !base.value) return;
  copyField(form.value, base.value, key);
  marks.value = new Map([...marks.value, [key, "disk"]]);
  reloaded.value = reloaded.value?.filter((field) => field !== key) ?? null;
}

function markColor(key: string): string | undefined {
  const mark = marks.value.get(key);
  return mark === "conflict" ? "warning" : mark ? "info" : undefined;
}

function blockClass(key: string): Record<string, boolean> {
  const mark = marks.value.get(key);
  return mark ? { [`field-block--${mark}`]: true } : {};
}

const accessMessages = computed(() => [
  ...(form.value?.release ? [] : ["Public needs a release."]),
  ...markAt("access"),
]);

function notesSummary(kind: TableKind): string {
  const notes = form.value?.notes[kind];
  if (!notes) return "";
  const parts = [
    notes.descriptions.length ? plural(notes.descriptions.length, "description") : "",
    notes.comments.length ? plural(notes.comments.length, "comment") : "",
  ].filter(Boolean);
  const changed = marks.value.has(`notes.${kind}.descriptions`) || marks.value.has(`notes.${kind}.comments`);
  return [parts.join(", ") || "No notes", changed ? "changed on disk" : ""].filter(Boolean).join(" · ");
}

function setKind(kind: unknown): void {
  const chosen = kindItems.value.find((item) => item.value === kind)?.value;
  if (form.value && chosen) form.value.provenance = withKind(form.value.provenance, chosen satisfies ProvenanceKind);
}

function addAsset(): void {
  form.value?.provenance.assets.push({ url: "", sha256: "" });
}

function removeAsset(index: number): void {
  form.value?.provenance.assets.splice(index, 1);
}

// Saving

function refused(issues: ValidationIssue[], sent: MetadataForm): void {
  const grouped = issuesByTarget(sent, issues);
  errors.value = grouped.fields;
  failure.value = {
    text: grouped.fields.size ? "study.json was not saved. Fix the marked fields." : "study.json was not saved.",
    issues: grouped.general,
  };
  // The notes of a table kind with an issue open, so that the issue shows.
  const kinds = TABLE_KINDS.filter((kind) => [...grouped.fields.keys()].some((key) => key.startsWith(`notes.${kind}.`)));
  openPanels.value = [...new Set([...openPanels.value, ...kinds])];
}

async function save(): Promise<void> {
  const current = form.value;
  const at = revision.value;
  if (!current || at === null || !canSave.value) return;
  const sent = clone(current);
  const metadata = fromForm(sent);
  saving.value = true;
  failure.value = null;
  errors.value = new Map();
  noUser.value = null;
  referenceError.value = "";
  announce("");
  try {
    const result = await study.saveMetadata(at, metadata);
    const written = toForm(metadata);
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
    if (isRevisionConflict(caught))
      conflict.value = { revision: caught.body.revision, theirs: readStudyJson(caught.body.content) };
    else if (isValidationError(caught)) refused(caught.body.issues, sent);
    else if (isNoUser(caught)) noUser.value = userHint(caught);
    else failure.value = { text: `study.json was not saved. ${messageOf(caught)}`, issues: [] };
  } finally {
    saving.value = false;
  }
}

/** Put the edits on top of study.json on disk and mark what changed there. */
function reload(): void {
  const changed = conflict.value;
  if (!changed?.theirs || !form.value) return;
  const start = base.value ?? toForm({});
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
  const kinds = TABLE_KINDS.filter((kind) => marks.value.has(`notes.${kind}.descriptions`) || marks.value.has(`notes.${kind}.comments`));
  openPanels.value = [...new Set([...openPanels.value, ...kinds])];
}

/** Drop the edits: the form shows study.json as the app last read it. Undo brings them back. */
function discard(): void {
  if (!studyJson.value || !form.value) return;
  const discarded: Discarded = {
    form: clone(form.value),
    base: base.value && clone(base.value),
    revision: revision.value,
    adopted,
    marks: marks.value,
    reloaded: reloaded.value,
  };
  adopt(studyJson.value);
  undo.value = discarded;
  clearTimeout(undoTimer);
  undoTimer = setTimeout(() => (undo.value = null), NOTICE_MS);
  announce("Changes discarded.");
}

/** Bring back the form of the last Discard, over the revision it was read from. */
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

/** An invalid study.json: start a new one from what the folder summary could read. */
function startNew(): void {
  if (!detail.value) return;
  form.value = startForm(detail.value, author.value ?? "");
  base.value = null;
}

const newFields = computed(() => {
  if (!detail.value) return [];
  const start = startForm(detail.value, author.value ?? "");
  return [
    { name: "Creator", value: start.creator || "None" },
    { name: "Curators", value: start.curators.map((curator) => curator.user).join(", ") || "None" },
    { name: "PMID", value: start.reference.pmid || "None" },
    { name: "DOI", value: start.reference.doi || "None" },
    { name: "Issue", value: start.issue ? `#${start.issue}` : "None" },
    { name: "Release", value: start.release ? releaseLabel(start.release) : "None" },
  ];
});

// Leaving

const leaving = ref(false);
let answer: ((leave: boolean) => void) | null = null;

/** Whether to leave: at once without unsaved edits, otherwise after the dialog answers. */
function confirmLeave(): boolean | Promise<boolean> {
  if (!dirty.value) return true;
  answer?.(false);
  leaving.value = true;
  return new Promise((resolve) => (answer = resolve));
}

function answerLeave(leave: boolean): void {
  const resolve = answer;
  answer = null;
  leaving.value = false;
  if (leave && studyJson.value) adopt(studyJson.value);
  resolve?.(leave);
}

// Closing the dialog with Escape or a click outside stays.
watch(leaving, (value) => {
  if (!value && answer) answerLeave(false);
});
useReturnFocus(leaving, sectionHeading);

onBeforeRouteLeave(() => confirmLeave());
onBeforeRouteUpdate((to, from) =>
  to.params.section === from.params.section &&
  to.params.substance === from.params.substance &&
  to.params.name === from.params.name
    ? true
    : confirmLeave(),
);

/** Closing or reloading the tab with unsaved edits asks through the browser. */
function beforeUnload(event: BeforeUnloadEvent): void {
  if (dirty.value) event.preventDefault();
}

onMounted(() => window.addEventListener("beforeunload", beforeUnload));
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnload);
  clearTimeout(undoTimer);
  answer?.(false);
});
</script>

<template>
  <div class="metadata">
    <!-- A live region stays in the page while it is empty, so that screen readers announce its
         text; the bar shows it. -->
    <span role="status" aria-live="polite" class="metadata-notice d-sr-only">{{ notice }}</span>
    <section v-if="!form && studyJson" class="metadata-invalid">
      <VAlert type="error" variant="tonal" density="compact" class="status-alert">
        <p class="metadata-alert-text">
          {{
            writable
              ? "study.json is not valid, so the form cannot show it."
              : "study.json cannot be written from the app."
          }}
        </p>
        <ul v-if="studyJson.issues.length" class="metadata-alert-issues">
          <li v-for="(problem, index) in studyJson.issues" :key="index">{{ problem.message }}</li>
        </ul>
      </VAlert>
      <template v-if="writable">
        <p class="metadata-text">Fix study.json in your editor, or start a new one from what the folder shows:</p>
        <dl class="panel-facts">
          <template v-for="fact in newFields" :key="fact.name">
            <dt>{{ fact.name }}</dt>
            <dd>{{ fact.value }}</dd>
          </template>
        </dl>
        <div>
          <VBtn variant="tonal" color="primary" prepend-icon="fas fa-file-circle-plus" @click="startNew">
            Start a new study.json from these fields
          </VBtn>
        </div>
      </template>
    </section>

    <VForm v-else-if="form" class="metadata-form" @submit.prevent>
      <VCard tag="section" border class="metadata-card" :aria-labelledby="ids.reference">
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.reference" tag="h3" class="metadata-card-title">Reference</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-card-body">
          <div class="field-row">
            <VTextField
              v-model="form.reference.pmid"
              label="PMID"
              hide-details="auto"
              autocomplete="off"
              spellcheck="false"
              :error-messages="errorsAt('reference.pmid')"
              :messages="markAt('reference.pmid')"
              :base-color="markColor('reference.pmid')"
              class="field-pmid"
            >
              <template v-if="disk.has('reference.pmid')" #details>
                <DiskVersion field="reference.pmid" @use="useDisk('reference.pmid')" />
              </template>
            </VTextField>
            <VTextField
              v-model="form.reference.doi"
              label="DOI"
              hide-details="auto"
              placeholder="10.1000/xyz123"
              autocomplete="off"
              spellcheck="false"
              :error-messages="errorsAt('reference.doi')"
              :messages="markAt('reference.doi')"
              :base-color="markColor('reference.doi')"
            >
              <template v-if="disk.has('reference.doi')" #details>
                <DiskVersion field="reference.doi" @use="useDisk('reference.doi')" />
              </template>
            </VTextField>
          </div>
          <p v-if="identifiersChanged" class="field-note">
            Saving study.json fetches reference.json for the new identifiers.
          </p>
          <div class="reference-snapshot">
            <VChip size="small" variant="tonal" :color="match.tone" class="status-chip reference-match">
              {{ match.label }}
            </VChip>
            <template v-if="reference.kind === 'reference'">
              <p class="reference-title" :class="{ 'reference-title--missing': !reference.title }">
                {{ reference.title || "No title in reference.json" }}
              </p>
              <p v-if="reference.authors" class="reference-line">{{ reference.authors }}</p>
              <p v-if="reference.source" class="reference-line reference-source">{{ reference.source }}</p>
            </template>
            <p v-else-if="reference.kind === 'error'" class="reference-line">{{ reference.text }}</p>
            <p v-else class="reference-line reference-source">No reference.json yet.</p>
          </div>
          <div>
            <VBtn variant="tonal" color="primary" prepend-icon="fas fa-pen" @click="referenceOpen = true">
              Correct title, authors, journal...
            </VBtn>
          </div>
        </VCardText>
      </VCard>

      <VCard tag="section" border class="metadata-card" :aria-labelledby="ids.people">
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.people" tag="h3" class="metadata-card-title">People</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-card-body">
          <PeopleFields
            v-model:creator="form.creator"
            v-model:curators="form.curators"
            v-model:collaborators="form.collaborators"
            :profiles="profiles"
            :errors="errors"
            :marks="marks"
            :disk="disk"
            @use-disk="useDisk"
          />
        </VCardText>
      </VCard>

      <VCard tag="section" border class="metadata-card" :aria-labelledby="ids.access">
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.access" tag="h3" class="metadata-card-title">Access and provenance</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-card-body">
          <div class="field-row field-row--radios">
            <VRadioGroup
              v-model="form.licence"
              label="Licence"
              inline
              :error-messages="errorsAt('licence')"
              :messages="markAt('licence')"
              :hide-details="!errorsAt('licence').length && !markAt('licence').length"
            >
              <VRadio label="Open" value="open" />
              <VRadio label="Closed" value="closed" />
              <template v-if="disk.has('licence')" #details>
                <DiskVersion field="licence" @use="useDisk('licence')" />
              </template>
            </VRadioGroup>
            <VRadioGroup
              v-model="form.access"
              label="Access"
              inline
              :error-messages="errorsAt('access')"
              :messages="accessMessages"
              :hide-details="!errorsAt('access').length && !accessMessages.length"
            >
              <VRadio label="Public" value="public" :disabled="!form.release" />
              <VRadio label="Private" value="private" />
              <template v-if="disk.has('access')" #details>
                <DiskVersion field="access" @use="useDisk('access')" />
              </template>
            </VRadioGroup>
          </div>
          <VSelect
            :model-value="form.provenance.kind"
            :items="kindItems"
            label="Provenance"
            hide-details="auto"
            :readonly="imported !== null"
            :menu-icon="imported ? '' : '$dropdown'"
            :error-messages="errorsAt('provenance.kind')"
            :messages="imported ? ['Set by the importer', ...markAt('provenance.kind')] : markAt('provenance.kind')"
            :base-color="markColor('provenance.kind')"
            class="field-provenance"
            @update:model-value="setKind"
          >
            <template v-if="disk.has('provenance.kind')" #details>
              <DiskVersion field="provenance.kind" @use="useDisk('provenance.kind')" />
            </template>
          </VSelect>
          <!-- The importer sets a data import: the form shows it and has no fields for it. -->
          <template v-if="imported">
            <dl class="panel-facts data-import-facts">
              <dt>Importer</dt>
              <dd>{{ imported.importer }} {{ imported.importer_version }}</dd>
              <dt>Source</dt>
              <dd>{{ imported.source_key }}, release {{ imported.release }}, revision {{ imported.revision }}</dd>
              <dt>Evidence</dt>
              <dd>{{ imported.evidence_kind }}, {{ imported.reference_scope }}</dd>
              <dt>Assets</dt>
              <dd>{{ plural(imported.assets.length, "asset") }}</dd>
            </dl>
            <p v-if="errorsAt('provenance.data_import').length" class="field-error">
              {{ errorsAt("provenance.data_import").join(" ") }}
            </p>
          </template>
          <template v-else>
            <div class="field-grid">
              <VTextField
                v-model="form.provenance.source_key"
                label="Source key"
                hide-details="auto"
                autocomplete="off"
                spellcheck="false"
                :error-messages="errorsAt('provenance.source_key')"
                :messages="markAt('provenance.source_key')"
                :base-color="markColor('provenance.source_key')"
              >
                <template v-if="disk.has('provenance.source_key')" #details>
                  <DiskVersion field="provenance.source_key" @use="useDisk('provenance.source_key')" />
                </template>
              </VTextField>
              <template v-if="form.provenance.kind === 'automatic_curation'">
                <VTextField
                  v-model="form.provenance.method"
                  label="Method"
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt('provenance.method')"
                  :messages="markAt('provenance.method')"
                  :base-color="markColor('provenance.method')"
                >
                  <template v-if="disk.has('provenance.method')" #details>
                    <DiskVersion field="provenance.method" @use="useDisk('provenance.method')" />
                  </template>
                </VTextField>
                <VTextField
                  v-model="form.provenance.version"
                  label="Version"
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt('provenance.version')"
                  :messages="markAt('provenance.version')"
                  :base-color="markColor('provenance.version')"
                >
                  <template v-if="disk.has('provenance.version')" #details>
                    <DiskVersion field="provenance.version" @use="useDisk('provenance.version')" />
                  </template>
                </VTextField>
                <VTextField
                  v-model="form.provenance.run_id"
                  label="Run ID"
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt('provenance.run_id')"
                  :messages="markAt('provenance.run_id')"
                  :base-color="markColor('provenance.run_id')"
                >
                  <template v-if="disk.has('provenance.run_id')" #details>
                    <DiskVersion field="provenance.run_id" @use="useDisk('provenance.run_id')" />
                  </template>
                </VTextField>
              </template>
            </div>
            <div
              v-if="form.provenance.kind === 'automatic_curation'"
              class="field-block assets-block"
              :class="blockClass('provenance.assets')"
            >
              <h4 class="field-heading">Assets</h4>
              <div v-if="marks.has('provenance.assets')" class="field-mark-row">
                <p class="field-mark">{{ markAt("provenance.assets")[0] }}</p>
                <DiskVersion
                  v-if="disk.has('provenance.assets')"
                  field="provenance.assets"
                  @use="useDisk('provenance.assets')"
                />
              </div>
              <div v-for="(asset, index) in form.provenance.assets" :key="index" class="asset-row">
                <VTextField
                  v-model="asset.url"
                  :label="`Asset ${index + 1} URL`"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt(`provenance.assets.${index}.url`)"
                  hide-details="auto"
                />
                <VTextField
                  v-model="asset.sha256"
                  :label="`Asset ${index + 1} SHA-256`"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt(`provenance.assets.${index}.sha256`)"
                  hide-details="auto"
                />
                <VBtn
                  icon="fas fa-xmark"
                  variant="text"
                  density="comfortable"
                  size="small"
                  :aria-label="`Remove asset ${index + 1}`"
                  class="row-remove"
                  @click="removeAsset(index)"
                />
              </div>
              <p v-if="!form.provenance.assets.length" class="field-empty">
                No assets. An automatic curation needs at least one.
              </p>
              <p v-if="errorsAt('provenance.assets').length" class="field-error">
                {{ errorsAt("provenance.assets").join(" ") }}
              </p>
              <VBtn variant="text" color="primary" prepend-icon="fas fa-plus" class="row-add" @click="addAsset">
                Add asset
              </VBtn>
            </div>
          </template>
        </VCardText>
      </VCard>

      <VCard tag="section" border class="metadata-card" :aria-labelledby="ids.release">
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.release" tag="h3" class="metadata-card-title">Issue and release</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-card-body">
          <dl class="panel-facts">
            <dt>Issue</dt>
            <dd>
              <a v-if="issueLink && form.issue" :href="issueLink" target="_blank" rel="noopener noreferrer">
                #{{ form.issue }}
              </a>
              <template v-else>{{ form.issue ? `#${form.issue}` : "No issue" }}</template>
              <span v-if="marks.has('issue')" class="field-mark-inline">{{ markAt("issue")[0] }}</span>
            </dd>
            <dt>Release</dt>
            <dd>
              {{ form.release ? releaseLabel(form.release) : "Not released" }}
              <span v-if="marks.has('release')" class="field-mark-inline">{{ markAt("release")[0] }}</span>
            </dd>
          </dl>
          <p class="field-note">Set when the study is released.</p>
          <p v-if="errorsAt('issue').length || errorsAt('release').length" class="field-error">
            {{ [...errorsAt("issue"), ...errorsAt("release")].join(" ") }}
          </p>
        </VCardText>
      </VCard>

      <VCard tag="section" border class="metadata-card" :aria-labelledby="ids.notes">
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.notes" tag="h3" class="metadata-card-title">Descriptions and comments</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-card-body">
          <NotesFields
            v-model:descriptions="form.descriptions"
            v-model:comments="form.comments"
            prefix=""
            :kind="null"
            :author="author"
            :profiles="profiles"
            :errors="errors"
            :marks="marks"
            :disk="disk"
            @use-disk="useDisk"
          />
        </VCardText>
      </VCard>

      <VCard tag="section" border class="metadata-card" :aria-labelledby="ids.tables">
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.tables" tag="h3" class="metadata-card-title">Notes per table</VCardTitle>
        </VCardItem>
        <VCardText class="metadata-card-body">
          <VExpansionPanels v-model="openPanels" multiple variant="accordion" class="notes-panels">
            <VExpansionPanel v-for="kind in TABLE_KINDS" :key="kind" :value="kind" elevation="0">
              <!-- The space keeps the kind and the summary apart for screen readers. -->
              <VExpansionPanelTitle class="notes-title">
                <span class="notes-kind">{{ TABLE_KIND_LABELS[kind] }}</span> <span class="notes-summary">{{ notesSummary(kind) }}</span>
              </VExpansionPanelTitle>
              <VExpansionPanelText>
                <NotesFields
                  v-model:descriptions="form.notes[kind].descriptions"
                  v-model:comments="form.notes[kind].comments"
                  :prefix="`notes.${kind}.`"
                  :kind="kind"
                  :author="author"
                  :profiles="profiles"
                  :errors="errors"
                  :marks="marks"
                  :disk="disk"
                  @use-disk="useDisk"
                />
              </VExpansionPanelText>
            </VExpansionPanel>
          </VExpansionPanels>
        </VCardText>
      </VCard>
    </VForm>

    <div v-if="barShown && form" class="metadata-savebar">
      <VAlert
        v-if="referenceError"
        type="warning"
        variant="tonal"
        density="compact"
        closable
        class="status-alert metadata-reference-error"
        @click:close="referenceError = ''"
      >
        {{ referenceError }}
      </VAlert>
      <VAlert
        v-if="reloaded"
        type="info"
        variant="tonal"
        density="compact"
        closable
        class="status-alert metadata-reloaded"
        @click:close="reloaded = null"
      >
        <p class="metadata-alert-text">
          Reloaded study.json from disk. Fields that changed there are marked, and your edits are kept.
        </p>
        <p v-if="reloaded.length" class="metadata-alert-text">
          Changed on both sides, your version is kept: {{ reloaded.map(fieldLabel).join(", ") }}.
        </p>
      </VAlert>
      <VAlert
        v-if="conflict"
        type="warning"
        variant="tonal"
        density="compact"
        class="status-alert metadata-conflict"
      >
        <div class="metadata-alert-row">
          <p class="metadata-alert-text">
            study.json changed on disk after you opened this form.
            {{
              conflict.theirs
                ? "Reload it to keep your edits on top of the new version."
                : "It is not valid JSON now, so it cannot be merged. Fix it in your editor, then save again."
            }}
          </p>
          <VBtn v-if="conflict.theirs" variant="flat" color="primary" size="small" @click="reload">Reload</VBtn>
        </div>
      </VAlert>
      <UserHint v-if="noUser" :text="noUser" class="metadata-failure" />
      <VAlert
        v-if="failure"
        type="error"
        variant="tonal"
        density="compact"
        closable
        class="status-alert metadata-failure"
        @click:close="failure = null"
      >
        <p class="metadata-alert-text">{{ failure.text }}</p>
        <ul v-if="failure.issues.length" class="metadata-alert-issues">
          <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
        </ul>
      </VAlert>
      <div class="savebar-row">
        <span class="savebar-text">
          <i class="fas fa-circle savebar-dot" aria-hidden="true"></i>
          {{ dirty ? "Unsaved changes in study.json" : notice || "No unsaved changes" }}
        </span>
        <div class="savebar-actions">
          <VBtn v-if="undo" variant="text" color="primary" @click="undoDiscard">Undo</VBtn>
          <VBtn variant="text" :disabled="!dirty || saving" @click="discard">Discard</VBtn>
          <VBtn variant="flat" color="primary" :disabled="!canSave" :loading="saving" @click="save">Save</VBtn>
        </div>
      </div>
    </div>

    <ReferenceDialog
      v-model="referenceOpen"
      :unsaved-identifiers="identifiersChanged"
      :fallback-focus="sectionHeading"
      @saved="announce('reference.json saved.')"
      @use-doi="useDoi"
    />

    <VDialog v-model="leaving" max-width="440" :aria-labelledby="ids.leave">
      <VCard>
        <VCardItem class="metadata-card-head">
          <VCardTitle :id="ids.leave" tag="h2">Leave without saving?</VCardTitle>
        </VCardItem>
        <VCardText>Your changes to study.json are not saved. Leaving discards them.</VCardText>
        <VCardActions class="dialog-actions">
          <VSpacer />
          <VBtn variant="text" @click="answerLeave(false)">Stay</VBtn>
          <VBtn variant="flat" color="primary" @click="answerLeave(true)">Discard and leave</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.metadata {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 56rem;
}
/* Hidden, it stays in the page for screen readers but takes no gap. */
.metadata-notice {
  position: absolute;
}
.metadata-alert-text,
.metadata-text {
  margin: 0;
}
.metadata-alert-text + .metadata-alert-text {
  margin-top: 4px;
}
.metadata-alert-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
  overflow-wrap: anywhere;
}
.metadata-invalid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.metadata-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.metadata-card-head {
  padding-bottom: 0;
}
.metadata-card-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.metadata-card-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 16px;
}
.field-row--radios {
  gap: 8px 16px;
}
/* The label, the first radio circle and the messages of a radio group start at the edge of the
   card content, as the fields and headings do. */
.field-row--radios :deep(.v-radio-group > .v-input__control > .v-label) {
  margin-inline-start: 0;
}
/* The input of a radio is 5px wider than its circle on each side. */
.field-row--radios :deep(.v-selection-control-group) {
  padding-inline-start: 0;
  margin-inline-start: -5px;
}
.field-row--radios :deep(.v-input__details) {
  padding-inline: 0;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 16px;
}
.field-provenance {
  max-width: calc(50% - 8px);
}
.asset-row {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr) auto;
  align-items: start;
  gap: 8px 12px;
}
.asset-row > .row-remove {
  margin-top: 4px;
}
.reference-snapshot {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.reference-snapshot .reference-match {
  margin-bottom: 4px;
}
.reference-title,
.reference-line {
  margin: 0;
  overflow-wrap: anywhere;
}
.reference-title {
  font-weight: 600;
}
.reference-title--missing {
  font-weight: 400;
  font-style: italic;
}
.reference-line {
  font-size: 0.875rem;
}
.reference-source {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.notes-panels {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}
.notes-title {
  gap: 12px;
}
.notes-kind {
  font-weight: 600;
}
.notes-summary {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The bar stays in view at the bottom of the window while the form scrolls. */
.metadata-savebar {
  position: sticky;
  bottom: 12px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px 10px 16px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}
.savebar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
/* Wrapped below the text on a phone, the buttons stay at the end. */
.savebar-actions {
  display: flex;
  gap: 8px;
  margin-inline-start: auto;
}
/* The button of an alert follows its text, and goes below it in a narrow bar. */
.metadata-alert-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.metadata-alert-row > .metadata-alert-text {
  flex: 1 1 18rem;
}
.savebar-text {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.savebar-dot {
  font-size: 0.5rem;
  color: rgb(var(--v-theme-primary));
}
@media (max-width: 599.98px) {
  .field-row,
  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .field-provenance {
    max-width: none;
  }
  .asset-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .asset-row > .row-remove {
    grid-row: 1;
    grid-column: 2;
  }
  .metadata-savebar {
    bottom: 8px;
    padding: 8px 8px 8px 12px;
  }
}
</style>
