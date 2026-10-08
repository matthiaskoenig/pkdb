<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VDialog,
  VSpacer,
  VTextarea,
} from "vuetify/components";
import type { ValidationIssue } from "../api/types";
import { useReturnFocus, type FocusTarget } from "../composables/useReturnFocus";
import { GROW_ROWS, sizesFieldsByContent } from "../fieldSizing";
import { acknowledgeFailure, acknowledgement, location, locationKey } from "../problems";
import type { ReviewFailure } from "../review";
import { useStudyStore } from "../stores/study";
import UserHint from "./UserHint.vue";

/**
 * Acknowledges a warning with a reason: a resolved review item that names the warning and its
 * location, and covers exactly this warning. The reason stays after Cancel for the same warning,
 * and starts empty for another one.
 */
const props = defineProps<{
  issue: ValidationIssue | null;
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
const open = defineModel<boolean>({ default: false });
/** Whether the acknowledgement is being written; the section waits with its actions meanwhile. */
const busy = defineModel<boolean>("busy", { default: false });
const emit = defineEmits<{ acknowledged: [issue: ValidationIssue] }>();

const study = useStudyStore();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
const autoGrow = !sizesFieldsByContent();

const reason = ref("");
const failure = ref<ReviewFailure | null>(null);

const payload = computed(() => (props.issue ? acknowledgement(props.issue) : null));
const writable = computed(() => study.detail?.review.revision != null && study.detail.review.value !== null);
const canSubmit = computed(() => payload.value !== null && writable.value && !busy.value && reason.value.trim() !== "");

watch(
  () => (props.issue ? locationKey(props.issue) : null),
  () => {
    reason.value = "";
    failure.value = null;
  },
);

watch(open, (value) => {
  if (value) failure.value = null;
});

async function submit(): Promise<void> {
  const issue = props.issue;
  const revision = study.detail?.review.revision;
  if (!issue || !payload.value || !canSubmit.value || revision == null) return;
  busy.value = true;
  failure.value = null;
  try {
    await study.reviewAction(revision, "acknowledge", { ...payload.value, text: reason.value.trim() });
    reason.value = "";
    open.value = false;
    emit("acknowledged", issue);
  } catch (caught) {
    failure.value = acknowledgeFailure(caught);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <!-- While the item is written, the dialog stays open, so that a failure is seen. -->
  <VDialog v-model="open" max-width="640" scrollable :persistent="busy" :aria-labelledby="titleId">
    <VCard v-if="issue" tag="form" @submit.prevent="submit">
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">Acknowledge warning</VCardTitle>
      </VCardItem>
      <VCardText class="acknowledge-body">
        <dl class="panel-facts acknowledge-facts">
          <dt>Code</dt>
          <dd><code class="acknowledge-code">{{ issue.code }}</code></dd>
          <dt>Location</dt>
          <dd>{{ location(issue) }}</dd>
          <dt>Message</dt>
          <dd>{{ issue.message }}</dd>
        </dl>
        <p class="field-note">
          A resolved review item keeps the reason. Dismiss the item to bring the warning back.
        </p>
        <VTextarea
          v-model="reason"
          label="Reason"
          required
          rows="3"
          :auto-grow="autoGrow"
          :max-rows="GROW_ROWS"
          variant="outlined"
          density="compact"
          hint="Required. Say why this warning is expected."
          persistent-hint
          class="grow-textarea"
        />

        <VAlert
          v-if="failure?.kind === 'conflict'"
          type="warning"
          variant="tonal"
          density="compact"
          class="status-alert acknowledge-conflict"
        >
          {{ failure.text }}
        </VAlert>
        <UserHint v-else-if="failure?.kind === 'user'" :text="failure.text" />
        <VAlert
          v-else-if="failure"
          type="error"
          variant="tonal"
          density="compact"
          class="status-alert acknowledge-failure"
        >
          {{ failure.text }}
          <ul v-if="failure.issues.length" class="acknowledge-issues">
            <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
          </ul>
        </VAlert>
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" :disabled="busy" @click="open = false">Cancel</VBtn>
        <VBtn type="submit" variant="flat" color="primary" :disabled="!canSubmit" :loading="busy">Acknowledge</VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.acknowledge-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* A long name breaks only where it does not fit on a line of its own. */
.acknowledge-facts dd {
  line-height: 1.45;
  overflow-wrap: break-word;
}
.acknowledge-code {
  font-size: 0.875rem;
  font-weight: 600;
}
.acknowledge-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
  overflow-wrap: anywhere;
}
</style>
