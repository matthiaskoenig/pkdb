<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch, watchEffect } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { VProgressLinear } from "vuetify/components";
import { ApiError, ServerStopped, SessionMissing } from "../../study-views/errors";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import PaperViewer from "../components/PaperViewer.vue";
import { PAPER } from "../../study-views/data";
import { curationRoutes } from "../routes";
import { useStudyStore } from "../stores/study";
import { actionFailure, failureOf, type ActionFailure } from "../../study-views/study";

/**
 * A PDF of a study in a tab of its own, which New tab of the paper pane opens in the same
 * browser session: a slim head with the study, which links to its paper in the Data section,
 * and the name of the file, above the viewer, which fills the rest of the window. The page has
 * no app bar; the status banner still says when the local server stopped.
 *
 * The page polls the study page as the study page does: the file of the address shows only when
 * it is a PDF of the study, and the viewer opens it again when it changes on disk. A file that is
 * no PDF of the study, or one that went from the folder, shows an alert instead.
 */
const route = useRoute();
const study = useStudyStore();
const substance = computed(() => String(route.params.substance));
const name = computed(() => String(route.params.name));
const identity = computed(() => `${substance.value}/${name.value}`);
const file = computed(() => String(route.params.file));
/** The paper of the study in the Data section, showing this PDF. */
const back = computed(() => curationRoutes.section(identity.value, "data", { source: PAPER, pdf: file.value }));

watch(identity, () => void study.open(substance.value, name.value), { immediate: true });
onBeforeUnmount(() => study.close());

/** The study page of the study of the address; null while it loads. */
const detail = computed(() => (study.detail?.id === identity.value ? study.detail : null));
/** The PDF of the address among the PDFs of the study; null for a file that is none of them. */
const paper = computed(() => detail.value?.papers.find((entry) => entry.file === file.value) ?? null);
/** Whether the page has shown the PDF of the address, which can go from the folder and come back. */
const shown = ref(false);
watch(file, () => (shown.value = false));
watch(paper, (value) => {
  if (value) shown.value = true;
});

/** Why the page shows no PDF: the study or the file is not there. */
const failure = computed<ActionFailure | null>(() => {
  const value = detail.value;
  if (value)
    return paper.value
      ? null
      : actionFailure(
          shown.value ? `${file.value} is no longer in the study folder.` : `${file.value} is not a PDF of this study.`,
        );
  const error = study.error;
  // The status banner says when the local server stopped or the session was lost.
  if (error === null || error instanceof ServerStopped || error instanceof SessionMissing) return null;
  if (error instanceof ApiError && error.status === 404)
    return actionFailure(`There is no study folder ${identity.value} in the workspace. It may have been moved or renamed.`);
  return failureOf(error, "The study could not be loaded.");
});

// The tab says which PDF it shows; the app gets its title back when the page closes.
const title = document.title;
watchEffect(() => {
  document.title = `${file.value} · ${identity.value} · PK-DB`;
});
onBeforeUnmount(() => {
  document.title = title;
});
</script>

<template>
  <div class="paper-page">
    <header class="paper-page-head">
      <RouterLink :to="back" class="paper-page-study">{{ identity }}</RouterLink>
      <span class="paper-page-separator" aria-hidden="true">/</span>
      <h1 class="paper-page-file" :title="file">{{ file }}</h1>
    </header>
    <PaperViewer v-if="paper" :url="paper.url" :file="file" :version="paper.version" class="paper-page-viewer" />
    <!-- It goes when the PDF is there: no close button. -->
    <ActionFailureAlert v-else-if="failure" :failure="failure" :study="identity" :closable="false" class="paper-page-failure" />
    <VProgressLinear v-else indeterminate color="primary" aria-label="Loading the study" />
  </div>
</template>

<style scoped>
/* The page fills the window below a status banner and does not scroll; the pages scroll in the viewer. */
:global(.v-application__wrap:has(.paper-page)) {
  height: 100dvh;
}
:global(.v-main:has(.paper-page)) {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
}
.paper-page {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
}
.paper-page-head {
  display: flex;
  flex: 0 0 auto;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
  padding: 6px 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
}
.paper-page-study {
  flex: 0 0 auto;
  font-size: 13px;
}
.paper-page-separator {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.paper-page-file {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  font-size: 15px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.paper-page-viewer {
  flex: 1 1 0;
}
.paper-page-failure {
  margin: 12px;
}
</style>
