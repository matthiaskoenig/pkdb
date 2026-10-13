<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import type { TableResponse } from "../api/types";
import { columnName, keptColumns, ROW, visibleColumns, type CellIssues, type IssueCells } from "../grid";

/** Above this many rows, only the rows near the view render; the others are spacers. */
const VIRTUAL_ROWS = 500;
/** The height of a row and of the header until one is measured: 22 px with the line below. */
const ROW_HEIGHT = 22;
/** The height of the region until it is measured, such as without a layout. */
const VIEW_HEIGHT = 600;
/** The rows that render beyond each edge of the view. */
const OVERSCAN = 10;
/** The rendered rows move in steps of this many rows, so that most scrolling renders nothing. */
const STEP = 10;

/**
 * The rows of a table with the lines of its TSV file, or of a raw table with the column letters of
 * its sheet, read only. Rows that open review items target are amber, cells with problems are
 * outlined and describe the problems to screen readers, a column can be marked, and empty
 * columns can be hidden. The header and the line column stay in view while the rows scroll.
 *
 * Above 500 rows, only the rows near the view render, between spacers of the height of the
 * others; `aria-rowcount` and `aria-rowindex` give screen readers the place of each row. The
 * `focus` line scrolls into view with its cell marked and focused. The line buttons of a
 * selectable grid are one Tab stop: the arrow keys move the focus to the row above or below,
 * Home and End to the first and the last row.
 *
 * A tinted grid shows the class of information of its table: its header row and its cells in the
 * color `--info` of its pane.
 */
const props = withDefaults(
  defineProps<{
    table: TableResponse;
    highlightLines?: Set<number>;
    /** A column to mark, or several. */
    markColumn?: string | readonly string[] | null;
    /** What a marked column is, for screen readers. */
    markText?: string;
    issueCells?: IssueCells;
    focus?: { line: number; column?: string } | null;
    hideEmpty?: boolean;
    /** The indices of the columns to show, in this order; else every column, or those that `hideEmpty` leaves. */
    columns?: number[] | null;
    /** The accessible name of the region; `Rows of <file>` by default. */
    label?: string | null;
    /** The header of the line column, such as Row for the rows of a sheet; null leaves the column out. */
    lineHeader?: string | null;
    /** Whether a click on a row selects its line: the line cell becomes a button. */
    selectable?: boolean;
    /** The lines of the rows to show; null shows every row. */
    visibleLines?: ReadonlySet<number> | null;
    /** Whether the rows show the class of information of their table in the color `--info` of an ancestor. */
    tinted?: boolean;
  }>(),
  {
    highlightLines: () => new Set<number>(),
    markColumn: null,
    markText: "the marked column",
    issueCells: () => new Map(),
    focus: null,
    hideEmpty: false,
    columns: null,
    label: null,
    lineHeader: "Line",
    selectable: false,
    visibleLines: null,
    tinted: false,
  },
);
const emit = defineEmits<{ "select-line": [line: number] }>();
defineSlots<{
  /** The content of the line cell of a row; its line by default. */
  line?: (props: { line: number }) => unknown;
}>();

const id = useId();
const region = ref<HTMLElement | null>(null);

/** The rows that show: all, or those of `visibleLines`. */
const shownRows = computed(() =>
  props.visibleLines ? props.table.rows.filter((row) => props.visibleLines!.has(row.line)) : props.table.rows,
);

const raw = computed(() => props.table.kind === "raw");
const lines = computed(() => props.lineHeader !== null);

const marked = computed(
  () => new Set(typeof props.markColumn === "string" ? [props.markColumn] : (props.markColumn ?? [])),
);
/** The columns that stay when empty columns are hidden: marked, focused, or with a problem. */
const kept = computed(() => keptColumns(props.issueCells, ...marked.value, props.focus?.column));
const headers = computed(() =>
  (props.columns ?? visibleColumns(props.table, props.hideEmpty, kept.value)).map((index) => ({
    index,
    name: columnName(props.table, index),
  })),
);
const span = computed(() => headers.value.length + (lines.value ? 1 : 0));

// The rows near the view

const virtual = computed(() => shownRows.value.length > VIRTUAL_ROWS);
const rowHeight = ref(ROW_HEIGHT);
const headerHeight = ref(ROW_HEIGHT);
const viewRows = ref(Math.ceil(VIEW_HEIGHT / ROW_HEIGHT));
/** The index of the first rendered row. */
const start = ref(0);
/** Whether rows scroll below the header, which then needs its background. */
const scrolled = ref(false);
/**
 * Whether more columns follow at the end of the region, which the rows then fade out to, the
 * sizes of its scroll bars, which the fade leaves free, and the height of the header row, which a
 * tinted grid fades out to its own tint.
 */
const more = ref(false);
const scrollbars = ref({ x: 0, y: 0 });
const fade = computed(() => ({
  "--grid-scrollbar-x": `${scrollbars.value.x}px`,
  "--grid-scrollbar-y": `${scrollbars.value.y}px`,
  "--grid-head-height": `${headerHeight.value}px`,
}));

function windowEnd(first: number): number {
  return Math.min(shownRows.value.length, first + viewRows.value + 2 * OVERSCAN + STEP);
}

/** The first row to render for `scrollTop`: a step at least `OVERSCAN` rows above the view. */
function windowStart(scrollTop: number): number {
  const first = Math.floor(Math.max(0, scrollTop - headerHeight.value) / rowHeight.value);
  return Math.max(0, Math.min(Math.floor(first / STEP) * STEP - OVERSCAN, shownRows.value.length - 1));
}

const from = computed(() => (virtual.value ? Math.min(start.value, Math.max(0, shownRows.value.length - 1)) : 0));
const to = computed(() => (virtual.value ? windowEnd(from.value) : shownRows.value.length));
const rendered = computed(() =>
  shownRows.value.slice(from.value, to.value).map((row, offset) => ({ row, index: from.value + offset })),
);
const before = computed(() => from.value * rowHeight.value);
const after = computed(() => (shownRows.value.length - to.value) * rowHeight.value);

/** A focused cell that is about to leave the rendered rows gives the focus to the region. */
function keepFocus(first: number): void {
  const element = region.value;
  const active = document.activeElement;
  if (!element || !(active instanceof HTMLElement) || active === element || !element.contains(active)) return;
  const index = Number(active.closest<HTMLElement>("tr[data-index]")?.dataset.index ?? -1);
  if (index >= 0 && (index < first || index >= windowEnd(first))) element.focus({ preventScroll: true });
}

function update(): void {
  const element = region.value;
  if (!element) return;
  scrolled.value = element.scrollTop > 0;
  more.value = element.scrollLeft + element.clientWidth < element.scrollWidth - 1;
  if (more.value) {
    const { borderTopWidth, borderBottomWidth, borderLeftWidth, borderRightWidth } = getComputedStyle(element);
    scrollbars.value = {
      x: element.offsetHeight - element.clientHeight - parseFloat(borderTopWidth) - parseFloat(borderBottomWidth),
      y: element.offsetWidth - element.clientWidth - parseFloat(borderLeftWidth) - parseFloat(borderRightWidth),
    };
  }
  if (!virtual.value) return;
  const next = windowStart(element.scrollTop);
  if (next === start.value) return;
  keepFocus(next);
  start.value = next;
}

/** The heights of a row, the header and the view, once the region has a layout. */
function measure(): void {
  const element = region.value;
  if (!element) return;
  const row = element.querySelector("tbody tr[data-index]")?.getBoundingClientRect().height ?? 0;
  const header = element.querySelector("thead tr")?.getBoundingClientRect().height ?? 0;
  if (row > 0) rowHeight.value = row;
  if (header > 0) headerHeight.value = header;
  if (element.clientHeight > 0) viewRows.value = Math.ceil(element.clientHeight / rowHeight.value);
  update();
}

let observer: ResizeObserver | undefined;
onMounted(() => {
  measure();
  observer = new ResizeObserver(measure);
  if (region.value) observer.observe(region.value);
});
onBeforeUnmount(() => observer?.disconnect());
// New rows of the same table keep the scroll position, which the browser shortens to the rows.
// Other columns, such as hidden empty ones, change the width of the rows.
watch(
  [() => props.table, headers],
  () => void nextTick(measure),
);

// Problems, targets and the focus

interface Note {
  id: string;
  severity: CellIssues["severity"];
  text: string;
}

/**
 * The problems of the rendered cells by `<line>:<column index>`, -1 for the line cell: a problem
 * of the whole row or of a column that does not show. Line 0 of a table is its header.
 */
const notes = computed(() => {
  const found = new Map<string, Note>();
  const shown = new Map(headers.value.map(({ index, name }) => [name, index]));
  const lines = [...(raw.value ? [] : [0]), ...rendered.value.map(({ row }) => row.line)];
  for (const line of lines)
    for (const [name, cell] of props.issueCells.get(line) ?? []) {
      const index = name === ROW ? -1 : (shown.get(name) ?? -1);
      const key = `${line}:${index}`;
      const prior = found.get(key);
      found.set(key, {
        id: `${id}-${line}-${index < 0 ? "line" : index}`,
        severity: prior?.severity === "error" ? "error" : cell.severity,
        text: [prior?.text, ...cell.messages].filter(Boolean).join(" "),
      });
    }
  return found;
});
const targetNote = `${id}-target`;

const focusLine = computed(() => props.focus?.line ?? null);
/** The column of the focus when it shows; else the focus marks the line cell. */
const focusColumn = computed(() => {
  const column = props.focus?.column;
  return column !== undefined && headers.value.some(({ name }) => name === column) ? column : null;
});

function isFocus(line: number, name: string | null): boolean {
  return line === focusLine.value && (name === null ? focusColumn.value === null : name === focusColumn.value);
}

function cellClass(line: number, index: number, name: string): Record<string, boolean> {
  const note = notes.value.get(`${line}:${index}`);
  return {
    "grid-cell--error": note?.severity === "error",
    "grid-cell--warning": note?.severity === "warning",
    "grid-cell--marked": marked.value.has(name),
    "grid-cell--focus": isFocus(line, name),
    "grid-raw": raw.value,
  };
}

function lineClass(line: number): Record<string, boolean> {
  const note = notes.value.get(`${line}:-1`);
  return {
    "grid-cell--error": note?.severity === "error",
    "grid-cell--warning": note?.severity === "warning",
    "grid-cell--focus": isFocus(line, null),
  };
}

/** The problems of the header of a table, at its line 0; a raw table has no header line. */
function headerNote(index: number): Note | undefined {
  return raw.value ? undefined : notes.value.get(`0:${index}`);
}

/** The classes of a header cell; the index -1 is the header of the line column. */
function headerClass(index: number, name: string | null): Record<string, boolean> {
  const note = headerNote(index);
  return {
    "grid-cell--error": note?.severity === "error",
    "grid-cell--warning": note?.severity === "warning",
    "grid-cell--marked": name !== null && marked.value.has(name),
    "grid-letter": raw.value && index >= 0,
  };
}

function described(...ids: (string | undefined | false)[]): string | undefined {
  return ids.filter(Boolean).join(" ") || undefined;
}

/**
 * How far a region scrolls so that the span from `start` to `end` shows between `low` and `high`:
 * not at all when it shows whole, so that the rows under the pointer stay where they are; the
 * least when it shows in part or `nearest` asks for it; else to the middle.
 */
function scrollFor(start: number, end: number, low: number, high: number, nearest = false): number {
  if (start >= low && end <= high) return 0;
  if (nearest || (end > low && start < high)) return start < low ? start - low : end - high;
  return start - low - (high - low - (end - start)) / 2;
}

/** Render the row at `index` of the shown rows, with the row in the middle of the view. */
async function renderRow(index: number): Promise<boolean> {
  const element = region.value;
  if (!element || !virtual.value || (index >= from.value && index < to.value)) return false;
  const view = element.clientHeight || VIEW_HEIGHT;
  element.scrollTop = Math.max(0, headerHeight.value + index * rowHeight.value - (view - rowHeight.value) / 2);
  update();
  await nextTick();
  return true;
}

/**
 * Scroll the region to `cell` when it is not in view below the header and, for a cell of a
 * column, right of the line column; whether the region scrolled.
 */
function scrollToCell(cell: HTMLElement, nearest = false): boolean {
  const element = region.value;
  if (!element) return false;
  const box = element.getBoundingClientRect();
  const target = cell.getBoundingClientRect();
  const top = box.top + element.clientTop;
  const down = scrollFor(target.top, target.bottom, top + headerHeight.value, top + element.clientHeight, nearest);
  element.scrollTop += down;
  let right = 0;
  if (cell.tagName === "TD") {
    const left = box.left + element.clientLeft;
    const start = lines.value ? (element.querySelector("thead .rows-line")?.getBoundingClientRect().width ?? 0) : 0;
    right = scrollFor(target.left, target.right, left + start, left + element.clientWidth);
    element.scrollLeft += right;
  }
  return down !== 0 || right !== 0;
}

/**
 * Where the page shows below what sticks at the top of the window: the bottom of the banner of
 * unsaved changes while it sticks, which publishes where and its height (UnsavedBanner), else of
 * the app bar.
 */
function stickyBottom(element: HTMLElement): number {
  const style = getComputedStyle(element);
  const length = (name: string) => Number.parseFloat(style.getPropertyValue(name)) || 0;
  return (length("--unsaved-banner-top") || length("--v-layout-top")) + length("--unsaved-banner-height");
}

/**
 * Scroll the region to the focused cell when it is not in view, bring the region into the page
 * view when the cell was not in the window either, or under the app bar or the banner of unsaved
 * changes, then focus the cell without scrolling again. A focus in view, such as of a clicked row,
 * leaves the rows in place. Only the region scrolls to the cell, so that the page keeps what is
 * above the region in view (its margin: `--rows-scroll-margin`).
 */
async function reveal(): Promise<void> {
  const element = region.value;
  const index = focusLine.value === null ? -1 : shownRows.value.findIndex((row) => row.line === focusLine.value);
  if (!element || index < 0) return;
  const moved = await renderRow(index);
  const cell = element.querySelector<HTMLElement>(".grid-cell--focus");
  if (!cell) return;
  const { top, bottom } = cell.getBoundingClientRect();
  const outside = top < stickyBottom(element) || bottom > window.innerHeight;
  if (scrollToCell(cell) || moved || outside) element.scrollIntoView({ block: "nearest" });
  cell.focus({ preventScroll: true });
}

// By value: a reload of the table or the study gives an equal focus, which keeps the scroll and the focus.
watch(
  () => (props.focus ? `${props.focus.line}:${props.focus.column ?? ""}` : null),
  () => void nextTick(reveal),
  { immediate: true },
);

// The keyboard: the line buttons of a selectable grid are one Tab stop, which the arrow keys move.

/** The line whose button the keyboard reached last; a new focus of the route takes its place. */
const keyLine = ref<number | null>(null);
watch(focusLine, (line) => (keyLine.value = line));
/** The line whose button is the Tab stop: the one the keyboard reached, else the focus line, else the first rendered row. */
const tabLine = computed(() => {
  const shown = new Set(rendered.value.map(({ row }) => row.line));
  return [keyLine.value, focusLine.value].find((line) => line !== null && shown.has(line)) ?? rendered.value[0]?.row.line;
});

const MOVES: Record<string, (index: number, last: number) => number> = {
  ArrowUp: (index) => index - 1,
  ArrowDown: (index) => index + 1,
  Home: () => 0,
  End: (_, last) => last,
};

/** Move the focus from the line cell of the shown row `index`, or its button, to the button of another row. */
async function moveFocus(event: KeyboardEvent, index: number): Promise<void> {
  const move = MOVES[event.key];
  const cell = event.currentTarget as HTMLElement;
  if (!move || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (!cell.querySelector(".grid-line-button")) return;
  event.preventDefault();
  const last = shownRows.value.length - 1;
  const next = Math.min(last, Math.max(0, move(index, last)));
  keyLine.value = shownRows.value[next]?.line ?? null;
  await renderRow(next);
  const button = region.value?.querySelector<HTMLElement>(`tr[data-index="${next}"] .grid-line-button`);
  if (!button) return;
  scrollToCell(button.closest("th") ?? button, true);
  button.focus({ preventScroll: true });
}
</script>

<template>
  <div
    class="table-grid"
    :class="{ 'table-grid--more': more, 'table-grid--selectable': selectable, 'table-grid--tinted': tinted }"
    :style="fade"
  >
    <!-- The rows scroll inside their region, which takes the focus so that a keyboard can scroll it. -->
    <div
      ref="region"
      class="rows-scroll"
      :class="{ 'rows-scroll--sticky-line': lines, 'rows-scroll--stuck': scrolled }"
      tabindex="0"
      role="region"
      :aria-label="label ?? `Rows of ${table.file}`"
      @scroll.passive="update"
    >
      <table class="rows-table rows-table--packed" :aria-rowcount="shownRows.length + 1">
        <thead>
          <tr aria-rowindex="1">
            <th
              v-if="lines"
              scope="col"
              class="rows-line"
              :class="headerClass(-1, null)"
              :aria-describedby="described(headerNote(-1)?.id)"
            >
              {{ lineHeader }}
            </th>
            <th
              v-for="column in headers"
              :key="column.index"
              scope="col"
              :class="headerClass(column.index, column.name)"
              :aria-describedby="described(headerNote(column.index)?.id)"
            >
              {{ column.name
              }}<span v-if="marked.has(column.name)" class="d-sr-only">, {{ markText }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="before" aria-hidden="true" class="grid-spacer">
            <td :colspan="span" :style="{ height: `${before}px` }"></td>
          </tr>
          <tr
            v-for="{ row, index } in rendered"
            :key="row.line"
            :data-index="index"
            :aria-rowindex="index + 2"
            :class="{ 'grid-row--target': highlightLines.has(row.line), 'grid-row--focus': row.line === focusLine }"
            @click="selectable && emit('select-line', row.line)"
          >
            <th
              v-if="lines"
              scope="row"
              class="rows-line"
              :class="lineClass(row.line)"
              :tabindex="isFocus(row.line, null) ? -1 : undefined"
              :aria-describedby="
                described(highlightLines.has(row.line) && targetNote, notes.get(`${row.line}:-1`)?.id)
              "
              @keydown="selectable && moveFocus($event, index)"
            >
              <slot name="line" :line="row.line">
                <button
                  v-if="selectable"
                  type="button"
                  class="grid-line-button"
                  :tabindex="row.line === tabLine ? 0 : -1"
                  :title="`Select line ${row.line}`"
                  @focus="keyLine = row.line"
                  @click.stop="emit('select-line', row.line)"
                >
                  {{ row.line }}
                </button>
                <template v-else>{{ row.line }}</template>
              </slot>
            </th>
            <td
              v-for="column in headers"
              :key="column.index"
              :class="cellClass(row.line, column.index, column.name)"
              :tabindex="isFocus(row.line, column.name) ? -1 : undefined"
              :aria-describedby="described(notes.get(`${row.line}:${column.index}`)?.id)"
            >
              {{ row.cells[column.index] ?? "" }}
            </td>
          </tr>
          <tr v-if="after" aria-hidden="true" class="grid-spacer">
            <td :colspan="span" :style="{ height: `${after}px` }"></td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- What the marks mean, for screen readers; descriptions may name hidden elements. -->
    <div hidden>
      <span :id="targetNote">Targeted by an open review item.</span>
      <span v-for="note in notes.values()" :id="note.id" :key="note.id">{{ note.text }}</span>
    </div>
  </div>
</template>

<style scoped>
.table-grid {
  /* The amber of the app (themes.ts) for the bar of a targeted row and the outline of a warning:
     3:1 on the surface and on the rows of open review items in both themes. */
  --grid-amber: rgb(var(--v-theme-caution));
  min-width: 0;
}
/* More columns follow: the rows fade out at the end of the region, above the cells and inside its
   border and scroll bars, so that a cut word shows that the rows scroll. */
.table-grid--more {
  position: relative;
}
.table-grid--more::after {
  content: "";
  position: absolute;
  inset-block: 1px calc(1px + var(--grid-scrollbar-x, 0px));
  inset-inline-end: calc(1px + var(--grid-scrollbar-y, 0px));
  z-index: 2;
  width: 40px;
  border-start-end-radius: 7px;
  border-end-end-radius: 7px;
  background: linear-gradient(to left, rgb(var(--v-theme-surface)), rgba(var(--v-theme-surface), 0));
  pointer-events: none;
}
/* A tinted grid, such as the rows of the Data section, shows the class of information of its
   table in the color `--info` (the RGB of a theme color): the header row over the surface at
   `--v-info-head-tint`, the cells at `--v-info-cell-tint`, opaque on the line column, which
   covers the rows that scroll below it, and a hovered row at the tint of the header. The amber
   rows of open review items and the selected row keep their own tints. Where more columns
   follow, the header row fades out to its own tint and the rows to the surface. */
.table-grid--tinted {
  --grid-head: color-mix(in srgb, rgb(var(--info)) var(--v-info-head-tint), rgb(var(--v-theme-surface)));
}
.table-grid--tinted .rows-table thead th {
  background-color: var(--grid-head);
}
.table-grid--tinted.table-grid--more::after {
  background:
    linear-gradient(to left, var(--grid-head), transparent) top / 100% var(--grid-head-height) no-repeat,
    linear-gradient(to left, rgb(var(--v-theme-surface)), rgba(var(--v-theme-surface), 0)) bottom / 100%
      calc(100% - var(--grid-head-height)) no-repeat;
}
.table-grid--tinted td {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--v-info-cell-tint), transparent);
}
.table-grid--tinted tbody .rows-line {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--v-info-cell-tint), rgb(var(--v-theme-surface)));
}
/* Rows that open review items target: a tint that lets the shadows of the sides show through,
   and an opaque tint on the line column, which covers the rows that scroll below it. The line
   has a bar, so that the rows stand out without the color. */
.rows-table .grid-row--target > td {
  background-color: rgba(var(--v-theme-warning), 0.14);
}
.rows-scroll .rows-table .grid-row--target > .rows-line {
  background-color: color-mix(in srgb, rgb(var(--v-theme-warning)) 14%, rgb(var(--v-theme-surface)));
}
/* The bar covers the line below the row, so that the bars of adjacent rows join. */
.rows-table .grid-row--target > .rows-line::before {
  content: "";
  position: absolute;
  inset-block: 0 -1px;
  inset-inline-start: 0;
  width: 3px;
  background-color: var(--grid-amber);
}
/* The row of the focus: a tint, opaque on the line column, which covers the rows below it. */
.rows-table .grid-row--focus > td {
  background-color: rgba(var(--v-theme-primary), 0.12);
}
.rows-scroll .rows-table .grid-row--focus > .rows-line {
  background-color: color-mix(in srgb, rgb(var(--v-theme-primary)) 12%, rgb(var(--v-theme-surface)));
}
/* A selectable row shows the pointer, and under it the tint of a hovered entry of the navigator,
   opaque on the line column; the rows of open review items and of the focus keep their tints. */
.table-grid--selectable tbody tr[data-index] {
  cursor: pointer;
}
.table-grid--selectable .rows-table tbody tr:not(.grid-row--target, .grid-row--focus):hover > td {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}
.table-grid--selectable .rows-scroll .rows-table tbody tr:not(.grid-row--target, .grid-row--focus):hover > .rows-line {
  background-color: color-mix(in srgb, rgb(var(--v-theme-on-surface)) 5%, rgb(var(--v-theme-surface)));
}
.table-grid--tinted.table-grid--selectable .rows-table tbody tr:not(.grid-row--target, .grid-row--focus):hover > td {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--v-info-head-tint), transparent);
}
.table-grid--tinted.table-grid--selectable
  .rows-scroll
  .rows-table
  tbody
  tr:not(.grid-row--target, .grid-row--focus):hover
  > .rows-line {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--v-info-head-tint), rgb(var(--v-theme-surface)));
}
/* Its line is a button that looks like the line. */
.grid-line-button {
  all: unset;
  cursor: pointer;
  width: 100%;
}
.grid-line-button:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
/* A cell with a problem has an outline inside, which leaves the content and the lines in place,
   and a cell of the selected row the lines of its frame. Both are inset shadows, so that a
   problem of the selected row keeps its outline inside the frame. */
.rows-table :is(td, th) {
  box-shadow: var(--grid-outline, 0 0 transparent), var(--grid-frame, 0 0 transparent);
}
.rows-table .grid-cell--error {
  --grid-outline: inset 0 0 0 2px rgb(var(--v-theme-error));
}
.rows-table .grid-cell--warning {
  --grid-outline: inset 0 0 0 2px var(--grid-amber);
}
/* The selected row: a frame of 1 px in the primary color around its tint, which keeps it apart
   on the green and violet tints of the tables. Every cell draws its top and bottom, the first cell
   the start and the last cell the end; a cell that is both draws both. */
.rows-table .grid-row--focus > * {
  --grid-frame:
    inset var(--grid-frame-start, 0px) 1px rgb(var(--v-theme-primary)),
    inset calc(-1 * var(--grid-frame-end, 0px)) -1px rgb(var(--v-theme-primary));
}
.rows-table .grid-row--focus > :first-child {
  --grid-frame-start: 1px;
}
.rows-table .grid-row--focus > :last-child {
  --grid-frame-end: 1px;
}
/* The marked column: a tint over the cell, so that the header keeps its background below it. */
.rows-table .grid-cell--marked {
  background-image: linear-gradient(rgba(var(--v-theme-primary), 0.1), rgba(var(--v-theme-primary), 0.1));
}
/* The cell of the focus: a ring inside the outline of a problem. A focused cell shows the same
   ring; the focus ring of the page would sit outside the cell, below its neighbours. The ring
   leaves room around the 12 px text of a 22 px row. */
.rows-table .grid-cell--focus,
.rows-table :is(td, th):focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -4px;
}
/* Raw tables: lines between the columns, as in a spreadsheet; the line column has its own.
   Cells keep their spaces as printed. */
.grid-letter + .grid-letter,
.grid-raw + .grid-raw {
  border-inline-start: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.rows-table thead .grid-letter {
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.grid-raw {
  white-space: pre;
}
/* The rows that do not render keep their height. */
.rows-table .grid-spacer > td {
  padding: 0;
  border: 0;
}
</style>
