<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useTheme } from "vuetify";
import { VAlert, VBtn, VProgressLinear } from "vuetify/components";
import type { SourceView } from "../api/types";
import { plural } from "../overview";
import {
  dataRows,
  isCalibrated,
  legendEntries,
  overlayTraces,
  plotTraces,
  rowAt,
  type EventPoint,
  type OverlayMode,
} from "../overlay";
import { loadNoncedPlotly, plotlyImport, retryPlotly } from "../plotly";
import { messageOf } from "../study";
import { plotColors } from "../../features/plots/theme";

/**
 * A figure source drawn with Plotly. In `overlay` mode the digitized points and the mapped rows
 * sit on the image of the figure, in its pixels; in `plot` mode the mapped rows of the series
 * without a dataset are plotted in the units of their tables. Without `mode`, the overlay shows
 * when the figure has a digitization on an image of known size, else the plot.
 *
 * With `highlight`, the other series fade. A click on a mapped point emits its file and line.
 * The plot is an image with a name, a legend and a data table for assistive technology.
 */
const props = defineProps<{ view: SourceView; highlight?: string | null; mode?: OverlayMode }>();
const emit = defineEmits<{ "select-row": [row: { file: string; line: number }] }>();

/** Beyond this many points, the data table scrolls below a header that stays in view. */
const SCROLL_ROWS = 12;

const theme = useTheme();
const host = ref<HTMLElement | null>(null);

const shown = computed<OverlayMode>(() => props.mode ?? (isCalibrated(props.view) ? "overlay" : "plot"));
/** The width of the plot on the screen, which the observer below follows. */
const hostWidth = ref(0);
/** The size of the image on the screen in steps of 5 %, for the size of the marks of the overlay. */
const markScale = computed(() => {
  const width = props.view.image_size?.[0];
  return width && hostWidth.value ? Math.round((hostWidth.value / width) * 20) / 20 : 1;
});
const dark = computed(() => theme.current.value.dark);
const plot = computed(() => {
  const colors = { dark: dark.value, colors: plotColors(theme.current.value.colors) };
  const highlight = props.highlight ?? null;
  return shown.value === "overlay"
    ? overlayTraces(props.view, highlight, colors, markScale.value)
    : plotTraces(props.view, highlight, colors);
});

const legend = computed(() => legendEntries(props.view, shown.value, dark.value));
const rows = computed(() => dataRows(props.view, shown.value));
/** Whether a point of the plot selects a row: the plot has a mapped row. */
const selectable = computed(() => rows.value.some((row) => row.line !== null));
const emphasized = computed(() =>
  legend.value.some((entry) => entry.series === props.highlight) ? (props.highlight ?? null) : null,
);
/** The emphasized series has no dataset, so the overlay cannot show it. */
const notDigitized = computed(
  () => shown.value === "overlay" && props.highlight != null && props.view.unmatched.includes(props.highlight),
);

const name = computed(() => {
  const series = legend.value.map((entry) => entry.series).join(", ");
  const of = series ? ` of the series ${series}` : "";
  const emphasis = emphasized.value ? `, with ${emphasized.value} emphasized` : "";
  if (shown.value === "plot") {
    const count = rows.value.length;
    return `Plot of ${plural(count, "mapped row")} of ${props.view.source}${of}${emphasis}`;
  }
  const raw = props.view.overlay.filter((point) => point.role === "raw").length;
  const mapped = props.view.overlay.length - raw;
  return `Figure ${props.view.source} with ${plural(raw, "digitized point")} and ${plural(mapped, "mapped row")}${of}${emphasis}`;
});
const caption = computed(() =>
  shown.value === "overlay"
    ? `Digitized points and mapped rows of ${props.view.source}`
    : `Mapped rows of ${props.view.source} without a digitization`,
);

/** The overlay keeps the proportions of the image, at most at its own size. */
const hostStyle = computed(() => {
  const size = props.view.image_size;
  return shown.value === "overlay" && size ? { aspectRatio: `${size[0]} / ${size[1]}`, maxWidth: `${size[0]}px` } : {};
});

// Drawing

const loading = ref(false);
/** What went wrong with the last drawing; the import of Plotly or the plot. */
const failure = ref<{ kind: "import" | "draw"; message: string } | null>(null);

let generation = 0;
let engine: Awaited<ReturnType<typeof loadNoncedPlotly>> | undefined;
let observer: ResizeObserver | undefined;
/** Whether Plotly has drawn into the element, which it then resizes with the element. */
let drawn = false;
let disposed = false;
let rendering = Promise.resolve();
const listening = new WeakSet<HTMLElement>();

/** Whether the pointer is over a point that selects a row. */
const pointer = ref(false);

function rowOf(event: { points: EventPoint[] }) {
  const point = event.points[0];
  return point ? rowAt(props.view, point) : null;
}

function selectPoint(event: { points: EventPoint[] }): void {
  const row = rowOf(event);
  if (row) emit("select-row", row);
}

watch(
  [host, plot, () => plotlyImport.attempt],
  () => {
    const current = ++generation;
    const element = host.value;
    if (!element) return;
    const { traces, layout } = plot.value;
    loading.value = engine === undefined;
    const render = async () => {
      if (disposed || generation !== current) return;
      let phase: "import" | "draw" = "import";
      try {
        const loaded = await loadNoncedPlotly();
        if (disposed || generation !== current) return;
        engine = loaded;
        phase = "draw";
        const plotted = await loaded.react(element, traces, layout, {
          responsive: true,
          displaylogo: false,
          displayModeBar: false,
          modeBarButtonsToRemove: [],
          doubleClick: false,
          showTips: false,
        });
        if (disposed) {
          loaded.purge(element);
          return;
        }
        if (!listening.has(plotted)) {
          plotted.on("plotly_click", selectPoint);
          plotted.on("plotly_hover", (event) => (pointer.value = rowOf(event) !== null));
          plotted.on("plotly_unhover", () => (pointer.value = false));
          listening.add(plotted);
        }
        failure.value = null;
        drawn = true;
      } catch (caught) {
        if (generation === current) failure.value = { kind: phase, message: messageOf(caught) };
      } finally {
        if (generation === current) loading.value = false;
      }
    };
    // One Plotly call at a time, so that an older render cannot finish after a newer one.
    rendering = rendering.catch(() => undefined).then(render);
  },
  { flush: "post" },
);

// The plot follows the size of its element, such as when the window or the rail changes.
watch(host, (element) => {
  observer?.disconnect();
  if (!element) return;
  observer = new ResizeObserver(([entry]) => {
    if (entry) hostWidth.value = entry.contentRect.width;
    if (drawn) void engine?.Plots.resize(element).catch(() => undefined);
  });
  observer.observe(element);
});

function reload(): void {
  window.location.reload();
}

onBeforeUnmount(() => {
  disposed = true;
  generation++;
  observer?.disconnect();
  if (host.value) engine?.purge(host.value);
});
</script>

<template>
  <div class="source-overlay">
    <VAlert v-if="failure" type="error" variant="tonal" density="compact" class="status-alert overlay-failure">
      <p class="overlay-failure-text">
        <template v-if="failure.kind === 'draw'">The plot could not be drawn.</template>
        <template v-else-if="plotlyImport.state === 'failed again'">
          The plot could not be loaded. Reload the page to try again.
        </template>
        <template v-else>The plot could not be loaded.</template>
      </p>
      <p class="overlay-failure-detail">{{ failure.message }}</p>
      <template #append>
        <VBtn
          v-if="failure.kind === 'import' && plotlyImport.state === 'failed again'"
          variant="text"
          size="small"
          @click="reload"
        >
          Reload the page
        </VBtn>
        <VBtn v-else variant="text" size="small" @click="retryPlotly">Retry</VBtn>
      </template>
    </VAlert>
    <VProgressLinear v-if="loading" indeterminate color="primary" aria-label="Loading the plot" />
    <!-- Plotly adds classes to its element, which a class binding would replace: the classes that
         change go on the frame around it. -->
    <div class="overlay-frame" :class="[`overlay-frame--${shown}`, { 'overlay-frame--pointer': pointer }]">
      <div ref="host" class="overlay-host" role="img" :aria-label="name" :style="hostStyle" />
    </div>
    <p v-if="notDigitized" class="field-note">{{ highlight }} is not digitized.</p>

    <ul v-if="legend.length" class="overlay-legend" aria-label="Series">
      <li
        v-for="entry in legend"
        :key="entry.series"
        class="overlay-legend-item"
        :class="{
          'overlay-legend-item--emphasized': entry.series === emphasized,
          'overlay-legend-item--faded': emphasized !== null && entry.series !== emphasized,
        }"
      >
        <span class="overlay-swatch" :style="{ backgroundColor: entry.color }" aria-hidden="true"></span>
        {{ entry.series }}<span v-if="entry.series === emphasized" class="d-sr-only">, emphasized</span>
      </li>
    </ul>
    <p v-if="shown === 'overlay'" class="overlay-key" aria-hidden="true">
      <span class="overlay-key-item">
        <svg viewBox="0 0 12 12" class="overlay-glyph"><circle cx="6" cy="6" r="3.5" /></svg>
        Digitized point
      </span>
      <span class="overlay-key-item">
        <svg viewBox="0 0 12 12" class="overlay-glyph overlay-glyph--line">
          <path d="M2 2 L10 10 M10 2 L2 10" />
        </svg>
        Mapped row
      </span>
      <span class="overlay-key-item">
        <svg viewBox="0 0 12 12" class="overlay-glyph overlay-glyph--line"><path d="M6 1 L6 11" /></svg>
        Error bar of a mapped row
      </span>
    </p>

    <p v-if="selectable" class="overlay-key">
      Click a {{ shown === "overlay" ? "cross" : "point" }} to show its row in the Tables section.
    </p>

    <details v-if="rows.length" class="overlay-data">
      <summary>Data of the plot</summary>
      <div
        class="rows-scroll rows-scroll--fit"
        :class="{ 'rows-scroll--tall': rows.length > SCROLL_ROWS }"
        tabindex="0"
        role="region"
        :aria-label="caption"
      >
        <table class="rows-table">
          <caption class="d-sr-only">{{ caption }}</caption>
          <thead>
            <tr>
              <th scope="col">Series</th>
              <th scope="col">Point</th>
              <th scope="col">x</th>
              <th scope="col">y</th>
              <th scope="col">File</th>
              <th scope="col" class="rows-line">Line</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in rows" :key="index">
              <th scope="row">{{ row.series }}</th>
              <td>{{ row.kind }}</td>
              <td class="overlay-value">{{ row.x }}</td>
              <td class="overlay-value">{{ row.y }}</td>
              <td>{{ row.file }}</td>
              <td class="rows-line">{{ row.line ?? "-" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </div>
</template>

<style scoped>
.source-overlay {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.overlay-failure-text,
.overlay-failure-detail {
  margin: 0;
}
.overlay-failure-detail {
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}
/* The overlay has the proportions of the image; Plotly fits it after a resize, so that the box
   never takes the height of the previous plot. */
.overlay-host {
  width: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
/* A frame that takes no room, so that the plot has the size of the image. */
.overlay-frame--overlay .overlay-host {
  box-shadow: 0 0 0 1px rgba(var(--v-border-color), var(--v-border-opacity));
}
.overlay-frame--plot .overlay-host {
  height: 360px;
}
/* Plotly shows a pointer over the whole plot when it does not zoom; only a point that selects a
   row takes one. These rules are more specific than those of Plotly. */
.overlay-frame :deep(.nsewdrag.cursor-pointer) {
  cursor: default;
}
.overlay-frame--pointer :deep(.nsewdrag.cursor-pointer) {
  cursor: pointer;
}
.overlay-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.875rem;
  line-height: 1.45;
}
.overlay-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  overflow-wrap: anywhere;
}
.overlay-legend-item--emphasized {
  font-weight: 600;
}
/* A ring in the text color keeps a light swatch visible on either surface. */
.overlay-swatch {
  flex: 0 0 auto;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(var(--v-theme-on-surface), 0.3);
}
.overlay-legend-item--faded .overlay-swatch {
  opacity: 0.35;
}
.overlay-key {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 0;
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.overlay-key-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.overlay-glyph {
  width: 12px;
  height: 12px;
  fill: currentColor;
}
.overlay-glyph--line {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
}
.overlay-data summary {
  width: fit-content;
  cursor: pointer;
  font-size: 0.875rem;
}
.overlay-data .rows-scroll {
  margin-top: 8px;
}
/* The series names a row, in the weight of the other cells. */
.overlay-data tbody th {
  font-weight: 400;
}
.overlay-value {
  font-variant-numeric: tabular-nums;
}
</style>
