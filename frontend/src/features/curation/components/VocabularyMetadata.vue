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
function annotationUrl(item: DetailRecord): string | undefined {
  if (typeof item.url !== "string") return undefined;
  let url = item.url;
  if (/\{\$id\}|%7B\$id%7D/i.test(url)) {
    const term = item.term ?? item.accession;
    if (typeof term !== "string" || !term.trim()) return undefined;
    url = url.replace(/\{\$id\}|%7B\$id%7D/gi, (_match, offset: number) => {
      // Older vocabulary exports contain provider templates, sometimes with
      // the ontology prefix already present immediately before the placeholder.
      const prefix = term.includes(":") ? term.slice(0, term.indexOf(":") + 1) : "";
      const preceding = url.slice(0, offset);
      const identifier = prefix && preceding.toLowerCase().endsWith(prefix.toLowerCase())
        ? term.slice(prefix.length)
        : term;
      return encodeURIComponent(identifier);
    });
  }
  return externalUrl(url);
}
function annotationName(item: DetailRecord): string {
  const value = item.term ?? item.accession;
  const term = typeof value === "string" ? value : "";
  const source = item.collection ?? item.name;
  const resource = typeof source === "string" ? source : "";
  const identifier = resource && !term.toLowerCase().startsWith(`${resource.toLowerCase()}:`)
    ? [resource, term].filter(Boolean).join(": ")
    : term;
  return [identifier, item.label]
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
        v-if="annotationUrl(item)"
        :href="annotationUrl(item)"
        target="_blank"
        rel="noopener noreferrer"
        :title="typeof item.description === 'string' ? item.description : undefined"
        class="resource-link"
      >{{ annotationName(item) || text(item.url) }} <span aria-hidden="true">↗</span></a>
      <span v-else>{{ annotationName(item) || text(item.description) }}</span>
    </div>
  </div>
</template>
<style scoped>
.metadata {
  font-size: 0.75rem;
  overflow-wrap: anywhere;
}
.resource-link {
  text-decoration: underline;
  text-underline-offset: 2px;
}
.relation {
  opacity: 0.8;
}
</style>
