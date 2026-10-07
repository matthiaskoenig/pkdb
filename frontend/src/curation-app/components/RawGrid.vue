<script setup lang="ts">
import { computed } from "vue";
import { columnLetters } from "../sources";

/** Beyond this many rows, the rows scroll below a header that stays in view. */
const SCROLL_ROWS = 12;

/**
 * The raw extraction of a paper table as printed: every cell as text in its position, with the
 * column letters and the lines of the file, as in its workbook sheet.
 */
const props = defineProps<{
  grid: string[][];
  /** The accessible name of the grid, such as `Raw extraction Example_Tab2.tsv`. */
  label: string;
}>();

const width = computed(() => Math.max(0, ...props.grid.map((row) => row.length)));
const letters = computed(() => Array.from({ length: width.value }, (_, index) => columnLetters(index)));
</script>

<template>
  <!-- The grid scrolls inside its region, which takes the focus so that a keyboard can scroll it. -->
  <div
    class="rows-scroll rows-scroll--fit raw-grid"
    :class="{ 'rows-scroll--tall': grid.length > SCROLL_ROWS }"
    tabindex="0"
    role="region"
    :aria-label="label"
  >
    <table class="rows-table">
      <thead>
        <tr>
          <th scope="col" class="rows-line">Line</th>
          <th v-for="letter in letters" :key="letter" scope="col" class="raw-letter">{{ letter }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in grid" :key="index">
          <th scope="row" class="rows-line">{{ index + 1 }}</th>
          <td v-for="column in width" :key="column" class="raw-cell">{{ row[column - 1] ?? "" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
/* Lines between the columns, as in a spreadsheet. */
.raw-letter,
.raw-cell {
  border-inline-start: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.raw-letter {
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Cells keep the spaces between their words as printed. */
.raw-cell {
  white-space: pre;
}
</style>
