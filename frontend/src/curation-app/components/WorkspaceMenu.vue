<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { VAlert, VBtn, VCard, VMenu } from "vuetify/components";
import type { Snapshot } from "../api/types";
import { splitPath } from "../paths";
import { useOverviewStore } from "../stores/overview";
import RecentWorkspaces from "./RecentWorkspaces.vue";

type Anchor = "bottom start" | "bottom";

const props = withDefaults(defineProps<{ snapshot: Snapshot; location?: Anchor }>(), { location: "bottom start" });
const emit = defineEmits<{ choose: [] }>();

const overview = useOverviewStore();
const open = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);
/** The header shows the folder name; the menu, the title and the accessible name the path. */
const name = computed(() => splitPath(props.snapshot.workspace).name);
/** The local server does not answer: the menu shows the last known state and offers no actions. */
const stale = computed(() => overview.error !== null);

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
        :title="snapshot.workspace"
        :aria-label="`Workspace: ${snapshot.workspace}`"
      >
        <span class="text-truncate">{{ name }}</span>
      </VBtn>
    </template>
    <VCard elevation="6" border class="header-menu workspace-panel">
      <h2>Workspace</h2>
      <p class="panel-path">{{ snapshot.workspace }}</p>
      <p v-if="stale" class="panel-note">The local server does not answer. This is the last known state.</p>
      <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
      <div class="panel-actions">
        <VBtn
          variant="tonal"
          color="primary"
          prepend-icon="fas fa-folder-tree"
          :disabled="busy || stale"
          @click="choose"
        >
          Choose workspace
        </VBtn>
      </div>
      <RecentWorkspaces
        :snapshot="snapshot"
        :disabled="busy || stale"
        @open="(path) => run(() => overview.selectWorkspace(path), { close: true })"
        @remove="(path) => run(() => overview.forgetWorkspace(path), { close: false })"
      />
    </VCard>
  </VMenu>
</template>
