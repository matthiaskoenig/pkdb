<script setup lang="ts">
import { computed } from "vue";
import { plural } from "../overview";

/**
 * The problems and the open review items of an entry of the navigator of the Data section, each
 * a number after its icon, with its meaning in the title and for screen readers; none for zero.
 * The problems are one number, in the error tone when there is an error, else in the warning tone.
 */
const props = defineProps<{ errors: number; warnings: number; items: number }>();

/** `2 errors, 4 warnings`, `6 warnings`: the problems by severity. */
const problems = computed(() =>
  [
    props.errors ? plural(props.errors, "error") : "",
    props.warnings ? plural(props.warnings, "warning") : "",
  ]
    .filter(Boolean)
    .join(", "),
);
</script>

<template>
  <span
    v-if="errors + warnings"
    class="nav-count"
    :class="errors ? 'nav-count--error' : 'nav-count--warning'"
    :title="problems"
  >
    <i :class="errors ? 'fas fa-circle-exclamation' : 'fas fa-triangle-exclamation'" aria-hidden="true"></i>
    <span class="d-sr-only">{{ problems }}</span>
    <span aria-hidden="true">{{ errors + warnings }}</span>
  </span>
  <span v-if="items" class="nav-count" :title="plural(items, 'open review item')">
    <i class="fas fa-comment" aria-hidden="true"></i>
    <span class="d-sr-only">{{ plural(items, "open review item") }}</span>
    <span aria-hidden="true">{{ items }}</span>
  </span>
</template>

<style scoped>
.nav-count {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex: none;
  font-variant-numeric: tabular-nums;
}
.nav-count > i {
  font-size: 10px;
}
.nav-count--error {
  color: rgb(var(--v-theme-error));
}
/* The amber of the app (themes.ts), as the warnings of the table grid. */
.nav-count--warning {
  color: rgb(var(--v-theme-caution));
}
</style>
