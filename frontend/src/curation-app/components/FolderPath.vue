<script setup lang="ts">
import { computed } from "vue";
import { pathSegments } from "../paths";

const props = defineProps<{ path: string }>();

const segments = computed(() => pathSegments(props.path));
</script>

<template>
  <!-- A long path wraps only after its separators; folder names keep their hyphens. -->
  <span class="folder-path-text"
    ><template v-for="(segment, index) in segments" :key="index"
      ><wbr v-if="index > 0" /><span class="folder-path-segment">{{ segment }}</span></template
    ></span
  >
</template>

<style scoped>
/* A segment wraps inside only when it is longer than the line on its own. */
.folder-path-segment {
  display: inline-block;
  max-width: 100%;
  overflow-wrap: anywhere;
}
</style>
