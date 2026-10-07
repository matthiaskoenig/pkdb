<script setup lang="ts">
import { computed, useId } from "vue";
import type { MappedTable } from "../api/types";
import { plural } from "../overview";
import { listedRows } from "../sources";
import { sectionRoute } from "../study";

/** At most this many rows are listed per table; the Tables section has all of them. */
const LISTED_ROWS = 100;
/** Beyond this many rows, the rows scroll below a header that stays in view. */
const SCROLL_ROWS = 12;

/**
 * The rows that tables map from a source, by table, with the line of each row in its file. A
 * line opens the row in the Tables section.
 */
const props = defineProps<{
  tables: MappedTable[];
  /** The identity of the study, for the links to the Tables section. */
  study: string;
}>();

const id = useId();
const listed = computed(() =>
  props.tables.map((table) => ({ table, ...listedRows(table, LISTED_ROWS) })),
);

function lineRoute(file: string, line: number) {
  return sectionRoute(props.study, "tables", { file, line: String(line) });
}
</script>

<template>
  <div class="mapped-rows">
    <section
      v-for="(entry, index) in listed"
      :key="entry.table.file"
      class="mapped-table"
      :aria-labelledby="`${id}-${index}`"
    >
      <div class="mapped-head">
        <h4 :id="`${id}-${index}`" class="mapped-file">{{ entry.table.file }}</h4>
        <span class="mapped-count">{{ plural(entry.total, "row") }}</span>
      </div>
      <p v-if="entry.total > entry.rows.length" class="field-note">
        The first {{ entry.rows.length }} rows are listed. The Tables section has all of them.
      </p>
      <div
        v-if="entry.rows.length"
        class="rows-scroll rows-scroll--fit"
        :class="{ 'rows-scroll--tall': entry.rows.length > SCROLL_ROWS }"
        tabindex="0"
        role="region"
        :aria-label="`Rows of ${entry.table.file}`"
      >
        <table class="rows-table">
          <thead>
            <tr>
              <th scope="col" class="rows-line">Line</th>
              <th v-for="column in entry.columns" :key="column" scope="col">{{ entry.table.header[column] }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in entry.rows" :key="row.line">
              <th scope="row" class="rows-line">
                <RouterLink
                  :to="lineRoute(entry.table.file, row.line)"
                  :aria-label="`Show line ${row.line} of ${entry.table.file} in the Tables section`"
                >
                  {{ row.line }}
                </RouterLink>
              </th>
              <td v-for="column in entry.columns" :key="column">{{ row.cells[column] ?? "" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.mapped-rows {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mapped-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.mapped-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px 12px;
}
.mapped-file {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.mapped-count {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
