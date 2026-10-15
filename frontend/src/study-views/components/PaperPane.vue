<script setup lang="ts">
import { computed, useId } from "vue";
import { useRouter } from "vue-router";
import { useStudyViews } from "../context";
import type { PaperFile } from "../types";
import { formatBytes, shownPaper, type PaperPlace } from "../paper";
import PaperViewer from "./PaperViewer.vue";

/**
 * The source pane of the paper in the Data section. Its head names the PDF, offers the other
 * PDFs of the folder in a select, shows the size, opens the PDF in a tab of its own (New tab) and
 * holds what the page puts after it (slot `actions`, the curation app: Open in PDF program); below
 * it what the page says about those actions (slot `status`), then the viewer. The section
 * keeps the pane mounted while other sources show, so that the viewer keeps its page and zoom,
 * and keeps the place of the viewer for when the pane mounts again, as when the panes stack.
 */
const props = defineProps<{
  /** The study `<substance>/<name>`. */
  study: string;
  /** The PDFs of the folder, `<name>.pdf` first; never empty. */
  papers: PaperFile[];
  /** The PDF chosen in the head; null, or one that is gone, shows the first. */
  file: string | null;
}>();
const emit = defineEmits<{ "update:file": [file: string] }>();
/** Where the viewer stands in its PDF, which the section keeps with `v-model:place`. */
const place = defineModel<PaperPlace | null>("place", { default: null });
defineSlots<{ actions?: (props: { file: string }) => unknown; status?: () => unknown }>();

/** The id of the select of the PDFs, which a browser expects of a form field. */
const fileId = useId();
const router = useRouter();
const views = useStudyViews();
const capabilities = views.capabilities;

const paper = computed(() => shownPaper(props.papers, props.file)!);
/** The address of the PDF in a tab of its own; null when the page has no such page. */
const tab = computed(() => {
  const target = views.routes.paper(props.study, paper.value.file);
  return target === null ? null : router.resolve(target).href;
});

function choose(event: Event): void {
  emit("update:file", (event.target as HTMLSelectElement).value);
}
</script>

<template>
  <section class="paper-pane" :aria-label="`Paper ${paper.file}`">
    <div class="pane-head">
      <i class="fas fa-file-pdf" aria-hidden="true"></i>
      <h3 class="pane-head-name">Paper</h3>
      <select
        v-if="papers.length > 1"
        :id="fileId"
        class="pane-head-select paper-file"
        aria-label="PDF of the paper"
        :value="paper.file"
        @change="choose"
      >
        <option v-for="entry in papers" :key="entry.file" :value="entry.file">{{ entry.file }}</option>
      </select>
      <span v-else class="pane-head-part" :title="paper.file">{{ paper.file }}</span>
      <span class="pane-head-part pane-head-part--fixed">{{ formatBytes(paper.bytes) }}</span>
      <span class="paper-actions">
        <a
          v-if="tab"
          class="paper-action"
          :href="tab"
          target="_blank"
          rel="noopener"
          aria-label="New tab"
          title="New tab"
        >
          <i class="fas fa-up-right-from-square" aria-hidden="true"></i>
          <span class="paper-action-label">New tab</span>
        </a>
        <slot v-if="capabilities.edit" name="actions" :file="paper.file" />
      </span>
    </div>
    <slot v-if="capabilities.edit" name="status" />
    <PaperViewer
      v-model:place="place"
      :url="paper.url"
      :file="paper.file"
      :version="paper.version"
      class="paper-pane-viewer"
    />
  </section>
</template>

<style scoped>
.paper-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  container-type: inline-size;
}
/* A long PDF name shortens in the select before the size and the actions do. */
.paper-file {
  flex: 0 1 auto;
  min-width: calc(4 * var(--study-rem, 1rem));
}
.paper-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 4px;
  margin-inline-start: auto;
}
/* As high as the smallest target of the app, 24 px, inside the 26 px head with its line below. */
.paper-action,
:slotted(.paper-action) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 24px;
  padding-inline: 6px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  /* Not the face of a button of the browser, which is grey in both themes. */
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font: inherit;
  text-decoration: none;
}
.paper-action:hover:not(:disabled),
:slotted(.paper-action:hover:not(:disabled)) {
  background: rgba(var(--v-theme-primary), 0.08);
}
.paper-action:disabled,
:slotted(.paper-action:disabled) {
  opacity: var(--v-disabled-opacity);
}
.paper-action:focus-visible,
:slotted(.paper-action:focus-visible) {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
/* In a narrow pane the actions show their icons; their names stay in their labels and titles. */
@container (max-width: 440px) {
  .paper-action-label,
  :slotted(.paper-action-label) {
    display: none;
  }
}
.paper-pane-failure,
:slotted(.paper-pane-failure) {
  margin: 8px;
}
.paper-pane-viewer {
  flex: 1 1 0;
}
</style>
