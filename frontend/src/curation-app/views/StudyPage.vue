<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch, type Component } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from "vue-router";
import {
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VContainer,
  VDialog,
  VProgressLinear,
  VSpacer,
} from "vuetify/components";
import { ApiError, ServerStopped, SessionMissing } from "../../study-views/errors";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import CurationStudyHeader from "../components/CurationStudyHeader.vue";
import SectionTabs from "../components/SectionTabs.vue";
import UnsavedBanner from "../components/UnsavedBanner.vue";
import { useReturnFocus } from "../composables/useReturnFocus";
import { sectionHeading } from "../../study-views/focus";
import { useSaveShortcut } from "../composables/useSaveShortcut";
import { selectedNotesKind, selectionOf } from "../../study-views/data";
import ActivitySection from "../sections/ActivitySection.vue";
import CurationDataSection from "../sections/CurationDataSection.vue";
import CurationProblemsSection from "../sections/CurationProblemsSection.vue";
import CurationReviewSection from "../sections/CurationReviewSection.vue";
import MetadataSection from "../sections/MetadataSection.vue";
import { formatTime } from "../../study-views/overview";
import { curationRoutes } from "../routes";
import { useStudyStore } from "../stores/study";
import {
  defaultSection,
  failureOf,
  isSection,
  SECTION_LABELS,
  sectionCounts,
  type Section,
} from "../../study-views/study";
import { duplicateFolders, duplicateHeading, lastUploadUrl } from "../local";

/**
 * The component of each section. A section gets the open study from the study store; the
 * Metadata and Data sections edit its draft of study.json, whose unsaved fields the tabs mark and
 * the banner under them names.
 */
const SECTION_VIEWS: Record<Section, Component> = {
  metadata: MetadataSection,
  data: CurationDataSection,
  problems: CurationProblemsSection,
  review: CurationReviewSection,
  activity: ActivitySection,
};

const route = useRoute();
const router = useRouter();
const study = useStudyStore();
const headingId = useId();
const leaveId = useId();

const substance = computed(() => String(route.params.substance));
const name = computed(() => String(route.params.name));
const identity = computed(() => `${substance.value}/${name.value}`);
const section = computed<Section | null>(() => (isSection(route.params.section) ? route.params.section : null));

// The store polls the detail of the open study with its ETag until the page closes it.
watch(identity, () => void study.open(substance.value, name.value), { immediate: true });

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
  return failureOf(error, "The study could not be loaded.");
});
const counts = computed(() => (detail.value ? sectionCounts(detail.value) : {}));

/** In Data, the kind of the notes above the selected table, whose fields a refused save marks there; null elsewhere. */
const notesKind = computed(() =>
  section.value === "data" && detail.value ? selectedNotesKind(detail.value, selectionOf(route.query)) : null,
);

/** The facts of the study at the end of the line of tabs: the last upload, with its page on PK-DB. */
const facts = computed<{ text: string; href?: string }[]>(() => {
  const value = detail.value;
  if (!value?.last_upload) return [];
  const href = lastUploadUrl(value);
  return [{ text: `Last upload ${formatTime(value.last_upload.at)}`, ...(href ? { href } : {}) }];
});

// Leaving the study

const leaving = ref(false);
let answer: ((leave: boolean) => void) | null = null;

/** Whether to leave the study: at once without unsaved edits of study.json, otherwise after the dialog answers. */
function confirmLeave(): boolean | Promise<boolean> {
  if (!study.draft.dirty) return true;
  answer?.(false);
  leaving.value = true;
  return new Promise((resolve) => (answer = resolve));
}

/** Leaving closes the study, which forgets its draft. */
function answerLeave(leave: boolean): void {
  const resolve = answer;
  answer = null;
  leaving.value = false;
  resolve?.(leave);
}

// Closing the dialog with Escape or a click outside stays.
watch(leaving, (value) => {
  if (!value && answer) answerLeave(false);
});
useReturnFocus(leaving, sectionHeading);

// Another section of the study keeps the draft; another study or page asks first.
onBeforeRouteLeave(() => confirmLeave());
onBeforeRouteUpdate((to, from) =>
  to.params.substance === from.params.substance && to.params.name === from.params.name ? true : confirmLeave(),
);

/** Closing or reloading the tab with unsaved edits asks through the browser. */
function beforeUnload(event: BeforeUnloadEvent): void {
  if (study.draft.dirty) event.preventDefault();
}

onMounted(() => window.addEventListener("beforeunload", beforeUnload));
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnload);
  answer?.(false);
  study.close();
});

// Ctrl+S (Cmd+S on macOS) saves the draft of study.json from any section; the draft saves only
// what it can: nothing without changes, during a save, or before the Reload of a conflict.
useSaveShortcut(() => void study.draft.save());

// Without a valid section, the page shows the section that the study needs first.
watch(
  [detail, section],
  ([value, current]) => {
    if (value && current === null) void router.replace(curationRoutes.section(identity.value, defaultSection(value)));
  },
  { immediate: true },
);
</script>

<template>
  <VContainer fluid class="study-page" :class="section && `study-page--${section}`">
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
      <RouterLink :to="curationRoutes.overview()" class="study-back">Back to the studies</RouterLink>
    </section>

    <template v-else>
      <!-- The study band: the header of the study and its tabs, set apart from the section below. -->
      <div v-if="detail" class="study-band elevation-1">
        <CurationStudyHeader :detail="detail" :stale="study.error !== null" />
        <SectionTabs
          :substance="substance"
          :name="name"
          :active="section"
          :counts="counts"
          :unsaved="study.draft.unsaved"
          :facts="facts"
        />
      </div>
      <!-- It goes once the study loads again: no close button. It stands below the band, which hangs from the app bar. -->
      <ActionFailureAlert
        v-if="loadError"
        :failure="loadError"
        :study="identity"
        :closable="false"
        class="study-load-failure"
      />
      <template v-if="detail">
        <!-- The draft of study.json, which Metadata and the notes in Data edit: its row stays in
             these two sections, and the others show it once the draft has something to say. -->
        <UnsavedBanner :section="section" :kind="notesKind" />
        <section v-if="section" class="study-section" :aria-labelledby="headingId">
          <!-- It names the section for screen readers, and takes the focus after a dialog of the section when the control that opened it is gone (sectionHeading of focus.ts finds it by its attribute). -->
          <h2 :id="headingId" tabindex="-1" class="d-sr-only" data-study-section-heading>{{ SECTION_LABELS[section] }}</h2>
          <component :is="SECTION_VIEWS[section]" />
        </section>
      </template>
      <div v-else-if="!study.error" class="study-loading">
        <VProgressLinear indeterminate color="primary" aria-label="Loading the study" />
      </div>
    </template>

    <VDialog v-model="leaving" max-width="440" :aria-labelledby="leaveId">
      <VCard>
        <VCardItem class="leave-head">
          <VCardTitle :id="leaveId" tag="h2">Leave without saving?</VCardTitle>
        </VCardItem>
        <VCardText>Your changes to study.json are not saved. Leaving discards them.</VCardText>
        <VCardActions class="dialog-actions">
          <VSpacer />
          <VBtn variant="text" @click="answerLeave(false)">Stay</VBtn>
          <VBtn variant="flat" color="primary" @click="answerLeave(true)">Discard and leave</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </VContainer>
</template>

<style scoped>
/* Little room above the header: the app bar, the header line and the section tabs together take at
   most 110 px, which leaves the rest of the window to the section. */
.study-page {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 2px 16px 8px;
}
/* The study band: the header of the study and its tabs, from edge to edge of the window right
   below the app bar (it takes back the padding of the page), on the primary color at 8 % of the
   surface (the theme color study-band), with a rule and the lightest shadow of Vuetify
   (elevation-1) below it, so that it reads as the header of the section, whose cards are white on
   the grey page. */
.study-band {
  flex: none;
  margin: -2px -16px 0;
  padding: 0 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-study-band));
}
/* A stacking context of its own: nothing that a section raises, such as the sticky header of a
   table, rises above the banner of unsaved changes, which the section scrolls under. */
/* The alert of a study that cannot be loaded again keeps a gap below the band. */
.study-load-failure {
  margin-top: 8px;
}
.study-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  padding-top: 8px;
  isolation: isolate;
}
/* The cards of Metadata take at most 100rem, and the banner of unsaved changes above them ends
   where they end; the other sections and their banner take the whole width. */
.study-page--metadata > .study-section,
.study-page--metadata > :deep(.unsaved-banner) {
  max-width: 100rem;
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
.leave-head {
  padding-bottom: 0;
}
</style>
