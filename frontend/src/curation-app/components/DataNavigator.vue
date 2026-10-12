<script setup lang="ts">
import { computed, useId } from "vue";
import type { StudyDetail, TableEntry } from "../api/types";
import { fileCounts, sourceCounts, tablesByInfo } from "../data";
import { INFO_HEADINGS, infoStyle } from "../info";
import { plural } from "../overview";
import { SOURCE_ICONS } from "../sources";
import NavigatorCounts from "./NavigatorCounts.vue";

/**
 * The tables of a study first, under the headings of their class of information (Subjects,
 * Interventions, Data, Raw extractions) in the order of the workbook sheets, each with a bar in
 * the color of its class, its problems, its open review items and its rows; then the sources of
 * the study, with a thumbnail of their image.
 */
const props = defineProps<{
  detail: StudyDetail;
  source: string | null;
  file: string | null;
}>();
const emit = defineEmits<{ "select-source": [source: string]; "select-file": [file: string] }>();

const tablesId = useId();
const sourcesId = useId();

const counts = computed(() => fileCounts(props.detail));

/** The name of a table file without `.tsv`. */
function stem(file: string): string {
  return file.endsWith(".tsv") ? file.slice(0, -".tsv".length) : file;
}

function entryOf(table: TableEntry) {
  return {
    file: table.file,
    name: stem(table.file),
    errors: counts.value.problems.get(table.file)?.errors ?? 0,
    warnings: counts.value.problems.get(table.file)?.warnings ?? 0,
    items: counts.value.items.get(table.file) ?? 0,
    rows: table.rows === null ? null : { count: table.rows, text: plural(table.rows, "row") },
  };
}

/** The tables by class of information, without the classes that the study has no tables of. */
const groups = computed(() =>
  tablesByInfo(props.detail).map(({ info, tables }) => ({
    info,
    id: `${tablesId}-${info}`,
    heading: INFO_HEADINGS[info],
    entries: tables.map(entryOf),
  })),
);

const sources = computed(() =>
  props.detail.sources.map((summary) => ({ summary, counts: sourceCounts(props.detail, summary) })),
);
</script>

<template>
  <nav aria-label="Tables and sources" class="data-navigator">
    <h3 :id="tablesId" class="nav-heading">Tables</h3>
    <div v-for="group in groups" :key="group.info" class="nav-group">
      <h4 :id="group.id" class="nav-group-heading">{{ group.heading }}</h4>
      <ul :aria-labelledby="group.id" class="nav-list">
        <li v-for="entry in group.entries" :key="entry.file">
          <button
            type="button"
            class="nav-file"
            :style="infoStyle(group.info)"
            :aria-current="entry.file === file ? 'true' : undefined"
            @click="emit('select-file', entry.file)"
          >
            <span class="nav-bar" aria-hidden="true"></span>
            <!-- The name without .tsv, cut at its end; screen readers read the file name in full. -->
            <span class="nav-name" :title="entry.file" aria-hidden="true">{{ entry.name }}</span>
            <span class="nav-file-name d-sr-only">{{ entry.file }}</span>
            <NavigatorCounts :errors="entry.errors" :warnings="entry.warnings" :items="entry.items" />
            <span v-if="entry.rows" class="nav-rows" :title="entry.rows.text">
              <span class="d-sr-only">{{ entry.rows.text }}</span>
              <span aria-hidden="true">{{ entry.rows.count }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>
    <h3 :id="sourcesId" class="nav-heading">Sources</h3>
    <ul :aria-labelledby="sourcesId" class="nav-list">
      <li v-for="{ summary, counts: count } in sources" :key="summary.source">
        <button
          type="button"
          class="nav-source"
          :aria-current="summary.source === source ? 'true' : undefined"
          @click="emit('select-source', summary.source)"
        >
          <!-- Decoded while it is painted, which works around Chromium 153: with decoding="async"
               it defers the decode of a large image (checker imaging) and paints the thumbnail
               white until then, and in some loads it never decoded some of them, so that
               Walther1983_Tab1 to _Tab3 stayed white for good. -->
          <img v-if="summary.image_url" :src="summary.image_url" alt="" loading="lazy" class="nav-thumb" />
          <span v-else class="nav-thumb nav-thumb--icon" aria-hidden="true"><i :class="SOURCE_ICONS[summary.kind]"></i></span>
          <span class="nav-text">
            <span class="nav-name" :title="summary.source">{{ summary.source }}</span>
            <span class="nav-kind">{{ summary.kind }}</span>
          </span>
          <NavigatorCounts :errors="count.errors" :warnings="count.warnings" :items="count.items" />
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
/* The headings, the bars of the tables and the thumbnails of the sources share one left edge. */
.nav-heading {
  margin: 8px 5px 4px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.nav-group-heading {
  margin: 6px 5px 2px;
  font-size: 11px;
  font-weight: 600;
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
/* 40 px: the 34 px thumbnail, 2 px above and below it, and the border. */
.nav-source {
  display: grid;
  grid-template-columns: 48px 1fr auto auto;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 2px 6px 2px 4px;
}
/* As high as the smallest target of the app, 24 px. */
.nav-file {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 24px;
  padding: 0 6px 0 4px;
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
/* The class of information of a table: a bar of 4 px in its color, 3:1 on the surface. */
.nav-bar {
  flex: none;
  align-self: stretch;
  width: 4px;
  margin-block: 4px;
  border-radius: 2px;
  background: rgb(var(--info));
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
.nav-file .nav-name {
  flex: 1 1 auto;
}
/* The rows of a table: a muted number on a tinted pill, apart from the counts with their icons. Up
   to 99 rows the pill has one width, so that the pills and the badges before them line up: two
   digits, the padding, and a pixel for digits that a font draws a fraction wider than its 0. A
   longer count makes it wider. */
.nav-rows {
  flex: none;
  min-width: calc(2ch + 11px);
  padding: 0 5px;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.07);
  font-size: 11px;
  line-height: 16px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
