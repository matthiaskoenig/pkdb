<script setup lang="ts">
import { computed, ref, shallowRef, useId, watch } from "vue";
import { VCard, VCardText, VProgressLinear } from "vuetify/components";
import { isAbort } from "../api/client";
import type { ReviewTarget, SourceView, TableResponse } from "../api/types";
import { plural } from "../overview";
import { matchingRows, matchText, seriesOfTarget, shownColumns, targetText } from "../review";
import { useStudyStore } from "../stores/study";
import { messageOf, tableFiles } from "../study";
import SourceOverlay from "./SourceOverlay.vue";

/** At most this many rows are listed; the Tables section has all of them. */
const LISTED_ROWS = 100;

/**
 * What a review item is about: the rows of its table that match its row filters, with its column
 * marked, and for a digitized series the figure overlay with that series emphasized. Nothing
 * shows for the whole study or a file that is no table.
 */
const props = defineProps<{ target: ReviewTarget | undefined }>();

const study = useStudyStore();
const headingId = useId();

const file = computed(() => props.target?.file ?? null);
const filters = computed(() => props.target?.rows ?? {});
const filtered = computed(() => Object.keys(filters.value).length > 0);
/** A data table or a raw table of the study, whose rows the local API serves. */
const tableFile = computed(() =>
  file.value !== null && study.detail !== null && tableFiles(study.detail).includes(file.value) ? file.value : null,
);
/** The digitized series of a timecourse target: a figure with a WebPlotDigitizer project. */
const series = computed(() => {
  const found = seriesOfTarget(props.target);
  const summary = found && study.detail?.sources.find((source) => source.source === found.source);
  return summary?.raw_kind === "digitization" ? found : null;
});

/** Loads `read()` into `data` when `key` changes and when the detail changes; late answers are dropped. */
function useLoaded<T>(key: () => string | null, read: (key: string) => Promise<T>) {
  // Shallow: a table of thousands of rows needs no deep reactivity.
  const data = shallowRef<{ key: string; content: T } | null>(null);
  const error = ref<string | null>(null);
  const loading = ref(false);
  let request = 0;
  watch(
    [key, () => study.detail],
    async ([name]) => {
      const current = ++request;
      error.value = null;
      // The last answer stays while the same resource revalidates.
      if (data.value?.key !== name) data.value = null;
      if (name === null) return;
      loading.value = data.value === null;
      try {
        const content = await read(name);
        if (current === request) data.value = { key: name, content };
      } catch (caught) {
        if (current === request && !isAbort(caught)) error.value = messageOf(caught);
      } finally {
        if (current === request) loading.value = false;
      }
    },
    { immediate: true },
  );
  return { data, error, loading };
}

const {
  data: table,
  error: tableError,
  loading: tableLoading,
} = useLoaded<TableResponse>(
  () => tableFile.value,
  (name) => study.table(name),
);
const {
  data: figure,
  error: figureError,
  loading: figureLoading,
} = useLoaded<SourceView>(
  () => series.value?.source ?? null,
  (name) => study.source(name),
);

const rows = computed(() => {
  const loaded = table.value?.content;
  if (!loaded || loaded.kind !== "table") return null;
  const matched = matchingRows(loaded.header, loaded.rows, filters.value);
  const column = props.target?.column ?? null;
  const kept = shownColumns(loaded.header, matched, [...Object.keys(filters.value), ...(column ? [column] : [])]);
  // The column of the item comes first, so that it is in view in a wide table.
  const marked = column === null ? -1 : loaded.header.indexOf(column);
  return {
    header: loaded.header,
    columns: marked < 0 ? kept : [marked, ...kept.filter((index) => index !== marked)],
    marked,
    matched: matched.length,
    total: loaded.rows.length,
    listed: matched.slice(0, LISTED_ROWS),
    hidden: matched.length > 0 && kept.length < loaded.header.length,
  };
});
const rawTable = computed(() => table.value?.content.kind === "raw");
const shown = computed(() => tableFile.value !== null || series.value !== null);
</script>

<template>
  <VCard v-if="shown" tag="section" border class="review-target" :aria-labelledby="headingId">
    <VCardText class="target-body">
      <div class="target-head">
        <h3 :id="headingId" class="target-heading">Target</h3>
        <p class="target-text">{{ targetText(target) }}</p>
      </div>

      <div v-if="tableFile" class="target-block">
        <VProgressLinear v-if="tableLoading" indeterminate color="primary" :aria-label="`Loading ${tableFile}`" />
        <p v-else-if="tableError" class="field-error">
          The rows of {{ tableFile }} could not be loaded. {{ tableError }}
        </p>
        <p v-else-if="rawTable" class="field-note">The Sources section shows this raw table.</p>
        <template v-else-if="rows">
          <p class="target-caption">
            {{ filtered ? matchText(rows.matched, rows.total) : `The table has ${plural(rows.total, "row")}.` }}
            <template v-if="filtered && rows.matched === 0">
              The rows may have changed since the item was written.
            </template>
            <template v-if="rows.matched > rows.listed.length">
              The first {{ rows.listed.length }} are listed.
            </template>
            <template v-if="rows.hidden">Empty columns are hidden.</template>
          </p>
          <!-- The rows scroll inside their region, which takes the focus so that a keyboard can scroll it. -->
          <div
            v-if="rows.listed.length"
            class="target-scroll"
            tabindex="0"
            role="region"
            :aria-label="`Rows of ${tableFile}`"
          >
            <table class="target-rows">
              <thead>
                <tr>
                  <th scope="col" class="target-line">Line</th>
                  <th
                    v-for="index in rows.columns"
                    :key="index"
                    scope="col"
                    :class="{ 'target-column': index === rows.marked }"
                  >
                    {{ rows.header[index]
                    }}<span v-if="index === rows.marked" class="d-sr-only">, the column of the item</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rows.listed" :key="row.line">
                  <th scope="row" class="target-line">{{ row.line }}</th>
                  <td
                    v-for="index in rows.columns"
                    :key="index"
                    :class="{ 'target-column': index === rows.marked }"
                  >
                    {{ row.cells[index] ?? "" }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>

      <div v-if="series" class="target-block">
        <h4 class="field-heading">Figure {{ series.source }}</h4>
        <VProgressLinear
          v-if="figureLoading"
          indeterminate
          color="primary"
          :aria-label="`Loading figure ${series.source}`"
        />
        <p v-else-if="figureError" class="field-error">
          Figure {{ series.source }} could not be loaded. {{ figureError }}
        </p>
        <SourceOverlay
          v-else-if="figure"
          :view="figure.content"
          :highlight="series.series"
        />
      </div>
    </VCardText>
  </VCard>
</template>

<style scoped>
.target-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.target-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px 12px;
}
.target-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.target-text {
  margin: 0;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.target-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.target-caption {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
/* At most about twelve rows show at once; the header and the line stay in view while the rows scroll. */
.target-scroll {
  max-height: 420px;
  overflow: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.target-rows {
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.8125rem;
}
.target-rows th,
.target-rows td {
  height: 32px;
  padding: 0 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  text-align: start;
  white-space: nowrap;
}
.target-rows tbody tr:last-child > * {
  border-bottom: 0;
}
.target-rows thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: rgb(var(--v-theme-surface));
  font-weight: 600;
}
.target-rows .target-line {
  position: sticky;
  left: 0;
  z-index: 1;
  background: rgb(var(--v-theme-surface));
  font-variant-numeric: tabular-nums;
}
.target-rows thead .target-line {
  z-index: 3;
}
.target-rows tbody .target-line {
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The tint sits over the surface, so that the sticky header stays opaque. */
.target-rows .target-column {
  background-image: linear-gradient(rgba(var(--v-theme-primary), 0.1), rgba(var(--v-theme-primary), 0.1));
}
</style>
