<script setup lang="ts">
import { computed, useId } from "vue";
import type { MappedTable } from "../api/types";
import { plural } from "../overview";
import { mappedGrid } from "../sources";
import { sectionRoute } from "../study";
import TableGrid from "./TableGrid.vue";

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
const listed = computed(() => props.tables.map((table) => ({ table, ...mappedGrid(table) })));

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
        <span class="mapped-count">{{ plural(entry.grid.rows.length, "row") }}</span>
      </div>
      <TableGrid v-if="entry.grid.rows.length" :table="entry.grid" :columns="entry.columns">
        <template #line="{ line }">
          <RouterLink
            :to="lineRoute(entry.table.file, line)"
            :aria-label="`Show line ${line} of ${entry.table.file} in the Tables section`"
          >
            {{ line }}
          </RouterLink>
        </template>
      </TableGrid>
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
