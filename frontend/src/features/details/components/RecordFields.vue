<script setup lang="ts">
import { computed } from "vue";
import {
  externalUrl,
  isRecord,
  label,
  text,
  type DetailRecord,
} from "../types";
const props = withDefaults(
  defineProps<{ data: DetailRecord; omit?: string[]; depth?: number }>(),
  { omit: () => [], depth: 0 },
);
const entries = computed(() =>
  Object.entries(props.data).filter(([key]) => !props.omit.includes(key)),
);
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
          v-else-if="isRecord(value) && depth < 8"
          :data="value"
          :depth="depth + 1"
        />
        <span v-else>{{ text(value) }}</span>
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
}
</style>
