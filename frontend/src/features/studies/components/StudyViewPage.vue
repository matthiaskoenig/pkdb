<script setup lang="ts">
import "../../../study-views/styles.css";
import { computed, nextTick, useId, useTemplateRef, watch, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VBtn, VDefaultsProvider, VProgressLinear } from "vuetify/components";
import ActionFailureAlert from "../../../study-views/components/ActionFailureAlert.vue";
import MetadataView from "../../../study-views/components/MetadataView.vue";
import SectionTabs from "../../../study-views/components/SectionTabs.vue";
import StudyHeader from "../../../study-views/components/StudyHeader.vue";
import { provideStudyViews } from "../../../study-views/context";
import { COMPACT_DEFAULTS } from "../../../study-views/density";
import DataSection from "../../../study-views/sections/DataSection.vue";
import ProblemsSection from "../../../study-views/sections/ProblemsSection.vue";
import ReviewSection from "../../../study-views/sections/ReviewSection.vue";
import {
  defaultSection,
  failureOf,
  isSection,
  SECTION_LABELS,
  sectionCounts,
  studyName,
  visibleSections,
  type Section,
} from "../../../study-views/study";
import { useSessionStore } from "../../../stores/session";
import { useStudyListStore } from "../../../stores/studyList";
import StudyDetailPage from "../../details/components/StudyDetailPage.vue";
import { returnToSearch } from "../../details/resultPosition";
import {
  AUDIENCE_CAPABILITIES,
  hasSearch,
  searchQuery,
  STORAGE_PREFIX,
  STUDIES_ROUTE,
  studyPageData,
  websiteRoutes,
} from "../context";
import { useWebsiteStudy } from "../useWebsiteStudy";

/**
 * The page of a study format 2 study on the website (#963): the views of the curation app, with
 * Metadata and Data for everyone and Problems and Review for who may write the study, as the
 * backend decides by the session. A study without a stored view shows on the record page
 * (StudyDetailPage), as a study format 1 study does.
 */
const props = defineProps<{ sid: string }>();

/** The views of the sections; Activity has none on the website, which runs no jobs. */
const SECTION_VIEWS: Partial<Record<Section, Component>> = {
  metadata: MetadataView,
  data: DataSection,
  problems: ProblemsSection,
  review: ReviewSection,
};

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const remembered = useStudyListStore();
const headingId = useId();

const { detail: loaded, audience, error, missing, reload } = useWebsiteStudy(() => props.sid);
/** The view of the study of the route; null while it loads. */
const detail = computed(() => (loaded.value?.id === props.sid ? loaded.value : null));
const capabilities = computed(() => AUDIENCE_CAPABILITIES[audience.value ?? "public"]);
const routes = websiteRoutes(route);
provideStudyViews({
  capabilities,
  routes,
  data: studyPageData({ id: () => props.sid, detail, error }),
  parts: { failureDetails: null },
  storagePrefix: STORAGE_PREFIX,
});

const substance = computed(() => props.sid.slice(0, props.sid.indexOf("/")));
const name = computed(() => studyName({ id: props.sid }));
const section = computed<Section | null>(() => (isSection(route.params.section) ? route.params.section : null));
const sections = computed(() => visibleSections(capabilities.value));
const counts = computed(() => (detail.value ? sectionCounts(detail.value) : {}));
const loadFailure = computed(() =>
  error.value !== null && !missing.value ? failureOf(error.value, "The study could not be loaded.") : null,
);

// Without a section, or with one that the reader does not see, the page shows the section that
// the study needs first, keeping the keys of the search.
watch(
  [detail, section, sections],
  ([value, current, visible]) => {
    if (!value || (current !== null && visible.includes(current))) return;
    const first = defaultSection(value);
    void router.replace(routes.section(props.sid, visible.includes(first) ? first : "metadata"));
  },
  { immediate: true },
);

// The identity of the study takes the focus when a study shows, as the heading of the record page does.
const root = useTemplateRef<HTMLElement>("root");
watch(
  () => detail.value?.id ?? null,
  async (id, previous) => {
    if (id === null || id === previous) return;
    await nextTick();
    root.value?.querySelector<HTMLElement>("h1.study-identity")?.focus({ preventScroll: true });
  },
);

// Back to the data search that opened the study, where it was, or to the Studies page as the reader left it.
const fromSearch = computed(() => hasSearch(route.query));
const studies = computed(() => ({ name: STUDIES_ROUTE, query: remembered.query }));
function backToSearch(): void {
  returnToSearch(router, session.epoch, { path: "/data", query: searchQuery(route.query) });
}
</script>

<template>
  <StudyDetailPage v-if="missing" :sid="sid" />
  <div v-else ref="root" class="website-study" :class="section && `website-study--${section}`">
    <VDefaultsProvider :defaults="COMPACT_DEFAULTS">
      <div class="website-study-back">
        <VBtn v-if="fromSearch" variant="text" prepend-icon="fas fa-arrow-left" @click="backToSearch">
          Back to the search
        </VBtn>
        <VBtn v-else variant="text" prepend-icon="fas fa-arrow-left" :to="studies">All studies</VBtn>
      </div>
      <ActionFailureAlert v-if="loadFailure" :failure="loadFailure" :study="sid" :closable="false">
        <template #append>
          <VBtn variant="tonal" color="primary" @click="reload()">Retry</VBtn>
        </template>
      </ActionFailureAlert>
      <template v-if="detail">
        <div class="website-study-head">
          <StudyHeader :detail="detail" />
          <SectionTabs :substance="substance" :name="name" :active="section" :counts="counts" :unsaved="[]" />
        </div>
        <section v-if="section && sections.includes(section)" class="website-study-section" :aria-labelledby="headingId">
          <!-- It names the section for screen readers and takes the focus after a dialog of a section (focus.ts). -->
          <h2 :id="headingId" tabindex="-1" class="d-sr-only" data-study-section-heading>{{ SECTION_LABELS[section] }}</h2>
          <component :is="SECTION_VIEWS[section]" />
        </section>
      </template>
      <div v-else-if="error === null" class="website-study-loading">
        <VProgressLinear indeterminate color="primary" aria-label="Loading the study" />
      </div>
    </VDefaultsProvider>
  </div>
</template>

<style scoped>
.website-study {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.website-study-back {
  display: flex;
}
/* The header and the tabs of the study above a rule, on the page: the study band of the curation app stays there. */
.website-study-head {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.website-study-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  padding-top: 4px;
  isolation: isolate;
}
/* The cards of Metadata take at most 100rem, as in the curation app; the other sections the whole width. */
.website-study--metadata > .website-study-section {
  max-width: 100rem;
}
.website-study-loading {
  max-width: 24rem;
}
</style>
