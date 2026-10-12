<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VChip, VProgressLinear } from "vuetify/components";
import type { StudyDetail, TableResponse } from "../api/types";
import {
  ALL_ROWS,
  filterChoices,
  filteredLines,
  filterOf,
  filterValue,
  findTable,
  isShared,
  type RowFilter,
} from "../data";
import { columnCount, issueCells, itemsWithoutRows, keptColumns, targetLines, visibleColumns } from "../grid";
import { infoColor, infoStyle } from "../info";
import { plural } from "../overview";
import type { ActionFailure } from "../study";
import { kindLabel } from "../tableKinds";
import ActionFailureAlert from "./ActionFailureAlert.vue";
import TableGrid from "./TableGrid.vue";

/**
 * The right pane of the Data section: the rows of one table file, read only. Rows that open
 * review items target are amber and cells with problems are outlined. A click on a row selects
 * its line. A shared table, whose rows name their source, has a Source select in its head: all
 * rows, those of one source, or those without a source; the line of the route always shows, so
 * that a link to a row never lands on a hidden one. The default slot renders between the head
 * and the grid, where the section puts the notes of the table kind and its conflict panel.
 *
 * The pane tints its table and shows its kind in the color of its class of information. Its head
 * wraps rather than cut what it shows in a narrow pane, and the notes about the rows stand right
 * above the grid as sentences that wrap.
 */
const props = defineProps<{
  detail: StudyDetail;
  file: string;
  table: TableResponse | null;
  /** The study page that the rows were loaded for, whose review items and targets belong to them. */
  rowsDetail: StudyDetail | null;
  loading: boolean;
  /** Why the rows could not be loaded, with what the local server said about it. */
  error: ActionFailure | null;
  /** The cell of the route: its line, and its column when it names one. */
  focus: { line: number; column?: string } | null;
  /** The filter of the rows of a shared table, which the section keeps per table. */
  filter: RowFilter;
  hideEmpty: boolean;
}>();
const emit = defineEmits<{ "select-line": [line: number]; retry: []; "update:filter": [filter: RowFilter] }>();
defineSlots<{ default?: () => unknown }>();

/** The table in the study page: its kind and class of information. */
const entry = computed(() => findTable(props.detail, props.file));

/** The options of the Source select; only a shared table has them. */
const choices = computed(() => (props.table && isShared(props.detail, props.file) ? filterChoices(props.table) : []));
/** The filter that applies: one whose source the rows no longer name shows all rows. */
const applied = computed<RowFilter>(() =>
  choices.value.some((choice) => choice.value === filterValue(props.filter)) ? props.filter : ALL_ROWS,
);
/** The lines that show when filtered, with the line of the route; null shows every row. */
const visible = computed(() => {
  if (!props.table || !choices.value.length) return null;
  const lines = filteredLines(props.table, applied.value);
  if (lines && props.focus) lines.add(props.focus.line);
  return lines;
});

function choose(event: Event): void {
  emit("update:filter", filterOf((event.target as HTMLSelectElement).value));
}

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

/** The count of the head line: the rows that show of all rows when filtered. */
const count = computed(() => {
  const total = props.table?.rows.length ?? 0;
  if (!visible.value || !props.table) return plural(total, "row");
  const shown = props.table.rows.filter((row) => visible.value!.has(row.line)).length;
  return `${shown.toLocaleString("en-US")} of ${plural(total, "row")}`;
});

/** The targets, the cells with problems and the hidden columns, in sentences, which show above the grid. */
const sentences = computed(() => (hiddenColumns.value ? [...notes.value, hiddenText.value] : notes.value));

/** The rows and the sentences, for screen readers. */
const caption = computed(() => (props.table ? [`${count.value}.`, ...sentences.value].join(" ") : ""));

/** Whether the filtered table has no row and no focus. */
const empty = computed(() => visible.value !== null && !props.table?.rows.some((row) => visible.value!.has(row.line)));
const emptyText = computed(() =>
  applied.value.kind === "source"
    ? `No rows of ${applied.value.source} in ${props.file}.`
    : `Every row of ${props.file} names a source.`,
);

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
  <section class="rows-pane" :aria-label="`Table ${file}`" :style="entry ? infoStyle(entry.info) : undefined">
    <!-- A narrow pane wraps the head rather than clip its parts; the file name keeps its icon beside it. -->
    <div class="pane-head">
      <div class="pane-head-title">
        <i :class="table?.kind === 'raw' ? 'fas fa-table-cells' : 'fas fa-table'" aria-hidden="true"></i>
        <h3 class="pane-head-name" :title="file">{{ file }}</h3>
      </div>
      <!-- The kind in the color of the class of information of the table; its text stays in the text color. -->
      <VChip v-if="entry" size="x-small" variant="tonal" :color="infoColor(entry.info)" class="status-chip pane-head-kind">
        {{ kindLabel(detail, entry.kind) }}
      </VChip>
      <template v-if="table">
        <span class="pane-head-part pane-head-part--fixed" aria-hidden="true">{{ count }}</span>
        <label v-if="choices.length" class="pane-head-filter">
          <span aria-hidden="true">Source</span>
          <select class="pane-head-select" aria-label="Source of the rows" :value="filterValue(applied)" @change="choose">
            <option v-for="choice in choices" :key="choice.value" :value="choice.value">{{ choice.title }}</option>
          </select>
        </label>
        <span v-if="focus" class="pane-head-line">Line {{ focus.line }}</span>
        <p class="d-sr-only">{{ caption }}</p>
      </template>
    </div>
    <!-- What the section shows between the head and the rows, such as the notes of the table kind and the conflicts. -->
    <slot></slot>

    <!-- The sentences of the caption after the count, whole, right above the rows they describe: each
         wraps to a line of its own rather than be cut. -->
    <p v-if="table && sentences.length" class="rows-pane-notes" aria-hidden="true">
      <span v-for="sentence in sentences" :key="sentence">{{ sentence }}</span>
    </p>

    <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${file}`" />
    <!-- It goes when the rows load again, after Retry or a change of the study: no close button. -->
    <ActionFailureAlert v-else-if="error" :failure="error" :study="detail.id" :closable="false">
      <template #append>
        <VBtn variant="text" size="small" @click="emit('retry')">Retry</VBtn>
      </template>
    </ActionFailureAlert>
    <template v-else-if="table">
      <p v-if="missingLine !== null" class="pane-note">
        Line {{ missingLine }} is not a row of {{ table.file }}. The table may have changed since the last
        validation.
      </p>
      <p v-if="empty" class="pane-missing">
        <i class="fas fa-filter" aria-hidden="true"></i>
        <span role="status">{{ emptyText }}</span>
        <VBtn variant="text" size="small" color="primary" @click="emit('update:filter', ALL_ROWS)">Show all rows</VBtn>
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
        :tinted="entry !== undefined"
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
/* The head is one line of 26 px, as the head of the source pane beside it, until a narrow pane
   wraps it: the parts move to a second line whole. Only the file name ends in an ellipsis, when
   it has a line of its own and still no room. */
.rows-pane > .pane-head {
  flex-wrap: wrap;
  row-gap: 2px;
  height: auto;
  min-height: 26px;
  padding-block: 1px;
  overflow: hidden;
}
.pane-head-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.pane-head-title > .pane-head-name {
  flex-shrink: 1;
  min-width: 0;
}
.pane-head-kind {
  flex: 0 0 auto;
}
/* The notes above the grid: sentences in the size of the head, 8 px from the edges. */
.rows-pane > .rows-pane-notes {
  display: flex;
  flex-wrap: wrap;
  gap: 0 12px;
  margin: 0;
  padding: 2px 8px;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.pane-head-line {
  flex: 0 0 auto;
  margin-inline-start: auto;
  font-variant-numeric: tabular-nums;
}
/* The Source select of a shared table: 22 px high inside the 26 px head, with a border of 3:1. */
.pane-head-filter {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The notes stand 8 px from the edges, as in the source pane, which has a padding. */
.rows-pane > .pane-note {
  padding: 4px 8px;
}
.rows-pane > .pane-missing,
.rows-pane > .status-alert {
  margin: 8px;
}
/* The rows take the room that they need, and what the head, the notes and the conflicts leave of
   the pane: open notes grow into the room below a short table. In a pane too short for all, the
   rows give up their room first, down to their header and four rows of 22 px with a scroll bar,
   or all of their rows when they are fewer: their factor of shrinking outweighs that of the notes,
   which outweighs that of the conflicts. Then the panels above them shrink and scroll on their own.
   The basis is the height of the rows, and the height of 120 px only bounds their automatic
   minimum, the smaller of it and the height of the rows. */
.rows-pane-grid {
  --rows-max-height: 100%;
  flex: 1 1000000 content;
  height: 120px;
}
.rows-pane-grid :deep(.rows-scroll) {
  height: 100%;
  border-radius: 0;
  border-inline: 0;
}
/* The fade of more columns ends at the edge of the region, which has no radius and no side borders here. */
.rows-pane-grid.table-grid--more::after {
  inset-inline-end: var(--grid-scrollbar-y, 0px);
  border-radius: 0;
}
</style>
