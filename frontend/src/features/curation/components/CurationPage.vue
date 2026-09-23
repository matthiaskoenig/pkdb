<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, watch } from "vue";
import { VBtn, VSelect, VTextField } from "vuetify/components";
import { api, errorMessage } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
import { isRecord, text, type DetailRecord } from "../../details/types";
import DetailPanel from "../../details/components/DetailPanel.vue";
import VocabularyHighlight from "./VocabularyHighlight.vue";
import VocabularyMetadata from "./VocabularyMetadata.vue";

const session = useSessionStore();
const draft = ref("");
const search = ref("");
const category = ref("all");
const page = ref(1);
const count = ref(0);
const rows = shallowRef<DetailRecord[]>([]);
const loading = ref(false);
const failure = ref("");
const selected = ref<string>();
let controller: AbortController | undefined;
let generation = 0;
let searchTimer: ReturnType<typeof setTimeout> | undefined;
const copyStatus = ref("");
const pages = computed(() => Math.max(1, Math.ceil(count.value / 20)));
const categories = [
  "all",
  "substance",
  "measurement_type",
  "choice",
  "tissue",
  "method",
  "route",
  "form",
  "application",
];
async function load() {
  controller?.abort();
  controller = new AbortController();
  const current = ++generation;
  const epoch = session.epoch;
  loading.value = true;
  failure.value = "";
  rows.value = [];
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: 20,
      ordering: "name",
      search: search.value,
    };
    if (category.value !== "all") params.ntype = category.value;
    const response = await api.get<unknown>("/api/v1/info_nodes/", {
      params,
      signal: controller.signal,
    });
    if (current !== generation || epoch !== session.epoch) return;
    const envelope = response.data;
    if (
      !isRecord(envelope) ||
      !isRecord(envelope.data) ||
      typeof envelope.data.count !== "number" ||
      !Array.isArray(envelope.data.data) ||
      !envelope.data.data.every(
        (item: unknown) => isRecord(item) && typeof item.sid === "string",
      )
    )
      throw new Error("The vocabulary response is invalid.");
    count.value = envelope.data.count;
    rows.value = envelope.data.data.filter(isRecord);
  } catch (error) {
    if (current === generation) failure.value = errorMessage(error);
  } finally {
    if (current === generation) loading.value = false;
  }
}
function submit() {
  clearTimeout(searchTimer);
  page.value = 1;
  search.value = draft.value;
  void load();
}
function changePage(value: number) {
  page.value = value;
  void load();
}
watch(draft, () => {
  clearTimeout(searchTimer);
  controller?.abort();
  generation++;
  loading.value = false;
  searchTimer = setTimeout(submit, 250);
});
watch(category, submit);
async function copyName(name: string) {
  try {
    await navigator.clipboard.writeText(name);
    copyStatus.value = `Copied ${name}`;
  } catch {
    copyStatus.value = `Could not copy. Select and copy the name manually: ${name}`;
  }
}
watch(
  () => session.epoch,
  () => {
    selected.value = undefined;
    void load();
  },
);
void load();
onBeforeUnmount(() => {
  generation++;
  clearTimeout(searchTimer);
  controller?.abort();
});
</script>
<template>
  <section class="curation-page">
    <h1>Vocabulary and curation</h1>
    <p>
      Explore the controlled terminology used to describe studies, substances,
      measurements and subject characteristics.
    </p>
    <p>
      <a
        href="https://github.com/matthiaskoenig/pkdb_data/blob/develop/CURATION.md"
        target="_blank"
        rel="noopener noreferrer"
        >Study curation guidelines</a
      >
    </p>
    <form @submit.prevent="submit">
      <VTextField
        v-model="draft"
        label="Search vocabulary"
        density="compact"
        hide-details
      /><VSelect
        v-model="category"
        :items="categories"
        label="Vocabulary category"
        density="compact"
        hide-details
      /><VBtn type="submit" :disabled="loading">Search vocabulary</VBtn>
    </form>
    <p class="copy-status" role="status" aria-live="polite">{{ copyStatus }}</p>
    <p v-if="loading" role="status">Loading vocabulary…</p>
    <div v-else-if="failure" role="alert">
      <p>{{ failure }}</p>
      <VBtn @click="load">Retry vocabulary</VBtn>
    </div>
    <template v-else>
      <p role="status">{{ count }} vocabulary terms</p>
      <div class="table-scroll">
        <table>
          <caption>
            Vocabulary terms ordered by name
          </caption>
          <colgroup>
            <col style="width: 18%" />
            <col style="width: 12%" />
            <col style="width: 30%" />
            <col style="width: 15%" />
            <col style="width: 25%" />
          </colgroup>
          <thead>
            <tr>
              <th>Name / label</th>
              <th>Type</th>
              <th>Description</th>
              <th>Synonyms</th>
              <th>Metadata / annotations</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="text(row.sid)">
              <th scope="row">
                <button
                  type="button"
                  class="copy-name"
                  :aria-label="`Copy name ${text(row.name)}`"
                  title="Copy curation name"
                  @click="copyName(text(row.name))"
                >
                  <VocabularyHighlight :value="text(row.name)" :query="search" />
                  <span aria-hidden="true" class="copy-icon"> ⧉</span>
                </button>
                <div v-if="row.label && row.label !== row.name" class="term-label">
                  {{ text(row.label) }}
                </div>
                <button
                  type="button"
                  class="term details-link"
                  :aria-label="`Details for ${text(row.name)}`"
                  @click="selected = text(row.sid)"
                >Details</button>
              </th>
              <td>{{ text(row.ntype) }}<br />{{ text(row.dtype) }}</td>
              <td>
                <VocabularyHighlight
                  :value="text(row.description)"
                  :query="search"
                />
              </td>
              <td>
                {{
                  Array.isArray(row.synonyms)
                    ? row.synonyms.map(text).join(", ")
                    : "None reported"
                }}
              </td>
              <td><VocabularyMetadata :row="row" /></td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="5">No matching terminology.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav aria-label="Vocabulary pages">
        <VBtn :disabled="page <= 1" @click="changePage(page - 1)">Previous</VBtn
        ><span>Page {{ page }} of {{ pages }}</span
        ><VBtn :disabled="page >= pages" @click="changePage(page + 1)">
          Next
        </VBtn>
      </nav>
    </template>
    <DetailPanel
      v-if="selected"
      entity="info_nodes"
      :identifier="selected"
      @close="selected = undefined"
    />
  </section>
</template>
<style scoped>
.curation-page {
  max-width: 90rem;
  margin: auto;
  padding: 1rem;
}
form {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
}
form > * {
  min-width: 12rem;
}
.table-scroll {
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  width: 100%;
  min-width: 54rem;
  font-size: 0.8125rem;
  line-height: 1.4;
}
th,
td {
  text-align: left;
  vertical-align: top;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid currentColor;
}
nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin: 1rem;
}
.term {
  text-decoration: underline;
  color: rgb(var(--v-theme-primary));
  text-align: left;
}
.copy-name {
  color: rgb(var(--v-theme-primary));
  font-family: monospace;
  font-size: 0.8125rem;
  text-align: left;
  overflow-wrap: anywhere;
  user-select: text;
}
.copy-name, .details-link {
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
  min-height: 1.5rem;
}
.copy-name:hover {
  text-decoration: underline;
}
.copy-icon, .term-label, .details-link {
  font-size: 0.75rem;
}
.details-link {
  display: block;
}
.term-label {
  font-weight: normal;
}
.copy-status {
  font-size: 0.8125rem;
  margin: 0.5rem 0;
}
.curation-page > p {
  font-size: 0.875rem;
}
h1 {
  font-size: 1.75rem;
}
th:first-child {
  min-width: 10rem;
}
@media (max-width: 600px) {
  .curation-page { padding: 0; }
}
</style>
