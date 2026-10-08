<script setup lang="ts">
import { computed, useId } from "vue";
import { useRouter } from "vue-router";
import { VCard, VCardText, VProgressLinear } from "vuetify/components";
import type { ReviewItem, SourceView, StudyDetail, TableResponse } from "../api/types";
import { useLoaded } from "../composables/useLoaded";
import { targetMatch } from "../grid";
import { plural } from "../overview";
import { matchText, rowsAt, shownColumns, targetText } from "../review";
import { useStudyStore } from "../stores/study";
import { beyondLimits, sectionRoute, tableFiles } from "../study";
import SourceOverlay from "./SourceOverlay.vue";
import TableGrid from "./TableGrid.vue";

/**
 * What a review item is about: the rows of its table that match its row filters, with its column
 * marked, and for a digitized series the figure overlay with that series emphasized, as the local
 * server matched its target. Nothing shows for the whole study or a file that is no table. The
 * rows link to the Tables section. Beyond the upload limits a target of a file says that its rows
 * cannot be shown.
 */
const props = defineProps<{ item: ReviewItem }>();

const study = useStudyStore();
const router = useRouter();
const headingId = useId();

const target = computed(() => props.item.target);
const file = computed(() => target.value?.file ?? null);
/** A data table or a raw table of the study, whose rows the local API serves. */
const tableFile = computed(() =>
  file.value !== null && study.detail !== null && tableFiles(study.detail).includes(file.value) ? file.value : null,
);
/** The digitized series of a timecourse or scatter target: a figure with a WebPlotDigitizer project. */
const series = computed(() => targetMatch(study.detail?.targets ?? {}, props.item).series);

const {
  data: table,
  error: tableError,
  loading: tableLoading,
} = useLoaded<TableResponse, StudyDetail | null>(
  () => tableFile.value,
  (name) => study.table(name),
  () => study.detail,
);
/**
 * The lines of the target as the local server matched them for the study page that the rows were
 * loaded for: after a table changed, a newer page can arrive before the rows.
 */
const rowsTargets = computed(() => table.value?.version?.targets ?? {});
const match = computed(() => targetMatch(rowsTargets.value, props.item));
/** Whether a row filter narrows the rows; without one, the target is the whole table. */
const filtered = computed(() => match.value.lines !== null);
/** A new item that the page of the rows does not know yet: its rows come with the next load. */
const pending = computed(
  () =>
    tableError.value === null &&
    !(props.item.id in rowsTargets.value) &&
    props.item.id in (study.detail?.targets ?? {}),
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
  const lines = match.value.lines;
  const matched = lines === null ? loaded.rows : rowsAt(loaded.rows, lines);
  const column = target.value?.column ?? null;
  const filters = Object.keys(target.value?.rows ?? {});
  const kept = shownColumns(loaded.header, matched, [...filters, ...(column ? [column] : [])]);
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
/**
 * Beyond the upload limits the local server lists no tables and matches no target: a target of a
 * file, which may be a table, says why its rows do not show.
 */
const limited = computed(() => file.value !== null && study.detail !== null && beyondLimits(study.detail));
const shown = computed(() => tableFile.value !== null || series.value !== null || limited.value);
</script>

<template>
  <VCard v-if="shown" tag="section" border class="review-target" :aria-labelledby="headingId">
    <VCardText class="target-body">
      <div class="target-head">
        <h3 :id="headingId" class="target-heading">Target</h3>
        <p class="target-text">{{ targetText(target) }}</p>
      </div>

      <p v-if="limited" class="field-note target-limits">
        This study is beyond the upload limits, so the app cannot show the rows of its tables. See
        <RouterLink :to="sectionRoute(study.detail?.id ?? '', 'problems')">Problems</RouterLink>.
      </p>

      <div v-if="tableFile" class="target-block">
        <VProgressLinear
          v-if="tableLoading || pending"
          indeterminate
          color="primary"
          :aria-label="`Loading ${tableFile}`"
        />
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
