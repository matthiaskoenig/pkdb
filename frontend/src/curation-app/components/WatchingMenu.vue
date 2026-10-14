<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { VAlert, VBtn, VCard, VChip, VMenu } from "vuetify/components";
import type { Snapshot } from "../api/types";
import { formatTime } from "../overview";
import { useOverviewStore } from "../stores/overview";
import { stateChip } from "../stateChip";
import { failureOf, type ActionFailure } from "../study";
import ActionFailureAlert from "./ActionFailureAlert.vue";

type Anchor = "bottom end" | "bottom";

const props = withDefaults(
  defineProps<{
    snapshot: Snapshot;
    location?: Anchor;
    /** On the teal app bar: the chip of the button takes the colors of the bar. */
    bar?: boolean;
  }>(),
  { location: "bottom end", bar: false },
);

const overview = useOverviewStore();
const open = ref(false);
const busy = ref(false);
const failure = ref<ActionFailure | null>(null);

// A failure belongs to the action that caused it, not to the next visit of the menu.
watch(open, (value) => {
  if (value) failure.value = null;
});

/** The last failure of the watcher; it fails until a later check of the workspace succeeds. */
const watcher = computed(() => props.snapshot.watcher_error);
const failing = computed(() => watcher.value !== null && !watcher.value.recovered);
const state = computed(() =>
  failing.value
    ? { label: "Error", tone: "error" as const }
    : props.snapshot.paused
      ? { label: "Paused", tone: "warning" as const }
      : { label: "Active", tone: "success" as const },
);
/** The local server does not answer: the menu shows the last known state and offers no actions. */
const stale = computed(() => overview.error !== null);
/** The chip of the state on the button, and in the heading of the menu, which stands on the surface. */
const buttonChip = computed(() => stateChip(stale.value ? undefined : state.value.tone, props.bar));
const headingChip = computed(() => stateChip(stale.value ? undefined : state.value.tone, false));
/** Uploads with an unknown outcome, which Resume checks on the server first. */
const unknownUploads = computed(() => props.snapshot.studies.some((row) => row.status === "unknown"));

/** Pause the automatic actions, or check unknown uploads and resume them. */
async function toggle(): Promise<void> {
  busy.value = true;
  failure.value = null;
  try {
    if (props.snapshot.paused) await overview.resume();
    else await overview.pause(true);
  } catch (caught) {
    failure.value = failureOf(caught);
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
        <VChip :color="buttonChip.color" :variant="buttonChip.variant" size="small" :class="buttonChip.class">
          {{ state.label }}
        </VChip>
      </VBtn>
    </template>
    <VCard elevation="6" border class="header-menu watching-panel">
      <div class="panel-heading">
        <h2>File watching</h2>
        <VChip :color="headingChip.color" :variant="headingChip.variant" size="small" :class="headingChip.class">
          {{ state.label }}
        </VChip>
      </div>
      <p v-if="stale" class="panel-note">The local server does not answer. This is the last known state.</p>
      <p v-if="snapshot.paused">Automatic actions are paused. Saved files wait until you resume.</p>
      <p v-else>Saving a file starts the On save action of its study.</p>
      <p v-if="snapshot.paused && unknownUploads" class="panel-note">
        Resume first checks the uploads with an unknown outcome on the server.
      </p>
      <VAlert v-if="watcher && !watcher.recovered" type="error" variant="tonal" density="compact" class="status-alert watcher-error">
        <p class="watcher-error-text">File watching failed at {{ formatTime(watcher.time) }}. It tries again every second.</p>
        <pre v-if="watcher.detail" class="watcher-error-detail failure-detail" tabindex="0">{{ watcher.detail }}</pre>
        <p class="watcher-error-log">The log has the traceback: {{ snapshot.log_file }}</p>
      </VAlert>
      <p v-else-if="watcher" class="panel-note watcher-recovered">
        File watching works again after an error at {{ formatTime(watcher.time) }}.
      </p>
      <ActionFailureAlert v-if="failure" :failure="failure" :closable="false" />
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

<style scoped>
.watcher-error-text,
.watcher-error-log {
  margin: 0;
}
/* The lines of the detail are capped by .failure-detail in styles.css. */
.watcher-error-detail {
  margin: 2px 0;
}
.watcher-error-log {
  overflow-wrap: anywhere;
}
</style>
