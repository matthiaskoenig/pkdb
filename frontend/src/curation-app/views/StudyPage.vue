<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useId, watch, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VContainer, VProgressLinear } from "vuetify/components";
import { ApiError, ServerStopped, SessionMissing } from "../api/client";
import SectionTabs from "../components/SectionTabs.vue";
import StudyHeader from "../components/StudyHeader.vue";
import ActivitySection from "../sections/ActivitySection.vue";
import DataSection from "../sections/DataSection.vue";
import MetadataSection from "../sections/MetadataSection.vue";
import ProblemsSection from "../sections/ProblemsSection.vue";
import ReviewSection from "../sections/ReviewSection.vue";
import { formatTime, MODE_LABELS } from "../overview";
import { useStudyStore } from "../stores/study";
import {
  defaultSection,
  duplicateFolders,
  duplicateHeading,
  isSection,
  lastUploadUrl,
  SECTION_LABELS,
  sectionCounts,
  type Section,
} from "../study";

/**
 * The component of each section. A section gets the open study from the study store, and a
 * section with a form emits `unsaved` with whether it has unsaved changes, which the tabs mark.
 */
const SECTION_VIEWS: Record<Section, Component> = {
  metadata: MetadataSection,
  review: ReviewSection,
  problems: ProblemsSection,
  data: DataSection,
  activity: ActivitySection,
};

const route = useRoute();
const router = useRouter();
const study = useStudyStore();
const headingId = useId();

const substance = computed(() => String(route.params.substance));
const name = computed(() => String(route.params.name));
const identity = computed(() => `${substance.value}/${name.value}`);
const section = computed<Section | null>(() => (isSection(route.params.section) ? route.params.section : null));

// The store polls the detail of the open study with its ETag until the page closes it.
watch(identity, () => void study.open(substance.value, name.value), { immediate: true });
onBeforeUnmount(() => study.close());

/** The detail of the study of the route; null while it loads. */
const detail = computed(() => (study.detail?.id === identity.value ? study.detail : null));

/** A study that the page cannot show: not in the workspace, or the identity of two folders. */
const failure = computed(() => {
  const error = study.error;
  if (!(error instanceof ApiError)) return null;
  if (error.status === 404) return { kind: "missing" as const };
  if (error.status === 409) return { kind: "duplicate" as const, paths: duplicateFolders(error.body) };
  return null;
});
const duplicateAdvice = computed(() =>
  failure.value?.kind === "duplicate" && failure.value.paths.length === 2
    ? `Both folders below are ${identity.value}. Rename one of them to open the study.`
    : `Several folders are ${identity.value}. Rename all but one of them to open the study.`,
);
/** Why the study could not be loaded; the header banner reports a stopped server or a missing session. */
const loadError = computed(() => {
  const error = study.error;
  if (error === null || failure.value || error instanceof ServerStopped || error instanceof SessionMissing) return null;
  return `The study could not be loaded. ${error.message}`;
});
const counts = computed(() => (detail.value ? sectionCounts(detail.value) : {}));

/** The facts of the study at the end of the line of tabs. */
const facts = computed(() => {
  const value = detail.value;
  if (!value) return [];
  const list: { text: string; href?: string }[] = [{ text: `On save: ${MODE_LABELS[value.mode]}` }];
  if (value.last_upload) {
    const href = lastUploadUrl(value);
    list.push({ text: `Last upload ${formatTime(value.last_upload.at)}`, ...(href ? { href } : {}) });
  }
  return list;
});

/** The section on the screen when it has unsaved changes; only that section can have any. */
const unsaved = ref<Section | null>(null);
const unsavedSections = computed(() => (unsaved.value ? [unsaved.value] : []));
watch([section, identity], () => (unsaved.value = null));

function markUnsaved(value: boolean): void {
  unsaved.value = value ? section.value : null;
}

// Without a valid section, the page shows the section that the study needs first.
watch(
  [detail, section],
  ([value, current]) => {
    if (value && current === null)
      void router.replace({
        name: "Study",
        params: { substance: substance.value, name: name.value, section: defaultSection(value) },
      });
  },
  { immediate: true },
);
</script>

<template>
  <VContainer fluid class="study-page">
    <section v-if="failure" class="study-failure">
      <template v-if="failure.kind === 'missing'">
        <h1>This study is not in the workspace</h1>
        <p>There is no study folder {{ identity }} in the workspace. It may have been moved or renamed.</p>
      </template>
      <template v-else>
        <h1>{{ duplicateHeading(failure.paths.length) }}</h1>
        <p>{{ duplicateAdvice }}</p>
        <ul v-if="failure.paths.length" class="study-failure-paths">
          <li v-for="path in failure.paths" :key="path">{{ path }}</li>
        </ul>
      </template>
      <RouterLink to="/" class="study-back">Back to the studies</RouterLink>
    </section>

    <template v-else>
      <VAlert v-if="loadError" type="error" variant="tonal" density="compact" class="status-alert">
        {{ loadError }}
      </VAlert>
      <template v-if="detail">
        <StudyHeader :detail="detail" :stale="study.error !== null" />
        <SectionTabs
          :substance="substance"
          :name="name"
          :active="section"
          :counts="counts"
          :unsaved="unsavedSections"
          :facts="facts"
        />
        <section v-if="section" class="study-section" :aria-labelledby="headingId">
          <!-- It names the section for screen readers, and takes the focus after a dialog of the section when the control that opened it is gone. -->
          <h2 :id="headingId" tabindex="-1" class="d-sr-only">{{ SECTION_LABELS[section] }}</h2>
          <component :is="SECTION_VIEWS[section]" @unsaved="markUnsaved" />
        </section>
      </template>
      <div v-else-if="!study.error" class="study-loading">
        <VProgressLinear indeterminate color="primary" aria-label="Loading the study" />
      </div>
    </template>
  </VContainer>
</template>

<style scoped>
.study-page {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 8px 12px;
}
.study-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  padding-top: 8px;
}
.study-failure {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  max-width: 48rem;
}
.study-failure h1,
.study-failure p {
  margin: 0;
}
.study-failure-paths {
  margin: 0;
  padding-inline-start: 20px;
  overflow-wrap: anywhere;
}
.study-loading {
  max-width: 24rem;
}
</style>
