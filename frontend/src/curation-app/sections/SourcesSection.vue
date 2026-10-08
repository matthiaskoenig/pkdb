<script setup lang="ts">
import { computed, useId } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VBtn, VProgressLinear, VTab, VTabs } from "vuetify/components";
import type { SourceSummary, SourceView } from "../api/types";
import MappedRows from "../components/MappedRows.vue";
import ProblemItem from "../components/ProblemItem.vue";
import SourceOverlay from "../components/SourceOverlay.vue";
import TableGrid from "../components/TableGrid.vue";
import { useLoaded } from "../composables/useLoaded";
import { rawTable } from "../grid";
import { drawsOnImage, plottedSeries } from "../overlay";
import { groupByFile, groupCounts, locationKey, validatesAfterWrite } from "../problems";
import { sourceProblems } from "../sources";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { sectionRoute, tableFiles } from "../study";

/**
 * One tab per source of the study. A paper table shows its image beside its raw extraction as
 * printed; a figure shows the overlay of its digitized points and mapped rows on its image, or
 * its image beside a plot of the mapped rows when it has no digitization. Below them the mapped
 * rows by table and the problems of the files of the source. Missing files are named.
 *
 * The chosen source is the `source` of the route, so that other sections can link to it. A
 * clicked mapped point or row opens the Tables section at its file and line.
 */
const study = useStudyStore();
const overview = useOverviewStore();
const route = useRoute();
const router = useRouter();
const id = useId();

const ICONS: Record<SourceSummary["kind"], string> = {
  table: "fas fa-table",
  figure: "fas fa-chart-line",
  text: "fas fa-align-left",
};

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");
const sources = computed(() => detail.value?.sources ?? []);

const linked = computed(() => (typeof route.query.source === "string" ? route.query.source : null));
/** The source of the route, else the first source. */
const selected = computed(
  () => sources.value.find((entry) => entry.source === linked.value) ?? sources.value[0] ?? null,
);
const tab = computed({
  get: () => selected.value?.source,
  set: (value: unknown) => {
    if (typeof value !== "string" || value === linked.value) return;
    void router.replace({ query: { ...route.query, source: value } });
  },
});

const tabId = (source: string) => `${id}-tab-${source}`;
const panelId = `${id}-panel`;

const { data, error, loading, reload } = useLoaded<SourceView>(
  () => selected.value?.source ?? null,
  (name) => study.source(name),
  () => study.detail,
);
/** The view of the chosen source; null while another one is shown or it loads. */
const view = computed(() => (data.value && data.value.key === selected.value?.source ? data.value.content : null));
const kind = computed(() => selected.value?.kind ?? null);
/** The raw extraction of a paper table with the lines of its rows. */
const raw = computed(() =>
  view.value?.raw_grid && selected.value?.raw ? rawTable(selected.value.raw, view.value.raw_grid) : null,
);
const calibrated = computed(() => (view.value ? drawsOnImage(view.value) : false));
const plotted = computed(() => (view.value ? plottedSeries(view.value) : []));
/** The width of the image of a digitized figure, which the plot beside the overlay does not exceed. */
const figureWidth = computed(() => (view.value?.image_size ? { "--figure-width": `${view.value.image_size[0]}px` } : {}));
/** Why the series without a dataset are plotted on their own. */
const unmatchedNote = computed(() => {
  const one = view.value?.unmatched.length === 1;
  return `${view.value?.digitization} has no dataset for ${one ? "this series" : "these series"}, so ${one ? "its" : "their"} mapped rows are plotted here.`;
});
const alt = computed(() => `${selected.value?.source ?? ""} of ${identity.value}`);

const tables = computed(() => new Set(detail.value ? tableFiles(detail.value) : []));
/** The problems of the files of the source by file, in the order of the Problems section. */
const problemGroups = computed(() =>
  view.value && selected.value && detail.value
    ? groupByFile(sourceProblems(detail.value.problems, selected.value, view.value))
    : [],
);
/** Whether the local server validates the study after a write, for the mark of an acknowledged warning. */
const automatic = computed(() =>
  detail.value ? validatesAfterWrite(detail.value.mode, overview.snapshot ?? null) : true,
);

/** A clicked mapped point opens its row in the Tables section. */
function showRow(row: { file: string; line: number }): void {
  void router.push(sectionRoute(identity.value, "tables", { file: row.file, line: String(row.line) }));
}
</script>

<template>
  <div class="sources">
    <p v-if="!sources.length" class="sources-empty">The study has no sources yet.</p>
    <template v-else>
      <VTabs
        v-model="tab"
        show-arrows
        center-active
        color="primary"
        density="compact"
        aria-label="Sources"
        class="sources-tabs scroll-tabs"
      >
        <VTab
          v-for="entry in sources"
          :id="tabId(entry.source)"
          :key="entry.source"
          :value="entry.source"
          :prepend-icon="ICONS[entry.kind]"
          :aria-controls="entry.source === selected?.source ? panelId : undefined"
          class="sources-tab"
        >
          {{ entry.source }}
        </VTab>
      </VTabs>

      <!-- The panel takes the focus after its tab, as its first content is no control. -->
      <div
        v-if="selected"
        :id="panelId"
        role="tabpanel"
        tabindex="0"
        :aria-labelledby="tabId(selected.source)"
        class="source-panel"
        :style="figureWidth"
      >
        <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${selected.source}`" />
        <VAlert v-else-if="error" type="error" variant="tonal" density="compact" class="status-alert">
          {{ selected.source }} could not be loaded. {{ error }}
          <template #append>
            <VBtn variant="text" size="small" @click="reload">Retry</VBtn>
          </template>
        </VAlert>

        <template v-else-if="view">
          <!-- The overlay draws the raw extraction of a figure on its image. -->
          <section v-if="calibrated" class="source-block" :aria-labelledby="`${id}-overlay`">
            <h3 :id="`${id}-overlay`" class="source-heading">Digitization on the image</h3>
            <SourceOverlay :view="view" mode="overlay" @select-row="showRow" />
          </section>
          <section
            v-if="calibrated && view.unmatched.length"
            class="source-block source-unmatched"
            :aria-labelledby="`${id}-unmatched`"
          >
            <h3 :id="`${id}-unmatched`" class="source-heading">Not digitized: {{ view.unmatched.join(", ") }}</h3>
            <p class="field-note">{{ unmatchedNote }}</p>
            <SourceOverlay v-if="plotted.length" :view="view" mode="plot" @select-row="showRow" />
          </section>

          <div v-if="!calibrated && kind !== 'text'" class="source-columns">
            <section class="source-block" :aria-labelledby="`${id}-image`">
              <h3 :id="`${id}-image`" class="source-heading">Image</h3>
              <div v-if="view.image_url" class="figure-frame figure-frame--paper source-image">
                <img
                  :src="view.image_url"
                  :alt="alt"
                  :width="view.image_size?.[0]"
                  :height="view.image_size?.[1]"
                />
              </div>
              <div v-else class="source-missing">
                <i class="fas fa-file-circle-plus source-missing-icon" aria-hidden="true"></i>
                <div>
                  <p class="source-missing-name">No image: add {{ selected.missing_image }}</p>
                  <p class="source-missing-hint">Save the {{ kind }} from the paper as a PNG image in the study folder.</p>
                </div>
              </div>
            </section>

            <section v-if="kind === 'table'" class="source-block" :aria-labelledby="`${id}-raw`">
              <h3 :id="`${id}-raw`" class="source-heading">Raw extraction</h3>
              <TableGrid v-if="raw" :table="raw" :label="`Raw extraction ${raw.file}`" />
              <div v-else class="source-missing">
                <i class="fas fa-file-circle-plus source-missing-icon" aria-hidden="true"></i>
                <div>
                  <p class="source-missing-name">No raw extraction: add {{ selected.missing_raw }}</p>
                  <p class="source-missing-hint">Use Add table in the study menu to add it as a sheet of the workbook.</p>
                </div>
              </div>
            </section>

            <section v-else class="source-block" :aria-labelledby="`${id}-plot`">
              <h3 :id="`${id}-plot`" class="source-heading">Plot of the mapped rows</h3>
              <SourceOverlay v-if="plotted.length" :view="view" mode="plot" @select-row="showRow" />
              <p v-else class="field-note">No timecourse or scatter rows to plot.</p>
            </section>
          </div>

          <div v-if="kind === 'figure' && selected.missing_raw" class="source-missing">
            <i class="fas fa-file-circle-plus source-missing-icon" aria-hidden="true"></i>
            <div>
              <p class="source-missing-name">No raw extraction: add {{ selected.missing_raw }}</p>
              <p class="source-missing-hint">Digitize the figure in WebPlotDigitizer and import the project with pkdb digitize import.</p>
            </div>
          </div>

          <section class="source-block" :aria-labelledby="`${id}-mapped`">
            <h3 :id="`${id}-mapped`" class="source-heading">Mapped rows</h3>
            <MappedRows v-if="view.mapped.length" :tables="view.mapped" :study="identity" />
            <p v-else class="field-note">No rows of the tables name {{ view.source }} as their source.</p>
          </section>

          <section v-if="problemGroups.length" class="source-block source-problems" :aria-labelledby="`${id}-problems`">
            <h3 :id="`${id}-problems`" class="source-heading">Problems</h3>
            <!-- As in the Problems section: by file, the files with errors first. -->
            <section
              v-for="(group, groupIndex) in problemGroups"
              :key="group.file ?? ''"
              class="problem-group"
              :aria-labelledby="`${id}-file-${groupIndex}`"
            >
              <div class="problem-group-head">
                <div class="problem-group-title">
                  <h4 :id="`${id}-file-${groupIndex}`" class="problem-file">{{ group.file }}</h4>
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
          </section>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sources {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.sources-empty {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.sources-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.source-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}
.source-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.source-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
/* The image beside the raw extraction or the plot in two equal columns, below it in a narrow
   window. The frames and tables fill their column, so that their edges line up with the column
   and with the mapped rows below, which span the panel. */
.source-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr));
  gap: 24px;
  align-items: start;
}
/* The image keeps its size in its frame, centered on the paper; a larger image shrinks. */
.source-image {
  display: flex;
  justify-content: center;
  min-width: 0;
}
.source-image img {
  display: block;
  max-width: 100%;
  height: auto;
}
/* The plot of the series without a dataset is as wide as the overlay above it. */
.source-unmatched {
  max-width: calc(var(--figure-width) + 2px);
}
.source-missing {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.38);
  border-radius: 8px;
}
.source-missing-icon {
  flex: 0 0 auto;
  margin-top: 2px;
  font-size: 1.125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.source-missing-name,
.source-missing-hint {
  margin: 0;
  overflow-wrap: anywhere;
}
.source-missing-name {
  font-weight: 600;
}
.source-missing-hint {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
