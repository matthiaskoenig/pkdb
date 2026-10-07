<script setup lang="ts">
import { computed, ref } from "vue";
import { VAlert, VBtn, VCard, VChip, VMenu } from "vuetify/components";
import type { ConnectionStatus, Snapshot, VocabularyState } from "../api/types";
import { useOverviewStore } from "../stores/overview";

type Tone = "success" | "warning" | "error" | "info";
type Anchor = "bottom end" | "bottom";

const props = withDefaults(defineProps<{ snapshot: Snapshot; location?: Anchor }>(), { location: "bottom end" });
const emit = defineEmits<{ settings: [] }>();
const open = ref(false);

/** The badge and the explanation of each connection state. */
const STATES: Record<ConnectionStatus, { label: string; tone: Tone; detail: string }> = {
  connected: { label: "Connected", tone: "success", detail: "The server and its database answer." },
  offline: { label: "Offline", tone: "info", detail: "Offline mode: the app sends no network requests." },
  connecting: { label: "Connecting", tone: "info", detail: "The app checks the server and its database." },
  not_configured: {
    label: "Not configured",
    tone: "warning",
    detail: "No PK-DB server is set. Set it in the connection settings or with PKDB_ENDPOINT.",
  },
  unauthorized: { label: "Rejected API key", tone: "error", detail: "The server rejected the API key." },
  incompatible: { label: "Update pkdb", tone: "warning", detail: "The server needs a newer pkdb." },
  error: { label: "Error", tone: "error", detail: "The server check failed." },
};

const VOCABULARY: Record<VocabularyState["status"], string> = {
  offline: "Offline",
  not_checked: "Not checked yet",
  current: "Current",
};

const overview = useOverviewStore();
const state = computed(() => STATES[props.snapshot.connection]);
/** The local server does not answer: the menu shows the last known state. */
const stale = computed(() => overview.error !== null);
const checked = computed(() =>
  props.snapshot.checked_at ? new Date(props.snapshot.checked_at).toLocaleTimeString() : null,
);
const versions = computed(
  () =>
    `Client ${props.snapshot.client_version}` +
    (props.snapshot.server_version ? ` · server ${props.snapshot.server_version}` : ""),
);

function settings(): void {
  open.value = false;
  emit("settings");
}
</script>

<template>
  <VMenu v-model="open" :location="location" :close-on-content-click="false">
    <template #activator="{ props: activator }">
      <VBtn
        v-bind="activator"
        variant="text"
        prepend-icon="fas fa-plug"
        class="header-control"
        :aria-label="`Connection: ${state.label}`"
      >
        <span class="header-control-label">Connection</span>
        <VChip :color="stale ? undefined : state.tone" variant="tonal" size="small" class="status-chip">
          {{ state.label }}
        </VChip>
      </VBtn>
    </template>
    <VCard elevation="6" border class="header-menu connection-panel">
      <div class="panel-heading">
        <h2>Connection</h2>
        <VChip :color="stale ? undefined : state.tone" variant="tonal" size="small" class="status-chip">
          {{ state.label }}
        </VChip>
      </div>
      <p v-if="stale" class="panel-note">The local server does not answer. This is the last known state.</p>
      <p>{{ state.detail }}</p>
      <VAlert v-if="snapshot.connection_error" type="error" variant="tonal" density="compact" class="status-alert">
        {{ snapshot.connection_error }}
      </VAlert>
      <p v-if="checked" class="panel-note">Last checked {{ checked }}</p>
      <dl class="panel-facts">
        <dt>Upload target</dt>
        <dd>{{ snapshot.endpoint || "Not configured" }}</dd>
        <dt>PK-DB account</dt>
        <dd>{{ snapshot.account || "Not authenticated" }}</dd>
        <dt>Vocabulary</dt>
        <dd>{{ VOCABULARY[snapshot.vocabulary.status] }}</dd>
        <dt>pkdb version</dt>
        <dd>{{ versions }}</dd>
      </dl>
      <p v-if="snapshot.update_required">
        <template v-if="snapshot.server_version">The server runs pkdb {{ snapshot.server_version }}. </template>Stop
        pkdb curate, run <code>pkdb update</code> and start pkdb curate again.
      </p>
      <div class="panel-actions">
        <VBtn variant="tonal" color="primary" prepend-icon="fas fa-gear" @click="settings">
          Connection settings
        </VBtn>
      </div>
    </VCard>
  </VMenu>
</template>
