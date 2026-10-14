<script setup lang="ts">
/**
 * The fade at the bottom of a region that scrolls, while more of it follows below its view: the
 * content fades out into the surface, beside the scroll bar of the region. The frame of the
 * region positions it; `useMoreBelow` says when it shows and how wide the scroll bar is.
 */
defineProps<{
  /** The width of the vertical scroll bar of the region. */
  scrollbar: number;
}>();
</script>

<template>
  <div class="pane-more" :style="{ '--pane-scrollbar': `${scrollbar}px` }" aria-hidden="true"></div>
</template>

<style scoped>
.pane-more {
  position: absolute;
  inset-inline: 0 var(--pane-scrollbar, 0px);
  bottom: 0;
  height: 32px;
  background: linear-gradient(to top, rgb(var(--v-theme-surface)), rgba(var(--v-theme-surface), 0));
  pointer-events: none;
}
</style>
