<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VTextarea } from "vuetify/components";
import type { Comment, Profile } from "../../study-views/types";
import { GROW_ROWS, sizesFieldsByContent } from "../../study-views/fieldSizing";
import { markMessage, messagesAt, type FieldMark } from "../metadata";
import { profileOf as knownProfile } from "../../study-views/study";
import DiskVersion from "./DiskVersion.vue";
import PersonAvatar from "../../study-views/components/PersonAvatar.vue";

/**
 * Descriptions and comments: of the study, or of one table kind in its notes. The text areas show
 * no label: the headings name the lists, and `aria-label` names each text area for screen readers.
 * A comment shows its author once, above its text.
 */
const descriptions = defineModel<string[]>("descriptions", { required: true });
const comments = defineModel<Comment[]>("comments", { required: true });
const props = withDefaults(
  defineProps<{
    /** The path of the notes in study.json before `descriptions`: "" or `notes.outputs.`. */
    prefix: string;
    /** The table kind of the notes, which names the buttons for screen readers; null for the study. */
    kind: string | null;
    /** Who writes new comments; null when no user is set. */
    author: string | null;
    profiles: ReadonlyMap<string, Profile>;
    errors: ReadonlyMap<string, string[]>;
    marks: ReadonlyMap<string, FieldMark>;
    /** The disk values of the fields that changed on both sides at the last reload. */
    disk: ReadonlyMap<string, string>;
    /** The level of the headings Descriptions and Comments: 4 in a card, 5 in a panel of notes, below its heading. */
    headingLevel?: 4 | 5;
  }>(),
  { headingLevel: 4 },
);
const emit = defineEmits<{ useDisk: [key: string] }>();

const autoGrow = !sizesFieldsByContent();

const descriptionsKey = computed(() => `${props.prefix}descriptions`);
const commentsKey = computed(() => `${props.prefix}comments`);

function errorsAt(key: string): readonly string[] {
  return messagesAt(props.errors, key);
}

function markAt(key: string): string | null {
  const mark = props.marks.get(key);
  return mark ? markMessage(mark, props.disk.get(key) ?? null) : null;
}

function blockClass(key: string): Record<string, boolean> {
  const mark = props.marks.get(key);
  return mark ? { [`field-block--${mark}`]: true } : {};
}

/** ` of outputs`, which tells the buttons of the notes of each table kind apart. */
function of(preposition: string): string {
  return props.kind ? ` ${preposition} ${props.kind}` : "";
}

function profileOf(user: string): Profile {
  return knownProfile(props.profiles, user);
}

function setDescription(index: number, value: string): void {
  descriptions.value = descriptions.value.map((entry, position) => (position === index ? value : entry));
}

function setComment(index: number, text: string): void {
  comments.value = comments.value.map((entry, position) => (position === index ? { ...entry, text } : entry));
}

function addComment(): void {
  if (props.author) comments.value = [...comments.value, { user: props.author, text: "" }];
}
</script>

<template>
  <div class="notes-fields">
    <div class="field-block descriptions-block" :class="blockClass(descriptionsKey)">
      <component :is="`h${headingLevel}`" class="field-heading">Descriptions</component>
      <div v-if="markAt(descriptionsKey)" class="field-mark-row">
        <p class="field-mark">{{ markAt(descriptionsKey) }}</p>
        <DiskVersion
          v-if="disk.has(descriptionsKey)"
          :field="descriptionsKey"
          @use="emit('useDisk', descriptionsKey)"
        />
      </div>
      <div v-for="(entry, index) in descriptions" :key="index" class="note-row">
        <!-- Vuetify points aria-labelledby at the label of a field, which a field without a label
             does not have; the aria-label names the text area instead. -->
        <VTextarea
          :model-value="entry"
          :aria-label="`Description ${index + 1}`"
          :aria-labelledby="undefined"
          variant="outlined"
          density="compact"
          rows="1"
          :auto-grow="autoGrow"
          :max-rows="GROW_ROWS"
          class="grow-textarea grow-textarea--one-line"
          :error-messages="errorsAt(`${descriptionsKey}.${index}`)"
          hide-details="auto"
          @update:model-value="setDescription(index, $event)"
        />
        <VBtn
          icon="fas fa-xmark"
          variant="text"
          size="small"
          :aria-label="`Remove description ${index + 1}${of('of')}`"
          class="row-remove"
          @click="descriptions = descriptions.filter((_, position) => position !== index)"
        />
      </div>
      <p v-if="!descriptions.length" class="field-empty">No descriptions</p>
      <p v-if="errorsAt(descriptionsKey).length" class="field-error">{{ errorsAt(descriptionsKey).join(" ") }}</p>
      <VBtn
        variant="text"
        color="primary"
        prepend-icon="fas fa-plus"
        :aria-label="`Add description${of('to')}`"
        class="row-add"
        @click="descriptions = [...descriptions, '']"
      >
        Add description
      </VBtn>
    </div>

    <div class="field-block comments-block" :class="blockClass(commentsKey)">
      <component :is="`h${headingLevel}`" class="field-heading">Comments</component>
      <div v-if="markAt(commentsKey)" class="field-mark-row">
        <p class="field-mark">{{ markAt(commentsKey) }}</p>
        <DiskVersion v-if="disk.has(commentsKey)" :field="commentsKey" @use="emit('useDisk', commentsKey)" />
      </div>
      <div v-for="(entry, index) in comments" :key="index" class="note-row comment-row">
        <div class="comment-body">
          <span class="comment-author">
            <PersonAvatar :profile="profileOf(entry.user)" :size="20" />
            {{ profileOf(entry.user).display_name }}
          </span>
          <VTextarea
            :model-value="entry.text"
            :aria-label="`Comment ${index + 1} by ${entry.user}`"
            :aria-labelledby="undefined"
            variant="outlined"
            density="compact"
            rows="1"
            :auto-grow="autoGrow"
            :max-rows="GROW_ROWS"
            class="grow-textarea grow-textarea--one-line"
            :error-messages="errorsAt(`${commentsKey}.${index}`)"
            hide-details="auto"
            @update:model-value="setComment(index, $event)"
          />
        </div>
        <VBtn
          icon="fas fa-xmark"
          variant="text"
          size="small"
          :aria-label="`Remove comment ${index + 1}${of('on')}`"
          class="row-remove comment-remove"
          @click="comments = comments.filter((_, position) => position !== index)"
        />
      </div>
      <p v-if="!comments.length" class="field-empty">No comments</p>
      <p v-if="errorsAt(commentsKey).length" class="field-error">{{ errorsAt(commentsKey).join(" ") }}</p>
      <VBtn
        variant="text"
        color="primary"
        prepend-icon="fas fa-plus"
        :aria-label="`Add comment${of('on')}`"
        :disabled="!author"
        class="row-add"
        @click="addComment"
      >
        Add comment
      </VBtn>
      <p v-if="!author" class="field-note">Set your PK-DB user in Connection settings to add comments.</p>
    </div>
  </div>
</template>

<style scoped>
.notes-fields {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.note-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 8px;
}
/* The remove button (40 px) centers on the first line of its text area, which is as high as a
   field of one line (30 px), and adds no height to the row. */
.note-row > .row-remove {
  margin-block: -5px;
}
.comment-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.comment-author {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 600;
}
/* Below the author line (20 px) and the gap of 6 px above the text area of a comment. */
.note-row > .comment-remove {
  margin-top: 21px;
}
</style>
