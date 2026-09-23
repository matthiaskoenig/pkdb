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
import { api, errorMessage } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
import {
  detailPath,
  isRecord,
  record,
  records,
  relations,
  text,
  type DetailRecord,
} from "../types";
import { useDetailNavigation } from "../useDetailNavigation";
import RecordFields from "./RecordFields.vue";
import AttachmentCard from "./AttachmentCard.vue";
import StudyContents from "./StudyContents.vue";
const ScientificPlot = defineAsyncComponent(
  () => import("../../plots/components/ScientificPlot.vue"),
);
const props = defineProps<{ entity: string; identifier: string | number }>();
defineEmits<{ close: [] }>();
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
async function load() {
  controller?.abort();
  const current = ++generation;
  const epoch = session.epoch;
  controller = new AbortController();
  data.value = undefined;
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
      <section v-if="reference" aria-label="Publication">
        <h3>{{ text(reference.title) }}</h3>
        <p>{{ text(reference.journal) }} · {{ text(reference.date) }}</p>
        <p>{{ text(reference.abstract) }}</p>
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
      <RecordFields :data="data" :omit="['files', 'array', 'reference']" />
      <details v-if="data.array">
        <summary>Complete subset measurements</summary>
        <RecordFields :data="{ measurements: data.array }" />
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
