<script setup lang="ts">
import type { PaperPlace } from "../../study-views/paper";
import type { PaperFile } from "../../study-views/types";
import ActionFailureAlert from "../../study-views/components/ActionFailureAlert.vue";
import PaperPane from "../../study-views/components/PaperPane.vue";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { useOverviewStore } from "../stores/overview";

/**
 * The paper pane of the curation app: the shared pane (PaperPane.vue) with Open in PDF program in
 * its head, which opens the PDF with the system, and the failure or notice of that action below
 * its head. The props and events are those of the shared pane.
 */
const props = defineProps<{ study: string; papers: PaperFile[]; file: string | null }>();
const emit = defineEmits<{ "update:file": [file: string] }>();
const place = defineModel<PaperPlace | null>("place", { default: null });

const overview = useOverviewStore();
const { notice, announce } = useNotice();
const { busy, failure, run } = useAction<"open">(announce);

function openInProgram(file: string): Promise<void> {
  return run("open", async () => {
    await overview.openFile(props.study, file);
    return `${file} opened in the PDF program.`;
  });
}
</script>

<template>
  <PaperPane v-model:place="place" :study="study" :papers="papers" :file="file" @update:file="emit('update:file', $event)">
    <template #actions="{ file: shown }">
      <button
        type="button"
        class="paper-action"
        aria-label="Open in PDF program"
        title="Open in PDF program"
        :disabled="busy !== null"
        @click="openInProgram(shown)"
      >
        <i class="fas fa-file-export" aria-hidden="true"></i>
        <span class="paper-action-label">Open in PDF program</span>
      </button>
    </template>
    <template #status>
      <ActionFailureAlert v-if="failure" :failure="failure" :study="study" class="paper-pane-failure" @close="failure = null" />
      <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
      <span role="status" aria-live="polite" class="d-sr-only">{{ notice }}</span>
    </template>
  </PaperPane>
</template>
