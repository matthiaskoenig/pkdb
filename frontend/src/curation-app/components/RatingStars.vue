<script setup lang="ts">
/**
 * A rating from 0 to 5 in half steps, as a slider: the arrow keys change it by half a star, Home
 * and End go to 0 and 5. A click on the left or right half of a star sets it, and a click on the
 * set value clears it.
 */
const value = defineModel<number>({ required: true });
defineProps<{
  /** The name of the slider, such as "Rating of mkoenig". */
  label: string;
}>();

const MAX = 5;
const STARS = [1, 2, 3, 4, 5];

function icon(star: number): string {
  if (value.value >= star) return "fas fa-star";
  if (value.value >= star - 0.5) return "fas fa-star-half-stroke";
  return "far fa-star";
}

function choose(step: number): void {
  value.value = value.value === step ? 0 : step;
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
}
</script>

<template>
  <div
    role="slider"
    tabindex="0"
    :aria-label="label"
    aria-valuemin="0"
    :aria-valuemax="MAX"
    :aria-valuenow="value"
    :aria-valuetext="`${value} of ${MAX}`"
    class="rating"
    @keydown="onKeydown"
  >
    <span v-for="star in STARS" :key="star" class="rating-star">
      <i :class="[icon(star), { 'rating-icon--filled': value >= star - 0.5 }]" class="rating-icon" aria-hidden="true"></i>
      <!-- Pointer targets over the halves of the star; the slider takes the keys. -->
      <span
        v-for="step in [star - 0.5, star]"
        :key="step"
        class="rating-half"
        :class="step < star ? 'rating-half--start' : 'rating-half--end'"
        :data-step="step"
        aria-hidden="true"
        @click="choose(step)"
      ></span>
    </span>
    <span class="rating-value" aria-hidden="true">{{ value }}</span>
  </div>
</template>

<style scoped>
.rating {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 6px;
  --rating-fill: #b45309;
}
.v-theme--dark .rating {
  --rating-fill: #f5b942;
}
/* The focus ring goes around the stars and the value. */
.rating:focus-visible {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 1px;
}
.rating-star {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}
.rating-icon {
  font-size: 1.125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.rating-icon--filled {
  color: var(--rating-fill);
}
.rating-half {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 50%;
  cursor: pointer;
}
.rating-half--start {
  left: 0;
}
.rating-half--end {
  right: 0;
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
