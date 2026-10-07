<script setup lang="ts">
import { computed, useId } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VBtn, VProgressLinear, VTab, VTabs } from "vuetify/components";
import type { SourceView } from "../api/types";
import MappedRows from "../components/MappedRows.vue";
import RawGrid from "../components/RawGrid.vue";
import SourceOverlay from "../components/SourceOverlay.vue";
import { useLoaded } from "../composables/useLoaded";
import { isCalibrated, plottedSeries } from "../overlay";
import { location, SEVERITY_LABELS, tableQuery } from "../problems";
import { missingFiles, sourceKind, sourceProblems, type SourceKind } from "../sources";
import { useStudyStore } from "../stores/study";
import { sectionRoute, studyName, tableFiles } from "../study";

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
const route = useRoute();
const router = useRouter();
const id = useId();

const ICONS: Record<SourceKind, string> = {
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
const kind = computed<SourceKind | null>(() => (selected.value ? sourceKind(selected.value.source) : null));
const calibrated = computed(() => (view.value ? isCalibrated(view.value) : false));
const plotted = computed(() => (view.value ? plottedSeries(view.value) : []));
const missing = computed(() =>
  view.value && detail.value ? missingFiles(studyName(detail.value), view.value) : { image: null, raw: null },
);
/** Why the series without a dataset are plotted on their own. */
const unmatchedNote = computed(() => {
  const one = view.value?.unmatched.length === 1;
  return `${view.value?.digitization} has no dataset for ${one ? "this series" : "these series"}, so ${one ? "its" : "their"} mapped rows are plotted here.`;
});
const alt = computed(() => `${selected.value?.source ?? ""} of ${identity.value}`);

const tables = computed(() => new Set(detail.value ? tableFiles(detail.value) : []));
/** The problems of the files of the source, with the route to the cell of a problem in a table. */
const problems = computed(() => {
  if (!view.value || !selected.value || !detail.value) return [];
  return sourceProblems(detail.value.problems, selected.value, view.value).map((issue) => {
    const query = tables.value.has(issue.source?.file ?? "") ? tableQuery(issue) : null;
    return { issue, route: query ? sectionRoute(identity.value, "tables", query) : null };
  });
});

/** A clicked mapped point opens its row in the Tables section. */
function showRow(row: { file: string; line: number }): void {
  void router.push(sectionRoute(identity.value, "tables", { file: row.file, line: String(row.line) }));
}
</script>

<template>
  <div class="sources">
    <p v-if="!sources.length" class="sources-empty">The study has no sources yet.</p>
    <template v-else>
      <VTabs v-model="tab" show-arrows color="primary" density="compact" aria-label="Sources" class="sources-tabs">
        <VTab
          v-for="entry in sources"
          :id="tabId(entry.source)"
          :key="entry.source"
          :value="entry.source"
          :prepend-icon="ICONS[sourceKind(entry.source)]"
          :aria-controls="entry.source === selected?.source ? panelId : undefined"
          class="sources-tab"
        >
          {{ entry.source }}
        </VTab>
      </VTabs>

      <div v-if="selected" :id="panelId" role="tabpanel" :aria-labelledby="tabId(selected.source)" class="source-panel">
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
              <div v-if="view.image_url" class="source-image">
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
                  <p class="source-missing-name">No image: add {{ missing.image }}</p>
                  <p class="source-missing-hint">Save the {{ kind }} from the paper as a PNG image in the study folder.</p>
                </div>
              </div>
            </section>

            <section v-if="kind === 'table'" class="source-block" :aria-labelledby="`${id}-raw`">
              <h3 :id="`${id}-raw`" class="source-heading">Raw extraction</h3>
              <RawGrid v-if="view.raw_grid" :grid="view.raw_grid" :label="`Raw extraction ${selected.raw}`" />
              <div v-else class="source-missing">
                <i class="fas fa-file-circle-plus source-missing-icon" aria-hidden="true"></i>
                <div>
                  <p class="source-missing-name">No raw extraction: add {{ missing.raw }}</p>
                  <p class="source-missing-hint">Add table in the study menu adds it as a sheet of the workbook.</p>
                </div>
              </div>
            </section>

            <section v-else class="source-block" :aria-labelledby="`${id}-plot`">
              <h3 :id="`${id}-plot`" class="source-heading">Plot of the mapped rows</h3>
              <SourceOverlay v-if="plotted.length" :view="view" mode="plot" @select-row="showRow" />
              <p v-else class="field-note">No timecourse or scatter rows to plot.</p>
            </section>
          </div>

          <div v-if="kind === 'figure' && missing.raw" class="source-missing">
            <i class="fas fa-file-circle-plus source-missing-icon" aria-hidden="true"></i>
            <div>
              <p class="source-missing-name">No raw extraction: add {{ missing.raw }}</p>
              <p class="source-missing-hint">Digitize the figure in WebPlotDigitizer and import the project with pkdb digitize import.</p>
            </div>
          </div>

          <section class="source-block" :aria-labelledby="`${id}-mapped`">
            <h3 :id="`${id}-mapped`" class="source-heading">Mapped rows</h3>
            <MappedRows v-if="view.mapped.length" :tables="view.mapped" :study="identity" />
            <p v-else class="field-note">No rows of the tables name {{ view.source }} as their source.</p>
          </section>

          <section v-if="problems.length" class="source-block source-problems" :aria-labelledby="`${id}-problems`">
            <h3 :id="`${id}-problems`" class="source-heading">Problems</h3>
            <ul class="source-problem-list">
              <li v-for="({ issue, route: cell }, index) in problems" :key="index" class="source-problem">
                <div class="problem-head">
                  <i
                    :class="[
                      issue.severity === 'error' ? 'fas fa-circle-xmark' : 'fas fa-triangle-exclamation',
                      `source-problem-icon--${issue.severity}`,
                    ]"
                    class="source-problem-icon"
                    aria-hidden="true"
                  ></i>
                  <span class="d-sr-only">{{ SEVERITY_LABELS[issue.severity] }}</span>
                  <code class="problem-code">{{ issue.code }}</code>
                  <span class="source-problem-location">{{ location(issue) }}</span>
                  <RouterLink v-if="cell" :to="cell" class="source-problem-link">
                    Show in table
                  </RouterLink>
                </div>
                <p class="problem-message">{{ issue.message }}</p>
              </li>
            </ul>
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
/* The image beside the raw extraction or the plot; below it in a narrow column. */
.source-columns {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr));
  gap: 24px;
  align-items: start;
}
.source-image {
  min-width: 0;
}
/* A plot of a few series reads best at about the width of a figure. */
.source-unmatched {
  max-width: 56rem;
}
.source-image img {
  display: block;
  max-width: 100%;
  height: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background-color: #fff;
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
.source-problem-list {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.source-problem {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
}
.source-problem + .source-problem {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.source-problem-icon--error {
  color: rgb(var(--v-theme-error));
}
.source-problem-icon--warning {
  color: rgb(var(--v-theme-warning));
}
.source-problem-location {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  overflow-wrap: anywhere;
}
.source-problem-link {
  font-size: 0.875rem;
}
</style>
