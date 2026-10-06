<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { VBtn, VSelect } from "vuetify/components";
import { api, errorMessage } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
import { isRecord, text, type DetailRecord, type Relation } from "../types";
import { formatNumber } from "../../results/format";
import { centralValue } from "../../results/statistics";
import { scheduleText } from "../schedule";
const props = defineProps<{ sid: string }>();
defineEmits<{ open: [relation: Relation] }>();
const session = useSessionStore();
const category = ref("groups");
const categories = [
  { title: "Groups", value: "groups" },
  { title: "Individuals", value: "individuals" },
  { title: "Interventions", value: "interventions" },
  { title: "Measurements", value: "outputs" },
  { title: "Timecourses", value: "timecourses" },
  { title: "Scatters", value: "scatters" },
];
const rows = shallowRef<DetailRecord[]>([]);
const page = ref(1);
const count = ref(0);
const loading = ref(false);
const failure = ref("");
let controller: AbortController | undefined;
let generation = 0;
function relation(row: DetailRecord): Relation | undefined {
  const identifier = row.pk;
  if (typeof identifier !== "number" && typeof identifier !== "string") return;
  return {
    entity: category.value,
    identifier,
    title: text(row.name ?? row.measurement_type ?? identifier),
  };
}
// A quantity that is not reported is left out, not shown as a placeholder.
function quantity(row: DetailRecord): string {
  const value = centralValue(row);
  if (value === undefined || value === null) return "";
  const shown = typeof value === "number" ? formatNumber(value) : text(value);
  return row.unit ? `${shown} ${text(row.unit)}` : shown;
}
function points(row: DetailRecord): string {
  const count = Array.isArray(row.array) ? row.array.length : 0;
  return `${count} ${count === 1 ? "point" : "points"}`;
}
function summary(row: DetailRecord): string {
  if (["timecourses", "scatters"].includes(category.value)) return points(row);
  const schedule =
    category.value === "interventions" ? scheduleText(row) : undefined;
  return [quantity(row), schedule].filter(Boolean).join(" · ");
}
const PAGE_SIZE = 20;
const pages = computed(() => Math.max(1, Math.ceil(count.value / PAGE_SIZE)));
async function load() {
  controller?.abort();
  controller = new AbortController();
  const current = ++generation;
  const epoch = session.epoch;
  rows.value = [];
  failure.value = "";
  loading.value = true;
  const params: Record<string, string | number | boolean> = {
    study_sid: props.sid,
    page: page.value,
    page_size: PAGE_SIZE,
  };
  const entity = ["timecourses", "scatters"].includes(category.value)
    ? "subsets"
    : category.value;
  if (entity === "subsets")
    params.data_type =
      category.value === "timecourses" ? "timecourse" : "scatter";
  if (["outputs", "interventions"].includes(entity)) params.normed = true;
  try {
    const response = await api.get<unknown>(`/api/v1/${entity}/`, {
      params,
      signal: controller.signal,
    });
    if (current !== generation || epoch !== session.epoch) return;
    const value = response.data;
    if (
      !isRecord(value) ||
      !isRecord(value.data) ||
      typeof value.data.count !== "number" ||
      !Array.isArray(value.data.data) ||
      !value.data.data.every(isRecord)
    )
      throw new Error("The study contents response is invalid.");
    rows.value = value.data.data;
    count.value = value.data.count;
  } catch (error) {
    if (current === generation) failure.value = errorMessage(error);
  } finally {
    if (current === generation) loading.value = false;
  }
}
watch(
  [() => props.sid, category, () => session.epoch],
  () => {
    page.value = 1;
    void load();
  },
  { immediate: true },
);
function turn(delta: number) {
  page.value += delta;
  void load();
}
onBeforeUnmount(() => {
  generation++;
  controller?.abort();
});
</script>
<template>
  <section aria-label="Whole-study data">
    <h3>Explore all data from this study</h3>
    <p>
      These records belong to the study and are not restricted by the applied
      search.
    </p>
    <VSelect
      v-model="category"
      :items="categories"
      label="Study data category"
    />
    <p v-if="loading" role="status">Loading study records…</p>
    <div v-else-if="failure" role="alert">
      {{ failure }} <VBtn @click="load">Retry study records</VBtn>
    </div>
    <template v-else>
      <p>
        {{
          count === 0
            ? "No records"
            : `${count} ${count === 1 ? "record" : "records"}`
        }}
      </p>
      <ul class="records">
        <li v-for="(row, index) in rows" :key="text(row.pk) + index">
          <VBtn
            v-if="relation(row)"
            variant="text"
            @click="relation(row) && $emit('open', relation(row)!)"
          >
            {{ text(row.name ?? row.measurement_type ?? row.pk) }} ·
            {{ text(row.pk) }} </VBtn
          ><span
            v-if="
              ['outputs', 'interventions', 'timecourses', 'scatters'].includes(
                category,
              ) && summary(row)
            "
            class="summary"
            >{{ summary(row) }}</span
          >
        </li>
      </ul>
      <div v-if="pages > 1" class="pager">
        <VBtn :disabled="page === 1" @click="turn(-1)">Previous records</VBtn>
        <span>Page {{ page }} of {{ pages }}</span>
        <VBtn :disabled="page >= pages" @click="turn(1)">
          Next records
        </VBtn>
      </div>
    </template>
  </section>
</template>
<style scoped>
.records {
  list-style: none;
  padding: 0;
}
.records li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  column-gap: 0.5rem;
}
/* The record text lines up with the text around the list. */
.records :deep(.v-btn) {
  padding-inline: 0.5rem;
  margin-inline-start: -0.5rem;
  min-width: 0;
}
/* The summary reads like the record button next to it and wraps as a block. */
.summary {
  flex: 1 1 14rem;
  min-width: 0;
  font-size: 0.875rem;
  line-height: 1.4;
}
.pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
</style>
