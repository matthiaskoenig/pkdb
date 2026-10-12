<script setup lang="ts">
import { computed } from "vue";
import { VAlert, VBtn } from "vuetify/components";
import type { TableKind } from "../api/types";
import type { DraftSection } from "../composables/useStudyDraft";
import { fieldLabel } from "../metadata";
import { useStudyStore } from "../stores/study";
import ActionFailureAlert from "./ActionFailureAlert.vue";
import UserHint from "./UserHint.vue";

/**
 * The bar of the draft of study.json at the bottom of the Metadata and Data sections: the
 * unsaved changes with Save, Discard and Undo, and the outcome of the last save, reload or
 * reference change. Sticky, it stays in view at the bottom of the window while the section
 * scrolls; in a section that fills the window it ends the section. A refused save lists the
 * issues of the fields that its section does not show, such as a wrong PMID saved from Data.
 */
const props = withDefaults(
  defineProps<{
    section: DraftSection;
    /** In Data, the kind of the notes above the selected table; null for a raw table or none. */
    kind?: TableKind | null;
    sticky?: boolean;
  }>(),
  { kind: null, sticky: true },
);

const study = useStudyStore();
const draft = study.draft;
const failure = computed(() => draft.failureIn(props.section, props.kind));
</script>

<template>
  <!-- A live region stays in the page while it is empty and while the bar is hidden, so that
       screen readers announce its text; the bar shows it. -->
  <span role="status" aria-live="polite" class="savebar-notice d-sr-only">{{ draft.notice }}</span>
  <div v-if="draft.barShown && draft.form" class="study-savebar" :class="{ 'study-savebar--static': !sticky }">
    <VAlert
      v-if="draft.referenceError"
      type="warning"
      variant="tonal"
      density="compact"
      closable
      class="status-alert savebar-reference-error"
      @click:close="draft.referenceError = ''"
    >
      {{ draft.referenceError }}
    </VAlert>
    <VAlert
      v-if="draft.reloaded"
      type="info"
      variant="tonal"
      density="compact"
      closable
      class="status-alert savebar-reloaded"
      @click:close="draft.reloaded = null"
    >
      <p class="savebar-alert-text">
        Reloaded study.json from disk. Fields that changed there are marked, and your edits are kept.
      </p>
      <p v-if="draft.reloaded.length" class="savebar-alert-text">
        Changed on both sides, your version is kept: {{ draft.reloaded.map(fieldLabel).join(", ") }}.
      </p>
    </VAlert>
    <VAlert v-if="draft.conflict" type="warning" variant="tonal" density="compact" class="status-alert savebar-conflict">
      <div class="savebar-alert-row">
        <p class="savebar-alert-text">
          study.json changed on disk after you started editing it.
          {{
            draft.conflict.theirs
              ? "Reload it to keep your edits on top of the new version."
              : "It is not valid JSON now, so it cannot be merged. Fix it in your editor, then save again."
          }}
        </p>
        <VBtn v-if="draft.conflict.theirs" variant="flat" color="primary" size="small" @click="draft.reload()">
          Reload
        </VBtn>
      </div>
    </VAlert>
    <UserHint v-if="draft.noUser" :text="draft.noUser" class="savebar-failure" />
    <div v-if="failure" class="savebar-failure">
      <ActionFailureAlert :failure="failure" :study="study.identity" @close="draft.failure = null" />
    </div>
    <div class="savebar-row">
      <span class="savebar-text">
        <i class="fas fa-circle savebar-dot" aria-hidden="true"></i>
        {{ draft.dirty ? "Unsaved changes in study.json" : draft.notice || "No unsaved changes" }}
      </span>
      <div class="savebar-actions">
        <VBtn v-if="draft.undoable" variant="text" color="primary" @click="draft.undoDiscard()">Undo</VBtn>
        <VBtn variant="text" :disabled="!draft.dirty || draft.saving" @click="draft.discard()">Discard</VBtn>
        <VBtn variant="flat" color="primary" :disabled="!draft.canSave" :loading="draft.saving" @click="draft.save()">
          Save
        </VBtn>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The bar stays in view at the bottom of the window while the section scrolls. */
.study-savebar {
  --savebar-gap: 12px;
  position: sticky;
  bottom: var(--savebar-gap);
  z-index: 2;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px 10px 16px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  /* Above the bar only, where the section scrolls under it; below it is the page. */
  box-shadow: 0 -6px 16px -6px rgba(0, 0, 0, 0.16);
}
/* The page fills the gap below the bar, so that the section scrolls away under the bar rather
   than showing a cut line below it. */
.study-savebar::after {
  content: "";
  position: absolute;
  inset-inline: -1px;
  top: calc(100% + 1px);
  height: var(--savebar-gap);
  background: rgb(var(--v-theme-background));
}
/* In a section that fills the window, nothing scrolls under the bar: it ends the section. */
.study-savebar--static {
  position: relative;
  bottom: auto;
  box-shadow: none;
}
.study-savebar--static::after {
  content: none;
}
.savebar-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
/* Wrapped below the text on a phone, the buttons stay at the end. */
.savebar-actions {
  display: flex;
  gap: 8px;
  margin-inline-start: auto;
}
.savebar-alert-text {
  margin: 0;
}
.savebar-alert-text + .savebar-alert-text {
  margin-top: 4px;
}
/* The button of an alert follows its text, and goes below it in a narrow bar. */
.savebar-alert-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.savebar-alert-row > .savebar-alert-text {
  flex: 1 1 18rem;
}
.savebar-text {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.savebar-dot {
  font-size: 0.5rem;
  color: rgb(var(--v-theme-primary));
}
@media (max-width: 599.98px) {
  .study-savebar {
    --savebar-gap: 8px;
    padding: 8px 8px 8px 12px;
  }
}
</style>
