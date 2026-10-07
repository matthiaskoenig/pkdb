<script setup lang="ts">
import { computed, nextTick, ref } from "vue";

/**
 * A rating from 0 to 5 in half steps: a radio group of the ten half stars. The arrow keys change
 * it in half steps, Home and End go to 0 and 5, and choosing the checked half again clears it.
 */
const value = defineModel<number>({ required: true });
defineProps<{
  /** The name of the group, such as "Rating of mkoenig". */
  label: string;
  disabled?: boolean;
}>();

const MAX = 5;
const STARS = [1, 2, 3, 4, 5];
const root = ref<HTMLElement | null>(null);

/** The half star that takes the focus: the checked one, else the first. */
const focusable = computed(() => (value.value >= 0.5 && value.value % 0.5 === 0 ? value.value : 0.5));

function stepLabel(step: number): string {
  return step === 1 ? "1 star" : `${step} stars`;
}

function icon(star: number): string {
  if (value.value >= star) return "fas fa-star";
  if (value.value >= star - 0.5) return "fas fa-star-half-stroke";
  return "far fa-star";
}

function choose(step: number): void {
  value.value = value.value === step ? 0 : step;
}

function focusChecked(): void {
  void nextTick(() => root.value?.querySelector<HTMLElement>('[tabindex="0"]')?.focus());
}

const KEYS: Record<string, (current: number) => number> = {
  ArrowRight: (current) => Math.min(MAX, current + 0.5),
  ArrowUp: (current) => Math.min(MAX, current + 0.5),
  ArrowLeft: (current) => Math.max(0, current - 0.5),
  ArrowDown: (current) => Math.max(0, current - 0.5),
  Home: () => 0,
  End: () => MAX,
};

function onKeydown(event: KeyboardEvent): void {
  const step = KEYS[event.key];
  if (!step) return;
  event.preventDefault();
  value.value = step(value.value);
  focusChecked();
}
</script>

<template>
  <div
    ref="root"
    role="radiogroup"
    :aria-label="label"
    :aria-disabled="disabled ? 'true' : undefined"
    class="rating"
    :class="{ 'rating--disabled': disabled }"
    @keydown="onKeydown"
  >
    <span v-for="star in STARS" :key="star" class="rating-star">
      <i :class="[icon(star), { 'rating-icon--filled': value >= star - 0.5 }]" class="rating-icon" aria-hidden="true"></i>
      <button
        v-for="step in [star - 0.5, star]"
        :key="step"
        type="button"
        role="radio"
        class="rating-half"
        :class="step < star ? 'rating-half--start' : 'rating-half--end'"
        :aria-checked="value === step ? 'true' : 'false'"
        :aria-label="stepLabel(step)"
        :tabindex="step === focusable ? 0 : -1"
        :disabled="disabled"
        @click="choose(step)"
      ></button>
    </span>
    <span class="rating-value" aria-hidden="true">{{ value }}</span>
  </div>
</template>

<style scoped>
.rating {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  --rating-fill: #b45309;
}
.v-theme--dark .rating {
  --rating-fill: #f5b942;
}
.rating-star {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
}
.rating-icon {
  font-size: 1.125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.rating-icon--filled {
  color: var(--rating-fill);
}
/* The two halves of a star are transparent buttons over its left and right half. */
.rating-half {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 50%;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.rating-half--start {
  left: 0;
}
.rating-half--end {
  right: 0;
}
.rating-half:focus-visible {
  outline: none;
}
/* The focus ring goes around the star of the focused half. */
.rating-star:has(.rating-half:focus-visible) {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
.rating--disabled .rating-half {
  cursor: default;
}
.rating--disabled .rating-icon {
  opacity: var(--v-disabled-opacity);
}
/* As wide as "4.5", so that the fields of the curators beside it have one width. */
.rating-value {
  min-width: 3ch;
  margin-inline-start: 6px;
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
