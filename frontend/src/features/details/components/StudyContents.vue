<script setup lang="ts">
import { onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { VBtn, VSelect } from "vuetify/components";
import { api, errorMessage } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
import { isRecord, text, type DetailRecord, type Relation } from "../types";
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
    page_size: 20,
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
      <p>{{ count }} records</p>
      <ul>
        <li v-for="(row, index) in rows" :key="text(row.pk) + index">
          <VBtn
            v-if="relation(row)"
            variant="text"
            @click="relation(row) && $emit('open', relation(row)!)"
          >
            {{ text(row.name ?? row.measurement_type ?? row.pk) }} ·
            {{ text(row.pk) }} </VBtn
          ><span v-if="category === 'outputs'"
            >{{ text(row.value ?? row.mean ?? row.median) }}
            {{ text(row.unit) }}</span
          >
        </li>
      </ul>
      <VBtn :disabled="page === 1" @click="turn(-1)">Previous records</VBtn
      ><span>Page {{ page }}</span
      ><VBtn :disabled="page * 20 >= count" @click="turn(1)">
        Next records
      </VBtn>
    </template>
  </section>
</template>
