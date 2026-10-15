<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef, watch, watchPostEffect } from "vue";
import { VCheckboxBtn, VIcon, VTable } from "vuetify/components";
import { useStudyViews } from "../context";
import type { StudyRow } from "../types";
import { useCellTip } from "../composables/useCellTip";
import { useWindowPosition } from "../composables/useWindowPosition";
import type { SortKey, StudySort } from "../overview";
import {
  bodyParts,
  keepSizerRows,
  ROW_HEIGHT,
  rowItem,
  sameParts,
  sizerRows,
  type BodyPart,
  type RowItem,
} from "../studyTable";
import StudyTableRow from "./StudyTableRow.vue";
import StudyTooltip from "./StudyTooltip.vue";

const props = withDefaults(
  defineProps<{
    rows: StudyRow[];
    /** The name of the table for screen readers. */
    caption?: string;
  }>(),
  { caption: "Studies of the workspace" },
);
const selected = defineModel<string[]>("selected", { default: () => [] });
const sort = defineModel<StudySort>("sort", { required: true });
const emit = defineEmits<{ retry: [row: StudyRow] }>();
/** The profiles of the curators and the repository of the issues come from the page. */
const views = useStudyViews();

/**
 * The columns after the checkbox, in their order. The cells of StudyTableRow.vue and the sized
 * columns of studyTable.ts (SIZED_CELLS) follow the same order. A column with `needs` shows only
 * with that capability; the checkbox only with `edit`.
 */
const columns: { key: SortKey | null; label: string; cell: string; needs: "curation" | "jobs" | null }[] = [
  { key: "study", label: "Study", cell: "cell-study", needs: null },
  { key: "release", label: "Release", cell: "cell-release", needs: null },
  { key: "issue", label: "Issue", cell: "cell-issue", needs: "curation" },
  { key: null, label: "Curators", cell: "cell-curators", needs: null },
  { key: "review", label: "Review", cell: "cell-review", needs: "curation" },
  { key: "open_items", label: "Open items", cell: "cell-open", needs: "curation" },
  { key: "problems", label: "Problems", cell: "cell-problems", needs: "curation" },
  { key: "sync", label: "Sync", cell: "cell-sync", needs: "jobs" },
  { key: "upload", label: "Last upload", cell: "cell-upload", needs: "jobs" },
];
const capabilities = views.capabilities;
/** The columns that the reader sees: those of the curation and of the jobs only with them. */
const shownColumns = computed(() =>
  columns.filter((column) => column.needs === null || capabilities.value[column.needs]),
);
/** The cell classes of the shown columns, which the rows render. */
const cells = computed<ReadonlySet<string>>(() => new Set(shownColumns.value.map((column) => column.cell)));

/** Rows with a duplicate identity cannot be selected: every action of the server refuses them. */
const selectable = computed(() => props.rows.filter((row) => !row.duplicate));
const chosen = computed(() => new Set(selected.value));
const allSelected = computed(
  () => selectable.value.length > 0 && selectable.value.every((row) => chosen.value.has(row.id)),
);
const someSelected = computed(() => !allSelected.value && selectable.value.some((row) => chosen.value.has(row.id)));

// Vuetify marks a partial selection with aria-checked="mixed" only; the native state of the
// checkbox has to match it.
const selectAll = useTemplateRef<HTMLElement>("select-all");
watchPostEffect(() => {
  const input = selectAll.value?.querySelector("input");
  if (input) input.indeterminate = someSelected.value;
});

function isSelected(row: StudyRow): boolean {
  return !row.duplicate && chosen.value.has(row.id);
}

function toggle(row: StudyRow): void {
  selected.value = isSelected(row) ? selected.value.filter((id) => id !== row.id) : [...selected.value, row.id];
}

function toggleAll(): void {
  selected.value = allSelected.value ? [] : selectable.value.map((row) => row.id);
}

function sortBy(key: SortKey): void {
  sort.value = { key, descending: sort.value.key === key ? !sort.value.descending : false };
}

function ariaSort(key: SortKey | null): "ascending" | "descending" | undefined {
  if (key === null || sort.value.key !== key) return undefined;
  return sort.value.descending ? "descending" : "ascending";
}

/**
 * The half of the sort glyph that marks the sort order of the active column, drawn over the full
 * glyph: in Font Awesome 7 the up and down arrows are the top and the bottom half of the same box.
 */
function activeHalf(key: SortKey): string | null {
  if (sort.value.key !== key) return null;
  return sort.value.descending ? "fas fa-sort-down" : "fas fa-sort-up";
}

/**
 * The item of each row object, built once (the rows keep their objects through filters, sorting
 * and the polls that leave them as they are, see `keepUnchanged`) and again when the profiles or
 * the repository change.
 */
const cache = computed(() => ({
  profiles: views.data.profiles.value,
  repository: views.data.repository.value,
  items: new WeakMap<StudyRow, RowItem>(),
}));

function itemOf(row: StudyRow): RowItem {
  const { profiles, repository, items } = cache.value;
  let item = items.get(row);
  if (!item) items.set(row, (item = rowItem(row, profiles, repository)));
  return item;
}

const body = useTemplateRef<HTMLElement>("body");
const { position, schedule } = useWindowPosition(body, "tr.study-row");
// The filters above the table wrap differently with other counts and move the table.
watch(() => props.rows, schedule, { flush: "post" });
/** The height of every study row: ROW_HEIGHT at the default font size, more with a larger one. */
const rowHeight = computed(() => position.value.rowHeight ?? ROW_HEIGHT);

/** The folder of the study whose row has the keyboard focus: it stays rendered wherever it is. */
const focusedPath = ref<string | null>(null);
// A row that a filter removed has lost its focus with the element: it is not pinned when it returns.
watch(
  () => props.rows,
  (rows) => {
    if (focusedPath.value !== null && !rows.some((row) => row.path === focusedPath.value)) focusedPath.value = null;
  },
);
const pinned = computed(() => {
  const path = focusedPath.value;
  if (path === null) return null;
  const index = props.rows.findIndex((row) => row.path === path);
  return index < 0 ? null : index;
});

/** The rendered rows and the spaces between them; the same list while scrolling keeps them. */
const parts = computed<BodyPart[]>((previous) => {
  const next = bodyParts(
    { count: props.rows.length, top: position.value.top, height: position.value.height, pinned: pinned.value },
    rowHeight.value,
  );
  return previous && sameParts(previous, next) ? previous : next;
});

/** Hidden rows that give the columns the widths of all shown rows; those that stay render once. */
const sizers = computed<readonly StudyRow[]>((previous) => keepSizerRows(previous ?? [], sizerRows(props.rows)));

// The tooltip of the identities: one for the table, at the identity under the pointer or of the
// keyboard (`data-tip`, the folder of the study), so that the rows render no tooltip and none of
// them renders again when it shows, moves or hides.
const tip = useCellTip();

function studyOf(path: string): StudyRow | undefined {
  return props.rows.find((row) => row.path === path);
}

/** Anything in the page scrolled: a tooltip of the pointer hides, one of the focus follows its identity. */
function onScroll(): void {
  tip.scrolled(null);
}

onMounted(() => document.addEventListener("scroll", onScroll, { capture: true, passive: true }));
onBeforeUnmount(() => document.removeEventListener("scroll", onScroll, { capture: true }));

// A tooltip whose identity is no longer rendered, as after a filter or a scroll, hides.
watch(
  [parts, () => props.rows],
  () => {
    const cell = tip.cell.value;
    if (cell && !cell.isConnected) tip.hide();
  },
  { flush: "post" },
);

function focusIn(event: FocusEvent): void {
  const row = event.target instanceof Element ? event.target.closest("tr[aria-rowindex]") : null;
  const index = row ? Number(row.getAttribute("aria-rowindex")) - 2 : -1;
  focusedPath.value = props.rows[index]?.path ?? null;
  tip.focusIn(event);
}

function focusOut(event: FocusEvent): void {
  tip.focusOut(event);
  // Once the focus moved: when the window loses the focus, as to another application, the event
  // names no new target while the row keeps the focus of the page.
  setTimeout(() => {
    if (!body.value?.contains(document.activeElement)) focusedPath.value = null;
  });
}
</script>

<template>
  <VTable class="study-table" density="compact">
    <!-- The wrapper slot renders the table itself, so that it gets aria-rowcount: VTable passes
         only aria-label attributes to its table. -->
    <template #wrapper>
      <div class="v-table__wrapper">
        <table :aria-rowcount="rows.length + 1">
          <caption class="d-sr-only">
            {{ caption }}
          </caption>
          <thead>
            <tr aria-rowindex="1">
              <th v-if="capabilities.edit" ref="select-all" scope="col" class="cell-select">
                <VCheckboxBtn
                  :model-value="allSelected"
                  :indeterminate="someSelected"
                  :disabled="selectable.length === 0"
                  density="compact"
                  aria-label="Select all shown studies"
                  @update:model-value="toggleAll"
                />
              </th>
              <th
                v-for="column in shownColumns"
                :key="column.cell"
                scope="col"
                :class="column.cell"
                :aria-sort="ariaSort(column.key)"
              >
                <button v-if="column.key" type="button" class="sort-button" @click="sortBy(column.key)">
                  {{ column.label }}<span class="sort-icon" aria-hidden="true"
                    ><VIcon icon="fas fa-sort" size="12" class="sort-base" /><VIcon
                      v-if="activeHalf(column.key)"
                      :icon="activeHalf(column.key)!"
                      size="12"
                      class="sort-active"
                  /></span>
                </button>
                <template v-else>{{ column.label }}</template>
              </th>
            </tr>
          </thead>
          <tbody
            ref="body"
            @focusin="focusIn"
            @focusout="focusOut"
            @mouseover="tip.over"
            @mouseout="tip.out"
          >
            <StudyTableRow
              v-for="row in sizers"
              :key="row.path"
              :item="itemOf(row)"
              :selected="false"
              :row-index="null"
              :cells="cells"
            />
            <template v-for="part in parts" :key="part.kind === 'row' ? rows[part.index]!.path : part.key">
              <tr v-if="part.kind === 'space'" class="study-space" aria-hidden="true">
                <td
                  :colspan="shownColumns.length + (capabilities.edit ? 1 : 0)"
                  :style="{ height: `${part.rows * rowHeight}px` }"
                />
              </tr>
              <StudyTableRow
                v-else
                :item="itemOf(rows[part.index]!)"
                :selected="isSelected(rows[part.index]!)"
                :row-index="part.index + 2"
                :cells="cells"
                @toggle="toggle(rows[part.index]!)"
                @retry="emit('retry', rows[part.index]!)"
              />
            </template>
          </tbody>
        </table>
        <StudyTooltip :tip="tip" :study-of="studyOf" />
      </div>
    </template>
  </VTable>
</template>

<style scoped>
.study-table {
  background: transparent;
}
.study-table :deep(table) {
  min-width: 100%;
}
.study-table th {
  vertical-align: middle;
  /* Every header has one line height, also those of the columns whose cells set their own, so
     that the labels share a baseline. */
  line-height: 24px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.sort-button {
  display: inline-flex;
  /* The top of the line box, where a label without a button starts too. */
  vertical-align: top;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
/* One box for the base glyph and the active half, so that the arrow never moves or changes width. */
.sort-icon {
  display: inline-grid;
}
.sort-icon > .v-icon {
  grid-area: 1 / 1;
}
.sort-base {
  opacity: 0.6;
}
th[aria-sort] .sort-button {
  color: rgb(var(--v-theme-on-surface));
}
th[aria-sort] .sort-base {
  opacity: 0.3;
}
.sort-active {
  opacity: 1;
}
.study-table th.cell-open .sort-button {
  flex-direction: row-reverse;
}
.study-table th.cell-open {
  text-align: end;
}
</style>

<style>
/* The cells of the header and of every row (StudyTableRow.vue): one 24px line per study. The
   study column takes the room that the table has left: its title is cut with an ellipsis
   instead of wrapping, and every other cell stays on one line at the width of its content. */
.study-table th,
.study-table td {
  box-sizing: border-box;
  width: 1px;
  height: 24px;
  padding: 0 8px;
  white-space: nowrap;
  vertical-align: middle;
}
.study-table .cell-study {
  width: 100%;
  min-width: 12rem;
}
.study-table .cell-select {
  width: 48px;
  min-width: 48px;
  padding-inline: 8px 0;
}
/* The checkbox and the chips of a row fit the 24px of the row, of which 1px is its border. The
   input of the checkbox, its target, is 24px and reaches over the border. */
.study-table .cell-select .v-selection-control {
  justify-content: center;
  min-height: 23px;
  --v-selection-control-size: 20px;
}
.study-table .cell-select .v-selection-control__input {
  width: 24px;
  height: 24px;
}
/* The window renders other rows as the page scrolls. Should a row ever not have the height that
   the window measured, the browser must not anchor the scroll position to a row: it would pull the
   page back across the edge of a row, and the window would follow, without end. */
.study-table tbody {
  overflow-anchor: none;
}
/* The sizer rows (StudyTableRow.vue without a row index) take no height but keep the widths of
   their cells, and the space of the rows that are not rendered draws nothing. A space takes its
   height at once: Vuetify animates the height of cells, which would move the rendered rows away
   from their places, and so out of the window while it scrolls. */
.study-table tr.study-sizer {
  visibility: collapse;
}
.study-table tr.study-space > td {
  padding: 0;
  border: 0;
  transition: none;
}
/* A printed overview shows the rendered rows, without the pages of the space of the others. */
@media print {
  .study-table tr.study-space {
    display: none;
  }
}
</style>
