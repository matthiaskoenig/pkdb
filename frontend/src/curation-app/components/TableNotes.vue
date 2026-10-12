<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useId, watch } from "vue";
import type { Profile, TableKind } from "../api/types";
import { useMoreBelow } from "../composables/useMoreBelow";
import { issueMessage } from "../metadata";
import { notesKindOf, notesSummary } from "../notes";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { knownProfiles, sectionRoute } from "../study";
import { kindLabel, noteKinds } from "../tableKinds";
import MoreBelow from "./MoreBelow.vue";
import NotesFields from "./NotesFields.vue";

/**
 * The notes of a table kind in study.json, in a panel that opens and closes. Its header names
 * the kind and what the notes hold, such as "Notes of the subjects 2 descriptions · 1 comment";
 * its body edits their descriptions and comments in the draft of study.json, which the save bar
 * saves. Notes belong to a kind, so every table of a kind shows the same notes. The panel starts
 * closed, opens by itself for an issue in its notes, and the draft keeps it open or closed while
 * the study is open. While study.json is not valid it says so and lists the issues of its notes.
 *
 * Above the rows of a table it shares the rows pane with them, and its body scrolls on its own.
 * In a card of the Metadata section, which shows the notes of a kind without a table, it has a
 * frame of its own and shows its notes whole in the page, which scrolls.
 */
const props = withDefaults(
  defineProps<{
    kind: TableKind;
    /** Whether a link opened the notes: the toggle takes the focus, and says so with `took-focus`. */
    focused?: boolean;
    /** Whether the panel stands in a card, rather than above the rows of a table. */
    card?: boolean;
  }>(),
  { focused: false, card: false },
);
const emit = defineEmits<{ "took-focus": [] }>();

const study = useStudyStore();
const overview = useOverviewStore();
const draft = study.draft;
const headingId = useId();
const bodyId = useId();
const toggle = ref<HTMLButtonElement | null>(null);
const body = ref<HTMLElement | null>(null);
const content = ref<HTMLElement | null>(null);
/** Whether more of the open body follows below its view, which a fade at its bottom shows. */
const { more, scrollbar } = useMoreBelow(body, content);
/** The height of the open body whole, which the panel grows to at most; null until it is measured. */
const contentHeight = ref<number | null>(null);
watch(
  content,
  (element, _, onCleanup) => {
    if (!element) return;
    const observer = new ResizeObserver(() => (contentHeight.value = element.offsetHeight));
    observer.observe(element);
    onCleanup(() => observer.disconnect());
  },
  { immediate: true, flush: "post" },
);

const detail = computed(() => study.detail);
/** The kind as the study page names it, in lower case, such as `subjects`. */
const label = computed(() => (detail.value ? kindLabel(detail.value, props.kind) : props.kind).toLowerCase());
/** The notes of the kind in the draft; null while study.json is not valid. */
const notes = computed(() => draft.form?.notes[props.kind] ?? null);
const open = computed(() => draft.notesOpen.has(props.kind));
const changedOnDisk = computed(
  () => draft.marks.has(`notes.${props.kind}.descriptions`) || draft.marks.has(`notes.${props.kind}.comments`),
);
const summary = computed(() => {
  if (!notes.value) return "study.json is not valid";
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
    emit("took-focus");
  },
  { immediate: true },
);
</script>

<template>
  <section
    class="table-notes"
    :class="{ 'table-notes--open': open, 'table-notes--card': card }"
    :style="contentHeight === null ? undefined : { '--table-notes-content': `${contentHeight}px` }"
    :aria-labelledby="headingId"
  >
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
    <!-- The frame clips the body and the fade below the header when the panel shrinks; the body
         scrolls on its own, and while more of it follows below, a fade at its bottom shows it. -->
    <div v-show="open" class="table-notes-frame">
      <div :id="bodyId" ref="body" class="table-notes-body">
        <div ref="content" class="table-notes-content">
          <NotesFields
            v-if="notes"
            v-model:descriptions="notes.descriptions"
            v-model:comments="notes.comments"
            :prefix="`notes.${kind}.`"
            :kind="kind"
            :heading-level="5"
            :author="author"
            :profiles="profiles"
            :errors="draft.errors"
            :marks="draft.marks"
            :disk="draft.disk"
            @use-disk="draft.useDisk"
          />
          <template v-else>
            <p class="table-notes-text">study.json is not valid, so its notes cannot show here. Fix it in your editor, or start a new one in <RouterLink :to="metadataRoute">Metadata</RouterLink>.</p>
            <ul v-if="fileIssues.length" class="table-notes-issues">
              <li v-for="(message, index) in fileIssues" :key="index">{{ message }}</li>
            </ul>
          </template>
        </div>
      </div>
      <MoreBelow v-if="open && more" :scrollbar="scrollbar" />
    </div>
  </section>
</template>

<style scoped>
/* The header has the height of the head of the rows pane. */
.table-notes {
  --table-notes-head: 26px;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  min-height: calc(var(--table-notes-head) + 1px);
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* Open in the rows pane, the notes take the room that the rows leave, up to their whole height
   (the measured height of their content): above a short table they show whole. Above a long table,
   whose rows give up their room first (RowsPane.vue), they keep 40 % of the window, at most 28rem,
   and their body scrolls. In a short pane they then shrink down to their header and its border
   before the conflicts above them, rather than push the rows out of the pane. */
.table-notes--open:not(.table-notes--card) {
  flex: 1000 1000 calc(var(--table-notes-head) + 1px + min(40vh, 28rem));
  max-height: calc(var(--table-notes-head) + 1px + var(--table-notes-content));
}
/* In a card, the panel has a frame of its own instead of the line below it in the rows pane, and
   its body no scroll of its own: the page scrolls. */
.table-notes--card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}
.table-notes--card .table-notes-body {
  overflow-y: visible;
}
.table-notes-heading {
  flex: 0 0 auto;
  margin: 0;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
}
/* One line as high as the head of the rows pane above it, with the same padding and text size,
   which the panel keeps whole when it shrinks. */
.table-notes-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: var(--table-notes-head);
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
.table-notes-frame {
  position: relative;
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.table-notes-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}
/* The padding is part of the content, whose height the panel grows to. */
.table-notes-content {
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
