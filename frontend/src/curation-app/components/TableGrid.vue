<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import type { TableResponse } from "../api/types";
import { columnName, keptColumns, ROW, visibleColumns, type CellIssues, type IssueCells } from "../grid";

/** Above this many rows, only the rows near the view render; the others are spacers. */
const VIRTUAL_ROWS = 500;
/** The height of a row and of the header until one is measured: 32 px with the line below. */
const ROW_HEIGHT = 32;
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
 * `focus` line scrolls into view with its cell marked and focused.
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
  },
);
defineSlots<{
  /** The content of the line cell of a row; its line by default. */
  line?: (props: { line: number }) => unknown;
}>();

const id = useId();
const region = ref<HTMLElement | null>(null);

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

const virtual = computed(() => props.table.rows.length > VIRTUAL_ROWS);
const rowHeight = ref(ROW_HEIGHT);
const headerHeight = ref(ROW_HEIGHT);
const viewRows = ref(Math.ceil(VIEW_HEIGHT / ROW_HEIGHT));
/** The index of the first rendered row. */
const start = ref(0);
/** Whether rows scroll below the header, which then needs its background. */
const scrolled = ref(false);

function windowEnd(first: number): number {
  return Math.min(props.table.rows.length, first + viewRows.value + 2 * OVERSCAN + STEP);
}

/** The first row to render for `scrollTop`: a step at least `OVERSCAN` rows above the view. */
function windowStart(scrollTop: number): number {
  const first = Math.floor(Math.max(0, scrollTop - headerHeight.value) / rowHeight.value);
  return Math.max(0, Math.min(Math.floor(first / STEP) * STEP - OVERSCAN, props.table.rows.length - 1));
}

const from = computed(() => (virtual.value ? Math.min(start.value, Math.max(0, props.table.rows.length - 1)) : 0));
const to = computed(() => (virtual.value ? windowEnd(from.value) : props.table.rows.length));
const rendered = computed(() =>
  props.table.rows.slice(from.value, to.value).map((row, offset) => ({ row, index: from.value + offset })),
);
const before = computed(() => from.value * rowHeight.value);
const after = computed(() => (props.table.rows.length - to.value) * rowHeight.value);

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
watch(
  () => props.table,
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
 * of the whole row or of a column that does not show. Line 1 of a table is its header.
 */
const notes = computed(() => {
  const found = new Map<string, Note>();
  const shown = new Map(headers.value.map(({ index, name }) => [name, index]));
  const lines = [...(raw.value ? [] : [1]), ...rendered.value.map(({ row }) => row.line)];
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

/** The problems of the header of a table, at its line 1; a raw table has no header line. */
function headerNote(index: number): Note | undefined {
  return raw.value ? undefined : notes.value.get(`1:${index}`);
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

/** Scroll the focused line into view, then focus its cell, without scrolling again. */
async function reveal(): Promise<void> {
  const element = region.value;
  const index = focusLine.value === null ? -1 : props.table.rows.findIndex((row) => row.line === focusLine.value);
  if (!element || index < 0) return;
  if (virtual.value) {
    // Render the rows around the line first, with the line in the middle of the view.
    const view = element.clientHeight || VIEW_HEIGHT;
    element.scrollTop = Math.max(0, headerHeight.value + index * rowHeight.value - (view - rowHeight.value) / 2);
    update();
    await nextTick();
  }
  const cell = element.querySelector<HTMLElement>(".grid-cell--focus");
  if (!cell) return;
  // The sticky header and line column keep a margin: see the styles.
  if (typeof cell.scrollIntoView === "function") cell.scrollIntoView({ block: "center", inline: "center" });
  cell.focus({ preventScroll: true });
}

// By value: a reload of the table or the study gives an equal focus, which keeps the scroll and the focus.
watch(
  () => (props.focus ? `${props.focus.line}:${props.focus.column ?? ""}` : null),
  () => void nextTick(reveal),
  { immediate: true },
);
</script>

<template>
  <div class="table-grid">
    <!-- The rows scroll inside their region, which takes the focus so that a keyboard can scroll it. -->
    <div
      ref="region"
      class="rows-scroll"
      :class="{ 'rows-scroll--sticky-line': lines, 'rows-scroll--tall': scrolled }"
      tabindex="0"
      role="region"
      :aria-label="label ?? `Rows of ${table.file}`"
      @scroll.passive="update"
    >
      <table class="rows-table rows-table--packed" :aria-rowcount="table.rows.length + 1">
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
            :class="{ 'grid-row--target': highlightLines.has(row.line) }"
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
            >
              <slot name="line" :line="row.line">{{ row.line }}</slot>
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
  /* Amber of the bar of a targeted row and of the outline of a warning: 3:1 on the surface and
     on the rows of open review items in both themes; the theme's warning color is lighter. */
  --grid-amber: #8f5300;
  min-width: 0;
}
.v-theme--dark .table-grid {
  --grid-amber: #ffb547;
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
/* A cell with a problem has an outline inside, which leaves the content and the lines in place. */
.rows-table .grid-cell--error {
  box-shadow: inset 0 0 0 2px rgb(var(--v-theme-error));
}
.rows-table .grid-cell--warning {
  box-shadow: inset 0 0 0 2px var(--grid-amber);
}
/* The marked column: a tint over the cell, so that the header keeps its background below it. */
.rows-table .grid-cell--marked {
  background-image: linear-gradient(rgba(var(--v-theme-primary), 0.1), rgba(var(--v-theme-primary), 0.1));
}
/* The cell of the focus: a ring inside the outline of a problem. A focused cell shows the same
   ring; the focus ring of the page would sit outside the cell, below its neighbours. */
.rows-table .grid-cell--focus,
.rows-table :is(td, th):focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: -5px;
}
/* A cell scrolled into view stays clear of the header and the line column. */
.rows-table tbody :is(td, th) {
  scroll-margin-block-start: 40px;
}
.rows-scroll--sticky-line .rows-table tbody td {
  scroll-margin-inline-start: var(--line-width);
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
