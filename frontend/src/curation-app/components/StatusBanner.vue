<script setup lang="ts">
import { computed } from "vue";
import { VAlert } from "vuetify/components";
import { ServerStopped, SessionMissing } from "../api/client";
import { useOverviewStore } from "../stores/overview";

const overview = useOverviewStore();

/** What the curator should do while the state of the local server cannot be loaded. */
const message = computed(() => {
  const error = overview.error;
  if (error === null) return null;
  if (error instanceof ServerStopped) return "The local server stopped. Start pkdb curate again.";
  if (error instanceof SessionMissing) return "This page has no session. Open the link that pkdb curate printed.";
  return `The state of the local server could not be loaded. ${error.message}`;
});
</script>

<template>
  <VAlert
    v-if="message"
    type="error"
    variant="tonal"
    density="compact"
    rounded="0"
    class="status-banner status-alert"
  >
    {{ message }}
  </VAlert>
</template>

<style scoped>
.status-banner {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
