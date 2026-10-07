<script setup lang="ts">
import { computed, onBeforeUnmount, useId, watch, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VContainer, VProgressLinear } from "vuetify/components";
import { ApiError, ServerStopped, SessionMissing } from "../api/client";
import SectionRail from "../components/SectionRail.vue";
import StudyHeader from "../components/StudyHeader.vue";
import SectionPlaceholder from "../sections/SectionPlaceholder.vue";
import { useStudyStore } from "../stores/study";
import {
  defaultSection,
  duplicateFolders,
  duplicateHeading,
  isSection,
  railCounts,
  SECTION_LABELS,
  type Section,
} from "../study";

/**
 * The component of each section; a section without one shows a placeholder. A section gets the
 * open study from the study store.
 */
const SECTION_VIEWS: Partial<Record<Section, Component>> = {};

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
const counts = computed(() => (detail.value ? railCounts(detail.value) : {}));

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
        <div class="study-body">
          <SectionRail :substance="substance" :name="name" :active="section" :counts="counts" class="study-rail" />
          <section v-if="section" class="study-section" :aria-labelledby="headingId">
            <h2 :id="headingId" class="study-section-heading">{{ SECTION_LABELS[section] }}</h2>
            <component :is="SECTION_VIEWS[section]" v-if="SECTION_VIEWS[section]" />
            <SectionPlaceholder v-else />
          </section>
        </div>
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
  gap: 16px;
  padding: 24px 16px;
}
.study-body {
  display: grid;
  grid-template-columns: 13rem minmax(0, 1fr);
  gap: 24px;
  align-items: start;
  padding-top: 16px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* The rail stays in view below the app bar while a long section scrolls. */
.study-rail {
  position: sticky;
  top: 80px;
}
.study-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
/* As tall as a link of the rail, so that the heading lines up with the first one. */
.study-section-heading {
  display: flex;
  align-items: center;
  min-height: 40px;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.4;
}
@media (max-width: 599.98px) {
  .study-body {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }
  .study-rail {
    position: static;
  }
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
