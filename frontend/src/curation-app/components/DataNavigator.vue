<script setup lang="ts">
import { computed, useId } from "vue";
import type { SourceSummary, StudyDetail } from "../api/types";
import { fileCounts, sourceCounts } from "../data";
import { plural } from "../overview";
import { rawTableFiles, tableFiles } from "../study";

/**
 * The sources of a study with a thumbnail of their image, and its table files in workbook
 * order, each with its problems and open review items. While a source is selected and its rows
 * are known, a file shows how many rows of the source it has, and files without any are dimmed.
 */
const props = defineProps<{
  detail: StudyDetail;
  source: string | null;
  file: string | null;
  rows: ReadonlyMap<string, number> | null;
}>();
const emit = defineEmits<{ "select-source": [source: string]; "select-file": [file: string] }>();

const ICONS: Record<SourceSummary["kind"], string> = {
  table: "fas fa-table",
  figure: "fas fa-chart-line",
  text: "fas fa-align-left",
};

const sourcesId = useId();
const tablesId = useId();

const counts = computed(() => fileCounts(props.detail));
const raw = computed(() => rawTableFiles(props.detail));
const sources = computed(() =>
  props.detail.sources.map((summary) => ({ summary, counts: sourceCounts(props.detail, summary) })),
);
const files = computed(() =>
  tableFiles(props.detail).map((file) => ({
    file,
    raw: raw.value.has(file),
    problems: counts.value.problems.get(file) ?? 0,
    items: counts.value.items.get(file) ?? 0,
    rows: props.rows?.get(file) ?? null,
    other: props.rows !== null && !props.rows.has(file),
  })),
);
</script>

<template>
  <nav aria-label="Sources and tables" class="data-navigator">
    <h3 :id="sourcesId" class="nav-heading">Sources</h3>
    <ul :aria-labelledby="sourcesId" aria-label="Sources" class="nav-list">
      <li v-for="{ summary, counts: count } in sources" :key="summary.source">
        <button
          type="button"
          class="nav-source"
          :aria-current="summary.source === source ? 'true' : undefined"
          @click="emit('select-source', summary.source)"
        >
          <img v-if="summary.image_url" :src="summary.image_url" alt="" loading="lazy" decoding="async" class="nav-thumb" />
          <span v-else class="nav-thumb nav-thumb--icon" aria-hidden="true"><i :class="ICONS[summary.kind]"></i></span>
          <span class="nav-text">
            <span class="nav-name">{{ summary.source }}</span>
            <span class="nav-kind">{{ summary.kind }}</span>
          </span>
          <span v-if="count.problems" class="nav-count nav-count--problems">
            <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
            <span class="d-sr-only">{{ plural(count.problems, "problem") }}</span>
            <span aria-hidden="true">{{ count.problems }}</span>
          </span>
          <span v-if="count.items" class="nav-count">
            <i class="fas fa-comment" aria-hidden="true"></i>
            <span class="d-sr-only">{{ plural(count.items, "open review item") }}</span>
            <span aria-hidden="true">{{ count.items }}</span>
          </span>
        </button>
      </li>
    </ul>
    <h3 :id="tablesId" class="nav-heading">Tables</h3>
    <ul :aria-labelledby="tablesId" aria-label="Tables" class="nav-list">
      <li v-for="entry in files" :key="entry.file">
        <button
          type="button"
          class="nav-file"
          :class="{ 'nav-file--other': entry.other }"
          :aria-current="entry.file === file ? 'true' : undefined"
          @click="emit('select-file', entry.file)"
        >
          <i :class="entry.raw ? 'fas fa-table-cells' : 'fas fa-table'" aria-hidden="true"></i>
          <span class="nav-name">{{ entry.file }}</span>
          <span v-if="entry.raw" class="d-sr-only">, raw table</span>
          <span v-if="entry.problems" class="nav-count nav-count--problems">
            <span class="d-sr-only">{{ plural(entry.problems, "problem") }}</span>
            <span aria-hidden="true">{{ entry.problems }}</span>
          </span>
          <span v-if="entry.items" class="nav-count">
            <span class="d-sr-only">{{ plural(entry.items, "open review item") }}</span>
            <span aria-hidden="true">{{ entry.items }}</span>
          </span>
          <span v-if="entry.rows !== null" class="nav-rows">
            <span class="d-sr-only">{{ plural(entry.rows, "row") }} of {{ source }}</span>
            <span aria-hidden="true">{{ entry.rows }}</span>
          </span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.data-navigator {
  overflow: auto;
  height: 100%;
  padding: 4px;
  font-size: 12px;
}
.nav-heading {
  margin: 8px 6px 4px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.nav-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.nav-source,
.nav-file {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 6px;
  background: none;
  color: inherit;
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.nav-source {
  display: grid;
  grid-template-columns: 48px 1fr auto auto;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 3px 6px;
}
.nav-file {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
  padding: 0 6px;
}
.nav-source:hover,
.nav-file:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}
.nav-source[aria-current="true"],
.nav-file[aria-current="true"] {
  background: rgba(var(--v-theme-primary), 0.12);
  border-color: rgba(var(--v-theme-primary), 0.35);
}
.nav-source:focus-visible,
.nav-file:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
.nav-thumb {
  width: 48px;
  height: 34px;
  object-fit: cover;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 3px;
  background: #fff;
}
.nav-thumb--icon {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
}
.nav-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.nav-name {
  min-width: 0;
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-kind {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.nav-count {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex: none;
}
.nav-count--problems {
  color: rgb(var(--v-theme-error));
}
.nav-file .nav-name {
  flex: 1 1 auto;
}
/* Dimmed by its color, which keeps a contrast of 4.5:1; an opacity on top of the text color would not. */
.nav-file--other .nav-name {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.nav-rows {
  flex: none;
  margin-inline-start: auto;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
