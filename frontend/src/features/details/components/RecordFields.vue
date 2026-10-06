<script setup lang="ts">
import { computed } from "vue";
import {
  externalUrl,
  isRecord,
  label,
  text,
  type DetailRecord,
} from "../types";
import { statisticText } from "../../results/format";
const props = withDefaults(
  defineProps<{ data: DetailRecord; omit?: string[]; depth?: number }>(),
  { omit: () => [], depth: 0 },
);
const entries = computed(() =>
  Object.entries(props.data).filter(([key]) => !props.omit.includes(key)),
);
// Statistics are rounded for reading and coefficients of variation shown as
// percent; the record itself is unchanged.
function shown(key: string, value: unknown): string {
  return statisticText(key, value) ?? text(value);
}
function items(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}
</script>
<template>
  <dl class="record-fields">
    <template v-for="[key, value] in entries" :key="key">
      <dt>{{ label(key) }}</dt>
      <dd>
        <a
          v-if="key === 'url' && externalUrl(value)"
          :href="externalUrl(value)"
          target="_blank"
          rel="noopener noreferrer"
          >{{ text(value) }}</a
        >
        <template v-else-if="Array.isArray(value)">
          <span v-if="!value.length">None reported</span>
          <ul v-else>
            <li v-for="(item, index) in items(value)" :key="index">
              <RecordFields
                v-if="isRecord(item) && depth < 8"
                :data="item"
                :depth="depth + 1"
              /><RecordFields
                v-else-if="Array.isArray(item) && depth < 8"
                :data="{ dimensions: item }"
                :depth="depth + 1"
              /><span v-else>{{ text(item) }}</span>
            </li>
          </ul>
        </template>
        <RecordFields
          v-else-if="isRecord(value) && Object.keys(value).length && depth < 8"
          :data="value"
          :depth="depth + 1"
        />
        <span v-else>{{ shown(key, value) }}</span>
      </dd>
    </template>
  </dl>
</template>
<style scoped>
.record-fields {
  display: grid;
  grid-template-columns: minmax(7rem, 1fr) minmax(0, 3fr);
  gap: 0.5rem 1rem;
  margin: 0.5rem 0;
  overflow-wrap: anywhere;
}
dt {
  font-weight: 600;
}
dd {
  margin: 0;
}
ul {
  padding-inline-start: 1rem;
}
li {
  margin-bottom: 0.5rem;
}
@media (max-width: 600px) {
  .record-fields {
    grid-template-columns: 1fr;
  }
  dd {
    margin-bottom: 0.75rem;
  }
  /* In one column, the fields of a nested record are indented under its label. */
  dd > .record-fields {
    margin-block: 0.25rem 0;
    padding-inline-start: 0.75rem;
    border-inline-start: 2px solid
      rgba(var(--v-border-color), var(--v-border-opacity));
  }
}
</style>
