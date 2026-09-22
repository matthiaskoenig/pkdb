<script setup lang="ts">
import { computed } from "vue";
import { columns } from "../columns";
import { cellText } from "../cells";
import { label } from "../../../api/contracts";
import type { ApiRecord } from "../../../api/contracts";
import type { ResultTab } from "../../search/model";
import HighlightText from "../../../components/common/HighlightText.vue";
const props = defineProps<{
  tab: ResultTab;
  items: ApiRecord[];
  order: string;
  query: string;
}>();
const emit = defineEmits<{
  order: [order: string];
  detail: [identifier: string | number];
}>();
const headers = computed(() => columns[props.tab]);
function identifier(row: ApiRecord): string | number | undefined {
  const id = props.tab === "studies" ? row.sid : (row.pk ?? row.id ?? row.sid);
  return typeof id === "string" || typeof id === "number" ? id : undefined;
}
function open(row: ApiRecord) {
  const id = identifier(row);
  if (id !== undefined) emit("detail", id);
}
function sort(key: string) {
  emit("order", props.order === key ? `-${key}` : key);
}
</script>
<template>
  <div
    class="table-scroll"
    tabindex="0"
    :aria-label="`${tab} results table, scroll horizontally if needed`"
  >
    <table class="science-table">
      <caption class="sr-only">
        {{
          tab
        }}
        in the applied selection
      </caption>
      <thead>
        <tr>
          <th scope="col">Explore</th>
          <th
            v-for="column in headers"
            :key="column.key"
            scope="col"
            :aria-sort="
              column.order && order.replace(/^-/, '') === column.order
                ? order.startsWith('-')
                  ? 'descending'
                  : 'ascending'
                : undefined
            "
          >
            <button
              v-if="column.order"
              type="button"
              class="sort-button"
              @click="sort(column.order)"
            >
              {{ column.title }}
              <span aria-hidden="true">{{
                order === column.order
                  ? "↑"
                  : order === `-${column.order}`
                    ? "↓"
                    : "↕"
              }}</span></button
            ><template v-else>{{ column.title }}</template>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in items" :key="identifier(row) ?? index">
          <td>
            <button
              type="button"
              class="detail-button"
              :disabled="identifier(row) === undefined"
              :aria-label="`View ${label(row.sid ?? row.name ?? row.pk)}`"
              @click="open(row)"
            >
              View <span aria-hidden="true">↗</span>
            </button>
          </td>
          <td v-for="column in headers" :key="column.key">
            <HighlightText :text="cellText(row, column.key)" :query="query" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
