<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { VAlert, VBtn, VProgressLinear } from "vuetify/components";
import type { SourceSummary, SourceView } from "../api/types";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { rawTable } from "../grid";
import { drawsOnImage, plottedSeries, type SelectedRow } from "../overlay";
import { groupByFile, groupCounts, locationKey, validatesAfterWrite } from "../problems";
import { sourceProblems } from "../sources";
import { tableFiles } from "../study";
import ProblemItem from "./ProblemItem.vue";
import SourceOverlay from "./SourceOverlay.vue";
import TableGrid from "./TableGrid.vue";

/**
 * The middle pane of the Data section: one source as the paper shows it. A paper table shows its
 * image above its raw extraction as printed; a figure shows the overlay of its digitized points
 * and mapped rows on its image, or its image above a plot of the mapped rows when it has no
 * digitization. Missing files are named in one line each; the problems of the files of the source
 * follow in a disclosure. A click on a mapped point emits its row, which the section selects.
 */
const props = defineProps<{
  summary: SourceSummary;
  /** The view of the source; null while it loads or failed to load. */
  view: SourceView | null;
  loading: boolean;
  error: string | null;
  /** The row that the curator selected, whose point gets a ring. */
  selected: SelectedRow;
}>();
const emit = defineEmits<{ "select-row": [row: { file: string; line: number }]; retry: [] }>();

const study = useStudyStore();
const overview = useOverviewStore();
const id = useId();

const ICONS: Record<SourceSummary["kind"], string> = {
  table: "fas fa-table",
  figure: "fas fa-chart-line",
  text: "fas fa-align-left",
};

type Zoom = "fit" | "full";
const ZOOM_KEY = "pkdb-curation:source-zoom";

/** The zoom of the image of this viewer, which the page keeps without storage too. */
function storedZoom(): Zoom {
  try {
    return localStorage.getItem(ZOOM_KEY) === "full" ? "full" : "fit";
  } catch {
    return "fit";
  }
}
const zoom = ref<Zoom>(storedZoom());

function setZoom(value: Zoom): void {
  zoom.value = value;
  try {
    localStorage.setItem(ZOOM_KEY, value);
  } catch {
    // The zoom then lasts until the page closes.
  }
}

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");
const kind = computed(() => props.summary.kind);
/** The raw extraction of a paper table with the lines of its rows. */
const raw = computed(() =>
  props.view?.raw_grid && props.summary.raw ? rawTable(props.summary.raw, props.view.raw_grid) : null,
);
const calibrated = computed(() => (props.view ? drawsOnImage(props.view) : false));
const plotted = computed(() => (props.view ? plottedSeries(props.view) : []));
/** Whether the image block shows: the overlay of a calibrated figure replaces it, a text has none. */
const showsImage = computed(() => props.view !== null && !calibrated.value && kind.value !== "text");
/** The width of the image of a digitized figure, which the plot beside the overlay does not exceed. */
const figureWidth = computed(() =>
  props.view?.image_size ? { "--figure-width": `${props.view.image_size[0]}px` } : {},
);
/** Why the series without a dataset are plotted on their own. */
const unmatchedNote = computed(() => {
  const one = props.view?.unmatched.length === 1;
  return `${props.view?.digitization} has no dataset for ${one ? "this series" : "these series"}, so ${one ? "its" : "their"} mapped rows are plotted here.`;
});
const alt = computed(() => `${props.summary.source} of ${identity.value}`);

const tables = computed(() => new Set(detail.value ? tableFiles(detail.value) : []));
/** The problems of the files of the source by file, in the order of the Problems section. */
const problemGroups = computed(() =>
  props.view && detail.value ? groupByFile(sourceProblems(detail.value.problems, props.summary, props.view)) : [],
);
const problemCount = computed(() => problemGroups.value.reduce((sum, group) => sum + group.issues.length, 0));
/** Whether the local server validates the study after a write, for the mark of an acknowledged warning. */
const automatic = computed(() =>
  detail.value ? validatesAfterWrite(detail.value.mode, overview.snapshot ?? null) : true,
);
</script>

<template>
  <section class="source-pane" :aria-label="`Source ${summary.source}`" :style="figureWidth">
    <div class="pane-head">
      <i :class="ICONS[summary.kind]" aria-hidden="true"></i>
      <h3 class="pane-head-name">{{ summary.source }}</h3>
      <span class="pane-head-part">{{ summary.kind }}</span>
      <span v-if="summary.image" class="pane-head-part pane-head-file">{{ summary.image }}</span>
      <div v-if="showsImage && view?.image_url" class="zoom" role="group" aria-label="Image size">
        <button type="button" :aria-pressed="zoom === 'fit'" @click="setZoom('fit')">Fit</button>
        <button type="button" :aria-pressed="zoom === 'full'" @click="setZoom('full')">100 %</button>
      </div>
    </div>

    <!-- It scrolls on its own and takes the focus, so that a keyboard can scroll it: its first content is no control. -->
    <div class="pane-body" tabindex="0">
      <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${summary.source}`" />
      <VAlert v-else-if="error" type="error" variant="tonal" density="compact" class="status-alert">
        {{ summary.source }} could not be loaded. {{ error }}
        <template #append>
          <VBtn variant="text" size="small" @click="emit('retry')">Retry</VBtn>
        </template>
      </VAlert>

      <template v-else-if="view">
        <!-- The overlay draws the raw extraction of a figure on its image. -->
        <section v-if="calibrated" class="pane-block" :aria-labelledby="`${id}-overlay`">
          <h4 :id="`${id}-overlay`" class="pane-heading">Digitization on the image</h4>
          <SourceOverlay :view="view" mode="overlay" :selected="selected" @select-row="emit('select-row', $event)" />
        </section>
        <section
          v-if="calibrated && view.unmatched.length"
          class="pane-block source-unmatched"
          :aria-labelledby="`${id}-unmatched`"
        >
          <h4 :id="`${id}-unmatched`" class="pane-heading">Not digitized: {{ view.unmatched.join(", ") }}</h4>
          <p class="pane-note">{{ unmatchedNote }}</p>
          <SourceOverlay
            v-if="plotted.length"
            :view="view"
            mode="plot"
            :selected="selected"
            @select-row="emit('select-row', $event)"
          />
        </section>

        <template v-if="showsImage">
          <section class="pane-block" :aria-labelledby="`${id}-image`">
            <h4 :id="`${id}-image`" class="pane-heading">Image</h4>
            <div v-if="view.image_url" class="image-scroll">
              <img
                :src="view.image_url"
                :alt="alt"
                :width="view.image_size?.[0]"
                :height="view.image_size?.[1]"
                class="source-image"
                :class="{ 'source-image--figure': kind === 'figure', 'source-image--full': zoom === 'full' }"
              />
            </div>
            <p v-else class="pane-missing">
              <i class="fas fa-file-circle-plus" aria-hidden="true"></i>
              <span class="pane-missing-text"
                ><b>No image:</b> add {{ summary.missing_image }}.
                <span class="pane-missing-hint">Save it from the paper as a PNG image.</span></span
              >
            </p>
          </section>

          <section v-if="kind === 'table'" class="pane-block" :aria-labelledby="`${id}-raw`">
            <h4 :id="`${id}-raw`" class="pane-heading">Raw extraction</h4>
            <TableGrid v-if="raw" :table="raw" :label="`Raw extraction ${raw.file}`" class="source-raw" />
            <p v-else class="pane-missing">
              <i class="fas fa-file-circle-plus" aria-hidden="true"></i>
              <span class="pane-missing-text"
                ><b>No raw extraction:</b> add {{ summary.missing_raw }}
                <span class="pane-missing-hint">with Add table.</span></span
              >
            </p>
          </section>

          <section v-else class="pane-block" :aria-labelledby="`${id}-plot`">
            <h4 :id="`${id}-plot`" class="pane-heading">Plot of the mapped rows</h4>
            <SourceOverlay
              v-if="plotted.length"
              :view="view"
              mode="plot"
              :selected="selected"
              @select-row="emit('select-row', $event)"
            />
            <p v-else class="pane-note">No timecourse or scatter rows to plot.</p>
          </section>
        </template>

        <p v-if="kind === 'text'" class="pane-note">The rows of this source cite the text of the paper.</p>

        <p v-if="kind === 'figure' && summary.missing_raw" class="pane-missing">
          <i class="fas fa-file-circle-plus" aria-hidden="true"></i>
          <span class="pane-missing-text"
            ><b>No digitization:</b> add {{ summary.missing_raw }}.
            <span class="pane-missing-hint"
              >Digitize it in WebPlotDigitizer and import it with pkdb digitize import.</span
            ></span
          >
        </p>

        <details v-if="problemGroups.length" :open="problemGroups.length > 0" class="source-problems">
          <summary>Problems ({{ problemCount }})</summary>
          <!-- As in the Problems section: by file, the files with errors first. -->
          <section
            v-for="(group, groupIndex) in problemGroups"
            :key="group.file ?? ''"
            class="problem-group"
            :aria-labelledby="`${id}-file-${groupIndex}`"
          >
            <div class="problem-group-head">
              <div class="problem-group-title">
                <h5 :id="`${id}-file-${groupIndex}`" class="problem-file">{{ group.file }}</h5>
                <span class="problem-group-counts">{{ groupCounts(group.issues) }}</span>
              </div>
            </div>
            <ul class="problem-list">
              <ProblemItem
                v-for="(issue, index) in group.issues"
                :key="index"
                :issue="issue"
                :study="identity"
                :id-base="`${id}-problem-${groupIndex}-${index}`"
                :showable="tables.has(group.file ?? '')"
                :pending="study.acknowledgedKeys.includes(locationKey(issue))"
                :automatic="automatic"
                :disabled="false"
                :validating="false"
                :offers-acknowledge="false"
              />
            </ul>
          </section>
        </details>
      </template>
    </div>
  </section>
</template>

<style scoped>
.source-pane {
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
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* The source and its kind keep their room in a narrow pane; the image file name shortens first. */
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
  flex: 0 0 auto;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.pane-head-file {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.zoom {
  display: flex;
  flex: 0 0 auto;
  margin-inline-start: auto;
}
.zoom button {
  height: 20px;
  padding-inline: 8px;
  font-size: 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  color: rgb(var(--v-theme-on-surface));
}
.zoom button:first-child {
  border-radius: 4px 0 0 4px;
}
.zoom button:last-child {
  margin-inline-start: -1px;
  border-radius: 0 4px 4px 0;
}
.zoom button[aria-pressed="true"] {
  background: rgb(var(--v-theme-primary));
  border-color: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
.pane-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 10px;
  min-height: 0;
  padding: 8px;
  overflow: auto;
}
.pane-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.pane-heading {
  margin: 0;
  font-size: 10.5px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  overflow-wrap: anywhere;
}
.pane-note {
  margin: 0;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The image scrolls sideways at its full size. */
.image-scroll {
  overflow-x: auto;
}
.source-image {
  display: block;
  width: 100%;
  height: auto;
  background: #fff;
}
.source-image--figure {
  width: auto;
  max-width: 100%;
  max-height: 330px;
  margin: 0 auto;
}
.source-image--full {
  width: auto;
  max-width: none;
  max-height: none;
}
.source-raw {
  --rows-max-height: 40vh;
}
/* The plot of the series without a dataset is as wide as the overlay above it. */
.source-unmatched {
  max-width: calc(var(--figure-width, 100%) + 2px);
}
/* The icon, then one text that wraps as a paragraph in a narrow pane; a long file name breaks only
   when it does not fit into a line. */
.pane-missing {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 0;
  padding: 3px 8px;
  font-size: 11.5px;
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.38);
  border-radius: 6px;
}
.pane-missing-text {
  flex: 1 1 auto;
  min-width: 0;
  overflow-wrap: break-word;
}
.pane-missing-hint {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.source-problems summary {
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
/* The problems of the source are a compact form of the cards of the Problems section, with the
   12 to 13 px text and the small paddings of the panes. */
.source-problems .problem-group {
  margin-top: 6px;
  border-radius: 6px;
}
.source-problems .problem-group-head {
  gap: 8px;
  min-height: 0;
  padding: 3px 8px;
}
.source-problems .problem-file {
  font-size: 13px;
}
.source-problems .problem-group-counts {
  font-size: 12px;
}
.source-problems .problem {
  gap: 3px;
  padding: 6px 8px;
}
.source-problems :deep(.problem-severity) {
  --v-chip-height: 20px;
}
.source-problems :deep(.problem-code) {
  font-size: 12px;
}
.source-problems :deep(.problem-message) {
  font-size: 13px;
  line-height: 1.4;
}
.source-problems :deep(.problem-fact) {
  font-size: 12px;
  line-height: 1.4;
}
</style>
