<script setup lang="ts">
import { computed } from "vue";
import { plural } from "../overview";
import { columnLetters } from "../sources";

/**
 * At most this many rows are listed; the Tables section has all of them. A paper table has far
 * fewer; the Tables section virtualizes its grids above the same number of rows.
 */
const LISTED_ROWS = 500;
/** Beyond this many rows, the rows scroll below a header that stays in view. */
const SCROLL_ROWS = 12;

/**
 * The raw extraction of a paper table as printed: every cell as text in its position, spaces
 * included, with the column letters and the lines of the file, as in its workbook sheet. The
 * line column stays in view while wide rows scroll.
 */
const props = defineProps<{
  grid: string[][];
  /** The accessible name of the grid, such as `Raw extraction Example_Tab2.tsv`. */
  label: string;
}>();

const listed = computed(() => props.grid.slice(0, LISTED_ROWS));
const width = computed(() => Math.max(0, ...props.grid.map((row) => row.length)));
const letters = computed(() => Array.from({ length: width.value }, (_, index) => columnLetters(index)));
</script>

<template>
  <div class="raw-grid">
    <p v-if="grid.length > listed.length" class="field-note">
      Showing {{ listed.length.toLocaleString("en-US") }} of {{ plural(grid.length, "row") }}. The Tables section
      has all of them.
    </p>
    <!-- The grid scrolls inside its region, which takes the focus so that a keyboard can scroll it. -->
    <div
      class="rows-scroll rows-scroll--sticky-line"
      :class="{ 'rows-scroll--tall': listed.length > SCROLL_ROWS }"
      tabindex="0"
      role="region"
      :aria-label="label"
    >
      <table class="rows-table rows-table--packed">
        <thead>
          <tr>
            <th scope="col" class="rows-line">Line</th>
            <th v-for="letter in letters" :key="letter" scope="col" class="raw-letter">{{ letter }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in listed" :key="index">
            <th scope="row" class="rows-line">{{ index + 1 }}</th>
            <td v-for="column in width" :key="column" class="raw-cell">{{ row[column - 1] ?? "" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.raw-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
/* Lines between the columns, as in a spreadsheet; the line column has its own. */
.raw-letter + .raw-letter,
.raw-cell + .raw-cell {
  border-inline-start: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.raw-letter {
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Cells keep their spaces as printed. */
.raw-cell {
  white-space: pre;
}
</style>
