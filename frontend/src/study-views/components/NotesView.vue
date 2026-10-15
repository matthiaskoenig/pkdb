<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from "vue";
import { useStudyViews } from "../context";
import { notesSummary } from "../notes";
import { knownProfiles, profileOf } from "../study";
import { kindLabel } from "../tableKinds";
import type { Profile, TableKind } from "../types";

/**
 * The notes of a table kind in study.json above the rows of its tables, read only: a panel that
 * opens and closes, with the header of the notes that the curation app edits there,
 * and the descriptions and the comments with their authors. Nothing shows for a kind without
 * notes. A link that names the notes (`focused`) opens them and moves the focus to their toggle,
 * once, which `took-focus` tells; for a kind without notes it tells it at once, as there is
 * nothing to open, so that the page forgets the link.
 */
const props = withDefaults(defineProps<{ kind: TableKind; focused?: boolean }>(), { focused: false });
const emit = defineEmits<{ "took-focus": [] }>();

const views = useStudyViews();
const detail = views.data.detail;
const headingId = useId();
const bodyId = useId();
const toggle = ref<HTMLButtonElement | null>(null);
const open = ref(false);

const notes = computed(() => detail.value?.metadata.value?.notes[props.kind] ?? null);
const descriptions = computed(() => notes.value?.descriptions ?? []);
const comments = computed(() => notes.value?.comments ?? []);
const shown = computed(() => descriptions.value.length + comments.value.length > 0);
/** The kind as the study names it, in lower case, such as `outputs`. */
const label = computed(() => (detail.value ? kindLabel(detail.value, props.kind) : props.kind).toLowerCase());
const summary = computed(() => (notes.value ? notesSummary(notes.value) : ""));
// Profiles: the curators that the page knows, and the people of the study who are not among them.
const roster = ref<Profile[]>([]);
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));

function authorName(user: string): string {
  return profileOf(profiles.value, user).display_name;
}

/** Open the notes that a link named and give their toggle the focus, once the study shows. */
async function takeFocus(): Promise<void> {
  if (!props.focused || !detail.value) return;
  if (shown.value) {
    open.value = true;
    await nextTick();
    toggle.value?.focus();
  }
  emit("took-focus");
}

onMounted(() => {
  views.data.curators().then(
    (loaded) => (roster.value = loaded),
    // Without the curators the comments show user names.
    () => undefined,
  );
  void takeFocus();
});
watch(
  () => props.focused && detail.value !== null,
  () => void takeFocus(),
);
</script>

<template>
  <section v-if="shown" class="notes-view" :aria-labelledby="headingId">
    <h4 :id="headingId" class="notes-view-heading">
      <button
        ref="toggle"
        type="button"
        class="notes-view-toggle"
        :aria-expanded="open"
        :aria-controls="bodyId"
        @click="open = !open"
      >
        <!-- The space keeps the kind and the summary apart for screen readers. -->
        <span class="notes-view-title">Notes of the {{ label }}</span> <span class="notes-view-summary">{{ summary }}</span>
        <i class="fas fa-chevron-down notes-view-chevron" aria-hidden="true"></i>
      </button>
    </h4>
    <div v-show="open" :id="bodyId" class="notes-view-body">
      <p v-for="(text, index) in descriptions" :key="`d${index}`" class="notes-view-text">{{ text }}</p>
      <p v-for="(comment, index) in comments" :key="`c${index}`" class="notes-view-text notes-view-comment">
        <span class="notes-view-author">{{ authorName(comment.user) }}</span> <span>{{ comment.text }}</span>
      </p>
    </div>
  </section>
</template>

<style scoped>
/* The header has the height of the head of the rows pane, as the notes of the curation app. */
.notes-view {
  flex: 0 0 auto;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.notes-view-heading {
  margin: 0;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
}
.notes-view-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 26px;
  padding: 2px 8px;
  border: 0;
  background: none;
  color: rgb(var(--v-theme-on-surface));
  font: inherit;
  font-size: 12px;
  text-align: start;
  white-space: nowrap;
  cursor: pointer;
}
.notes-view-toggle:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}
.notes-view-toggle:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}
.notes-view-title {
  flex: 0 0 auto;
  font-weight: 600;
}
.notes-view-summary {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.notes-view-chevron {
  flex: 0 0 auto;
  margin-inline-start: auto;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  transition: transform 0.15s ease;
}
.notes-view-toggle[aria-expanded="true"] .notes-view-chevron {
  transform: rotate(180deg);
}
/* Above a long table the notes keep at most 40 % of the window and scroll on their own. */
.notes-view-body {
  max-height: min(40vh, 28rem);
  overflow-y: auto;
  padding: 8px 12px 12px;
}
.notes-view-text {
  margin: 0;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.notes-view-text + .notes-view-text {
  margin-top: 6px;
}
.notes-view-author {
  font-weight: 600;
}
@media (prefers-reduced-motion: reduce) {
  .notes-view-chevron {
    transition: none;
  }
}
</style>
