<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { VAlert, VBtn } from "vuetify/components";
import type { TableKind } from "../api/types";
import { sectionHeading } from "../composables/useReturnFocus";
import { saveShortcut } from "../composables/useSaveShortcut";
import { changedLabels, fieldLabel, shortList } from "../metadata";
import { useStudyStore } from "../stores/study";
import type { Section } from "../study";
import { kindLabel } from "../tableKinds";
import ActionFailureAlert from "./ActionFailureAlert.vue";
import UserHint from "./UserHint.vue";

/**
 * The banner of the draft of study.json under the section tabs of the study page. Metadata and
 * Data, which edit study.json, keep its row at the same height in every state, so that nothing
 * moves when an edit starts or a notice ends: without unsaved changes it says so in a neutral
 * surface, with them it uses the caution color (amber) and names the changed fields, with Discard
 * and Save, and without them again it shows the notice of the last action for a few seconds, such
 * as `study.json saved.`, after a discard with Undo. The other sections show it from their
 * opening while study.json has unsaved changes, which were made in another section, or a notice
 * or an alert, and keep it until the curator leaves the section: a save there leaves it neutral
 * rather than taking it away. It never goes on a timer. It sticks below the app bar
 * while the page scrolls, with square top corners, and publishes where it sticks and its height
 * as `--unsaved-banner-top` and `--unsaved-banner-height`, so that what scrolls into view or
 * sticks stays below it. A refused save lists the issues of the fields that `section` does not
 * show, such as a wrong PMID saved from Data. Ctrl+S (Cmd+S on macOS) saves too (useSaveShortcut).
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
const textId = useId();
/** Whether the draft has something to say: unsaved changes, a notice, Undo of a discard, or an alert. */
const pending = computed(
  () =>
    draft.dirty ||
    draft.notice !== "" ||
    draft.undoable ||
    draft.failure !== null ||
    draft.noUser !== null ||
    draft.conflict !== null ||
    draft.reloaded !== null ||
    draft.referenceError !== "",
);
/**
 * In the sections that do not edit study.json, whether the banner shows: from the opening of the
 * section or the study while the draft has something to say, until the curator leaves it; neutral
 * after a save and on no timer, so that nothing moves below it later.
 */
const kept = ref(false);
watch(
  [() => props.section, () => study.identity],
  () => {
    kept.value = pending.value;
  },
  { immediate: true, flush: "sync" },
);
watch(
  pending,
  (value) => {
    if (value) kept.value = true;
  },
  { flush: "sync" },
);
/**
 * Whether the banner is on the page: always in the sections that edit study.json, elsewhere once
 * the draft has something to say there (`kept`).
 */
const shown = computed(
  () => draft.form !== null && (props.section === "metadata" || props.section === "data" || kept.value),
);
/**
 * Whether the banner sticks below the app bar while the page scrolls: while it has something to
 * say. Without, it stays in its place in the page and covers nothing.
 */
const sticky = computed(() => pending.value);
/** Whether no button has anything to act on: they keep their room, hidden, and the text stands alone. */
const idle = computed(() => !draft.dirty && !draft.undoable);
const failure = computed(() => (props.section ? draft.failureIn(props.section, props.kind) : draft.failure));
/** The changed fields by their labels, such as `Source key, Notes of the outputs`. */
const labels = computed(() => {
  const detail = study.detail;
  return changedLabels(draft.changed, (kind) => (detail ? kindLabel(detail, kind) : kind));
});
/** How many changed fields the banner names: three, fewer where they would not fit into its lines. */
const named = ref(3);
/**
 * The changed fields as the banner names them, such as `Source key, Licence and 2 more`. A new
 * study.json whose fields are all still empty has unsaved changes without any changed field.
 */
const fields = computed(() => shortList(labels.value, named.value) || "new file, not written yet");
const shortcut = saveShortcut();

const root = ref<HTMLElement | null>(null);
/** The box of the text, as wide as its lines, in which `measure` tries the names. */
const lines = ref<HTMLElement | null>(null);
const measure = ref<HTMLElement | null>(null);
/** Whether the banner sticks below the app bar, with the page scrolled under it. */
const stuck = ref(false);
let observer: ResizeObserver | undefined;

/**
 * Names as many changed fields, at most three, as fit into the lines of the text, one beside the
 * buttons and two on a phone (`--unsaved-banner-lines`), so that the banner keeps its height; one
 * at least, whose end the last line cuts off where even that does not fit.
 */
function fit(): void {
  const box = measure.value;
  const style = box ? getComputedStyle(box) : null;
  const lineHeight = style ? Number.parseFloat(style.lineHeight) : Number.NaN;
  // A single name has nothing to leave out.
  if (!box || !style || !Number.isFinite(lineHeight) || labels.value.length < 2) {
    named.value = 3;
    return;
  }
  const limit = (Number.parseInt(style.getPropertyValue("--unsaved-banner-lines")) || 1) * lineHeight + 0.5;
  let count = 3;
  for (; count > 1; count -= 1) {
    const prefix = Object.assign(document.createElement("strong"), { textContent: "Unsaved changes" });
    box.replaceChildren(prefix, ` to study.json: ${shortList(labels.value, count)}`);
    if (box.getBoundingClientRect().height <= limit) break;
  }
  box.replaceChildren();
  named.value = count;
}

/**
 * Sets on the root element the room that the banner takes in the page (`--unsaved-banner-space`)
 * and, while it sticks, where it sticks below the app bar (`--unsaved-banner-top`) and its height
 * (`--unsaved-banner-height`), which it covers of the page scrolled under it; removes them for a
 * hidden banner (null).
 */
function publish(element: HTMLElement | null = root.value): void {
  const style = document.documentElement.style;
  const height = element ? Math.ceil(element.getBoundingClientRect().height) : 0;
  const set = (name: string, value: string | null) =>
    value === null ? style.removeProperty(name) : style.setProperty(name, value);
  set("--unsaved-banner-space", element && height > 0 ? `${height}px` : null);
  const covers = element && height > 0 && sticky.value;
  set("--unsaved-banner-top", covers ? getComputedStyle(element).top : null);
  set("--unsaved-banner-height", covers ? `${height}px` : null);
}

/** Notes whether the page has scrolled the sticky banner up to where it sticks. */
function measureStuck(): void {
  const element = root.value;
  stuck.value =
    element !== null &&
    sticky.value &&
    element.getBoundingClientRect().top <= Number.parseFloat(getComputedStyle(element).top) + 0.5;
}

watch(
  root,
  (element) => {
    observer?.disconnect();
    observer = undefined;
    publish();
    measureStuck();
    if (!element) return;
    observer = new ResizeObserver(() => {
      publish();
      measureStuck();
      fit();
    });
    observer.observe(element);
    if (lines.value) observer.observe(lines.value);
  },
  { flush: "post" },
);
watch(sticky, () => {
  publish();
  measureStuck();
}, { flush: "post" });
watch([() => labels.value.join("\n"), () => draft.dirty], fit, { flush: "post" });

/**
 * Save, Discard and Undo become disabled or hidden once they acted. The banner takes the focus from
 * them when the action has ended and the banner says how, so that the focus does not fall to the
 * page and a screen reader reads the new text of the banner; focus that moved on stays.
 */
function act(action: () => unknown): void {
  void (async () => {
    await action();
    await nextTick();
    const element = root.value;
    const active = document.activeElement;
    if (element && (active === null || active === document.body || element.contains(active)))
      element.focus({ preventScroll: true });
  })();
}
// Where the banner goes while it has the focus, as when study.json on disk can no longer be read,
// the heading of the section takes the focus from it.
watch(
  shown,
  (now) => {
    if (now || !root.value?.contains(document.activeElement)) return;
    void nextTick(() => sectionHeading()?.focus({ preventScroll: true }));
  },
  { flush: "pre" },
);

onMounted(() => {
  window.addEventListener("scroll", measureStuck, { passive: true });
  // The names fit again once the font of the app has loaded.
  if ("fonts" in document) void document.fonts.ready.then(fit);
});
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
    v-if="shown"
    ref="root"
    role="region"
    :aria-labelledby="textId"
    tabindex="-1"
    class="unsaved-banner"
    :class="{
      'unsaved-banner--dirty': draft.dirty,
      'unsaved-banner--sticky': sticky,
      'unsaved-banner--stuck': stuck,
      'unsaved-banner--idle': idle,
    }"
  >
    <div class="unsaved-banner-row">
      <p :id="textId" class="unsaved-banner-text" :class="{ 'unsaved-banner-text--notice': !draft.dirty && draft.notice }">
        <i v-if="draft.dirty" class="fas fa-circle unsaved-banner-dot" aria-hidden="true"></i>
        <span ref="lines" class="unsaved-banner-lines">
          <span v-if="draft.dirty" class="unsaved-banner-message"
            ><strong>Unsaved changes</strong> to study.json: {{ fields }}</span
          >
          <span v-else class="unsaved-banner-message">{{ draft.notice || "No unsaved changes to study.json" }}</span>
          <span ref="measure" class="unsaved-banner-measure" aria-hidden="true"></span>
        </span>
      </p>
      <!-- Without anything to act on, the buttons keep their room, hidden (unsaved-banner-off),
           which takes them from the Tab order and from screen readers too. -->
      <div class="unsaved-banner-actions">
        <VBtn
          variant="text"
          color="primary"
          :disabled="!draft.undoable"
          :class="{ 'unsaved-banner-off': !draft.undoable }"
          @click="act(draft.undoDiscard)"
        >
          Undo
        </VBtn>
        <VBtn
          variant="text"
          :disabled="!draft.dirty || draft.saving"
          :class="{ 'unsaved-banner-off': !draft.dirty }"
          @click="act(draft.discard)"
        >
          Discard
        </VBtn>
        <VBtn
          variant="flat"
          color="primary"
          :disabled="!draft.canSave"
          :loading="draft.saving"
          :aria-keyshortcuts="shortcut.keys"
          :class="{ 'unsaved-banner-off': !draft.dirty }"
          @click="act(draft.save)"
        >
          Save
        </VBtn>
        <kbd class="unsaved-banner-key" :class="{ 'unsaved-banner-off': !draft.dirty }" aria-hidden="true">{{
          shortcut.label
        }}</kbd>
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
/* Under the section tabs. While it has something to say, it sticks below the app bar while the
   page scrolls, opaque, since the form scrolls under it, and scrolls on its own when its alerts
   are taller than half the window. Amber while study.json has unsaved changes (the theme colors
   caution and caution-tint), the surface otherwise. */
.unsaved-banner {
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
/* It takes the focus after its buttons acted, for screen readers; the focus moves on from it. */
.unsaved-banner:focus {
  outline: none;
}
.unsaved-banner--sticky {
  position: sticky;
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
:global(html:has(.unsaved-banner--sticky)) {
  scroll-padding-top: calc(var(--unsaved-banner-top, 0px) + var(--unsaved-banner-height, 0px) + 8px);
}
/* The text in one line beside the buttons, so that the row keeps its height in every state; on a
   phone in two lines above them (--unsaved-banner-lines). */
.unsaved-banner-row {
  --unsaved-banner-lines: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 4px 12px;
}
.unsaved-banner-text {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  margin: 0;
  font-size: 13px;
  line-height: 18px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.unsaved-banner-text--notice {
  color: rgb(var(--v-theme-on-surface));
}
.unsaved-banner--dirty .unsaved-banner-text {
  color: rgb(var(--v-theme-caution));
}
/* In the middle of the first line. */
.unsaved-banner-dot {
  flex: none;
  font-size: 0.5rem;
  line-height: 18px;
}
/* The names that do not fit into the lines become "and N more" (fit); the last line cuts off the
   end of a single name that is still too long. */
.unsaved-banner-lines {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
}
.unsaved-banner-message {
  display: -webkit-box;
  overflow: hidden;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: var(--unsaved-banner-lines);
  line-clamp: var(--unsaved-banner-lines);
}
.unsaved-banner-measure {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  overflow-wrap: anywhere;
  visibility: hidden;
}
.unsaved-banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.unsaved-banner-off {
  visibility: hidden;
}
.unsaved-banner-key {
  align-self: center;
  /* Its text sits on the baseline of the label of Save: the smaller font and the thicker bottom
     border lift it by a pixel. */
  position: relative;
  top: 1px;
  padding: 1px 5px 0;
  line-height: 16px;
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
/* On a phone the buttons go below the text, at the end, which keeps the room of two lines. */
@media (max-width: 599.98px) {
  .unsaved-banner {
    padding: 6px 6px 6px 10px;
  }
  .unsaved-banner-row {
    --unsaved-banner-lines: 2;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: calc(var(--unsaved-banner-lines) * 18px) auto;
  }
  .unsaved-banner-actions {
    grid-row: 2;
    grid-column: 1;
    justify-self: end;
  }
  /* With no button to show, the text stands in the middle of the room of both lines. */
  .unsaved-banner--idle .unsaved-banner-text {
    grid-row: 1 / -1;
    grid-column: 1;
  }
}
</style>
