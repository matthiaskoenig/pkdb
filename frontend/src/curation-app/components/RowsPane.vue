<script setup lang="ts">
import { computed } from "vue";
import { VAlert, VBtn, VProgressLinear } from "vuetify/components";
import type { StudyDetail, TableResponse } from "../api/types";
import { sourceLines, isShared } from "../data";
import { columnCount, issueCells, itemsWithoutRows, keptColumns, targetLines, visibleColumns } from "../grid";
import { plural } from "../overview";
import TableGrid from "./TableGrid.vue";

/**
 * The right pane of the Data section: the rows of one table file, read only. Rows that open
 * review items target are amber and cells with problems are outlined. A click on a row selects
 * its line. Of a shared table, `onlySource` shows only the rows of `source`, and the line of the
 * route always, so that a link to a row never lands on a hidden one. The default slot renders
 * above the grid, where the section puts its conflict panel.
 */
const props = defineProps<{
  detail: StudyDetail;
  file: string;
  table: TableResponse | null;
  /** The study page that the rows were loaded for, whose review items and targets belong to them. */
  rowsDetail: StudyDetail | null;
  loading: boolean;
  error: string | null;
  /** The cell of the route: its line, and its column when it names one. */
  focus: { line: number; column?: string } | null;
  source: string | null;
  onlySource: boolean;
  hideEmpty: boolean;
}>();
const emit = defineEmits<{ "select-line": [line: number]; retry: []; "show-all": [] }>();
defineSlots<{ default?: () => unknown }>();

/** Whether the rows are narrowed to those of the source. */
const filtered = computed(
  () => props.onlySource && props.source !== null && props.table !== null && isShared(props.detail, props.file),
);
/** The lines that show when filtered, with the line of the route; null shows every row. */
const visible = computed(() => {
  if (!filtered.value) return null;
  const lines = sourceLines(props.table!, props.source!);
  if (props.focus) lines.add(props.focus.line);
  return lines;
});

const reviewItems = computed(() => props.rowsDetail?.review.value?.items ?? []);
const highlight = computed(() =>
  props.table ? targetLines(props.table.file, reviewItems.value, props.rowsDetail?.targets ?? {}) : new Set<number>(),
);
const issues = computed(() => issueCells(props.detail.problems, props.file));

const without = computed(() =>
  props.table
    ? itemsWithoutRows(props.table.file, reviewItems.value, props.rowsDetail?.targets ?? {})
    : { whole: 0, unmatched: 0 },
);

/** The number of empty columns that are hidden. */
const hiddenColumns = computed(() => {
  const shown = props.table;
  if (!shown || !props.hideEmpty) return 0;
  return columnCount(shown) - visibleColumns(shown, true, keptColumns(issues.value, props.focus?.column)).length;
});
const hiddenText = computed(() =>
  hiddenColumns.value === 1 ? "1 empty column is hidden." : `${hiddenColumns.value} empty columns are hidden.`,
);

/** The open review items and the outlined problems, in sentences. */
const notes = computed(() => {
  const shown = props.table;
  if (!shown) return [];
  const parts: string[] = [];
  if (highlight.value.size) parts.push(`Open review items target ${plural(highlight.value.size, "row")}.`);
  const { whole, unmatched } = without.value;
  if (whole === 1) parts.push("1 open review item is about the whole table.");
  if (whole > 1) parts.push(`${whole} open review items are about the whole table.`);
  if (unmatched)
    parts.push(unmatched === 1 ? "1 open review item matches no row." : `${unmatched} open review items match no row.`);
  // A problem outlines its cell, the line of its row, or a header cell.
  const outlined = props.detail.problems.filter(
    (issue) => issue.source?.file === shown.file && issue.source.row != null,
  ).length;
  if (outlined === 1) parts.push("1 problem is outlined.");
  if (outlined > 1) parts.push(`${outlined.toLocaleString("en-US")} problems are outlined.`);
  return parts;
});

/** The rows, the targets, the cells with problems and the hidden columns, in sentences, for screen readers. */
const caption = computed(() => {
  if (!props.table) return "";
  const parts = [`${plural(props.table.rows.length, "row")}.`, ...notes.value];
  if (hiddenColumns.value) parts.push(hiddenText.value);
  return parts.join(" ");
});

/** The count of the head line: the rows that show of all rows when narrowed to the source. */
const count = computed(() => {
  const total = props.table?.rows.length ?? 0;
  if (!visible.value || !props.table) return plural(total, "row");
  const shown = props.table.rows.filter((row) => visible.value!.has(row.line)).length;
  return `${shown.toLocaleString("en-US")} of ${plural(total, "row")}`;
});

/** Whether the narrowed table has no row of the source and no focus. */
const empty = computed(() => visible.value !== null && !props.table?.rows.some((row) => visible.value!.has(row.line)));

/** The line of the route when it is no row of the table; line 1 of a table is its header. */
const missingLine = computed(() => {
  const shown = props.table;
  const line = props.focus?.line;
  if (!shown || line === undefined || (shown.kind === "table" && line === 1)) return null;
  return shown.rows.some((row) => row.line === line) ? null : line;
});
</script>

<template>
  <!-- Named apart from its grid, the region "Rows of <file>", so that each landmark has its own name. -->
  <section class="rows-pane" :aria-label="`Table ${file}`">
    <div class="pane-head">
      <i :class="table?.kind === 'raw' ? 'fas fa-table-cells' : 'fas fa-table'" aria-hidden="true"></i>
      <h3 class="pane-head-name">{{ file }}</h3>
      <template v-if="table">
        <span class="pane-head-part pane-head-count" aria-hidden="true">{{ count }}</span>
        <span v-if="hiddenColumns" class="pane-head-part" aria-hidden="true">
          {{ hiddenColumns === 1 ? "1 empty column hidden" : `${hiddenColumns} empty columns hidden` }}
        </span>
        <span v-for="note in notes" :key="note" class="pane-head-part" aria-hidden="true">{{ note }}</span>
        <span v-if="focus" class="pane-head-line">Line {{ focus.line }}</span>
        <p class="d-sr-only">{{ caption }}</p>
      </template>
    </div>

    <slot></slot>

    <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${file}`" />
    <VAlert v-else-if="error" type="error" variant="tonal" density="compact" class="status-alert">
      {{ file }} could not be loaded. {{ error }}
      <template #append>
        <VBtn variant="text" size="small" @click="emit('retry')">Retry</VBtn>
      </template>
    </VAlert>
    <template v-else-if="table">
      <p v-if="missingLine !== null" class="pane-note">
        Line {{ missingLine }} is not a row of {{ table.file }}. The table may have changed since the last
        validation.
      </p>
      <p v-if="empty" class="pane-missing">
        <i class="fas fa-filter" aria-hidden="true"></i>
        <span role="status">No rows of {{ source }} in {{ file }}.</span>
        <VBtn variant="text" size="small" color="primary" @click="emit('show-all')">Show all rows</VBtn>
      </p>
      <TableGrid
        v-else
        :key="table.file"
        :table="table"
        :highlight-lines="highlight"
        :issue-cells="issues"
        :focus="focus"
        :hide-empty="hideEmpty"
        :visible-lines="visible"
        selectable
        :label="table.kind === 'raw' ? `Raw table ${table.file}` : `Rows of ${table.file}`"
        class="rows-pane-grid"
        @select-line="emit('select-line', $event)"
      />
    </template>
  </section>
</template>

<style scoped>
.rows-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.pane-head {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 8px;
  height: 26px;
  padding-inline: 8px;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* The file name and the count of rows keep their room; the notes after them shorten first. */
.pane-head-name {
  flex: 0 0 auto;
  max-width: 100%;
  margin: 0;
  overflow: hidden;
  font-size: inherit;
  font-weight: 700;
  line-height: inherit;
  text-overflow: ellipsis;
}
.pane-head-part {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.pane-head-count {
  flex: 0 0 auto;
}
.pane-head-line {
  flex: 0 0 auto;
  margin-inline-start: auto;
  font-variant-numeric: tabular-nums;
}
.pane-note {
  margin: 0;
  padding: 4px 8px;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.pane-missing {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px;
  padding: 3px 8px;
  font-size: 11.5px;
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.38);
  border-radius: 6px;
}
.rows-pane-grid {
  --rows-max-height: 100%;
  flex: 1;
  min-height: 0;
}
.rows-pane-grid :deep(.rows-scroll) {
  height: 100%;
  border-radius: 0;
  border-inline: 0;
}
</style>
