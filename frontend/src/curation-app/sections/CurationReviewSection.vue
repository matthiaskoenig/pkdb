<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from "vue";
import { VAlert, VBtn } from "vuetify/components";
import type { ReviewItem } from "../../study-views/types";
import type { ItemAction } from "../../study-views/review";
import ActionFailureAlert from "../../study-views/components/ActionFailureAlert.vue";
import NewItemDialog from "../components/NewItemDialog.vue";
import UserHint from "../components/UserHint.vue";
import { useNotice } from "../composables/useNotice";
import { sectionHeading } from "../../study-views/focus";
import { reviewFailure, type ReviewFailure } from "../reviewWrites";
import { useStudyStore } from "../stores/study";
import ReviewSection from "../../study-views/sections/ReviewSection.vue";

/**
 * The Review section of the curation app: the shared section (ReviewSection.vue) with New item,
 * the reply, Resolve, Dismiss and Reopen of the selected item, which write review.json over the
 * revision that the page read, the failure or notice of the last write, and the New item dialog.
 * One write runs at a time; a stale revision reloads the items and asks to repeat the action.
 */
const study = useStudyStore();
const { notice, announce } = useNotice();
const section = useTemplateRef<InstanceType<typeof ReviewSection>>("section");

const review = computed(() => study.detail?.review ?? null);
const approved = computed(() => review.value?.value?.status === "approved");
const writable = computed(() => review.value?.revision != null && review.value.value !== null);

/** The action on an item that runs; one write at a time, so that feedback and revisions never mix. */
const busy = ref<ItemAction | null>(null);
/** Whether the New item dialog writes a new item. */
const adding = ref(false);
/**
 * The failure of the last action; it stays until it is dismissed, the next action starts or
 * another item is selected.
 */
const failure = ref<ReviewFailure | null>(null);
const newItem = ref(false);

watch(
  () => section.value?.selected?.id,
  () => (failure.value = null),
);

const REFUSED: Record<ItemAction, string> = {
  reply: "The reply was not posted.",
  resolve: "The item was not resolved.",
  dismiss: "The item was not dismissed.",
  reopen: "The item was not reopened.",
};

/** What an action did; for an acknowledgement, also what became of its warning. */
function doneText(action: ItemAction, item: ReviewItem): string {
  const code = item.acknowledges;
  switch (action) {
    case "reply":
      return "Reply posted.";
    case "resolve":
      return "Item resolved.";
    case "dismiss":
      return code ? `Item dismissed. Its warning ${code} is no longer acknowledged.` : "Item dismissed.";
    case "reopen":
      return code && item.state === "dismissed"
        ? `Item reopened. It acknowledges ${code} again.`
        : "Item reopened.";
  }
}

async function act(action: ItemAction, item: ReviewItem, text: string): Promise<void> {
  const revision = review.value?.revision;
  if (revision == null || busy.value !== null || adding.value) return;
  busy.value = action;
  failure.value = null;
  announce("");
  try {
    await study.reviewAction(revision, action, { item: item.id, ...(text ? { text } : {}) });
    section.value?.clearDraft(item.id);
    announce(doneText(action, item));
  } catch (caught) {
    failure.value = reviewFailure(caught, REFUSED[action]);
  } finally {
    busy.value = null;
  }
}

function added(item: ReviewItem | null): void {
  failure.value = null;
  if (item) section.value?.select(item.id, { show: true });
  announce("Item added.");
}
</script>

<template>
  <ReviewSection ref="section" :busy="busy" :blocked="adding" @act="act">
    <template #tools>
      <VBtn
        color="primary"
        prepend-icon="fas fa-plus"
        :disabled="!writable || approved || busy !== null"
        class="review-new"
        @click="newItem = true"
      >
        New item
      </VBtn>
    </template>
    <template #detail>
      <VAlert
        v-if="failure?.kind === 'conflict'"
        type="warning"
        variant="tonal"
        density="compact"
        closable
        class="status-alert review-conflict"
        @click:close="failure = null"
      >
        {{ failure.text }}
      </VAlert>
      <UserHint v-else-if="failure?.kind === 'user'" :text="failure.text" />
      <ActionFailureAlert
        v-else-if="failure"
        :failure="failure"
        :study="study.detail?.id ?? null"
        class="review-failure"
        @close="failure = null"
      />
      <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
      <span role="status" aria-live="polite" class="review-notice">{{ notice }}</span>
    </template>
    <template #dialogs>
      <NewItemDialog v-model="newItem" v-model:busy="adding" :fallback-focus="sectionHeading" @added="added" />
    </template>
  </ReviewSection>
</template>

<style scoped>
.review-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.review-notice:empty {
  position: absolute;
}
</style>
