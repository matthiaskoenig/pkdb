<script setup lang="ts">
import { computed } from "vue";
import {
  externalUrl,
  isRecord,
  records,
  text,
  type DetailRecord,
} from "../../details/types";

const props = defineProps<{ row: DetailRecord }>();
const measurement = computed(() =>
  isRecord(props.row.measurement_type) ? props.row.measurement_type : {},
);
const units = computed(() =>
  Array.isArray(measurement.value.units) ? measurement.value.units.map(text) : [],
);
function annotationName(item: DetailRecord): string {
  return [item.term ?? item.accession, item.label ?? item.name]
    .filter((value) => typeof value === "string" && value.length)
    .join(" · ");
}
</script>
<template>
  <div class="metadata">
    <div v-if="row.deprecated === true"><strong>Deprecated</strong></div>
    <div v-if="records(row.parents).length">
      <strong>Parents:</strong>
      {{ records(row.parents).map((item) => text(item.name)).join(", ") }}
    </div>
    <div v-if="units.length">
      <strong>Units:</strong> {{ units.join(", ") }}
    </div>
    <div v-if="records(measurement.choices).length">
      <strong>Choices:</strong>
      {{ records(measurement.choices).map((item) => text(item.name)).join(", ") }}
    </div>
    <div
      v-for="(item, index) in [...records(row.annotations), ...records(row.xrefs)]"
      :key="index"
    >
      <span v-if="item.relation" class="relation">{{ text(item.relation) }}: </span>
      <a
        v-if="externalUrl(item.url)"
        :href="externalUrl(item.url)"
        target="_blank"
        rel="noopener noreferrer"
        :title="typeof item.description === 'string' ? item.description : undefined"
      >{{ annotationName(item) || text(item.url) }}</a>
      <span v-else>{{ annotationName(item) || text(item.description) }}</span>
    </div>
  </div>
</template>
<style scoped>
.metadata {
  font-size: 0.75rem;
  overflow-wrap: anywhere;
}
.relation {
  opacity: 0.8;
}
</style>
