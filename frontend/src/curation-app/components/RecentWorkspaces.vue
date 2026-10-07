<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VChip, VIcon } from "vuetify/components";
import type { Snapshot } from "../api/types";

const props = defineProps<{ snapshot: Snapshot; disabled?: boolean }>();
const emit = defineEmits<{ open: [path: string]; remove: [path: string] }>();

/** The recent workspaces other than the current one. */
const others = computed(() => props.snapshot.recent_workspaces.filter((item) => item.path !== props.snapshot.workspace));
</script>

<template>
  <section v-if="others.length" class="recent-workspaces">
    <h3 class="panel-subtitle">Recent workspaces</h3>
    <ul class="recent-list">
      <li v-for="item in others" :key="item.path" class="recent-item">
        <VBtn
          variant="text"
          prepend-icon="fas fa-folder"
          class="recent-open"
          :disabled="disabled || !item.exists"
          :aria-label="`Open ${item.path}`"
          @click="emit('open', item.path)"
        >
          <span class="path-text" :title="item.path"><bdi>{{ item.path }}</bdi></span>
        </VBtn>
        <VChip v-if="!item.exists" size="small" variant="tonal" class="recent-missing">Unavailable</VChip>
        <VBtn
          icon
          variant="text"
          size="small"
          :disabled="disabled"
          :aria-label="`Remove ${item.path} from recent workspaces`"
          @click="emit('remove', item.path)"
        >
          <VIcon icon="fas fa-xmark" size="16" />
        </VBtn>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.panel-subtitle {
  margin: 0 0 4px;
  font-size: 0.875rem;
  font-weight: 600;
}
.recent-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.recent-item {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.recent-open {
  flex: 1 1 auto;
  justify-content: flex-start;
  min-width: 0;
}
.recent-open :deep(.v-btn__content) {
  min-width: 0;
}
.recent-missing {
  flex-shrink: 0;
}
</style>
