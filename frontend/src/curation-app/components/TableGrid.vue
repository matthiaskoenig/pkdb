<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import type { ColumnClass, NameKind, StudyNameLines, TableResponse, TableRow, ValidationIssue } from "../api/types";
import { useCellTip } from "../composables/useCellTip";
import {
  columnClass,
  columnName,
  HEADER_LINE,
  keptColumns,
  lineIssues,
  lineTipKey,
  ROW,
  visibleColumns,
  type CellIssues,
  type IssueCells,
} from "../grid";
import { cellParts, namedKind, type CellPart, type NameLink } from "../links";
import { problemsText } from "../problems";
import ProblemTooltip from "./ProblemTooltip.vue";

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
 * its sheet, read only. Rows that open review items target are amber. Cells with problems are
 * outlined, describe the problems to screen readers, and show them in one tooltip of the grid
 * 300 ms after the pointer rests on them; a line cell shows every problem of its line, also when
 * its line button has a keyboard focus, and the Line header, a Tab stop while the header has
 * problems, every problem of the header. A column can be marked, and empty columns can be
 * hidden. The header and the line column stay in view while the rows scroll.
 *
 * Above 500 rows, only the rows near the view render, between spacers of the height of the
 * others; `aria-rowcount` and `aria-rowindex` give screen readers the place of each row. The
 * `focus` line scrolls into view with its cell marked and focused. The line buttons of a
 * selectable grid are one Tab stop: the arrow keys move the focus to the row above or below,
 * Home and End to the first and the last row.
 *
 * A tinted grid shows what each column of its table names (`classes` of the table): the
 * subjects, the interventions and the data in their colors, the header cells in a stronger tint
 * than the cells, and `study` and `source` muted, in italics and without a tint. A raw table
 * and a table without classes have no tint.
 *
 * A selectable grid that has the lines of the names (`names`) links each name in a column of
 * names, such as `subjects`, `parent` or `interventions`, to its row: a click, or Enter on its
 * focus, emits `follow` with the file and the line of the row and the line of its own row. The
 * arrow keys Right and Left move from the line button of a row to its links and back.
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
    /**
     * Whether the header row is line 0 of the file, so that its line cell shows 0; a raw table has
     * no header line, and a grid of other rows, such as the versions of a conflict, sets it false.
     */
    headerLine?: boolean;
    /** Whether a click on a row selects its line: the line cell becomes a button. */
    selectable?: boolean;
    /** The lines of the rows to show; null shows every row. */
    visibleLines?: ReadonlySet<number> | null;
    /** Whether the columns show the class of information that the table gives each of them. */
    tinted?: boolean;
    /**
     * The lines of the names of subjects.tsv and interventions.tsv: a selectable grid links the
     * names in its cells to their rows.
     */
    names?: StudyNameLines | null;
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
    headerLine: true,
    selectable: false,
    visibleLines: null,
    tinted: false,
    names: null,
  },
);
const emit = defineEmits<{ "select-line": [line: number]; follow: [link: NameLink, line: number] }>();
const slots = defineSlots<{
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
/** Whether the line cell of the header row shows `HEADER_LINE`, the line of the header of a table. */
const numberedHeader = computed(() => props.headerLine && !raw.value);

const marked = computed(
  () => new Set(typeof props.markColumn === "string" ? [props.markColumn] : (props.markColumn ?? [])),
);
/** The columns that stay when empty columns are hidden: marked, focused, or with a problem. */
const kept = computed(() => keptColumns(props.issueCells, ...marked.value, props.focus?.column));
/** Whether the names in the cells link to their rows: in a selectable grid that has their lines, not of a raw table. */
const linking = computed(() => props.selectable && props.names !== null && !raw.value);
const headers = computed(() =>
  (props.columns ?? visibleColumns(props.table, props.hideEmpty, kept.value)).map((index) => {
    const name = columnName(props.table, index);
    return {
      index,
      name,
      info: props.tinted ? columnClass(props.table, index) : null,
      links: linking.value ? namedKind(name) : null,
    };
  }),
);

/** The parts of a cell of a column of names: its names with their links and the text between them. */
function partsOf(row: TableRow, column: { index: number; links: NameKind | null }): CellPart[] {
  const text = row.cells[column.index] ?? "";
  return column.links && props.names ? cellParts(text, props.names[column.links]) : [{ text, link: null }];
}

/** The id of the hidden text that says where a link goes: the line of its table. */
function linkNoteId(link: NameLink): string {
  return `${id}-to-${link.file}-${link.line}`;
}

/** The class of a cell of a column of the class `info`, which gives it its tint or its italics. */
function infoClass(info: ColumnClass | null): string | undefined {
  return info ? `grid-info--${info}` : undefined;
}

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
/** The height of the rows with their header, at which the shadows of the sides end in a higher region. */
const contentHeight = ref<number | null>(null);
const regionStyle = computed(() =>
  contentHeight.value === null ? {} : { "--rows-content-height": `${contentHeight.value}px` },
);
const fade = computed(() => ({
  "--grid-scrollbar-x": `${scrollbars.value.x}px`,
  "--grid-scrollbar-y": `${scrollbars.value.y}px`,
  "--grid-head-height": `${headerHeight.value}px`,
}));

/**
 * The class of the column that the end of the view cuts while more columns follow, whose head
 * tint the fade of the header row takes; null for an untinted grid or no cut column.
 */
const edge = ref<ColumnClass | null>(null);
/** The class on the grid for the fade: only a tinted column has a head tint to fade to. */
const edgeTint = computed(() => (edge.value === "meta" ? null : edge.value));

/** The class of the last header cell that starts inside the view of `element`. */
function edgeClass(element: HTMLElement): ColumnClass | null {
  if (!props.tinted) return null;
  const end = element.getBoundingClientRect().left + element.clientLeft + element.clientWidth;
  let found: ColumnClass | null = null;
  for (const cell of element.querySelectorAll<HTMLElement>("thead th[data-info]"))
    if (cell.getBoundingClientRect().left < end - 1) found = cell.dataset.info as ColumnClass;
  return found;
}

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

/** The targets of the links that show, each once, for the hidden texts that describe them. */
const linkTargets = computed<NameLink[]>(() => {
  const targets = new Map<string, NameLink>();
  for (const { row } of rendered.value) {
    for (const column of headers.value) {
      if (!column.links) continue;
      for (const part of partsOf(row, column)) if (part.link) targets.set(linkNoteId(part.link), part.link);
    }
  }
  return [...targets.values()];
});
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
  edge.value = more.value ? edgeClass(element) : null;
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
  const content = element.querySelector("table")?.getBoundingClientRect().height ?? 0;
  if (row > 0) rowHeight.value = row;
  if (header > 0) headerHeight.value = header;
  contentHeight.value = content > 0 ? content : null;
  if (element.clientHeight > 0) viewRows.value = Math.ceil(element.clientHeight / rowHeight.value);
  update();
}

let observer: ResizeObserver | undefined;
onMounted(() => {
  measure();
  observer = new ResizeObserver(measure);
  if (region.value) observer.observe(region.value);
  // The rows grow and shrink with the table, its columns and its filters.
  const table = region.value?.querySelector("table");
  if (table) observer.observe(table);
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
  /** The problems as screen readers read them, as the tooltip shows them. */
  text: string;
  /** The problems of the cell, which its tooltip lists. */
  issues: ValidationIssue[];
}

/** The lines whose problems the grid shows: the header line of a table and the lines of the rendered rows. */
const noteLines = computed(() => [...(numberedHeader.value ? [HEADER_LINE] : []), ...rendered.value.map(({ row }) => row.line)]);

/**
 * The problems of the rendered cells by `<line>:<column index>`, -1 for the line cell: a problem
 * of the whole row or of a column that does not show. The header of a table is at `HEADER_LINE`.
 */
const notes = computed(() => {
  const shown = new Map(headers.value.map(({ index, name }) => [name, index]));
  // The problems of each place; the line cell takes those of the columns that do not show.
  const places = new Map<string, { id: string; issues: ValidationIssue[] }>();
  for (const line of noteLines.value)
    for (const [name, cell] of props.issueCells.get(line) ?? []) {
      const index = name === ROW ? -1 : (shown.get(name) ?? -1);
      const key = `${line}:${index}`;
      const place = places.get(key);
      if (place) place.issues.push(...cell.issues);
      else places.set(key, { id: `${id}-${line}-${index < 0 ? "line" : index}`, issues: [...cell.issues] });
    }
  const found = new Map<string, Note>();
  for (const [key, { id: noteId, issues }] of places)
    found.set(key, {
      id: noteId,
      severity: issues.some((issue) => issue.severity === "error") ? "error" : "warning",
      text: problemsText(issues),
      issues,
    });
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

function cellClass(line: number, index: number, name: string, info: ColumnClass | null): Record<string, boolean> {
  const note = notes.value.get(`${line}:${index}`);
  return {
    "grid-cell--error": note?.severity === "error",
    "grid-cell--warning": note?.severity === "warning",
    "grid-cell--marked": marked.value.has(name),
    "grid-cell--focus": isFocus(line, name),
    "grid-raw": raw.value,
    ...(info ? { [`grid-info--${info}`]: true } : {}),
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

/** The problems of the header of a table, at its line 0; a raw table and a grid of other rows have no header line. */
function headerNote(index: number): Note | undefined {
  return numberedHeader.value ? notes.value.get(`${HEADER_LINE}:${index}`) : undefined;
}

/** The classes of a header cell; the index -1 is the header of the line column. */
function headerClass(index: number, name: string | null, info: ColumnClass | null = null): Record<string, boolean> {
  const note = headerNote(index);
  return {
    "grid-cell--error": note?.severity === "error",
    "grid-cell--warning": note?.severity === "warning",
    "grid-cell--marked": name !== null && marked.value.has(name),
    "grid-letter": raw.value && index >= 0,
    ...(info ? { [`grid-info--${info}`]: true } : {}),
  };
}

// The tooltip of the problems: one for the grid, at the cell under the pointer or of the keyboard.
// No outlined cell is a Tab stop: the keyboard reaches the problems through the line buttons,
// which show every problem of their line, and the Line header, which shows those of the header.

const tip = useCellTip();

/** Every problem of each line whose problems the grid shows, also of columns that do not show. */
const lineProblems = computed(() => {
  const found = new Map<number, ValidationIssue[]>();
  for (const line of noteLines.value) {
    const issues = lineIssues(props.issueCells, line);
    if (issues.length) found.set(line, issues);
  }
  return found;
});

/** The problems that a tooltip can list, by the `data-tip` of their cell. */
const tips = computed(() => {
  const found = new Map<string, ValidationIssue[]>();
  for (const [key, note] of notes.value) found.set(key, note.issues);
  for (const [line, issues] of lineProblems.value) found.set(lineTipKey(line), issues);
  return found;
});

/** The `data-tip` of the cell at `line` and the column `index` when it has problems. */
function tipOf(line: number, index: number): string | undefined {
  const key = `${line}:${index}`;
  return notes.value.has(key) ? key : undefined;
}

/** The `data-tip` of the line cell of `line` when the line has problems. */
function lineTip(line: number): string | undefined {
  return lineProblems.value.has(line) ? lineTipKey(line) : undefined;
}

/** The `data-tip` of a header cell; a raw table and a grid of other rows have no header line. */
function headerTip(index: number): string | undefined {
  return numberedHeader.value ? tipOf(HEADER_LINE, index) : undefined;
}

/**
 * The `data-tip` of the Line header while the header has problems: the header has no other
 * focusable element, so the Line header is then its one Tab stop.
 */
const headerLineTip = computed(() => (numberedHeader.value ? lineTip(HEADER_LINE) : undefined));

/** The id of the hidden text with every problem of `line`, which describes its line button or the Line header. */
function lineNoteId(line: number): string {
  return `${id}-${line}-all`;
}

/**
 * The id of the problems of the whole row of `line`, which describe its line cell. A line button
 * describes every problem of its line instead, of which they are a part.
 */
function rowNoteId(line: number): string | undefined {
  return props.selectable && !slots.line ? undefined : notes.value.get(`${line}:-1`)?.id;
}

function onScroll(): void {
  update();
  tip.scrolled(region.value);
}

// A tooltip whose cell left the rendered rows, or has no problems any more, hides.
watch(
  [rendered, tips],
  () => {
    const cell = tip.cell.value;
    const key = tip.key.value;
    if (cell && (!cell.isConnected || key === null || !tips.value.has(key))) tip.hide();
  },
  { flush: "post" },
);

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

/**
 * A key on a row of a selectable grid, from its line cell, its line button or a link of a name:
 * Up and Down move to the line button of the row above or below, Home and End to that of the
 * first or the last row, Right and Left along the line button and the links of the row. A cell
 * of a column, such as one that the route focused, keeps its keys.
 */
async function onRowKey(event: KeyboardEvent, index: number): Promise<void> {
  const row = event.currentTarget as HTMLElement;
  const from = event.target instanceof Element ? event.target.closest<HTMLElement>(".rows-line, .grid-link") : null;
  if (!from || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (!row.querySelector(".grid-line-button")) return;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    moveAlong(event, row, from);
    return;
  }
  await moveFocus(event, index);
}

/**
 * Move the focus along the line button and the links of `row` in their order, one step from
 * `from`, without wrapping; the line cell stands for its button. The view scrolls sideways to
 * the link.
 */
function moveAlong(event: KeyboardEvent, row: HTMLElement, from: HTMLElement): void {
  const stops = [...row.querySelectorAll<HTMLElement>(".grid-line-button, .grid-link")];
  const at = Math.max(0, stops.indexOf(from)); // the line cell stands for its button, the first stop
  const next = stops[Math.min(stops.length - 1, Math.max(0, at + (event.key === "ArrowRight" ? 1 : -1)))];
  // Where the focus cannot move, the browser scrolls the table sideways.
  if (!next || next === stops[at] || next === document.activeElement) return;
  event.preventDefault();
  scrollToCell(next.closest<HTMLElement>("td, th") ?? next, true);
  next.focus({ preventScroll: true });
}

/** Follow a link; the repeated clicks of a double-click follow nothing more. */
function onLinkClick(event: MouseEvent, link: NameLink, line: number): void {
  if (event.detail > 1) return;
  emit("follow", link, line);
}

/** Move the focus from the shown row `index` to the line button of another row. */
async function moveFocus(event: KeyboardEvent, index: number): Promise<void> {
  const move = MOVES[event.key];
  if (!move) return;
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
    :class="[
      { 'table-grid--more': more, 'table-grid--selectable': selectable, 'table-grid--tinted': tinted },
      infoClass(edgeTint),
    ]"
    :style="fade"
  >
    <!-- The rows scroll inside their region, which takes the focus so that a keyboard can scroll it. -->
    <div
      ref="region"
      class="rows-scroll"
      :class="{ 'rows-scroll--sticky-line': lines, 'rows-scroll--stuck': scrolled }"
      :style="regionStyle"
      tabindex="0"
      role="region"
      :aria-label="label ?? `Rows of ${table.file}`"
      @scroll.passive="onScroll"
      @mouseover="tip.over"
      @mouseout="tip.out"
      @focusin="tip.focusIn"
      @focusout="tip.focusOut"
    >
      <table class="rows-table rows-table--packed" :aria-rowcount="shownRows.length + 1">
        <thead>
          <tr aria-rowindex="1">
            <th
              v-if="lines"
              scope="col"
              class="rows-line"
              :class="headerClass(-1, null)"
              :data-tip="headerLineTip"
              :tabindex="headerLineTip ? 0 : undefined"
              :aria-describedby="headerLineTip ? lineNoteId(HEADER_LINE) : undefined"
            >
              <template v-if="numberedHeader"><span class="d-sr-only">{{ lineHeader }}</span> {{ HEADER_LINE }}</template>
              <template v-else>{{ lineHeader }}</template>
            </th>
            <th
              v-for="column in headers"
              :key="column.index"
              scope="col"
              :class="headerClass(column.index, column.name, column.info)"
              :data-info="column.info ?? undefined"
              :data-tip="headerTip(column.index)"
              :aria-describedby="described(headerNote(column.index)?.id)"
            >
              {{ column.name
              }}<span v-if="marked.has(column.name)" class="d-sr-only">, {{ markText }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="before" aria-hidden="true" class="grid-spacer" :style="{ height: `${before}px` }">
            <th v-if="lines" class="rows-line"></th>
            <td v-for="column in headers" :key="column.index" :class="infoClass(column.info)"></td>
          </tr>
          <tr
            v-for="{ row, index } in rendered"
            :key="row.line"
            :data-index="index"
            :aria-rowindex="index + 2"
            :class="{ 'grid-row--target': highlightLines.has(row.line), 'grid-row--focus': row.line === focusLine }"
            @click="selectable && emit('select-line', row.line)"
            @keydown="selectable && onRowKey($event, index)"
          >
            <th
              v-if="lines"
              scope="row"
              class="rows-line"
              :class="lineClass(row.line)"
              :tabindex="isFocus(row.line, null) ? -1 : undefined"
              :data-tip="lineTip(row.line)"
              :aria-describedby="described(highlightLines.has(row.line) && targetNote, rowNoteId(row.line))"
            >
              <slot name="line" :line="row.line">
                <button
                  v-if="selectable"
                  type="button"
                  class="grid-line-button"
                  :tabindex="row.line === tabLine ? 0 : -1"
                  :title="lineTip(row.line) ? undefined : `Select line ${row.line}`"
                  :aria-describedby="lineTip(row.line) ? lineNoteId(row.line) : undefined"
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
              :class="cellClass(row.line, column.index, column.name, column.info)"
              :tabindex="isFocus(row.line, column.name) ? -1 : undefined"
              :data-tip="tipOf(row.line, column.index)"
              :aria-describedby="described(notes.get(`${row.line}:${column.index}`)?.id)"
            ><template v-if="column.links"><template v-for="(part, at) in partsOf(row, column)" :key="at"><button
                    v-if="part.link"
                    type="button"
                    class="grid-link"
                    :class="`grid-link--${column.links}`"
                    tabindex="-1"
                    :title="tipOf(row.line, column.index) ? undefined : `Line ${part.link.line} of ${part.link.file}`"
                    :aria-describedby="described(linkNoteId(part.link), notes.get(`${row.line}:${column.index}`)?.id)"
                    @focus="keyLine = row.line"
                    @click.stop="onLinkClick($event, part.link, row.line)"
                  >{{ part.text }}</button><template v-else>{{ part.text }}</template></template></template><template v-else>{{ row.cells[column.index] ?? "" }}</template></td>
          </tr>
          <tr v-if="after" aria-hidden="true" class="grid-spacer" :style="{ height: `${after}px` }">
            <th v-if="lines" class="rows-line"></th>
            <td v-for="column in headers" :key="column.index" :class="infoClass(column.info)"></td>
          </tr>
        </tbody>
      </table>
    </div>
    <!-- What the marks mean, for screen readers; descriptions may name hidden elements. -->
    <div hidden>
      <span :id="targetNote">Targeted by an open review item.</span>
      <span v-for="link in linkTargets" :id="linkNoteId(link)" :key="linkNoteId(link)">Goes to line {{ link.line }} of {{ link.file }}.</span>
      <span v-for="note in notes.values()" :id="note.id" :key="note.id">{{ note.text }}</span>
      <span v-for="[line, issues] in lineProblems" :id="lineNoteId(line)" :key="lineNoteId(line)">{{
        problemsText(issues)
      }}</span>
    </div>
    <!-- One tooltip for the problems of every cell, at the cell under the pointer or of the keyboard. -->
    <ProblemTooltip v-if="tips.size" :tip="tip" :tips="tips" />
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
/* A tinted grid, such as the rows of the Data section, shows what each column names in the color
   `--info` of its class (the RGB of a theme color, info.ts): the header cell over the surface at
   `--info-head-tint`, the cells at `--info-cell-tint`, a hovered row at the tint of the header.
   The data have their own, stronger tints, so that their grey differs from the grey page.
   `study` and `source` are muted, in italics and without a tint, and the line column has no tint.
   The cell tint has the specificity of one class: the amber rows of open review items and the
   selected row keep their own tints. Where more columns follow, the header row fades out to the
   head tint of the column at the end of the view (its class on the grid, `edge`), and the rows to
   the surface. */
.grid-info--subjects {
  --info: var(--v-theme-info-subjects);
  --info-head-tint: var(--v-info-head-tint);
  --info-cell-tint: var(--v-info-cell-tint);
}
.grid-info--interventions {
  --info: var(--v-theme-info-interventions);
  --info-head-tint: var(--v-info-head-tint);
  --info-cell-tint: var(--v-info-cell-tint);
}
.grid-info--data {
  --info: var(--v-theme-info-data);
  --info-head-tint: var(--v-info-data-head-tint);
  --info-cell-tint: var(--v-info-data-cell-tint);
}
.table-grid--tinted .rows-table thead th:is(.grid-info--subjects, .grid-info--interventions, .grid-info--data) {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--info-head-tint), rgb(var(--v-theme-surface)));
}
.table-grid--tinted :where(td.grid-info--subjects, td.grid-info--interventions, td.grid-info--data) {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--info-cell-tint), transparent);
}
.table-grid--tinted .rows-table :is(th, td).grid-info--meta {
  font-style: italic;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.table-grid--more:is(.grid-info--subjects, .grid-info--interventions, .grid-info--data) {
  --grid-head: color-mix(in srgb, rgb(var(--info)) var(--info-head-tint), rgb(var(--v-theme-surface)));
}
.table-grid--more:is(.grid-info--subjects, .grid-info--interventions, .grid-info--data)::after {
  background:
    linear-gradient(to left, var(--grid-head), transparent) top / 100% var(--grid-head-height) no-repeat,
    linear-gradient(to left, rgb(var(--v-theme-surface)), rgba(var(--v-theme-surface), 0)) bottom / 100%
      calc(100% - var(--grid-head-height)) no-repeat;
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
.table-grid--selectable .rows-table tbody tr[data-index]:not(.grid-row--target, .grid-row--focus):hover > td {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}
.table-grid--selectable .rows-scroll .rows-table tbody tr[data-index]:not(.grid-row--target, .grid-row--focus):hover > .rows-line {
  background-color: color-mix(in srgb, rgb(var(--v-theme-on-surface)) 5%, rgb(var(--v-theme-surface)));
}
.table-grid--selectable
  .rows-table
  tbody
  tr[data-index]:not(.grid-row--target, .grid-row--focus):hover
  > td:is(.grid-info--subjects, .grid-info--interventions, .grid-info--data) {
  background-color: color-mix(in srgb, rgb(var(--info)) var(--info-head-tint), transparent);
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
/* A name that links to its row in subjects.tsv or interventions.tsv: the text of its cell in the
   color of the cell, which keeps its contrast on every tint of a row, with a dotted line below it
   in the color of the table that it opens; solid under the pointer and with the keyboard focus. */
.grid-link {
  all: unset;
  cursor: pointer;
  text-decoration: underline dotted;
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
}
.grid-link--subjects {
  text-decoration-color: rgb(var(--v-theme-info-subjects));
}
.grid-link--interventions {
  text-decoration-color: rgb(var(--v-theme-info-interventions));
}
.grid-link:hover,
.grid-link:focus-visible {
  text-decoration-style: solid;
}
.grid-link:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
  border-radius: 2px;
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
   on the tints of the columns. Every cell draws its top and bottom, the first cell
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
/* The rows that do not render keep their height; their cells keep the tint of their
   column. No border: it would add height to the rows that the spacer stands for. */
.rows-table .grid-spacer > * {
  padding: 0;
  border-bottom: 0;
}
</style>
