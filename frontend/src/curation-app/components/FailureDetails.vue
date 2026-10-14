<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { VBtn } from "vuetify/components";
import { failureFacts, failureMarkdown } from "../failures";
import { type FailureDetails } from "../../study-views/study";
import { useOverviewStore } from "../stores/overview";

/**
 * What the local server said about a failure: a Details disclosure with the request, the status,
 * the code, the type of the error, the request id, the time, the log file and the traceback, and
 * Copy details, which copies it as Markdown for an issue. The default slot adds links after it.
 */
const props = defineProps<{ text: string; details: FailureDetails }>();

const overview = useOverviewStore();
const copied = ref("");
const facts = computed(() =>
  failureFacts(props.details, overview.snapshot?.log_file ?? null),
);

async function copy(): Promise<void> {
  // Empty while it copies, so that the live region announces the same text again.
  copied.value = "";
  await nextTick();
  try {
    await navigator.clipboard.writeText(
      failureMarkdown(props.text, props.details),
    );
    copied.value = "Details copied.";
  } catch {
    copied.value = "The details could not be copied.";
  }
}
</script>

<template>
  <div class="failure-details">
    <details class="failure-disclosure">
      <summary class="failure-summary">Details</summary>
      <dl class="failure-facts">
        <template v-for="fact in facts" :key="fact.name">
          <dt>{{ fact.name }}</dt>
          <dd>{{ fact.value }}</dd>
        </template>
      </dl>
      <!-- At most 10 lines; it scrolls, with the keyboard too. -->
      <pre
        v-if="details.traceback"
        class="failure-traceback"
        tabindex="0"
        aria-label="Traceback"
        >{{ details.traceback.trim() }}</pre>
    </details>
    <div class="failure-actions">
      <VBtn
        variant="text"
        size="small"
        prepend-icon="fas fa-copy"
        class="failure-copy"
        @click="copy"
      >
        Copy details
      </VBtn>
      <slot />
    </div>
    <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
    <span role="status" aria-live="polite" class="failure-copied">{{
      copied
    }}</span>
  </div>
</template>

<style scoped>
.failure-details {
  margin-top: 4px;
  font-size: 0.875rem;
}
.failure-summary {
  width: fit-content;
  cursor: pointer;
}
.failure-facts {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 2px 12px;
  margin: 4px 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.failure-facts dt {
  font-weight: 500;
}
.failure-facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}
/* 10 lines of 1.4em, with the padding and the border of the box: then it scrolls. Long lines
   wrap, so that no horizontal scrollbar covers the last line. */
.failure-traceback {
  box-sizing: border-box;
  max-height: calc(10 * 1.4em + 10px);
  margin: 6px 0 0;
  padding: 4px 6px;
  overflow: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.75rem;
  line-height: 1.4;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
/* The text button keeps its padding outside the content edge, as the actions of the activity. */
.failure-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
  margin: 2px 0 0 -8px;
}
/* Empty, it stays in the page for screen readers but takes no space. */
.failure-copied:empty {
  position: absolute;
}
</style>
