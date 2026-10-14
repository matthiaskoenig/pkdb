<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { VBtn, VProgressLinear } from "vuetify/components";
import type { SourceSummary, SourceView } from "../../study-views/types";
import { useMoreBelow } from "../../study-views/composables/useMoreBelow";
import { useStudyViews } from "../../study-views/context";
import { rawTable } from "../../study-views/grid";
import { capped, drawsOnImage, plottedSeries, pointsOffScale, type SelectedRow } from "../../study-views/overlay";
import { groupByFile, groupCounts, locationKey } from "../../study-views/problems";
import { SOURCE_ICONS, sourceProblems } from "../../study-views/sources";
import { tableFiles, viewWithoutFiles, withoutFiles, type ActionFailure } from "../../study-views/study";
import ActionFailureAlert from "./ActionFailureAlert.vue";
import MoreBelow from "./MoreBelow.vue";
import PlotScales from "./PlotScales.vue";
import ProblemItem from "./ProblemItem.vue";
import SourceOverlay from "./SourceOverlay.vue";
import TableGrid from "./TableGrid.vue";

/**
 * The middle pane of the Data section: one source as the paper shows it. A paper table shows its
 * image above its raw extraction as printed; a figure shows the overlay of its digitized points
 * and mapped rows on its image, or its image above a plot of the mapped rows when it has no
 * digitization. Above a plot of mapped rows, the curator switches each axis between linear and log.
 * Missing files are named in one line each; the problems of the files of the source
 * follow in a disclosure. A click on a mapped point emits its row, which the section selects.
 * A reader without the files of the study sees no image and no raw extraction (a figure is
 * plotted), a reader without the curation no problems, and only `edit` names what to add.
 */
const props = defineProps<{
  summary: SourceSummary;
  /** The view of the source; null while it loads or failed to load. */
  view: SourceView | null;
  loading: boolean;
  /** Why the view could not be loaded, with what the local server said about it. */
  error: ActionFailure | null;
  /** The row that the curator selected, whose point gets a ring. */
  selected: SelectedRow;
}>();
const emit = defineEmits<{ "select-row": [row: NonNullable<SelectedRow>]; retry: [] }>();

const views = useStudyViews();
const capabilities = views.capabilities;
const id = useId();

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

/**
 * The view of the source as the reader may see it: without its image and raw extraction when the
 * page does not show the files, so that a digitized figure is plotted rather than drawn on an image.
 */
const sourceView = computed(() =>
  props.view && !capabilities.value.files ? viewWithoutFiles(props.view) : props.view,
);
const detail = views.data.detail;
/** The warnings acknowledged on this page that no later validation checked yet. */
const acknowledged = views.data.acknowledgedKeys;
const identity = computed(() => detail.value?.id ?? "");
/** The scales of the plots of the source: the curator's choice for the figure, else the digitization's, else linear. */
const { scales, choose } = views.data.plotScales(identity, () => sourceView.value);
/** The points of the plot that its log axes leave out. */
const offScale = computed(() => (sourceView.value ? pointsOffScale(sourceView.value, scales.value) : 0));
const kind = computed(() => props.summary.kind);
/** The raw extraction of a paper table with the lines of its rows. */
const raw = computed(() =>
  sourceView.value?.raw_grid && props.summary.raw ? rawTable(props.summary.raw, sourceView.value.raw_grid) : null,
);
/** Whether the overlay draws on the image; never for a reader without the files, whose view has no image. */
const calibrated = computed(() => (sourceView.value ? drawsOnImage(sourceView.value) : false));
const plotted = computed(() => (sourceView.value ? plottedSeries(sourceView.value) : []));
/** Whether the image block shows: the overlay of a calibrated figure replaces it, a text has none. */
const showsImage = computed(() => sourceView.value !== null && !calibrated.value && kind.value !== "text");
/** The width of the image of a digitized figure, which the plot beside the overlay does not exceed. */
const figureWidth = computed(() =>
  sourceView.value?.image_size ? { "--figure-width": `${sourceView.value.image_size[0]}px` } : {},
);
/** Why the series without a dataset are plotted on their own. */
const unmatchedNote = computed(() => {
  const one = sourceView.value?.unmatched.length === 1;
  return `${sourceView.value?.digitization} has no dataset for ${one ? "this series" : "these series"}, so ${one ? "its" : "their"} mapped rows are plotted here.`;
});
/** The series without a dataset that the heading lists, at most the limit of the legend. */
const unmatched = computed(() => capped(sourceView.value?.unmatched ?? []));
const alt = computed(() => `${props.summary.source} of ${identity.value}`);

/** The tables that the reader can open in the Data section: no raw table without the files. */
const tables = computed(() => {
  const value = detail.value;
  if (!value) return new Set<string>();
  return new Set(tableFiles(capabilities.value.files ? value : withoutFiles(value)));
});
/** The problems of the files of the source, in the order of the Problems section; the plot rings their rows. */
const sourceIssues = computed(() =>
  sourceView.value && detail.value && capabilities.value.curation
    ? sourceProblems(detail.value.problems, props.summary, sourceView.value)
    : [],
);
/** The problems of the files of the source by file. */
const problemGroups = computed(() => groupByFile(sourceIssues.value));
const problemCount = computed(() => problemGroups.value.reduce((sum, group) => sum + group.issues.length, 0));
/** Whether the server validates the study after a write, for the mark of an acknowledged warning. */
const automatic = views.data.validatesAfterWrite;

// More of the pane below its view: a fade at its bottom shows it, inside its scroll bar. The body
// changes with the window and the separator, the content with a loaded view or image.
const body = ref<HTMLElement | null>(null);
const content = ref<HTMLElement | null>(null);
const { more, scrollbar } = useMoreBelow(body, content);
</script>

<template>
  <section class="source-pane" :aria-label="`Source ${summary.source}`" :style="figureWidth">
    <div class="pane-head">
      <i :class="SOURCE_ICONS[summary.kind]" aria-hidden="true"></i>
      <h3 class="pane-head-name">{{ summary.source }}</h3>
      <!-- The source and its kind keep their room in a narrow pane; the image file name shortens first. -->
      <span class="pane-head-part pane-head-part--fixed">{{ summary.kind }}</span>
      <span v-if="capabilities.files && summary.image" class="pane-head-part">{{ summary.image }}</span>
      <div
        v-if="capabilities.files && showsImage && sourceView?.image_url"
        class="zoom switch-group"
        role="group"
        aria-label="Image size"
      >
        <button type="button" :aria-pressed="zoom === 'fit'" @click="setZoom('fit')">Fit</button>
        <button type="button" :aria-pressed="zoom === 'full'" @click="setZoom('full')">100 %</button>
      </div>
    </div>

    <!-- The body scrolls on its own and takes the focus, so that a keyboard can scroll it: its
         first content is no control. While more of it follows below, a fade at its bottom shows it. -->
    <div class="pane-frame">
      <div ref="body" class="pane-body" tabindex="0">
        <div ref="content" class="pane-content">
          <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${summary.source}`" />
          <!-- It goes when the view loads again, after Retry or a change of the study: no close button. -->
          <ActionFailureAlert v-else-if="error" :failure="error" :study="detail?.id ?? null" :closable="false">
            <template #append>
              <VBtn variant="text" size="small" @click="emit('retry')">Retry</VBtn>
            </template>
          </ActionFailureAlert>

          <template v-else-if="sourceView">
            <!-- The overlay draws the raw extraction of a figure on its image. -->
            <section v-if="calibrated" class="pane-block" :aria-labelledby="`${id}-overlay`">
              <h4 :id="`${id}-overlay`" class="pane-heading">Digitization on the image</h4>
              <SourceOverlay
                :view="sourceView"
                mode="overlay"
                :selected="selected"
                @select-row="emit('select-row', $event)"
              />
            </section>
            <section
              v-if="calibrated && sourceView.unmatched.length"
              class="pane-block source-unmatched"
              :aria-labelledby="`${id}-unmatched`"
            >
              <h4 :id="`${id}-unmatched`" class="pane-heading">Not digitized</h4>
              <!-- One name per item: names can contain commas. -->
              <ul class="source-unmatched-list" aria-label="Series without a dataset">
                <li v-for="name in unmatched.shown" :key="name">{{ name }}</li>
                <li v-if="unmatched.more">and {{ unmatched.more }} more series</li>
              </ul>
              <p class="pane-note">{{ unmatchedNote }}</p>
              <template v-if="plotted.length">
                <PlotScales :scales="scales" :hidden="offScale" @choose="choose" />
                <SourceOverlay
                  :view="sourceView"
                  mode="plot"
                  :scales="scales"
                  :selected="selected"
                  :problems="sourceIssues"
                  @select-row="emit('select-row', $event)"
                />
              </template>
            </section>

            <template v-if="showsImage">
              <section v-if="capabilities.files" class="pane-block" :aria-labelledby="`${id}-image`">
                <h4 :id="`${id}-image`" class="pane-heading">Image</h4>
                <div v-if="sourceView.image_url" class="image-scroll">
                  <img
                    :src="sourceView.image_url"
                    :alt="alt"
                    :width="sourceView.image_size?.[0]"
                    :height="sourceView.image_size?.[1]"
                    class="source-image"
                    :class="{ 'source-image--figure': kind === 'figure', 'source-image--full': zoom === 'full' }"
                  />
                </div>
                <p v-else class="pane-missing">
                  <i class="fas fa-file-circle-plus" aria-hidden="true"></i>
                  <span v-if="capabilities.edit" class="pane-missing-text"
                    ><b>No image:</b> add {{ summary.missing_image }}.
                    <span class="pane-missing-hint">Save it from the paper as a PNG image.</span></span
                  >
                  <span v-else class="pane-missing-text">No image.</span>
                </p>
              </section>

              <section
                v-if="kind === 'table' && capabilities.files"
                class="pane-block"
                :aria-labelledby="`${id}-raw`"
              >
                <h4 :id="`${id}-raw`" class="pane-heading">Raw extraction</h4>
                <TableGrid v-if="raw" :table="raw" :label="`Raw extraction ${raw.file}`" class="source-raw" />
                <p v-else class="pane-missing">
                  <i class="fas fa-file-circle-plus" aria-hidden="true"></i>
                  <span v-if="capabilities.edit" class="pane-missing-text"
                    ><b>No raw extraction:</b> add {{ summary.missing_raw }}
                    <span class="pane-missing-hint">with Add table.</span></span
                  >
                  <span v-else class="pane-missing-text">No raw extraction.</span>
                </p>
              </section>
              <p v-else-if="kind === 'table'" class="pane-note source-files-note">
                The image and the raw extraction of this table are not public.
              </p>

              <section v-else class="pane-block" :aria-labelledby="`${id}-plot`">
                <h4 :id="`${id}-plot`" class="pane-heading">Plot of the mapped rows</h4>
                <template v-if="plotted.length">
                  <PlotScales :scales="scales" :hidden="offScale" @choose="choose" />
                  <SourceOverlay
                    :view="sourceView"
                    mode="plot"
                    :scales="scales"
                    :selected="selected"
                    :problems="sourceIssues"
                    @select-row="emit('select-row', $event)"
                  />
                </template>
                <p v-else class="pane-note">No rows with a time or scatter rows to plot.</p>
              </section>
            </template>

            <p v-if="kind === 'text'" class="pane-note">The rows of this source cite the text of the paper.</p>

            <p v-if="capabilities.edit && kind === 'figure' && summary.missing_raw" class="pane-missing">
              <i class="fas fa-file-circle-plus" aria-hidden="true"></i>
              <span class="pane-missing-text"
                ><b>No digitization:</b> add {{ summary.missing_raw }}.
                <span class="pane-missing-hint"
                  >Digitize it in WebPlotDigitizer and import it with pkdb digitize import.</span
                ></span
              >
            </p>

            <!-- Open for each source, also after the curator closed them for the last one. -->
            <details
              v-if="capabilities.curation && problemGroups.length"
              :key="summary.source"
              open
              class="source-problems"
            >
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
                    :pending="acknowledged.includes(locationKey(issue))"
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
      </div>
      <MoreBelow v-if="more" :scrollbar="scrollbar" />
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
/* The zoom of the image (`switch-group` of src/study-views/styles.css) goes to the end of the head. */
.zoom {
  margin-inline-start: auto;
}
.pane-frame {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}
.pane-body {
  flex: 1;
  min-height: 0;
  padding: 8px;
  overflow: auto;
}
.pane-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
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
.source-unmatched-list {
  margin: 0 0 6px;
  padding-left: 18px;
  font-size: 13px;
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
