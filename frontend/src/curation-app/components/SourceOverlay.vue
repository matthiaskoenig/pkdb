<script setup lang="ts">
import { computed } from "vue";
import type { SourceView } from "../api/types";

/**
 * The figure overlay of a source: the raw points and the mapped rows on its image, with the
 * series `highlight` emphasized and the others faded.
 *
 * A placeholder until the Sources section brings the plot: it names the digitization and the
 * emphasized series.
 */
const props = defineProps<{ view: SourceView; highlight?: string | null }>();

const text = computed(() =>
  [
    props.view.digitization ? `Digitized in ${props.view.digitization}.` : "",
    props.highlight ? `Emphasized series: ${props.highlight}.` : "",
  ]
    .filter(Boolean)
    .join(" "),
);
</script>

<template>
  <p class="source-overlay">{{ text }}</p>
</template>

<style scoped>
.source-overlay {
  margin: 0;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
</style>
