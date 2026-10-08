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
  VCombobox,
  VDialog,
  VProgressLinear,
  VRadio,
  VRadioGroup,
  VSelect,
  VSpacer,
  VTextarea,
} from "vuetify/components";
import type { ReviewItem, ReviewTarget, TableResponse } from "../api/types";
import { useLoaded } from "../composables/useLoaded";
import { usePreview } from "../composables/usePreview";
import { useReturnFocus, type FocusTarget } from "../composables/useReturnFocus";
import { GROW_ROWS, sizesFieldsByContent } from "../fieldSizing";
import { KIND_LABELS, KINDS, matchText, reviewFailure, type ItemKind, type ReviewFailure } from "../review";
import { useStudyStore } from "../stores/study";
import { tableFiles } from "../study";
import UserHint from "./UserHint.vue";

/** At most this many values of a column are offered for a row filter. */
const OFFERED_VALUES = 200;

/**
 * Adds a review item: its kind, its text and an optional target, which is a file of the study,
 * narrowed for a table to the rows with given values and to a column. The fields stay after
 * Cancel and are emptied after the item was added.
 */
const open = defineModel<boolean>({ default: false });
const props = defineProps<{
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
/** Whether the new item is being written; the section waits with the actions on items meanwhile. */
const busy = defineModel<boolean>("busy", { default: false });
const emit = defineEmits<{ added: [item: ReviewItem | null] }>();

const study = useStudyStore();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
const targetId = useId();
const autoGrow = !sizesFieldsByContent();

interface RowFilter {
  /** Keys the fields of the filter, which stay with it when a filter above is removed. */
  id: number;
  column: string | null;
  value: string | null;
}

let filterIds = 0;

const kind = ref<ItemKind>("question");
const text = ref("");
const file = ref<string | null>(null);
const filters = ref<RowFilter[]>([]);
const column = ref<string | null>(null);
const failure = ref<ReviewFailure | null>(null);

const files = computed(() => study.detail?.files ?? []);
const writable = computed(() => study.detail?.review.revision != null && study.detail.review.value !== null);

// The rows and the column belong to the file; another file starts without them.
watch(file, () => {
  filters.value = [];
  column.value = null;
});

/**
 * Counts the openings of the dialog and the changes of the files of the study while it is open:
 * the rows of the chosen table load again and their count is asked again. A job that changes
 * the study page but no file asks nothing, and nothing is asked while the dialog is closed.
 */
const version = ref(0);
watch([() => study.detail?.files_version, open], () => {
  if (open.value) version.value += 1;
});

/** The chosen file when it is a table of the study; the rows on screen stay while they load again. */
const {
  data: loadedTable,
  error: tableFailure,
  loading,
} = useLoaded<TableResponse>(
  () => {
    const detail = study.detail;
    return file.value !== null && detail !== null && tableFiles(detail).includes(file.value) ? file.value : null;
  },
  (name) => study.table(name),
  () => version.value,
);
/** The header and rows of the chosen table; null for another file or a raw table. */
const table = computed(() => {
  const content = loadedTable.value?.content;
  return content?.kind === "table" ? { header: content.header, rows: content.rows } : null;
});
const tableError = computed(() =>
  tableFailure.value ? `The columns of ${file.value} could not be loaded. ${tableFailure.value}` : null,
);

watch(open, (value) => {
  if (value) failure.value = null;
});

/** The columns that a row filter can choose: those that no other filter has. */
function columnsFor(index: number): string[] {
  const taken = new Set(filters.value.filter((_, other) => other !== index).map((filter) => filter.column));
  return (table.value?.header ?? []).filter((name) => !taken.has(name));
}

/** The values of a column, as printed, to choose from. */
function valuesOf(name: string | null): string[] {
  const loaded = table.value;
  const index = name === null || !loaded ? -1 : loaded.header.indexOf(name);
  if (index < 0 || !loaded) return [];
  const values = new Set(loaded.rows.map((row) => row.cells[index] ?? "").filter(Boolean));
  return [...values].sort((a, b) => a.localeCompare(b, "en", { numeric: true })).slice(0, OFFERED_VALUES);
}

/** A filter with a column needs a value; until it has one, Add waits. */
function incomplete(filter: RowFilter): boolean {
  return filter.column !== null && !filter.value;
}

function setColumn(filter: RowFilter, name: string | null): void {
  filter.column = name;
  filter.value = null;
}

/** The row filters with a column and a value. */
const rows = computed(() =>
  Object.fromEntries(
    filters.value.flatMap((filter) => (filter.column && filter.value ? [[filter.column, filter.value]] : [])),
  ),
);

/** The draft target with its row filters, which the local server matches; null without filters. */
const draft = computed<ReviewTarget | null>(() =>
  file.value !== null && table.value !== null && Object.keys(rows.value).length
    ? { file: file.value, rows: rows.value }
    : null,
);
const preview = usePreview(
  () => {
    const detail = study.detail;
    if (!detail || draft.value === null) return null;
    // A preview that failed while the local server did not answer is asked again once it answers.
    return { study: detail.id, version: version.value, answering: study.error === null, target: draft.value };
  },
  (value) => study.previewTarget(value.target),
);
/**
 * How many rows the row filters match, of the rows of the same version of the table, as the
 * local server counted them: for the current filters, or for the last ones while the count of the
 * current ones loads; null without filters.
 */
const matches = computed(() => {
  const failed = preview.shownError.value;
  if (failed) return { matched: null, text: `The rows could not be matched. ${failed}` };
  const answer = preview.shown.value;
  if (!answer || answer.lines === null || answer.total === null) return null;
  return { matched: answer.lines.length, text: matchText(answer.lines.length, answer.total) };
});
const target = computed<ReviewTarget | null>(() => {
  if (file.value === null) return null;
  return {
    file: file.value,
    ...(Object.keys(rows.value).length ? { rows: rows.value } : {}),
    ...(column.value ? { column: column.value } : {}),
  };
});
/** Add waits for the count of the current row filters. */
const canAdd = computed(
  () =>
    writable.value &&
    !busy.value &&
    !loading.value &&
    !preview.loading.value &&
    text.value.trim() !== "" &&
    !filters.value.some(incomplete),
);

function reset(): void {
  kind.value = "question";
  text.value = "";
  file.value = null;
}

async function add(): Promise<void> {
  const revision = study.detail?.review.revision;
  if (!canAdd.value || revision == null) return;
  busy.value = true;
  failure.value = null;
  try {
    const result = await study.reviewAction(revision, "add", {
      kind: kind.value,
      text: text.value.trim(),
      ...(target.value ? { target: target.value } : {}),
    });
    reset();
    open.value = false;
    emit("added", result.item ?? null);
  } catch (caught) {
    failure.value = reviewFailure(caught, "The item was not added.");
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <VDialog v-model="open" max-width="640" scrollable :aria-labelledby="titleId">
    <VCard tag="form" @submit.prevent="add">
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">New review item</VCardTitle>
      </VCardItem>
      <VCardText class="new-item-body">
        <VRadioGroup v-model="kind" label="Kind" inline hide-details class="new-item-kind">
          <VRadio v-for="value in KINDS" :key="value" :value="value" :label="KIND_LABELS[value]" />
        </VRadioGroup>
        <VTextarea
          v-model="text"
          label="Text"
          rows="3"
          :auto-grow="autoGrow"
          :max-rows="GROW_ROWS"
          variant="outlined"
          density="compact"
          hide-details="auto"
          class="grow-textarea"
        />

        <section class="new-item-target" :aria-labelledby="targetId">
          <div>
            <h3 :id="targetId" class="new-item-heading">Target</h3>
            <p class="field-note">Optional. Without a file, the item is about the whole study.</p>
          </div>
          <VSelect v-model="file" :items="files" label="File" clearable hide-details />
          <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${file}`" />
          <p v-else-if="tableError" class="field-error">{{ tableError }}</p>
          <template v-else-if="table">
            <div class="field-block">
              <div>
                <h4 class="field-heading">Rows</h4>
                <p class="field-note">The item is about the rows that have all of these values.</p>
              </div>
              <div v-for="(filter, index) in filters" :key="filter.id" class="filter-row">
                <VSelect
                  :model-value="filter.column"
                  :items="columnsFor(index)"
                  :label="`Column ${index + 1}`"
                  hide-details
                  @update:model-value="setColumn(filter, $event)"
                />
                <VCombobox
                  v-model="filter.value"
                  :items="valuesOf(filter.column)"
                  :label="`Value ${index + 1}`"
                  :disabled="!filter.column"
                  :hint="incomplete(filter) ? 'Choose or type the value of the rows.' : ''"
                  persistent-hint
                  hide-details="auto"
                  autocomplete="off"
                  spellcheck="false"
                />
                <VBtn
                  icon="fas fa-xmark"
                  variant="text"
                  density="comfortable"
                  size="small"
                  :aria-label="`Remove row filter ${index + 1}`"
                  class="filter-remove"
                  @click="filters.splice(index, 1)"
                />
              </div>
              <!-- A live region stays in the page while it is empty, so that screen readers announce its
                   text. While the count of the current filters loads, the last one stays, marked as updating. -->
              <p
                role="status"
                class="new-item-matches"
                :class="{
                  'new-item-matches--none': matches?.matched === 0,
                  'field-error': matches?.matched === null,
                  'is-updating': preview.loading.value,
                }"
                :aria-busy="preview.loading.value"
              >{{ matches?.text ?? "" }}</p>
              <VBtn
                variant="text"
                color="primary"
                prepend-icon="fas fa-plus"
                class="row-add"
                @click="filters.push({ id: ++filterIds, column: null, value: null })"
              >
                Add row filter
              </VBtn>
            </div>
            <VSelect
              v-model="column"
              :items="table.header"
              label="Column"
              clearable
              hint="Optional. The column that the item is about."
              persistent-hint
            />
          </template>
          <p v-else-if="file" class="field-note">Rows and a column narrow only a table.</p>
        </section>

        <VAlert
          v-if="failure?.kind === 'conflict'"
          type="warning"
          variant="tonal"
          density="compact"
          class="status-alert"
        >
          {{ failure.text }}
        </VAlert>
        <UserHint v-else-if="failure?.kind === 'user'" :text="failure.text" />
        <VAlert v-else-if="failure" type="error" variant="tonal" density="compact" class="status-alert">
          {{ failure.text }}
          <ul v-if="failure.issues.length" class="new-item-issues">
            <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
          </ul>
        </VAlert>
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn type="submit" variant="flat" color="primary" :disabled="!canAdd" :loading="busy">Add</VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.new-item-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* The label and the circles of the radio buttons start at the edge of the fields below them. */
.new-item-kind :deep(.v-input__control > .v-label) {
  margin-inline-start: 0;
}
.new-item-kind :deep(.v-selection-control-group) {
  margin-inline-start: -8px;
}
.new-item-target {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.new-item-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.filter-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: start;
  gap: 8px 12px;
}
.filter-remove {
  margin-top: 4px;
}
.new-item-matches {
  margin: 0;
  font-size: 0.875rem;
}
.new-item-matches--none {
  font-weight: 600;
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.new-item-matches:empty {
  position: absolute;
}
.new-item-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
}
/* On a phone the value goes below its column, and the filters stand further apart than a column
   and its value. */
@media (max-width: 599.98px) {
  .filter-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
  .filter-row > :nth-child(2) {
    grid-row: 2;
  }
  .filter-row + .filter-row {
    margin-top: 8px;
  }
}
</style>
