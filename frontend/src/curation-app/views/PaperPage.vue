<script setup lang="ts">
import { computed, onBeforeUnmount, watchEffect } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { studyPath } from "../api/client";
import PaperViewer from "../components/PaperViewer.vue";
import { PAPER } from "../data";
import { sectionRoute } from "../study";

/**
 * A PDF of a study in a tab of its own, which New tab of the paper pane opens in the same
 * browser session: a slim head with the study, which links to its paper in the Data section,
 * and the name of the file, above the viewer, which fills the rest of the window. The page has
 * no app bar; the status banner still says when the local server stopped.
 */
const route = useRoute();
const identity = computed(() => `${String(route.params.substance)}/${String(route.params.name)}`);
const file = computed(() => String(route.params.file));
const url = computed(() => studyPath(identity.value, "files", file.value));
const back = computed(() => sectionRoute(identity.value, "data", { source: PAPER }));

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
    <PaperViewer :url="url" :file="file" class="paper-page-viewer" />
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
</style>
