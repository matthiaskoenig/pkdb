<script setup lang="ts">
import { computed, useId } from "vue";
import { useRouter } from "vue-router";
import type { PaperFile } from "../../study-views/types";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { formatBytes, paperRoute, shownPaper, type PaperPlace } from "../../study-views/paper";
import { useOverviewStore } from "../stores/overview";
import ActionFailureAlert from "./ActionFailureAlert.vue";
import PaperViewer from "./PaperViewer.vue";

/**
 * The source pane of the paper in the Data section. Its head names the PDF, offers the other
 * PDFs of the folder in a select, shows the size, and opens the PDF in a tab of its own (New tab)
 * or in the PDF program of the system (Open in PDF program); below it the viewer. The section
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

/** The id of the select of the PDFs, which a browser expects of a form field. */
const fileId = useId();
const router = useRouter();
const overview = useOverviewStore();
const { notice, announce } = useNotice();
const { busy, failure, run } = useAction<"open">(announce);

const paper = computed(() => shownPaper(props.papers, props.file)!);
const tab = computed(() => router.resolve(paperRoute(props.study, paper.value.file)).href);

function choose(event: Event): void {
  emit("update:file", (event.target as HTMLSelectElement).value);
}

function openInProgram(): Promise<void> {
  const file = paper.value.file;
  return run("open", async () => {
    await overview.openFile(props.study, file);
    return `${file} opened in the PDF program.`;
  });
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
        <a class="paper-action" :href="tab" target="_blank" rel="noopener" aria-label="New tab" title="New tab">
          <i class="fas fa-up-right-from-square" aria-hidden="true"></i>
          <span class="paper-action-label">New tab</span>
        </a>
        <button
          type="button"
          class="paper-action"
          aria-label="Open in PDF program"
          title="Open in PDF program"
          :disabled="busy !== null"
          @click="openInProgram"
        >
          <i class="fas fa-file-export" aria-hidden="true"></i>
          <span class="paper-action-label">Open in PDF program</span>
        </button>
      </span>
    </div>
    <ActionFailureAlert v-if="failure" :failure="failure" :study="study" class="paper-pane-failure" @close="failure = null" />
    <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
    <span role="status" aria-live="polite" class="d-sr-only">{{ notice }}</span>
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
  min-width: 4rem;
}
.paper-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 4px;
  margin-inline-start: auto;
}
/* As high as the smallest target of the app, 24 px, inside the 26 px head with its line below. */
.paper-action {
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
.paper-action:hover:not(:disabled) {
  background: rgba(var(--v-theme-primary), 0.08);
}
.paper-action:disabled {
  opacity: var(--v-disabled-opacity);
}
.paper-action:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
/* In a narrow pane the actions show their icons; their names stay in their labels and titles. */
@container (max-width: 440px) {
  .paper-action-label {
    display: none;
  }
}
.paper-pane-failure {
  margin: 8px;
}
.paper-pane-viewer {
  flex: 1 1 0;
}
</style>
