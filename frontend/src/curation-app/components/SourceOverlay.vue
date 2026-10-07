<script setup lang="ts">
import { computed } from "vue";
import type { SourceView } from "../api/types";

/**
 * The figure overlay of a source: the raw points and the mapped rows on its image, with the
 * series `highlight` emphasized and the others faded.
 *
 * A placeholder until the Sources section brings the plot: it names the source and the series.
 */
const props = defineProps<{ view: SourceView; highlight?: string | null }>();

const series = computed(() => [...new Set(props.view.overlay.map((point) => point.series))]);
</script>

<template>
  <div class="source-overlay">
    <p class="source-overlay-text">
      Figure {{ view.source }}<template v-if="view.digitization">, digitized in {{ view.digitization }}</template>.
    </p>
    <p v-if="highlight" class="source-overlay-text">Emphasized series: {{ highlight }}</p>
    <p v-if="series.length" class="source-overlay-text">Series: {{ series.join(", ") }}</p>
  </div>
</template>

<style scoped>
.source-overlay {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.source-overlay-text {
  margin: 0;
  font-size: 0.875rem;
  overflow-wrap: anywhere;
}
</style>
