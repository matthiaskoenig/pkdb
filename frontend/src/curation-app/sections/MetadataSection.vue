<script setup lang="ts">
import { computed, onMounted, ref, useId } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardItem,
  VCardText,
  VCardTitle,
  VChip,
  VForm,
  VRadio,
  VRadioGroup,
  VSelect,
  VTextField,
} from "vuetify/components";
import type { Profile } from "../../study-views/types";
import DiskField from "../components/DiskField.vue";
import DiskVersion from "../components/DiskVersion.vue";
import NotesFields from "../components/NotesFields.vue";
import PeopleFields from "../components/PeopleFields.vue";
import ReferenceDialog from "../components/ReferenceDialog.vue";
import TableNotes from "../components/TableNotes.vue";
import { sectionHeading } from "../../study-views/focus";
import { markMessages, messagesAt, NO_MESSAGES, startForm, withKind } from "../metadata";
import { PROVENANCE_LABELS, referenceMatch, referenceView, type ProvenanceKind } from "../../study-views/metadataView";
import { hasNotes, kindsWithTable } from "../../study-views/notes";
import { issueUrl, plural } from "../../study-views/overview";
import { useOverviewStore } from "../stores/overview";
import { curationRoutes } from "../routes";
import { useStudyStore } from "../stores/study";
import { knownProfiles, releaseLabel } from "../../study-views/study";
import { noteKinds } from "../../study-views/tableKinds";

/**
 * The form of study.json. It edits the draft of the study store, which the Data section edits
 * too; the banner of the study page saves the draft over the revision that it was read from. A
 * file changed on disk meanwhile is a conflict, and Reload puts the edits on top of the new
 * version. The study page asks before the study is left with unsaved edits.
 */
const study = useStudyStore();
const overview = useOverviewStore();
/** The draft of study.json of the open study. */
const draft = study.draft;
const ids = {
  reference: useId(),
  people: useId(),
  access: useId(),
  release: useId(),
  notes: useId(),
};

const detail = computed(() => study.detail);
/** study.json as the app last read it. */
const studyJson = computed(() => detail.value?.metadata ?? null);
/** The form of the draft; null while an invalid study.json shows its issues instead. */
const form = computed(() => draft.form);
const writable = computed(() => draft.writable);
const errors = computed(() => draft.errors);
const marks = computed(() => draft.marks);
const disk = computed(() => draft.disk);
const referenceOpen = ref(false);

/** The Data section, which shows the notes of each table above it. */
const dataRoute = computed(() => curationRoutes.section(detail.value?.id ?? "", "data"));
/**
 * The kinds with notes in study.json but no table in the study, such as after a table was
 * removed or beyond the upload limits: the Data section cannot show them, so Metadata does.
 */
const orphanKinds = computed(() => {
  const value = detail.value;
  if (!value) return [];
  const kinds = noteKinds(value);
  const tabled = kindsWithTable(value, kinds);
  return kinds.filter(
    (kind) => !tabled.includes(kind) && (hasNotes(draft.base?.notes[kind]) || hasNotes(draft.form?.notes[kind])),
  );
});

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
const match = computed(() => referenceMatch(detail.value?.reference_match ?? null));
const reference = computed(() => referenceView(detail.value?.reference ?? null));

function useDoi(doi: string): void {
  if (!form.value) return;
  form.value.reference = { pmid: "", doi };
  draft.announce(`DOI ${doi} is in the form. Save study.json to fetch its reference.`);
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

/** The mark message of each marked field: one array per field, kept until the marks change. */
const marked = computed(() => markMessages(marks.value, disk.value));

function errorsAt(key: string): readonly string[] {
  return messagesAt(errors.value, key);
}

function markAt(key: string): readonly string[] {
  return marked.value.get(key) ?? NO_MESSAGES;
}

/** The messages of the provenance kind: who set it, for an import, and its mark. */
const kindMessages = computed(() =>
  imported.value ? ["Set by the importer", ...markAt("provenance.kind")] : markAt("provenance.kind"),
);

/** Replace the edit of a field that changed on both sides with the version on disk. */
function useDisk(key: string): void {
  draft.useDisk(key);
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

/** An invalid study.json: start a new one from what the folder summary could read. */
function startNew(): void {
  if (detail.value) draft.startNew(startForm(detail.value, author.value ?? ""));
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
</script>

<template>
  <div class="metadata">
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
            <DiskField
              :control="VTextField"
              field="reference.pmid"
              :shown="disk.has('reference.pmid')"
              v-model="form.reference.pmid"
              label="PMID"
              hide-details="auto"
              autocomplete="off"
              spellcheck="false"
              :error-messages="errorsAt('reference.pmid')"
              :messages="markAt('reference.pmid')"
              :base-color="markColor('reference.pmid')"
              class="field-pmid"
              @use="useDisk('reference.pmid')"
            />
            <DiskField
              :control="VTextField"
              field="reference.doi"
              :shown="disk.has('reference.doi')"
              v-model="form.reference.doi"
              label="DOI"
              hide-details="auto"
              placeholder="10.1000/xyz123"
              autocomplete="off"
              spellcheck="false"
              :error-messages="errorsAt('reference.doi')"
              :messages="markAt('reference.doi')"
              :base-color="markColor('reference.doi')"
              @use="useDisk('reference.doi')"
            />
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
            <!-- Not DiskField: it needs an options prop, and forwarding the VRadio slot brings back
                 the forced update. -->
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
          <DiskField
            :control="VSelect"
            field="provenance.kind"
            :shown="disk.has('provenance.kind')"
            :model-value="form.provenance.kind"
            :items="kindItems"
            label="Provenance"
            hide-details="auto"
            :readonly="imported !== null"
            :menu-icon="imported ? '' : '$dropdown'"
            :error-messages="errorsAt('provenance.kind')"
            :messages="kindMessages"
            :base-color="markColor('provenance.kind')"
            class="field-provenance"
            @update:model-value="setKind"
            @use="useDisk('provenance.kind')"
          />
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
              <DiskField
                :control="VTextField"
                field="provenance.source_key"
                :shown="disk.has('provenance.source_key')"
                v-model="form.provenance.source_key"
                label="Source key"
                hide-details="auto"
                autocomplete="off"
                spellcheck="false"
                :error-messages="errorsAt('provenance.source_key')"
                :messages="markAt('provenance.source_key')"
                :base-color="markColor('provenance.source_key')"
                @use="useDisk('provenance.source_key')"
              />
              <template v-if="form.provenance.kind === 'automatic_curation'">
                <DiskField
                  :control="VTextField"
                  field="provenance.method"
                  :shown="disk.has('provenance.method')"
                  v-model="form.provenance.method"
                  label="Method"
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt('provenance.method')"
                  :messages="markAt('provenance.method')"
                  :base-color="markColor('provenance.method')"
                  @use="useDisk('provenance.method')"
                />
                <DiskField
                  :control="VTextField"
                  field="provenance.version"
                  :shown="disk.has('provenance.version')"
                  v-model="form.provenance.version"
                  label="Version"
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt('provenance.version')"
                  :messages="markAt('provenance.version')"
                  :base-color="markColor('provenance.version')"
                  @use="useDisk('provenance.version')"
                />
                <DiskField
                  :control="VTextField"
                  field="provenance.run_id"
                  :shown="disk.has('provenance.run_id')"
                  v-model="form.provenance.run_id"
                  label="Run ID"
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                  :error-messages="errorsAt('provenance.run_id')"
                  :messages="markAt('provenance.run_id')"
                  :base-color="markColor('provenance.run_id')"
                  @use="useDisk('provenance.run_id')"
                />
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
          <p class="field-note metadata-notes-hint">Notes of a table are in <RouterLink :to="dataRoute">Data</RouterLink>, above the table.</p>
          <div v-if="orphanKinds.length" class="metadata-orphans">
            <p class="field-note">
              {{
                orphanKinds.length === 1
                  ? "The study has no table of this kind, so its notes are here:"
                  : "The study has no table of these kinds, so their notes are here:"
              }}
            </p>
            <TableNotes v-for="kind in orphanKinds" :key="kind" :kind="kind" card />
          </div>
        </VCardText>
      </VCard>
    </VForm>

    <ReferenceDialog
      v-model="referenceOpen"
      :unsaved-identifiers="identifiersChanged"
      :fallback-focus="sectionHeading"
      @saved="draft.announce('reference.json saved.')"
      @use-doi="useDoi"
    />
  </div>
</template>

<style scoped>
/* The study page sets its width, at most 100rem. */
.metadata {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
/* The cards sit side by side where two of them fit, from a window of about 1400px. The cards of
   a row are as high as the higher one, so that the rows read evenly. */
.metadata-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 36rem), 1fr));
  align-items: stretch;
  gap: 12px;
}
/* Five cards leave the last one alone in its row of two: it takes the whole row. */
.metadata-form > .metadata-card:last-child:nth-child(odd) {
  grid-column: 1 / -1;
}
.metadata-orphans {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
/* The messages of a radio group start at the edge of the card content, as its label and its first
   circle do (styles.css). */
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
}
</style>
