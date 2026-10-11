<script setup lang="ts">
import { plural } from "../overview";

/**
 * The problems and the open review items of an entry of the navigator of the Data section, each
 * a number after its icon, with its meaning in the title and for screen readers; none for zero.
 */
defineProps<{ problems: number; items: number }>();
</script>

<template>
  <span v-if="problems" class="nav-count nav-count--problems" :title="plural(problems, 'problem')">
    <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
    <span class="d-sr-only">{{ plural(problems, "problem") }}</span>
    <span aria-hidden="true">{{ problems }}</span>
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
.nav-count--problems {
  color: rgb(var(--v-theme-error));
}
</style>
