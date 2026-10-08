<script setup lang="ts">
import { computed, useId } from "vue";
import { VBtn, VCard, VCardText, VChip, VTextarea } from "vuetify/components";
import type { Profile, ReviewItem } from "../api/types";
import { GROW_ROWS, sizesFieldsByContent } from "../fieldSizing";
import { formatTime } from "../overview";
import { KIND_ICONS, KIND_LABELS, STATE_LABELS, STATE_TONES, targetText, type ItemAction } from "../review";
import { profileOf } from "../study";
import PersonAvatar from "./PersonAvatar.vue";

/**
 * The selected review item: its text, author, target, thread and the actions on it. An open item
 * can be resolved or dismissed, a resolved one dismissed or reopened, and a dismissed one reopened.
 * Open and resolved items have a reply box, whose text these actions post too.
 */
const draft = defineModel<string>("draft", { required: true });
const props = defineProps<{
  item: ReviewItem;
  /** The profiles of the roster and of the people of the study, by user name. */
  profiles: ReadonlyMap<string, Profile>;
  /** The action that runs; while one runs, the others wait. */
  busy: ItemAction | null;
  /** Whether review.json can be written. */
  writable: boolean;
  /** Another write of review.json runs, such as a new item. */
  blocked: boolean;
  /** Whether a closed item can be reopened; not while the study is approved. */
  canReopen: boolean;
}>();
const emit = defineEmits<{ act: [action: ItemAction] }>();

const headingId = useId();
const threadId = useId();
const autoGrow = !sizesFieldsByContent();

const author = computed(() => profileOf(props.profiles, props.item.author));
const open = computed(() => props.item.state === "open");
/** A dismissed item has no reply box: it can only be reopened. */
const replyable = computed(() => props.item.state !== "dismissed");
/** No action while review.json cannot be written or another write runs. */
const locked = computed(() => !props.writable || props.blocked || props.busy !== null);
const hasDraft = computed(() => draft.value.trim() !== "");
const replyHint = computed(() =>
  open.value ? "Resolve and Dismiss add it to the thread too." : "Dismiss and Reopen add it to the thread too.",
);
const closed = computed(() => {
  const { resolved_by: by, resolved: at, state } = props.item;
  if (state === "open" || !by) return null;
  const verb = state === "resolved" ? "Resolved" : "Dismissed";
  return `${verb} by ${profileOf(props.profiles, by).display_name}${at ? ` on ${formatTime(at)}` : ""}.`;
});
const acknowledgement = computed(() => {
  const code = props.item.acknowledges;
  if (!code) return null;
  return props.item.state === "dismissed"
    ? `Dismissed, so it no longer acknowledges the warning ${code}. Reopen it to acknowledge the warning again.`
    : `Acknowledges the warning ${code}. Dismissing the item brings the warning back.`;
});
</script>

<template>
  <VCard tag="article" border class="review-detail" :aria-labelledby="headingId">
    <VCardText class="review-detail-body">
      <div class="review-detail-head">
        <h3 :id="headingId" class="review-detail-kind">
          <i :class="KIND_ICONS[item.kind]" class="review-detail-icon" aria-hidden="true"></i>{{ KIND_LABELS[item.kind] }}
        </h3>
        <VChip size="small" variant="tonal" :color="STATE_TONES[item.state]" class="status-chip review-detail-state">
          {{ STATE_LABELS[item.state] }}
        </VChip>
      </div>

      <p class="review-detail-text">{{ item.text }}</p>

      <div class="review-detail-author">
        <PersonAvatar :profile="author" />
        <div class="review-detail-byline">
          <span class="review-detail-name">{{ author.display_name }}</span>
          <span v-if="item.agent" class="review-detail-agent">
            <i class="fas fa-robot" aria-hidden="true"></i> written by {{ item.agent }}
          </span>
          <time :datetime="item.created" class="review-detail-time">{{ formatTime(item.created) }}</time>
        </div>
      </div>

      <dl class="panel-facts review-detail-facts">
        <dt>Target</dt>
        <dd>{{ targetText(item.target) }}</dd>
        <dt>ID</dt>
        <dd class="review-detail-id">{{ item.id }}</dd>
      </dl>
      <p v-if="closed" class="review-detail-note review-detail-closed">
        <i
          :class="item.state === 'resolved' ? 'fas fa-check' : 'fas fa-ban'"
          class="review-detail-icon review-detail-note-icon"
          aria-hidden="true"
        ></i>
        <span>{{ closed }}</span>
      </p>
      <p v-if="acknowledgement" class="review-detail-note">
        <i class="fas fa-check-double review-detail-icon review-detail-note-icon" aria-hidden="true"></i>
        <span>{{ acknowledgement }}</span>
      </p>

      <section class="review-thread" :aria-labelledby="threadId">
        <h4 :id="threadId" class="field-heading">Thread</h4>
        <ol v-if="item.thread.length" class="review-thread-list">
          <li v-for="(entry, index) in item.thread" :key="index" class="thread-entry">
            <PersonAvatar :profile="profileOf(profiles, entry.author)" :size="24" />
            <div class="thread-entry-body">
              <p class="thread-entry-head">
                <span class="thread-entry-name">{{ profileOf(profiles, entry.author).display_name }}</span>
                <time :datetime="entry.created" class="thread-entry-time">{{ formatTime(entry.created) }}</time>
              </p>
              <p class="thread-entry-text">{{ entry.text }}</p>
            </div>
          </li>
        </ol>
        <p v-else class="field-empty">No replies yet.</p>
      </section>

      <div v-if="replyable" class="review-reply">
        <VTextarea
          v-model="draft"
          label="Reply"
          rows="2"
          :auto-grow="autoGrow"
          :max-rows="GROW_ROWS"
          variant="outlined"
          density="compact"
          :hint="replyHint"
          persistent-hint
          :disabled="!writable"
          class="grow-textarea"
        />
        <div class="review-actions">
          <!-- Tonal while there is nothing to post, so that it does not outweigh the actions beside it. -->
          <VBtn
            :variant="hasDraft ? 'flat' : 'tonal'"
            color="primary"
            prepend-icon="fas fa-reply"
            :disabled="locked || !hasDraft"
            :loading="busy === 'reply'"
            @click="emit('act', 'reply')"
          >
            Reply
          </VBtn>
          <VBtn
            v-if="open"
            variant="tonal"
            color="primary"
            prepend-icon="fas fa-check"
            :disabled="locked"
            :loading="busy === 'resolve'"
            @click="emit('act', 'resolve')"
          >
            Resolve
          </VBtn>
          <VBtn
            v-else
            variant="tonal"
            color="primary"
            prepend-icon="fas fa-rotate-left"
            :disabled="locked || !canReopen"
            :loading="busy === 'reopen'"
            @click="emit('act', 'reopen')"
          >
            Reopen
          </VBtn>
          <VBtn
            variant="text"
            prepend-icon="fas fa-ban"
            :disabled="locked"
            :loading="busy === 'dismiss'"
            @click="emit('act', 'dismiss')"
          >
            Dismiss
          </VBtn>
        </div>
      </div>
      <div v-else class="review-actions">
        <VBtn
          variant="tonal"
          color="primary"
          prepend-icon="fas fa-rotate-left"
          :disabled="locked || !canReopen"
          :loading="busy === 'reopen'"
          @click="emit('act', 'reopen')"
        >
          Reopen
        </VBtn>
      </div>
    </VCardText>
  </VCard>
</template>

<style scoped>
.review-detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.review-detail-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}
.review-detail-kind {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.review-detail-icon {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.review-detail-text {
  margin: 0;
  font-size: 1rem;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.review-detail-author {
  display: flex;
  align-items: center;
  gap: 10px;
}
.review-detail-byline {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px 12px;
  min-width: 0;
  font-size: 0.875rem;
}
.review-detail-name {
  font-weight: 600;
}
.review-detail-agent,
.review-detail-time {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.review-detail-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8125rem;
}
.review-detail-note {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: -4px 0 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
.review-detail-note-icon {
  width: 1rem;
  flex: 0 0 auto;
  text-align: center;
}
.review-thread {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.review-thread-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.thread-entry {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: start;
  gap: 10px;
}
.thread-entry-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.thread-entry-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 12px;
  margin: 0;
  font-size: 0.875rem;
  /* As tall as the avatar beside it. */
  line-height: 24px;
}
.thread-entry-name {
  font-weight: 600;
}
.thread-entry-time {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.thread-entry-text {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.45;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.review-reply {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.review-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
