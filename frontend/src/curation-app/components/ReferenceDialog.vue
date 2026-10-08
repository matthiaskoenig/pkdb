<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VCheckbox,
  VDialog,
  VForm,
  VProgressLinear,
  VSpacer,
  VTextarea,
  VTextField,
} from "vuetify/components";
import type { Json, ReferenceAuthor, ReferencePreview, ReferenceRecord } from "../api/types";
import { useReturnFocus, type FocusTarget } from "../composables/useReturnFocus";
import { GROW_ROWS, sizesFieldsByContent } from "../fieldSizing";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";

/**
 * Corrections of `reference.json` of the open study: the title, the authors, the journal and the
 * date. study.json names the publication, so its PMID and DOI are not changed here; a study
 * without them can search a citation and take the DOI of a candidate into the form.
 *
 * A preview shows what saving would write; any edit afterwards needs a new preview.
 */
const open = defineModel<boolean>({ default: false });
const props = defineProps<{
  /** The form has a PMID or DOI that study.json does not have yet. */
  unsavedIdentifiers: boolean;
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
const emit = defineEmits<{ saved: []; useDoi: [doi: string] }>();

const study = useStudyStore();
const overview = useOverviewStore();
const autoGrow = !sizesFieldsByContent();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
const searchId = useId();
const correctionsId = useId();
const previewId = useId();

interface Corrections {
  title: string;
  /** One author per line: `last name, first name`. */
  authors: string;
  /** Organizations separated by semicolons. */
  organizations: string;
  journal: string;
  publication_date: string;
}

const EMPTY: Corrections = { title: "", authors: "", organizations: "", journal: "", publication_date: "" };

const LABELS: Record<string, string> = {
  title: "Title",
  authors: "Authors",
  journal: "Journal",
  publication_date: "Publication date",
  date: "Exact date",
  abstract: "Abstract",
  url: "URL",
  pmid: "PMID",
  doi: "DOI",
  sid: "Reference",
  name: "Name",
};

/** At most this many characters of a changed value are shown. */
const SHOWN = 160;

const fields = ref<Corrections>({ ...EMPTY });
/** The corrections as read; an identified reference previews only the fields that differ. */
let initial: Corrections = { ...EMPTY };
const refetch = ref(false);
const resetOverrides = ref(false);
const citation = ref("");
const loading = ref(false);
const loadError = ref("");
const searching = ref(false);
const searchError = ref("");
const candidates = ref<ReferenceRecord[] | null>(null);
const previewing = ref(false);
const previewError = ref("");
const preview = ref<ReferencePreview | null>(null);
const saving = ref(false);
const saveError = ref("");
/** Counts the edits: a preview that answers after an edit is dropped. */
let edits = 0;

const identifiers = computed(() => study.detail?.metadata.value?.reference ?? null);
/** A study without a PMID and DOI has a manual reference: its fields are the whole reference. */
const manual = computed(() => !identifiers.value?.pmid && !identifiers.value?.doi);
const offline = computed(() => overview.snapshot?.offline ?? true);
const identifierText = computed(() =>
  [
    identifiers.value?.pmid ? `PMID ${identifiers.value.pmid}` : "",
    identifiers.value?.doi ? `DOI ${identifiers.value.doi}` : "",
  ]
    .filter(Boolean)
    .join(" · "),
);

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught);
}

function authorName(author: ReferenceAuthor): string {
  if (author.organization) return author.organization;
  return [author.first_name, author.last_name].filter(Boolean).join(" ");
}

function correctionsOf(reference: ReferenceRecord): Corrections {
  const authors = reference.authors ?? [];
  return {
    title: reference.title ?? "",
    authors: authors
      .filter((author) => !author.organization)
      .map((author) => (author.first_name ? `${author.last_name ?? ""}, ${author.first_name}` : (author.last_name ?? "")))
      .join("\n"),
    organizations: authors
      .flatMap((author) => (author.organization ? [author.organization] : []))
      .join("; "),
    journal: reference.journal ?? "",
    publication_date: reference.publication_date ?? reference.date ?? "",
  };
}

function authorsOf(corrections: Corrections): ReferenceAuthor[] {
  const people = corrections.authors
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [last = "", ...first] = line.split(",");
      return { last_name: last.trim(), first_name: first.join(",").trim() };
    });
  const organizations = corrections.organizations
    .split(";")
    .map((name) => name.trim())
    .filter(Boolean)
    .map((organization) => ({ organization }));
  return [...people, ...organizations];
}

/** The search text of a reference: its title, first author and year. */
function citationOf(reference: ReferenceRecord): string {
  const first = reference.authors?.[0];
  const year = (reference.publication_date ?? reference.date ?? "").slice(0, 4);
  return [reference.title ?? "", first ? (first.organization ?? first.last_name ?? "") : "", year]
    .filter(Boolean)
    .join(" ");
}

/** `Smith et al. · Clin Pharmacokinet · 1988` */
function candidateFacts(candidate: ReferenceRecord): string {
  const authors = candidate.authors ?? [];
  const first = authors[0];
  const lead = first ? (first.organization ?? first.last_name ?? "") : "";
  return [authors.length > 1 ? `${lead} et al.` : lead, candidate.journal, candidate.publication_date]
    .filter(Boolean)
    .join(" · ");
}

const shownCandidates = computed(() =>
  (candidates.value ?? []).flatMap((candidate) => (candidate.doi ? [{ ...candidate, doi: candidate.doi }] : [])),
);

/**
 * The input of a preview. An identified reference sends only the changed fields, which become
 * corrections; a manual reference sends all of its fields.
 */
function previewInput() {
  const current = fields.value;
  const input: Partial<Record<"title" | "journal" | "publication_date", string | null>> & {
    authors?: ReferenceAuthor[];
  } = {};
  for (const key of ["title", "journal", "publication_date"] as const) {
    const value = current[key].trim();
    if (manual.value ? value : value !== initial[key].trim()) input[key] = value || null;
  }
  const authors = authorsOf(current);
  const authorsChanged =
    current.authors.trim() !== initial.authors.trim() || current.organizations.trim() !== initial.organizations.trim();
  if (manual.value ? authors.length : authorsChanged) input.authors = authors;
  return input;
}

/** Any edit makes the preview stale: Save waits for a new one. */
function invalidate(): void {
  edits += 1;
  preview.value = null;
  previewError.value = "";
  previewing.value = false;
}

async function load(): Promise<void> {
  invalidate();
  fields.value = { ...EMPTY };
  initial = { ...EMPTY };
  refetch.value = false;
  resetOverrides.value = false;
  citation.value = "";
  candidates.value = null;
  searchError.value = "";
  saveError.value = "";
  loadError.value = "";
  loading.value = true;
  try {
    const reference = await study.readReference();
    initial = correctionsOf(reference);
    fields.value = { ...initial };
    citation.value = citationOf(reference);
  } catch (caught) {
    loadError.value = `reference.json could not be read. ${messageOf(caught)}`;
  } finally {
    loading.value = false;
  }
}

watch(open, (value) => (value ? void load() : invalidate()), { immediate: true });
watch([fields, refetch, resetOverrides], invalidate, { deep: true });

async function search(): Promise<void> {
  const text = citation.value.trim();
  if (!text || searching.value) return;
  searching.value = true;
  searchError.value = "";
  try {
    candidates.value = await study.searchReference(text);
  } catch (caught) {
    candidates.value = null;
    searchError.value = messageOf(caught);
  } finally {
    searching.value = false;
  }
}

function useDoi(doi: string): void {
  emit("useDoi", doi);
  open.value = false;
}

async function runPreview(): Promise<void> {
  const at = edits;
  previewing.value = true;
  previewError.value = "";
  saveError.value = "";
  preview.value = null;
  try {
    const result = await study.previewReference(previewInput(), {
      refetch: refetch.value,
      resetOverrides: resetOverrides.value,
    });
    if (at === edits) preview.value = result;
  } catch (caught) {
    if (at === edits) previewError.value = messageOf(caught);
  } finally {
    if (at === edits) previewing.value = false;
  }
}

async function save(): Promise<void> {
  const token = preview.value?.token;
  if (!token || saving.value) return;
  saving.value = true;
  saveError.value = "";
  try {
    await study.saveReference(token);
    emit("saved");
    open.value = false;
  } catch (caught) {
    // A refused token is used up or stale: the next save needs a new preview.
    preview.value = null;
    saveError.value = `reference.json was not saved. ${messageOf(caught)}`;
  } finally {
    saving.value = false;
  }
}

function shown(value: Json | undefined): string {
  if (value === null || value === undefined || value === "") return "empty";
  if (Array.isArray(value))
    return (
      value
        .map((entry) =>
          typeof entry === "object" && entry !== null && !Array.isArray(entry)
            ? authorName({
                first_name: typeof entry.first_name === "string" ? entry.first_name : "",
                last_name: typeof entry.last_name === "string" ? entry.last_name : "",
                organization: typeof entry.organization === "string" ? entry.organization : null,
              })
            : String(entry),
        )
        .join(", ") || "empty"
    );
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  return text.length > SHOWN ? `${text.slice(0, SHOWN)}...` : text;
}

const previewed = computed(() => {
  const result = preview.value;
  if (!result) return null;
  const reference = result.reference;
  const warnings = reference.provenance?.warnings;
  return {
    title: reference.title || "No title",
    authors: (reference.authors ?? []).map(authorName).join(", "),
    facts: [
      reference.journal,
      reference.publication_date ?? reference.date,
      reference.pmid ? `PMID ${reference.pmid}` : null,
      reference.doi ? `DOI ${reference.doi}` : null,
    ]
      .filter(Boolean)
      .join(" · "),
    warnings: Array.isArray(warnings)
      ? warnings.filter((warning): warning is string => typeof warning === "string")
      : [],
    changes: Object.entries(result.changes)
      .filter(([field]) => field !== "provenance")
      .map(([field, change]) => `${LABELS[field] ?? field}: ${shown(change.before)} → ${shown(change.after)}`),
  };
});
</script>

<template>
  <VDialog v-model="open" max-width="720" scrollable :aria-labelledby="titleId">
    <VCard>
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">Reference</VCardTitle>
      </VCardItem>
      <VCardText class="reference-body">
        <p v-if="manual" class="reference-intro">
          study.json names no PMID or DOI. Search for the publication to use its DOI, or enter a manual reference with
          a title and at least one author.
        </p>
        <template v-else>
          <p class="reference-intro">
            Corrections are saved to reference.json. study.json names the publication by its PMID and DOI.
          </p>
          <p class="reference-ids">{{ identifierText }}</p>
        </template>
        <VAlert v-if="unsavedIdentifiers" type="warning" variant="tonal" density="compact" class="status-alert">
          Save study.json first. The reference uses the PMID and DOI that study.json has on disk.
        </VAlert>

        <VProgressLinear v-if="loading" indeterminate color="primary" aria-label="Reading reference.json" />
        <VAlert v-else-if="loadError" type="error" variant="tonal" density="compact" class="status-alert">
          {{ loadError }}
        </VAlert>
        <template v-else>
          <section v-if="manual" class="reference-part" :aria-labelledby="searchId">
            <h3 :id="searchId" class="reference-heading">Find the publication</h3>
            <div class="reference-search">
              <VTextField
                v-model="citation"
                label="Citation"
                hide-details
                autocomplete="off"
                @keydown.enter.prevent="search"
              />
              <VBtn variant="tonal" color="primary" :disabled="!citation.trim()" :loading="searching" @click="search">
                Search
              </VBtn>
            </div>
            <p v-if="offline" class="reference-note">Offline: only searches made before are found.</p>
            <VAlert v-if="searchError" type="error" variant="tonal" density="compact" class="status-alert">
              {{ searchError }}
            </VAlert>
            <ul v-if="shownCandidates.length" class="reference-candidates">
              <li v-for="candidate in shownCandidates" :key="candidate.doi" class="reference-candidate">
                <div class="candidate-text">
                  <p class="candidate-title">{{ candidate.title || candidate.doi }}</p>
                  <p class="candidate-facts">{{ candidateFacts(candidate) }}</p>
                  <p class="candidate-facts">DOI {{ candidate.doi }}</p>
                </div>
                <VBtn variant="tonal" color="primary" :aria-label="`Use DOI ${candidate.doi}`" @click="useDoi(candidate.doi)">
                  Use DOI
                </VBtn>
              </li>
            </ul>
            <p v-else-if="candidates" class="reference-note">
              No matching publications. You can enter a manual reference below.
            </p>
          </section>

          <VForm class="reference-part" :aria-labelledby="correctionsId" @submit.prevent="runPreview">
            <h3 :id="correctionsId" class="reference-heading">{{ manual ? "Manual reference" : "Corrections" }}</h3>
            <VTextField v-model="fields.title" label="Title" hide-details="auto" autocomplete="off" />
            <VTextarea
              v-model="fields.authors"
              label="Authors"
              hint="One per line: last name, first name"
              persistent-hint
              variant="outlined"
              density="compact"
              rows="2"
              :auto-grow="autoGrow"
              :max-rows="GROW_ROWS"
              class="grow-textarea"
            />
            <VTextField
              v-model="fields.organizations"
              label="Organizations"
              hint="Separate several with a semicolon"
              persistent-hint
              autocomplete="off"
            />
            <div class="reference-row">
              <VTextField
                v-model="fields.journal"
                label="Journal"
                hide-details="auto"
                autocomplete="off"
                class="reference-journal"
              />
              <VTextField
                v-model="fields.publication_date"
                label="Publication date"
                hint="YYYY, YYYY-MM or YYYY-MM-DD"
                persistent-hint
                autocomplete="off"
                class="reference-date"
              />
            </div>
            <div v-if="!manual" class="reference-options">
              <VCheckbox
                v-model="refetch"
                label="Fetch the metadata again"
                :disabled="offline"
                hide-details
                density="compact"
              />
              <p v-if="offline" class="reference-note reference-option-note">
                Offline: the metadata comes from the cache of earlier lookups.
              </p>
              <VCheckbox
                v-model="resetOverrides"
                label="Use the fetched metadata instead of saved corrections"
                hide-details
                density="compact"
              />
            </div>
            <div>
              <VBtn type="submit" variant="tonal" color="primary" :loading="previewing">Preview</VBtn>
            </div>
          </VForm>

          <VAlert v-if="previewError" type="error" variant="tonal" density="compact" class="status-alert">
            {{ previewError }}
          </VAlert>
          <section v-if="previewed" class="reference-part reference-preview" :aria-labelledby="previewId">
            <h3 :id="previewId" class="reference-heading">Preview</h3>
            <p class="preview-title">{{ previewed.title }}</p>
            <p v-if="previewed.authors" class="preview-line">{{ previewed.authors }}</p>
            <p v-if="previewed.facts" class="preview-line preview-facts">{{ previewed.facts }}</p>
            <ul v-if="previewed.warnings.length" class="preview-warnings">
              <li v-for="(warning, index) in previewed.warnings" :key="index">{{ warning }}</li>
            </ul>
            <ul v-if="previewed.changes.length" class="preview-changes">
              <li v-for="(change, index) in previewed.changes" :key="index">{{ change }}</li>
            </ul>
            <p v-else class="reference-note">No changes. Saving keeps reference.json as it is.</p>
          </section>
          <VAlert v-if="saveError" type="error" variant="tonal" density="compact" class="status-alert">
            {{ saveError }}
          </VAlert>
        </template>
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn variant="flat" color="primary" :disabled="!preview" :loading="saving" @click="save">Save reference</VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.reference-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.reference-intro,
.reference-ids,
.reference-note {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
.reference-ids {
  font-variant-numeric: tabular-nums;
}
.reference-note {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.reference-part {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.reference-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.reference-search {
  display: flex;
  align-items: center;
  gap: 8px;
}
.reference-candidates {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.reference-candidate {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
}
.reference-candidate + .reference-candidate {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.candidate-text {
  flex: 1 1 auto;
  min-width: 0;
}
.candidate-title,
.candidate-facts {
  margin: 0;
  overflow-wrap: anywhere;
}
.candidate-title {
  font-weight: 600;
}
.candidate-facts {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.reference-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 15rem;
  align-items: start;
  gap: 12px;
}
.reference-options {
  display: flex;
  flex-direction: column;
}
/* Below the label text of the checkbox above it. */
.reference-option-note {
  margin: -6px 0 4px 28px;
}
.reference-preview {
  padding: 12px 16px;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}
.preview-title,
.preview-line {
  margin: 0;
  overflow-wrap: anywhere;
}
.preview-title {
  font-weight: 600;
}
.preview-line {
  font-size: 0.875rem;
}
.preview-facts {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.preview-warnings,
.preview-changes {
  margin: 0;
  padding-inline-start: 20px;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
@media (max-width: 599.98px) {
  .reference-row {
    grid-template-columns: minmax(0, 1fr);
  }
  .reference-candidate {
    flex-wrap: wrap;
  }
}
</style>
