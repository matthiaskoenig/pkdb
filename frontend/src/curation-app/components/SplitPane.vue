<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

/**
 * Two panes side by side with a separator between them that a pointer drags and a keyboard
 * moves: arrow keys by 2 %, Home and End to the limits. Each pane keeps at least `minPx`. The
 * share of the start pane is a convenience of this viewer in `localStorage`, which may be
 * unavailable: the panes then open at `defaultShare`.
 */
const props = withDefaults(
  defineProps<{ storageKey: string; defaultShare?: number; minPx?: number; label: string }>(),
  { defaultShare: 45, minPx: 280 },
);
defineSlots<{ start?: () => unknown; end?: () => unknown }>();

const STEP = 2;
const root = ref<HTMLElement | null>(null);
const width = ref(0);

function stored(): number | null {
  try {
    const value = Number(localStorage.getItem(props.storageKey));
    return localStorage.getItem(props.storageKey) !== null && Number.isFinite(value) ? value : null;
  } catch {
    return null;
  }
}

function store(value: number): void {
  try {
    localStorage.setItem(props.storageKey, String(value));
  } catch {
    // Without storage the share lasts until the page closes.
  }
}

/** The limits of the share in percent, so that each pane keeps `minPx`; 10 to 90 before a layout. */
const limits = computed(() => {
  if (width.value <= 2 * props.minPx) return { min: 10, max: 90 };
  const min = Math.ceil((props.minPx / width.value) * 100);
  return { min, max: 100 - min };
});
const clamp = (value: number) => Math.min(limits.value.max, Math.max(limits.value.min, Math.round(value)));
const share = ref(stored() ?? props.defaultShare);
const shown = computed(() => clamp(share.value));

function set(value: number): void {
  share.value = clamp(value);
  store(share.value);
}

function key(event: KeyboardEvent): void {
  const moves: Record<string, () => number> = {
    ArrowLeft: () => shown.value - STEP,
    ArrowRight: () => shown.value + STEP,
    Home: () => limits.value.min,
    End: () => limits.value.max,
  };
  const move = moves[event.key];
  if (!move) return;
  event.preventDefault();
  set(move());
}

/** Ends the drag in progress, if any. */
let stopDrag: (() => void) | null = null;

/**
 * Drag the separator: it keeps the place under the pointer where it was grabbed, and no text of
 * the panes is selected on the way (the class `split-pane-dragging` of the body).
 */
function drag(event: PointerEvent): void {
  const element = root.value;
  if (!element) return;
  event.preventDefault();
  stopDrag?.();
  const box = element.getBoundingClientRect();
  const separator = event.currentTarget as HTMLElement;
  const grab = event.clientX - separator.getBoundingClientRect().left;
  separator.setPointerCapture(event.pointerId);
  document.body.classList.add("split-pane-dragging");
  const move = (next: PointerEvent) => set(((next.clientX - grab - box.left) / box.width) * 100);
  const stop = () => {
    separator.removeEventListener("pointermove", move);
    separator.removeEventListener("pointerup", stop);
    separator.removeEventListener("pointercancel", stop);
    document.body.classList.remove("split-pane-dragging");
    stopDrag = null;
  };
  separator.addEventListener("pointermove", move);
  separator.addEventListener("pointerup", stop);
  separator.addEventListener("pointercancel", stop);
  stopDrag = stop;
}

let observer: ResizeObserver | undefined;
onMounted(() => {
  if (!root.value) return;
  width.value = root.value.clientWidth;
  observer = new ResizeObserver(([entry]) => (width.value = entry?.contentRect.width ?? 0));
  observer.observe(root.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  stopDrag?.();
});
</script>

<template>
  <div ref="root" class="split-pane" :style="{ '--split-share': `${shown}%` }">
    <div class="split-pane-start"><slot name="start" /></div>
    <div
      role="separator"
      tabindex="0"
      aria-orientation="vertical"
      :aria-label="label"
      :aria-valuemin="limits.min"
      :aria-valuemax="limits.max"
      :aria-valuenow="shown"
      class="split-pane-separator"
      @keydown="key"
      @pointerdown="drag"
    ></div>
    <div class="split-pane-end"><slot name="end" /></div>
  </div>
</template>

<style scoped>
.split-pane {
  display: flex;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.split-pane-start {
  flex: 0 0 var(--split-share);
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.split-pane-end {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* 6 px to grab, with a grip in the middle; the focus ring stays inside. */
.split-pane-separator {
  flex: 0 0 6px;
  position: relative;
  cursor: col-resize;
  touch-action: none;
  background: rgb(var(--v-theme-background));
  border-inline: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.split-pane-separator::after {
  content: "";
  position: absolute;
  inset-inline-start: 1px;
  top: 50%;
  width: 2px;
  height: 28px;
  margin-top: -14px;
  border-radius: 1px;
  background: rgba(var(--v-theme-on-surface), 0.3);
}
/* While the separator is dragged, the pointer selects no text of the page. */
:global(body.split-pane-dragging) {
  user-select: none;
  -webkit-user-select: none;
}
.split-pane-separator:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: -2px;
}
</style>
