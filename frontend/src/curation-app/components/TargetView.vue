<script setup lang="ts">
import { computed, useId } from "vue";
import { useRouter } from "vue-router";
import { VCard, VCardText, VProgressLinear } from "vuetify/components";
import type { ReviewTarget, SourceView, TableResponse } from "../api/types";
import { useLoaded } from "../composables/useLoaded";
import { plural } from "../overview";
import { matchingRows, matchText, seriesOfTarget, shownColumns, targetText } from "../review";
import { useStudyStore } from "../stores/study";
import { sectionRoute, tableFiles } from "../study";
import SourceOverlay from "./SourceOverlay.vue";
import TableGrid from "./TableGrid.vue";

/**
 * What a review item is about: the rows of its table that match its row filters, with its column
 * marked, and for a digitized series the figure overlay with that series emphasized. Nothing
 * shows for the whole study or a file that is no table. The rows link to the Tables section.
 */
const props = defineProps<{ target: ReviewTarget | undefined }>();

const study = useStudyStore();
const router = useRouter();
const headingId = useId();

const file = computed(() => props.target?.file ?? null);
const filters = computed(() => props.target?.rows ?? {});
const filtered = computed(() => Object.keys(filters.value).length > 0);
/** A data table or a raw table of the study, whose rows the local API serves. */
const tableFile = computed(() =>
  file.value !== null && study.detail !== null && tableFiles(study.detail).includes(file.value) ? file.value : null,
);
/** The digitized series of a timecourse or scatter target: a figure with a WebPlotDigitizer project. */
const series = computed(() => {
  const found = seriesOfTarget(props.target);
  const summary = found && study.detail?.sources.find((source) => source.source === found.source);
  return summary?.raw_kind === "digitization" ? found : null;
});

const {
  data: table,
  error: tableError,
  loading: tableLoading,
} = useLoaded<TableResponse>(
  () => tableFile.value,
  (name) => study.table(name),
  () => study.detail,
);
const {
  data: figure,
  error: figureError,
  loading: figureLoading,
} = useLoaded<SourceView>(
  () => series.value?.source ?? null,
  (name) => study.source(name),
  () => study.detail,
);

/** A clicked mapped point of the figure opens its row in the Tables section. */
function showRow(row: { file: string; line: number }): void {
  if (study.detail) void router.push(sectionRoute(study.detail.id, "tables", { file: row.file, line: String(row.line) }));
}

const rows = computed(() => {
  const loaded = table.value?.content;
  if (!loaded || loaded.kind !== "table") return null;
  const matched = matchingRows(loaded.header, loaded.rows, filters.value);
  const column = props.target?.column ?? null;
  const kept = shownColumns(loaded.header, matched, [...Object.keys(filters.value), ...(column ? [column] : [])]);
  // The column of the item comes first, so that it is in view in a wide table.
  const marked = column === null ? -1 : loaded.header.indexOf(column);
  return {
    table: { ...loaded, rows: matched },
    columns: marked < 0 ? kept : [marked, ...kept.filter((index) => index !== marked)],
    column: marked < 0 ? null : column,
    matched: matched.length,
    total: loaded.rows.length,
    hidden: matched.length > 0 && kept.length < loaded.header.length,
  };
});

/** The Tables section at the target, or at its row `line`, with the column of the item. */
function tableRoute(line?: number) {
  const column = rows.value?.column;
  return sectionRoute(study.detail?.id ?? "", "tables", {
    file: tableFile.value ?? "",
    ...(line === undefined ? {} : { line: String(line) }),
    ...(column ? { column } : {}),
  });
}
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
        <p v-else-if="rawTable" class="field-note">
          This is a raw table. <RouterLink :to="tableRoute()">Show in table</RouterLink>
        </p>
        <template v-else-if="rows">
          <p class="target-caption">
            {{ filtered ? matchText(rows.matched, rows.total) : `The table has ${plural(rows.total, "row")}.` }}
            <template v-if="filtered && rows.matched === 0">
              The rows may have changed since the item was written.
            </template>
            <template v-if="rows.hidden">Empty columns are hidden.</template>
            <RouterLink :to="tableRoute(rows.table.rows[0]?.line)" class="target-link">Show in table</RouterLink>
          </p>
          <TableGrid
            v-if="rows.matched"
            :table="rows.table"
            :columns="rows.columns"
            :mark-column="rows.column"
            mark-text="the column of the item"
          >
            <template #line="{ line }">
              <RouterLink
                :to="tableRoute(line)"
                :aria-label="`Show line ${line} of ${tableFile} in the Tables section`"
              >
                {{ line }}
              </RouterLink>
            </template>
          </TableGrid>
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
          @select-row="showRow"
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
.target-link {
  margin-inline-start: 4px;
  white-space: nowrap;
}
</style>
