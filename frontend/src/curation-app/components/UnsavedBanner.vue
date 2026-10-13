<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { VAlert, VBtn } from "vuetify/components";
import type { TableKind } from "../api/types";
import { saveShortcut } from "../composables/useSaveShortcut";
import { changedLabels, fieldLabel, shortList } from "../metadata";
import { useStudyStore } from "../stores/study";
import type { Section } from "../study";
import { kindLabel } from "../tableKinds";
import ActionFailureAlert from "./ActionFailureAlert.vue";
import UserHint from "./UserHint.vue";

/**
 * The banner of the draft of study.json under the section tabs, in every section of the study
 * page. While the draft has unsaved changes it is amber and names the changed fields, with Undo,
 * Discard and Save; afterwards it shows the outcome of the last save, reload, discard or
 * reference change. It sticks below the app bar while the page scrolls, with square top corners,
 * and publishes where it sticks and its height as `--unsaved-banner-top` and
 * `--unsaved-banner-height`, so that what scrolls into view or sticks stays below it. A
 * refused save lists the issues of the fields that `section` does not show, such as a wrong PMID
 * saved from Data. Ctrl+S (Cmd+S on macOS) saves too (useSaveShortcut).
 */
const props = withDefaults(
  defineProps<{
    /** The section on the screen; null before the route names one. */
    section: Section | null;
    /** In Data, the kind of the notes above the selected table; null for a raw table, none, or another section. */
    kind?: TableKind | null;
  }>(),
  { kind: null },
);

const study = useStudyStore();
const draft = study.draft;
const failure = computed(() => (props.section ? draft.failureIn(props.section, props.kind) : draft.failure));
/**
 * The changed fields by their labels, such as `Source key, Notes of the outputs`. A new
 * study.json whose fields are all still empty has unsaved changes without any changed field.
 */
const fields = computed(() => {
  const detail = study.detail;
  const labels = changedLabels(draft.changed, (kind) => (detail ? kindLabel(detail, kind) : kind));
  return shortList(labels) || "New study.json";
});
const shortcut = saveShortcut();

const root = ref<HTMLElement | null>(null);
/** Whether the banner sticks below the app bar, with the page scrolled under it. */
const stuck = ref(false);
let observer: ResizeObserver | undefined;

/**
 * Sets on the root element where the banner sticks, below the app bar (`--unsaved-banner-top`),
 * and its height (`--unsaved-banner-height`); removes both for a hidden banner.
 */
function publish(element: HTMLElement | null): void {
  const style = document.documentElement.style;
  const height = element ? element.getBoundingClientRect().height : 0;
  if (element && height > 0) {
    style.setProperty("--unsaved-banner-top", getComputedStyle(element).top);
    style.setProperty("--unsaved-banner-height", `${Math.ceil(height)}px`);
  } else {
    style.removeProperty("--unsaved-banner-top");
    style.removeProperty("--unsaved-banner-height");
  }
}

/** Notes whether the page has scrolled the banner up to where it sticks. */
function measureStuck(): void {
  const element = root.value;
  stuck.value =
    element !== null && element.getBoundingClientRect().top <= Number.parseFloat(getComputedStyle(element).top) + 0.5;
}

watch(
  root,
  (element) => {
    observer?.disconnect();
    observer = undefined;
    publish(element);
    measureStuck();
    if (!element) return;
    observer = new ResizeObserver(() => {
      publish(element);
      measureStuck();
    });
    observer.observe(element);
  },
  { flush: "post" },
);

onMounted(() => window.addEventListener("scroll", measureStuck, { passive: true }));
onBeforeUnmount(() => {
  window.removeEventListener("scroll", measureStuck);
  observer?.disconnect();
  publish(null);
});
</script>

<template>
  <!-- A live region stays in the page while it is empty and while the banner is hidden, so that
       screen readers announce its text; the banner shows it. -->
  <span role="status" aria-live="polite" class="unsaved-banner-notice d-sr-only">{{ draft.notice }}</span>
  <div
    v-if="draft.bannerShown && draft.form"
    ref="root"
    class="unsaved-banner"
    :class="{ 'unsaved-banner--dirty': draft.dirty, 'unsaved-banner--stuck': stuck }"
  >
    <div class="unsaved-banner-row">
      <p class="unsaved-banner-text">
        <i v-if="draft.dirty" class="fas fa-circle unsaved-banner-dot" aria-hidden="true"></i>
        <span v-if="draft.dirty"><strong>Unsaved changes</strong> to study.json: {{ fields }}</span>
        <span v-else>{{ draft.notice || "No unsaved changes" }}</span>
      </p>
      <div class="unsaved-banner-actions">
        <VBtn v-if="draft.undoable" variant="text" color="primary" @click="draft.undoDiscard()">Undo</VBtn>
        <VBtn variant="text" :disabled="!draft.dirty || draft.saving" @click="draft.discard()">Discard</VBtn>
        <VBtn
          variant="flat"
          color="primary"
          :disabled="!draft.canSave"
          :loading="draft.saving"
          :aria-keyshortcuts="shortcut.keys"
          @click="draft.save()"
        >
          Save
        </VBtn>
        <kbd class="unsaved-banner-key" aria-hidden="true">{{ shortcut.label }}</kbd>
      </div>
    </div>
    <VAlert
      v-if="draft.referenceError"
      type="warning"
      variant="tonal"
      density="compact"
      closable
      class="status-alert unsaved-banner-reference-error"
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
      class="status-alert unsaved-banner-reloaded"
      @click:close="draft.reloaded = null"
    >
      <p class="unsaved-banner-alert-text">
        Reloaded study.json from disk. Fields that changed there are marked, and your edits are kept.
      </p>
      <p v-if="draft.reloaded.length" class="unsaved-banner-alert-text">
        Changed on both sides, your version is kept: {{ draft.reloaded.map(fieldLabel).join(", ") }}.
      </p>
    </VAlert>
    <VAlert
      v-if="draft.conflict"
      type="warning"
      variant="tonal"
      density="compact"
      class="status-alert unsaved-banner-conflict"
    >
      <div class="unsaved-banner-alert-row">
        <p class="unsaved-banner-alert-text">
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
    <UserHint v-if="draft.noUser" :text="draft.noUser" class="unsaved-banner-failure" />
    <div v-if="failure" class="unsaved-banner-failure">
      <ActionFailureAlert :failure="failure" :study="study.identity" @close="draft.failure = null" />
    </div>
  </div>
</template>

<style scoped>
/* Under the section tabs. It sticks below the app bar while the page scrolls, opaque, since the
   form scrolls under it, and scrolls on its own when its alerts are taller than half the window.
   Amber while study.json has unsaved changes (the theme colors caution and caution-tint), the surface
   otherwise. */
.unsaved-banner {
  position: sticky;
  top: var(--v-layout-top, 0px);
  z-index: 2;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 8px;
  max-height: 50vh;
  margin-top: 8px;
  padding: 6px 8px 6px 14px;
  overflow-y: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
}
.unsaved-banner--dirty {
  border-color: rgb(var(--v-theme-caution));
  background: rgb(var(--v-theme-caution-tint));
}
/* Stuck below the app bar, it hangs from it: square top corners, where nothing shows through. */
.unsaved-banner--stuck {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}
/* What scrolls into view, such as a focused field, stops 8 px below the stuck banner. */
:global(html:has(.unsaved-banner)) {
  scroll-padding-top: calc(var(--unsaved-banner-top, 0px) + var(--unsaved-banner-height, 0px) + 8px);
}
.unsaved-banner-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 12px;
}
.unsaved-banner-text {
  display: flex;
  flex: 1 1 16rem;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin: 0;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.unsaved-banner--dirty .unsaved-banner-text {
  color: rgb(var(--v-theme-caution));
}
.unsaved-banner-dot {
  font-size: 0.5rem;
}
/* Wrapped below the text on a phone, the buttons stay at the end. */
.unsaved-banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-inline-start: auto;
}
.unsaved-banner-key {
  padding: 0 5px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-bottom-width: 2px;
  border-radius: 4px;
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* No keyboard to press it on a touch screen, and no room on a phone. */
@media (hover: none), (max-width: 599.98px) {
  .unsaved-banner-key {
    display: none;
  }
}
.unsaved-banner-alert-text {
  margin: 0;
}
.unsaved-banner-alert-text + .unsaved-banner-alert-text {
  margin-top: 4px;
}
/* The button of an alert follows its text, and goes below it in a narrow banner. */
.unsaved-banner-alert-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.unsaved-banner-alert-row > .unsaved-banner-alert-text {
  flex: 1 1 18rem;
}
@media (max-width: 599.98px) {
  .unsaved-banner {
    padding: 6px 6px 6px 10px;
  }
}
</style>
