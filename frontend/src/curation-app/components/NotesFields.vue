<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VTextarea } from "vuetify/components";
import type { Comment, Profile } from "../api/types";
import { MARK_TEXT, type FieldMark } from "../metadata";
import PersonAvatar from "./PersonAvatar.vue";

/** Descriptions and comments: of the study, or of one table kind in its notes. */
const descriptions = defineModel<string[]>("descriptions", { required: true });
const comments = defineModel<Comment[]>("comments", { required: true });
const props = defineProps<{
  /** The path of the notes in study.json before `descriptions`: "" or `notes.outputs.`. */
  prefix: string;
  /** The table kind of the notes, which names the buttons for screen readers; null for the study. */
  kind: string | null;
  /** Who writes new comments; null when no user is set. */
  author: string | null;
  profiles: ReadonlyMap<string, Profile>;
  errors: ReadonlyMap<string, string[]>;
  marks: ReadonlyMap<string, FieldMark>;
}>();

const descriptionsKey = computed(() => `${props.prefix}descriptions`);
const commentsKey = computed(() => `${props.prefix}comments`);

function errorsAt(key: string): string[] {
  return props.errors.get(key) ?? [];
}

function markAt(key: string): string | null {
  const mark = props.marks.get(key);
  return mark ? MARK_TEXT[mark] : null;
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
  return (
    props.profiles.get(user) ?? { username: user, display_name: user, title: null, affiliation: null, avatar_url: null }
  );
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
      <h4 class="field-heading">Descriptions</h4>
      <p v-if="markAt(descriptionsKey)" class="field-mark">{{ markAt(descriptionsKey) }}</p>
      <div v-for="(entry, index) in descriptions" :key="index" class="note-row">
        <VTextarea
          :model-value="entry"
          :label="`Description ${index + 1}`"
          variant="outlined"
          density="compact"
          rows="2"
          class="grow-textarea"
          :error-messages="errorsAt(`${descriptionsKey}.${index}`)"
          hide-details="auto"
          @update:model-value="setDescription(index, $event)"
        />
        <VBtn
          icon="fas fa-xmark"
          variant="text"
          density="comfortable"
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
      <h4 class="field-heading">Comments</h4>
      <p v-if="markAt(commentsKey)" class="field-mark">{{ markAt(commentsKey) }}</p>
      <div v-for="(entry, index) in comments" :key="index" class="note-row comment-row">
        <div class="comment-body">
          <span class="comment-author">
            <PersonAvatar :profile="profileOf(entry.user)" :size="20" />
            {{ profileOf(entry.user).display_name }}
          </span>
          <VTextarea
            :model-value="entry.text"
            :label="`Comment by ${entry.user}`"
            variant="outlined"
            density="compact"
            rows="2"
            class="grow-textarea"
            :error-messages="errorsAt(`${commentsKey}.${index}`)"
            hide-details="auto"
            @update:model-value="setComment(index, $event)"
          />
        </div>
        <VBtn
          icon="fas fa-xmark"
          variant="text"
          density="comfortable"
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
/* The remove button centers on the first line of the text area. */
.note-row > .row-remove {
  margin-top: 6px;
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
.note-row > .comment-remove {
  margin-top: 32px;
}
</style>
