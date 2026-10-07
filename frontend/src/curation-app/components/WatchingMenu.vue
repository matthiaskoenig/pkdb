<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { VAlert, VBtn, VCard, VChip, VMenu } from "vuetify/components";
import type { Snapshot } from "../api/types";
import { useOverviewStore } from "../stores/overview";

type Anchor = "bottom end" | "bottom";

const props = withDefaults(defineProps<{ snapshot: Snapshot; location?: Anchor }>(), { location: "bottom end" });

const overview = useOverviewStore();
const open = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);

// A failure belongs to the action that caused it, not to the next visit of the menu.
watch(open, (value) => {
  if (value) error.value = null;
});

const state = computed(() =>
  props.snapshot.paused
    ? { label: "Paused", tone: "warning" as const }
    : { label: "Active", tone: "success" as const },
);
/** The local server does not answer: the menu shows the last known state and offers no actions. */
const stale = computed(() => overview.error !== null);
/** Uploads with an unknown outcome, which Resume checks on the server first. */
const unknownUploads = computed(() => props.snapshot.studies.some((row) => row.status === "unknown"));

/** Pause the automatic actions, or check unknown uploads and resume them. */
async function toggle(): Promise<void> {
  busy.value = true;
  error.value = null;
  try {
    if (props.snapshot.paused) await overview.resume();
    else await overview.pause(true);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : String(caught);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <VMenu v-model="open" :location="location" :close-on-content-click="false">
    <template #activator="{ props: activator }">
      <VBtn
        v-bind="activator"
        variant="text"
        prepend-icon="fas fa-eye"
        class="header-control"
        :aria-label="`File watching: ${state.label}`"
      >
        <span class="header-control-label">File watching</span>
        <VChip :color="stale ? undefined : state.tone" variant="tonal" size="small" class="status-chip">
          {{ state.label }}
        </VChip>
      </VBtn>
    </template>
    <VCard elevation="6" border class="header-menu watching-panel">
      <div class="panel-heading">
        <h2>File watching</h2>
        <VChip :color="stale ? undefined : state.tone" variant="tonal" size="small" class="status-chip">
          {{ state.label }}
        </VChip>
      </div>
      <p v-if="stale" class="panel-note">The local server does not answer. This is the last known state.</p>
      <p v-if="snapshot.paused">Automatic actions are paused. Saved files wait until you resume.</p>
      <p v-else>Saving a file starts the On save action of its study.</p>
      <p v-if="snapshot.paused && unknownUploads" class="panel-note">
        Resume first checks the uploads with an unknown outcome on the server.
      </p>
      <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
      <div class="panel-actions">
        <VBtn
          variant="tonal"
          color="primary"
          :prepend-icon="snapshot.paused ? 'fas fa-play' : 'fas fa-pause'"
          :loading="busy"
          :disabled="stale"
          @click="toggle"
        >
          {{ snapshot.paused ? "Resume automatic actions" : "Pause automatic actions" }}
        </VBtn>
      </div>
    </VCard>
  </VMenu>
</template>
