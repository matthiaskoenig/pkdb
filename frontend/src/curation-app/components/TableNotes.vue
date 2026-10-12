<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from "vue";
import type { Profile, TableKind } from "../api/types";
import { issueMessage } from "../metadata";
import { notesKindOf, notesSummary } from "../notes";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { knownProfiles, sectionRoute } from "../study";
import { kindLabel, noteKinds } from "../tableKinds";
import NotesFields from "./NotesFields.vue";

/**
 * The notes of a table kind in study.json, in a panel that opens and closes. Its header names
 * the kind and what the notes hold, such as "Notes of the subjects 2 descriptions · 1 comment";
 * its body edits their descriptions and comments in the draft of study.json, which the save bar
 * saves. Notes belong to a kind, so every table of a kind shows the same notes. The panel starts
 * closed, opens by itself for an issue in its notes, and the draft keeps it open or closed while
 * the study is open. Without a readable study.json it says so and lists the issues of its notes.
 */
const props = withDefaults(
  defineProps<{
    kind: TableKind;
    /** Whether a link opened the notes: the toggle takes the focus. */
    focused?: boolean;
  }>(),
  { focused: false },
);

const study = useStudyStore();
const overview = useOverviewStore();
const draft = study.draft;
const headingId = useId();
const bodyId = useId();
const toggle = ref<HTMLButtonElement | null>(null);

const detail = computed(() => study.detail);
/** The kind as the study page names it, in lower case, such as `subjects`. */
const label = computed(() => (detail.value ? kindLabel(detail.value, props.kind) : props.kind).toLowerCase());
/** The notes of the kind in the draft; null without a readable study.json. */
const notes = computed(() => draft.form?.notes[props.kind] ?? null);
const open = computed(() => draft.notesOpen.has(props.kind));
const changedOnDisk = computed(
  () => draft.marks.has(`notes.${props.kind}.descriptions`) || draft.marks.has(`notes.${props.kind}.comments`),
);
const summary = computed(() => {
  if (!notes.value) return "study.json cannot be read";
  return [notesSummary(notes.value), changedOnDisk.value ? "changed on disk" : ""].filter(Boolean).join(" · ");
});
/** The issues of study.json on disk in these notes, listed while the form cannot show them. */
const fileIssues = computed(() => {
  const value = detail.value;
  if (!value || notes.value) return [];
  const kinds = noteKinds(value);
  return value.metadata.issues.filter((issue) => notesKindOf(issue.field, kinds) === props.kind).map(issueMessage);
});
const metadataRoute = computed(() => sectionRoute(detail.value?.id ?? "", "metadata"));

// Profiles: the roster, and the people of the study who are not in it.
const roster = ref<Profile[]>([]);
onMounted(() => {
  study.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the roster the comments show user names.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));
const author = computed(() => overview.snapshot?.author.user ?? null);

watch(
  () => props.focused,
  async (value) => {
    if (!value) return;
    await nextTick();
    toggle.value?.focus();
  },
  { immediate: true },
);
</script>

<template>
  <section class="table-notes" :aria-labelledby="headingId">
    <h4 :id="headingId" class="table-notes-heading">
      <button
        ref="toggle"
        type="button"
        class="table-notes-toggle"
        :aria-expanded="open"
        :aria-controls="bodyId"
        @click="draft.setNotesOpen(kind, !open)"
      >
        <!-- The space keeps the kind and the summary apart for screen readers. -->
        <span class="table-notes-title">Notes of the {{ label }}</span> <span class="table-notes-summary">{{ summary }}</span>
        <i class="fas fa-chevron-down table-notes-chevron" aria-hidden="true"></i>
      </button>
    </h4>
    <div v-show="open" :id="bodyId" class="table-notes-body">
      <NotesFields
        v-if="notes"
        v-model:descriptions="notes.descriptions"
        v-model:comments="notes.comments"
        :prefix="`notes.${kind}.`"
        :kind="kind"
        :author="author"
        :profiles="profiles"
        :errors="draft.errors"
        :marks="draft.marks"
        :disk="draft.disk"
        @use-disk="draft.useDisk"
      />
      <template v-else>
        <p class="table-notes-text">study.json cannot be read, so its notes cannot show here. Fix it in your editor, or start a new one in <RouterLink :to="metadataRoute">Metadata</RouterLink>.</p>
        <ul v-if="fileIssues.length" class="table-notes-issues">
          <li v-for="(message, index) in fileIssues" :key="index">{{ message }}</li>
        </ul>
      </template>
    </div>
  </section>
</template>

<style scoped>
/* In a short pane, the open notes shrink to their header and its border, and their body scrolls,
   rather than push the rows out of the pane. */
.table-notes {
  display: flex;
  flex: 0 1 auto;
  flex-direction: column;
  min-height: 27px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.table-notes-heading {
  flex: 0 0 auto;
  margin: 0;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
}
/* As high as the head of the rows pane above it, with the same padding and text size. */
.table-notes-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 26px;
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
.table-notes-toggle:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}
.table-notes-toggle:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}
.table-notes-title {
  flex: 0 0 auto;
  font-weight: 600;
}
/* The summary shortens first in a narrow pane. */
.table-notes-summary {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.table-notes-chevron {
  flex: 0 0 auto;
  margin-inline-start: auto;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  transition: transform 0.15s ease;
}
.table-notes-toggle[aria-expanded="true"] .table-notes-chevron {
  transform: rotate(180deg);
}
/* Open, the notes leave most of the pane to the rows and scroll on their own. */
.table-notes-body {
  min-height: 0;
  max-height: min(40vh, 28rem);
  overflow-y: auto;
  padding: 8px 12px 12px;
}
.table-notes-text {
  margin: 0;
  font-size: 13px;
}
.table-notes-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
  font-size: 13px;
  overflow-wrap: anywhere;
}
@media (prefers-reduced-motion: reduce) {
  .table-notes-chevron {
    transition: none;
  }
}
</style>
