<script setup lang="ts">
import { VBtn, VIcon } from "vuetify/components";
import type { Snapshot } from "../api/types";

defineProps<{ author: Snapshot["author"] }>();
const emit = defineEmits<{ settings: [] }>();
</script>

<template>
  <div v-if="author.user" class="author">
    <VIcon icon="fas fa-user" size="small" />
    <span class="d-sr-only">User</span>
    <span class="author-name" :title="author.user">{{ author.user }}</span>
  </div>
  <div v-else class="author author-warning">
    <VIcon icon="fas fa-triangle-exclamation" color="warning" size="small" />
    <span class="author-reason" :title="author.reason ?? undefined">{{ author.reason }}</span>
    <VBtn variant="tonal" color="primary" size="small" @click="emit('settings')">Set user</VBtn>
  </div>
</template>

<style scoped>
.author {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8px;
  padding-inline: 8px;
}
/* As the labels of the buttons beside it. */
.author-name {
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.0071428571em;
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* Up to two lines fit into the header. */
.author-reason {
  display: -webkit-box;
  max-width: 17rem;
  overflow: hidden;
  font-size: 0.8125rem;
  line-height: 1.25;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
/* A narrower header shows the warning and its button; the reason stays for screen readers,
   and the settings dialog shows it. */
@media (max-width: 1279.98px) {
  .header-controls .author-reason {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
}
/* In the collapsed header the row lines up with the icons and labels of the buttons above, and
   the reason wraps beside its button. */
.header-panel .author {
  padding: 6px 16px 6px 12px;
}
.header-panel .author-warning {
  align-items: baseline;
}
.header-panel .author-reason {
  display: block;
  flex: 1 1 0;
  max-width: none;
  font-size: 0.875rem;
}
</style>
