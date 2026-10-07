<script setup lang="ts">
import { ref, watch } from "vue";
import { VAlert, VBtn, VCard, VMenu } from "vuetify/components";
import type { Snapshot } from "../api/types";
import { useOverviewStore } from "../stores/overview";
import RecentWorkspaces from "./RecentWorkspaces.vue";

type Anchor = "bottom start" | "bottom";

withDefaults(defineProps<{ snapshot: Snapshot; location?: Anchor }>(), { location: "bottom start" });
const emit = defineEmits<{ choose: [] }>();

const overview = useOverviewStore();
const open = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);

// A failure belongs to the action that caused it, not to the next visit of the menu.
watch(open, (value) => {
  if (value) error.value = null;
});

async function run(action: () => Promise<unknown>, { close }: { close: boolean }): Promise<void> {
  busy.value = true;
  error.value = null;
  try {
    await action();
    if (close) open.value = false;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : String(caught);
  } finally {
    busy.value = false;
  }
}

function choose(): void {
  open.value = false;
  emit("choose");
}
</script>

<template>
  <VMenu v-model="open" :location="location" :close-on-content-click="false">
    <template #activator="{ props: activator }">
      <VBtn
        v-bind="activator"
        variant="text"
        prepend-icon="fas fa-folder-open"
        class="header-control header-workspace"
        :aria-label="`Workspace: ${snapshot.workspace}`"
      >
        <span class="path-text" :title="snapshot.workspace"><bdi>{{ snapshot.workspace }}</bdi></span>
      </VBtn>
    </template>
    <VCard elevation="6" border class="header-menu workspace-panel">
      <h2>Workspace</h2>
      <p class="panel-path">{{ snapshot.workspace }}</p>
      <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
      <div class="panel-actions">
        <VBtn variant="tonal" color="primary" prepend-icon="fas fa-folder-tree" :disabled="busy" @click="choose">
          Choose workspace
        </VBtn>
      </div>
      <RecentWorkspaces
        :snapshot="snapshot"
        :disabled="busy"
        @open="(path) => run(() => overview.selectWorkspace(path), { close: true })"
        @remove="(path) => run(() => overview.forgetWorkspace(path), { close: false })"
      />
    </VCard>
  </VMenu>
</template>
