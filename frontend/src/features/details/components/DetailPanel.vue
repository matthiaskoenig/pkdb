<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  ref,
  shallowRef,
  watch,
} from "vue";
import { VBtn } from "vuetify/components";
import { provenanceText } from "../../../api/provenance";
import { api, errorMessage } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
import {
  detailPath,
  isRecord,
  record,
  records,
  relations,
  subsetPoints,
  text,
  type DetailRecord,
} from "../types";
import { useDetailNavigation } from "../useDetailNavigation";
import RecordFields from "./RecordFields.vue";
import AttachmentCard from "./AttachmentCard.vue";
import StudyContents from "./StudyContents.vue";
import StudyStatus from "./StudyStatus.vue";
import { scheduleText } from "../schedule";
const ScientificPlot = defineAsyncComponent(
  () => import("../../plots/components/ScientificPlot.vue"),
);
const props = defineProps<{ entity: string; identifier: string | number }>();
const emit = defineEmits<{ close: []; loaded: [data: DetailRecord] }>();
const session = useSessionStore();
const { trail, open, back, reset } = useDetailNavigation();
const target = computed(
  () =>
    trail.value.at(-1) ?? {
      entity: props.entity,
      identifier: props.identifier,
    },
);
const data = shallowRef<DetailRecord>();
const loading = ref(false);
const failure = ref("");
const showPlot = ref(false);
const heading = ref<HTMLElement>();
let controller: AbortController | undefined;
let generation = 0;
const related = computed(() => (data.value ? relations(data.value) : []));
const attachments = computed(() =>
  records(data.value?.files).flatMap((file) =>
    typeof file.file === "string" && typeof file.name === "string"
      ? [{ path: file.file, name: file.name }]
      : [],
  ),
);
const kind = computed(() =>
  data.value?.data_type === "timecourse"
    ? "timecourse"
    : data.value?.data_type === "scatter"
      ? "scatter"
      : undefined,
);
const title = computed(() =>
  data.value
    ? text(
        data.value.label ?? data.value.name ?? data.value.sid ?? data.value.pk,
      )
    : `${target.value.entity}: ${target.value.identifier}`,
);
const reference = computed(() =>
  isRecord(data.value?.reference) ? data.value.reference : undefined,
);
// Journal and date, whichever of them the publication has.
const published = computed(() =>
  [reference.value?.journal, reference.value?.publication_date || reference.value?.date]
    .filter((part) => part !== null && part !== undefined && part !== "")
    .map(text)
    .join(" · "),
);
const abstract = computed(() =>
  reference.value?.abstract ? text(reference.value.abstract) : "",
);
const schedule = computed(() =>
  target.value.entity === "interventions"
    ? scheduleText(data.value)
    : undefined,
);
// The schedule, the study status and the data source have their own sections.
const omitted = computed(() => [
  "files",
  "array",
  "reference",
  "provenance",
  "publication_id",
  ...(target.value.entity === "studies"
    ? [
        "sid",
        "pkdb_id",
        "release_date",
        "issue",
        "review_status",
        "open_review_items",
      ]
    : []),
  ...(schedule.value
    ? ["time", "time_end", "interval", "doses", "time_unit"]
    : []),
]);
// The study whose page is open, as the server named it: a PKDB identifier is
// answered with the study it identifies, which must not be loaded twice.
let loadedStudy: { sid: string; epoch: number } | undefined;
async function load() {
  controller?.abort();
  const current = ++generation;
  const epoch = session.epoch;
  controller = new AbortController();
  data.value = undefined;
  loadedStudy = undefined;
  failure.value = "";
  loading.value = true;
  showPlot.value = false;
  try {
    const response = await api.get<unknown>(
      detailPath(target.value.entity, target.value.identifier),
      { signal: controller.signal },
    );
    if (current === generation && epoch === session.epoch) {
      const parsed = record(response.data);
      if (
        typeof parsed.sid !== "string" &&
        typeof parsed.pk !== "number" &&
        typeof parsed.pk !== "string"
      )
        throw new Error(
          "The server returned a detail record without an identifier.",
        );
      data.value = parsed;
      if (target.value.entity === "studies" && typeof parsed.sid === "string")
        loadedStudy = { sid: parsed.sid, epoch };
      if (!trail.value.length) emit("loaded", parsed);
      await nextTick();
      if (current === generation) heading.value?.focus();
    }
  } catch (error) {
    if (current === generation && epoch === session.epoch)
      failure.value = errorMessage(error);
  } finally {
    if (current === generation) loading.value = false;
  }
}
watch(() => [props.entity, props.identifier], reset);
watch(
  [target, () => session.epoch],
  () => {
    const { entity, identifier } = target.value;
    if (
      entity === "studies" &&
      loadedStudy?.sid === identifier &&
      loadedStudy.epoch === session.epoch
    )
      return;
    void load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  generation++;
  controller?.abort();
});
</script>
<template>
  <section
    class="detail-panel"
    aria-label="Record details"
    :aria-busy="loading"
  >
    <header>
      <h2 ref="heading" tabindex="-1">{{ title }}</h2>
      <VBtn v-if="trail.length" variant="outlined" @click="back">
        Back to previous record </VBtn
      ><VBtn variant="text" @click="$emit('close')">Close details</VBtn>
    </header>
    <StudyStatus
      v-if="target.entity === 'studies' && data"
      :study="data"
    />
    <p class="context-note">
      Record details show broader scientific context. Related records and
      whole-study counts may include data outside the applied search.
    </p>
    <p v-if="loading" role="status">Loading details…</p>
    <div v-else-if="failure" role="alert">
      <p>{{ failure }}</p>
      <VBtn @click="load">Retry details</VBtn>
    </div>
    <template v-else-if="data">
      <nav v-if="related.length" aria-label="Related records">
        <VBtn
          v-for="relation in related"
          :key="`${relation.entity}-${relation.identifier}`"
          variant="tonal"
          size="small"
          @click="open(relation)"
        >
          {{ relation.title }}
        </VBtn>
      </nav>
      <section v-if="target.entity === 'studies'" aria-label="Data source">
        <h3>Data source</h3>
        <p>{{ provenanceText(data.provenance) }}</p>
      </section>
      <section v-if="schedule" aria-label="Schedule">
        <h3>Schedule</h3>
        <p>{{ schedule }}</p>
      </section>
      <section v-if="reference" aria-label="Publication">
        <h3>{{ text(reference.title) }}</h3>
        <p v-if="published">{{ published }}</p>
        <p v-if="abstract">{{ abstract }}</p>
        <a
          v-if="
            typeof reference.pmid === 'string' ||
            typeof reference.pmid === 'number'
          "
          :href="`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(reference.pmid)}/`"
          target="_blank"
          rel="noopener noreferrer"
          >Publication on PubMed</a
        >
      </section>
      <section v-if="kind">
        <VBtn v-if="!showPlot" @click="showPlot = true">
          Show
          {{ kind === "timecourse" ? "timecourse" : "scatter" }} plot </VBtn
        ><ScientificPlot v-if="showPlot" :points="data.array" :kind="kind" />
      </section>
      <StudyContents
        v-if="target.entity === 'studies' && typeof data.sid === 'string'"
        :sid="data.sid"
        @open="open"
      />
      <RecordFields :data="data" :omit="omitted" />
      <details v-if="data.array">
        <summary>Complete subset measurements</summary>
        <RecordFields :data="subsetPoints(data.array, kind)" />
      </details>
      <section v-if="reference">
        <h3>Reference details</h3>
        <RecordFields :data="reference" />
      </section>
      <section v-if="Array.isArray(data.files)">
        <h3>Attachments</h3>
        <p v-if="!attachments.length">
          No attachments are available with your current permissions.
        </p>
        <AttachmentCard
          v-for="file in attachments"
          :key="file.path"
          :path="file.path"
          :name="file.name"
        />
      </section>
    </template>
  </section>
</template>
<style scoped>
.detail-panel {
  padding: 1rem;
  min-width: 0;
}
header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}
header h2 {
  flex: 1;
}
/* The heading takes focus when a record opens; it is not a control. */
header h2:focus {
  outline: none;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-block: 1rem;
}
.context-note {
  font-size: 0.9rem;
}
section {
  margin-block: 1rem;
}
</style>
