<script setup lang="ts">
import { computed, shallowRef, useId, watch } from "vue";
import { VBtn, VProgressLinear } from "vuetify/components";
import type { ConflictData } from "../api/types";
import { columnName, conflictGrids, type Side } from "../grid";
import { plural } from "../overview";
import { useStudyStore } from "../stores/study";
import TableGrid from "./TableGrid.vue";

/**
 * The rows that the workbook and the tables changed differently since the last sync, per
 * conflicting file: the rows at the last sync, the rows of the sheet and the lines of the file
 * side by side, split into the cells of the table header. Keep workbook and Keep tables resolve
 * every conflict of the study; Open workbook opens it to make the rows equal.
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

/** The header of each conflicting table, null for a raw table or a table that does not load. */
const headers = shallowRef(new Map<string, string[] | null>());
let request = 0;

async function header(file: string): Promise<string[] | null> {
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
  unresolved.value.map((conflict) => {
    const grids = conflictGrids(conflict, headers.value.get(conflict.file) ?? null);
    return { conflict, grids, changed: grids.changed.map((index) => columnName(grids.tables, index)) };
  }),
);
const many = computed(() => files.value.length > 1);
</script>

<template>
  <section class="conflict-panel" :aria-labelledby="`${id}-heading`">
    <div class="conflict-intro">
      <h3 :id="`${id}-heading`" class="conflict-heading">Conflicting rows</h3>
      <p class="conflict-note">
        The workbook and the tables changed the same rows since the last sync. Keep one side. To combine both, edit
        the rows in the workbook, save it, and then keep the workbook.
        The columns that differ come first and are marked.
        <template v-if="many">Keep workbook and Keep tables resolve all conflicts.</template>
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
        v-for="({ conflict, grids, changed }, index) in shown"
        :key="`${conflict.file}-${index}`"
        class="conflict-file"
        :aria-labelledby="`${id}-${index}`"
      >
        <h4 :id="`${id}-${index}`" class="conflict-file-head">
          <span class="conflict-file-name">{{ conflict.file }}</span>
          <span class="conflict-sheet">sheet {{ conflict.sheet }}</span>
        </h4>
        <div class="conflict-sides">
          <section class="conflict-side" :aria-labelledby="`${id}-${index}-base`">
            <div class="conflict-side-head">
              <h5 :id="`${id}-${index}-base`" class="conflict-side-name">Last sync</h5>
              <span class="conflict-count">{{ plural(grids.base.rows.length, "row") }}</span>
            </div>
            <TableGrid
              v-if="grids.base.rows.length"
              :table="grids.base"
              :columns="grids.columns"
              :mark-column="changed"
              mark-text="changed"
              :line-header="null"
              :label="`${conflict.file} at the last sync`"
            />
            <p v-else class="field-note">Both sides added these rows.</p>
          </section>
          <section class="conflict-side" :aria-labelledby="`${id}-${index}-workbook`">
            <div class="conflict-side-head">
              <h5 :id="`${id}-${index}-workbook`" class="conflict-side-name">Workbook</h5>
              <span class="conflict-count">{{ plural(grids.workbook.rows.length, "row") }}</span>
            </div>
            <TableGrid
              v-if="grids.workbook.rows.length"
              :table="grids.workbook"
              :columns="grids.columns"
              :mark-column="changed"
              mark-text="changed"
              line-header="Row"
              :label="`Rows of the sheet ${conflict.sheet}`"
            />
            <p v-else class="field-note">The workbook removed the sheet.</p>
          </section>
          <section class="conflict-side" :aria-labelledby="`${id}-${index}-tables`">
            <div class="conflict-side-head">
              <h5 :id="`${id}-${index}-tables`" class="conflict-side-name">Tables</h5>
              <span class="conflict-count">{{ plural(grids.tables.rows.length, "row") }}</span>
            </div>
            <TableGrid
              v-if="grids.tables.rows.length"
              :table="grids.tables"
              :columns="grids.columns"
              :mark-column="changed"
              mark-text="changed"
              :label="`Lines of ${conflict.file}`"
            />
            <p v-else class="field-note">The tables removed the file.</p>
          </section>
        </div>
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
.conflict-note {
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
/* Side by side when they fit, below each other in a narrow window. */
.conflict-sides {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: 16px;
  align-items: start;
}
.conflict-side {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.conflict-side-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.conflict-side-name {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.5;
}
.conflict-count {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
