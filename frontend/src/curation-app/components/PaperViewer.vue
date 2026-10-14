<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, useId, watch } from "vue";
import { VBtn, VProgressLinear } from "vuetify/components";
import {
  FIT_LABELS,
  FITS,
  findText,
  loadPaperEngine,
  MAX_SCALE,
  MIN_SCALE,
  paperAnswer,
  paperFailure,
  paperImport,
  PaperImportFailed,
  retryPaper,
  zoomText,
  type Fit,
  type FindResult,
  type PaperPlace,
  type PaperSession,
  type PaperStart,
} from "../../study-views/paper";
import type { ActionFailure } from "../../study-views/study";
import ActionFailureAlert from "./ActionFailureAlert.vue";

/**
 * A PDF drawn with PDF.js (`paperEngine.ts`, loaded with the first paper): its pages one below
 * the other, each drawn while it is in view, with a text layer to select, copy and find text.
 * The toolbar has Previous page and Next page with the page of the pages, Zoom out and Zoom in
 * with the zoom (Fit width, Fit page, 100 %), and the find field: Enter goes to the next match,
 * Shift+Enter to the previous one, and Ctrl+F inside the viewer focuses the field. A PDF that is
 * missing, damaged or protected by a password shows the alert of a failed action, with Retry.
 * When its version changes, as when it was written on disk, the viewer opens the PDF again at its
 * place, on its page and zoom; another PDF starts on its first page at Fit width.
 */
const props = withDefaults(
  defineProps<{
    url: string;
    file: string;
    /** The version of the content of the PDF (`PaperFile.version`). */
    version?: string | null;
  }>(),
  { version: null },
);
/**
 * Where the viewer stands in its PDF. A parent that keeps it with `v-model:place` gets the viewer
 * back on its page and zoom when the viewer mounts again, as after a change on disk.
 */
const place = defineModel<PaperPlace | null>("place", { default: null });

/** The fields have ids, which a browser expects of a form field, and labels that only screen readers show. */
const id = useId();
const scroller = ref<HTMLDivElement | null>(null);
const findField = ref<HTMLInputElement | null>(null);
/** The open PDF; null while it opens or after it failed. */
const session = shallowRef<PaperSession | null>(null);
const pages = ref(0);
const page = ref(1);
const scale = ref(1);
/** The fit of the zoom; null after Zoom out or Zoom in, whose scale the zoom select shows. */
const fit = ref<Fit | null>("page-width");
const query = ref("");
const found = ref<FindResult | null>(null);
const loading = ref(false);
const failure = ref<ActionFailure | null>(null);
/** Whether PDF.js could not be imported, which a reload of the page may fix. */
const importFailed = ref(false);

const count = computed(() => findText(found.value, query.value));

/**
 * The opening of the PDF in view. The next opening and the unmount abort it: a PDF that is still
 * loading stops, and one that opens after all is closed at once and reports nothing.
 */
let opening: AbortController | null = null;

/** Keep the page and the zoom of the PDF in its place. */
function remember(): void {
  place.value = { url: props.url, page: page.value, fit: fit.value, scale: scale.value };
}

/** Close a PDF; one that fails to close is gone all the same. */
async function close(shown: PaperSession | null): Promise<void> {
  try {
    await shown?.close();
  } catch {
    // PDF.js has dropped the PDF and its worker already.
  }
}

async function open(): Promise<void> {
  opening?.abort();
  const own = new AbortController();
  opening = own;
  const { signal } = own;
  const container = scroller.value;
  const previous = session.value;
  session.value = null;
  found.value = null;
  // The PDF leaves the container at once; its worker goes in the background, which may take a
  // while when it is busy, and the next PDF does not wait for it.
  void close(previous);
  if (!container) return;
  // The PDF opens at its place again; another PDF on page 1 at Fit width.
  const kept = place.value;
  const start: PaperStart =
    kept?.url === props.url
      ? { page: kept.page, fit: kept.fit, scale: kept.scale }
      : { page: 1, fit: "page-width", scale: 1 };
  page.value = start.page;
  fit.value = start.fit;
  scale.value = start.scale;
  remember();
  pages.value = 0;
  loading.value = true;
  failure.value = null;
  importFailed.value = false;
  try {
    const engine = await loadPaperEngine();
    if (signal.aborted) return;
    const opened = await engine.openPaper(
      container,
      props.url,
      {
        opened: (value) => {
          if (!signal.aborted) pages.value = value;
        },
        page: (value) => {
          if (signal.aborted) return;
          page.value = value;
          remember();
        },
        scale: (value, preset) => {
          if (signal.aborted) return;
          scale.value = value;
          fit.value = preset;
          remember();
        },
        found: (result) => {
          if (!signal.aborted) found.value = result;
        },
      },
      start,
      signal,
    );
    if (signal.aborted) {
      void close(opened);
      return;
    }
    session.value = opened;
    if (query.value.trim()) opened.find(query.value, { again: false, previous: false });
  } catch (caught) {
    if (signal.aborted) return;
    // PDF.js reports an error status of the local server without its answer, which says why.
    const answer = await paperAnswer(caught, props.url);
    if (signal.aborted) return;
    importFailed.value = caught instanceof PaperImportFailed;
    failure.value = paperFailure(caught, props.file, props.url, answer);
  } finally {
    if (!signal.aborted) loading.value = false;
  }
}

// Once the scroll container exists, and again for another URL or version, and on Retry.
watch([scroller, () => props.url, () => props.version, () => paperImport.attempt], () => void open(), {
  flush: "post",
});

onBeforeUnmount(() => {
  opening?.abort();
  opening = null;
  const shown = session.value;
  session.value = null;
  void close(shown);
});

function goTo(target: number): void {
  if (session.value && pages.value > 0) session.value.goTo(Math.min(Math.max(target, 1), pages.value));
}

/** Go to the typed page; a page that the PDF lacks shows the page in view again. */
function typedPage(event: Event): void {
  const field = event.target as HTMLInputElement;
  const target = Number(field.value);
  if (Number.isInteger(target) && target >= 1 && target <= pages.value) goTo(target);
  else field.value = String(page.value);
}

function chooseZoom(event: Event): void {
  const chosen = FITS.find((value) => value === (event.target as HTMLSelectElement).value);
  if (!chosen) return;
  fit.value = chosen;
  remember();
  session.value?.fit(chosen);
}

watch(query, (value) => session.value?.find(value.trim() ? value : "", { again: false, previous: false }));

function findAgain(event: KeyboardEvent): void {
  if (query.value.trim()) session.value?.find(query.value, { again: true, previous: event.shiftKey });
}

/**
 * Ctrl+F (Cmd+F) inside the viewer goes to its find field instead of the find of the browser,
 * which stays while no PDF is shown.
 */
function focusFind(event: KeyboardEvent): void {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey || event.key.toLowerCase() !== "f") return;
  const field = findField.value;
  if (!field || field.disabled) return;
  event.preventDefault();
  field.focus();
  field.select();
}

function reload(): void {
  window.location.reload();
}
</script>

<template>
  <div class="paper-viewer" @keydown="focusFind">
    <div class="paper-toolbar">
      <span class="paper-tools">
        <button
          type="button"
          class="paper-tool"
          aria-label="Previous page"
          title="Previous page"
          :disabled="!session || page <= 1"
          @click="goTo(page - 1)"
        >
          <i class="fas fa-chevron-up" aria-hidden="true"></i>
        </button>
        <button
          type="button"
          class="paper-tool"
          aria-label="Next page"
          title="Next page"
          :disabled="!session || page >= pages"
          @click="goTo(page + 1)"
        >
          <i class="fas fa-chevron-down" aria-hidden="true"></i>
        </button>
        <label :for="`${id}-page`" class="d-sr-only">Page</label>
        <input
          :id="`${id}-page`"
          class="paper-field paper-number"
          type="number"
          inputmode="numeric"
          min="1"
          :max="Math.max(pages, 1)"
          :value="page"
          :disabled="!session"
          @change="typedPage"
        />
        <span class="paper-of" :class="{ 'paper-of--unknown': !pages }">of {{ pages }}</span>
      </span>
      <span class="paper-tools">
        <button
          type="button"
          class="paper-tool"
          aria-label="Zoom out"
          title="Zoom out"
          :disabled="!session || scale <= MIN_SCALE"
          @click="session?.zoom(-1)"
        >
          <i class="fas fa-magnifying-glass-minus" aria-hidden="true"></i>
        </button>
        <button
          type="button"
          class="paper-tool"
          aria-label="Zoom in"
          title="Zoom in"
          :disabled="!session || scale >= MAX_SCALE"
          @click="session?.zoom(1)"
        >
          <i class="fas fa-magnifying-glass-plus" aria-hidden="true"></i>
        </button>
        <label :for="`${id}-zoom`" class="d-sr-only">Zoom</label>
        <select
          :id="`${id}-zoom`"
          class="paper-field paper-zoom"
          :value="fit ?? 'custom'"
          :disabled="!session"
          @change="chooseZoom"
        >
          <option v-if="fit === null" value="custom" disabled>{{ zoomText(scale) }}</option>
          <option v-for="value in FITS" :key="value" :value="value">{{ FIT_LABELS[value] }}</option>
        </select>
      </span>
      <span class="paper-find">
        <label :for="`${id}-find`" class="d-sr-only">Find in the paper</label>
        <input
          :id="`${id}-find`"
          ref="findField"
          v-model="query"
          class="paper-field paper-find-field"
          type="search"
          placeholder="Find"
          :disabled="!session"
          @keydown.enter.prevent="findAgain"
        />
        <span class="paper-count" role="status">{{ count }}</span>
      </span>
    </div>
    <!-- It goes when the PDF opens again, after Retry or a change of the PDF: no close button. -->
    <ActionFailureAlert v-if="failure" :failure="failure" :closable="false" class="paper-failure">
      <template #append>
        <span class="paper-retry">
          <VBtn variant="text" size="small" @click="retryPaper">Retry</VBtn>
          <VBtn v-if="importFailed" variant="text" size="small" @click="reload">Reload the page</VBtn>
        </span>
      </template>
    </ActionFailureAlert>
    <!-- PDF.js needs an absolutely positioned container, which fills the rest of the viewer and
         scrolls. It takes the focus, so that a keyboard can scroll the pages. -->
    <div class="paper-frame">
      <VProgressLinear
        v-if="loading"
        indeterminate
        absolute
        location="top"
        color="primary"
        :aria-label="`Loading ${file}`"
      />
      <div ref="scroller" class="paper-scroll" role="region" :aria-label="`Pages of ${file}`" tabindex="0">
        <div class="pdfViewer"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.paper-viewer {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
/* The controls wrap in a narrow pane; the find field takes the room that is left. */
.paper-toolbar {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
  padding: 3px 8px;
  font-size: 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.paper-tools,
.paper-find {
  display: flex;
  align-items: center;
  gap: 4px;
}
.paper-find {
  flex: 1 1 10rem;
  min-width: 0;
}
/* As high as the smallest target of the app, 24 px. */
.paper-tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
}
.paper-tool:hover:not(:disabled) {
  background: rgba(var(--v-theme-on-surface), 0.06);
}
.paper-tool:disabled {
  cursor: default;
  opacity: var(--v-disabled-opacity);
}
.paper-field {
  height: 24px;
  padding-inline: 4px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.42);
  border-radius: 4px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  font: inherit;
}
.paper-tool:focus-visible,
.paper-field:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
/* The page field. Not `.paper-page`: that is the view of a PDF in a tab of its own (PaperPage.vue),
   which makes the window a column that does not scroll, and the viewer shows in the Data section too. */
.paper-number {
  width: 4.5em;
  text-align: end;
}
.paper-zoom {
  appearance: auto;
}
.paper-find-field {
  flex: 1 1 auto;
  min-width: 5rem;
  max-width: 16rem;
}
.paper-of,
.paper-count {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Hidden, but keeping its room, until the PDF has opened: the controls do not move. */
.paper-of--unknown {
  visibility: hidden;
}
/* The count keeps its width while it changes, so that the field does not move. */
.paper-count {
  min-width: 5.5em;
}
.paper-failure {
  flex: 0 0 auto;
  margin: 8px;
}
/* Retry above Reload the page, at the end of the alert. */
.paper-retry {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.paper-frame {
  position: relative;
  flex: 1 1 0;
  min-height: 0;
}
.paper-scroll {
  position: absolute;
  inset: 0;
  overflow: auto;
  background: rgba(var(--v-theme-on-surface), 0.08);
}
.paper-scroll:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}
</style>
