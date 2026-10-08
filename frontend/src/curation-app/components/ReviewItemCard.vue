<script setup lang="ts">
import { computed } from "vue";
import type { ReviewItem } from "../api/types";
import { formatTime, plural } from "../overview";
import { KIND_ICONS, KIND_LABELS, STATE_LABELS, STATE_TONES, targetText } from "../review";

/** An item in the list of the review section; clicking it selects the item. */
const props = defineProps<{
  item: ReviewItem;
  selected: boolean;
  /** The name of the author to show. */
  author: string;
}>();
const emit = defineEmits<{ select: [] }>();

const replies = computed(() => props.item.thread.length);
const agentLabel = computed(() => (props.item.agent ? `Written by ${props.item.agent}` : ""));
</script>

<template>
  <button
    type="button"
    class="review-card"
    :class="{ 'review-card--selected': selected }"
    :aria-current="selected ? 'true' : undefined"
    @click="emit('select')"
  >
    <span class="review-card-head">
      <span class="review-card-kind">
        <i :class="KIND_ICONS[item.kind]" class="review-card-icon" aria-hidden="true"></i>{{ KIND_LABELS[item.kind] }}
      </span>
      <!-- Not a VChip: Chrome leaves the text of its draggable="false" out of the name of the button. -->
      <span class="review-card-state" :class="`review-card-state--${STATE_TONES[item.state] ?? 'neutral'}`">
        {{ STATE_LABELS[item.state] }}
      </span>
      <span v-if="item.agent || replies" class="review-card-markers">
        <i
          v-if="item.agent"
          class="fas fa-robot review-card-agent"
          role="img"
          :aria-label="agentLabel"
          :title="agentLabel"
        ></i>
        <span v-if="replies" class="review-card-thread" role="img" :aria-label="plural(replies, 'reply', 'replies')">
          <i class="fas fa-comment" aria-hidden="true"></i>{{ replies }}
        </span>
      </span>
    </span>
    <span class="review-card-text">{{ item.text }}</span>
    <span class="review-card-facts">
      <span class="review-card-target">
        <i class="fas fa-crosshairs review-card-icon" aria-hidden="true"></i>{{ targetText(item.target) }}
      </span>
      <span v-if="item.acknowledges" class="review-card-code">
        <i class="fas fa-check-double review-card-icon" aria-hidden="true"></i>
        <span class="d-sr-only">{{
          item.state === "dismissed" ? "No longer acknowledges the warning " : "Acknowledges the warning "
        }}</span>
        {{ item.acknowledges }}
      </span>
    </span>
    <span class="review-card-meta">{{ author }} · {{ formatTime(item.created) }}</span>
  </button>
</template>

<style scoped>
.review-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 10px 12px 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  font: inherit;
  text-align: start;
  cursor: pointer;
}
.review-card:hover {
  background-image: linear-gradient(rgba(var(--v-theme-on-surface), 0.04), rgba(var(--v-theme-on-surface), 0.04));
}
/* A second border inside the first one marks the selection without moving the content. */
.review-card--selected,
.review-card--selected:hover {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: inset 0 0 0 1px rgb(var(--v-theme-primary));
  background-image: linear-gradient(rgba(var(--v-theme-primary), 0.08), rgba(var(--v-theme-primary), 0.08));
}
.review-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
}
.review-card-kind {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
  font-weight: 600;
}
.review-card-icon {
  width: 1rem;
  flex: 0 0 auto;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* As a small tonal chip of Vuetify: the status color tints it, the text keeps the surface color. */
.review-card-state {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 10px;
  border-radius: 9999px;
  font-size: 0.75rem;
  white-space: nowrap;
}
.review-card-state--warning {
  background-color: rgba(var(--v-theme-warning), var(--v-activated-opacity));
}
.review-card-state--success {
  background-color: rgba(var(--v-theme-success), var(--v-activated-opacity));
}
.review-card-state--neutral {
  background-color: rgba(var(--v-theme-on-surface), var(--v-activated-opacity));
}
.review-card-markers {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-inline-start: auto;
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.review-card-thread {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-variant-numeric: tabular-nums;
}
/* Two lines of the text; the selected item shows all of it. */
.review-card-text {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  font-size: 0.9375rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.review-card-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 16px;
  font-size: 0.8125rem;
  line-height: 1.4;
}
.review-card-target,
.review-card-code {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
  overflow-wrap: anywhere;
}
.review-card-meta {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
