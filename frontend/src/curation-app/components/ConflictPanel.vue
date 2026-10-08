<script setup lang="ts">
import { computed, shallowRef, useId, watch } from "vue";
import { VBtn, VProgressLinear } from "vuetify/components";
import type { ConflictData } from "../api/types";
import { useStudyStore } from "../stores/study";
import { isRawTable } from "../study";
import { conflictView, type Side } from "../tables";
import TableGrid from "./TableGrid.vue";

/**
 * The rows that the workbook and the tables changed differently since the last sync, per
 * conflicting file in one grid: a row per version (the last sync, the rows of the sheet, the
 * lines of the file) under the table header, the changed columns first and marked. Keep workbook
 * and Keep tables resolve every conflict of the study, also when its rows cannot be read; Open
 * workbook opens it to combine the rows.
 */
const props = defineProps<{
  conflicts: ConflictData[];
  /** The action that runs: a side that is kept, or `open`. */
  busy: Side | "open" | null;
  /** Another action runs. */
  disabled: boolean;
}>();
const emit = defineEmits<{ keep: [side: Side]; open: [] }>();

const study = useStudyStore();
const id = useId();

const unresolved = computed(() => props.conflicts.filter((conflict) => conflict.kept === null));
const files = computed(() => [...new Set(unresolved.value.map((conflict) => conflict.file))]);

/** The header of each conflicting table; null for a raw table, or a table that is deleted or does not load. */
const headers = shallowRef(new Map<string, string[] | null>());
let request = 0;

async function header(file: string): Promise<string[] | null> {
  // A deleted table takes its header from its sheet.
  if (isRawTable(file) || !study.detail?.files.includes(file)) return null;
  try {
    const table = await study.table(file);
    return table.kind === "table" ? table.header : null;
  } catch {
    return null;
  }
}

watch(
  () => files.value.join("\n"),
  async () => {
    const current = ++request;
    const loaded = await Promise.all(files.value.map(async (file) => [file, await header(file)] as const));
    if (current === request) headers.value = new Map(loaded);
  },
  { immediate: true },
);

const loading = computed(() => files.value.some((file) => !headers.value.has(file)));
const shown = computed(() =>
  unresolved.value.map((conflict) => ({
    conflict,
    view: conflictView(conflict, headers.value.get(conflict.file) ?? null),
  })),
);
const many = computed(() => files.value.length > 1);
</script>

<template>
  <section class="conflict-panel" :aria-labelledby="`${id}-heading`">
    <div class="conflict-intro">
      <h3 :id="`${id}-heading`" class="conflict-heading">Conflicting rows</h3>
      <p class="conflict-text">
        The workbook and the tables changed the same rows since the last sync. Keep one side. To combine both, edit
        the rows in the workbook, save it, and then keep the workbook.
        <template v-if="unresolved.length">The columns that differ come first and are marked.</template>
        <template v-if="many">Keep workbook and Keep tables resolve all conflicts.</template>
      </p>
      <p v-if="!unresolved.length" class="conflict-text">
        The conflicting rows could not be read. Open the workbook to see them, or keep one side.
      </p>
    </div>
    <div class="conflict-actions">
      <VBtn
        variant="tonal"
        color="primary"
        :disabled="disabled"
        :loading="busy === 'workbook'"
        @click="emit('keep', 'workbook')"
      >
        Keep workbook
      </VBtn>
      <VBtn
        variant="tonal"
        color="primary"
        :disabled="disabled"
        :loading="busy === 'tables'"
        @click="emit('keep', 'tables')"
      >
        Keep tables
      </VBtn>
      <VBtn
        variant="text"
        color="primary"
        prepend-icon="fas fa-arrow-up-right-from-square"
        :disabled="disabled"
        :loading="busy === 'open'"
        @click="emit('open')"
      >
        Open workbook
      </VBtn>
    </div>

    <VProgressLinear v-if="loading" indeterminate color="primary" aria-label="Loading the conflicting rows" />
    <template v-else>
      <section
        v-for="({ conflict, view }, index) in shown"
        :key="`${conflict.file}-${index}`"
        class="conflict-file"
        :aria-labelledby="`${id}-${index}`"
      >
        <h4 :id="`${id}-${index}`" class="conflict-file-head">
          <span class="conflict-file-name">{{ conflict.file }}</span>
          <span class="conflict-sheet">sheet {{ conflict.sheet }}</span>
        </h4>
        <p v-if="view.note" class="field-note conflict-note">{{ view.note }}</p>
        <TableGrid
          :table="view.table"
          :columns="view.columns"
          :mark-column="view.changed"
          mark-text="changed"
          line-header="Version"
          :label="`Conflicting rows of ${conflict.file}`"
          class="conflict-grid"
        >
          <template #line="{ line }">{{ view.labels.get(line) }}</template>
        </TableGrid>
      </section>
    </template>
  </section>
</template>

<style scoped>
/* A card in the error color of the status above it. */
.conflict-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-inline-start: 3px solid rgb(var(--v-theme-error));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
}
.conflict-intro {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.conflict-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.conflict-text {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
.conflict-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.conflict-file {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.conflict-file-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px 12px;
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.4;
}
.conflict-file-name {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.conflict-sheet {
  font-size: 0.8125rem;
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The version of a row, such as Workbook row 12, needs a wider line column. */
.conflict-grid {
  --rows-line-width: 8.5rem;
}
</style>
