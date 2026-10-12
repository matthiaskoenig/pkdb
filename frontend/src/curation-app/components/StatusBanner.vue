<script setup lang="ts">
import { computed } from "vue";
import { VAlert } from "vuetify/components";
import { ServerStopped, SessionMissing } from "../api/client";
import { useOverviewStore } from "../stores/overview";
import { failureOf } from "../study";
import ActionFailureAlert from "./ActionFailureAlert.vue";

const overview = useOverviewStore();

/** What the curator should do while the local server cannot be reached or the page has no session. */
const message = computed(() => {
  const error = overview.error;
  if (error instanceof ServerStopped) return "The local server stopped. Start pkdb curate again.";
  if (error instanceof SessionMissing) return "This page has no session. Open the link that pkdb curate printed.";
  return null;
});
/** Why the state of the local server could not be loaded otherwise, with what the server said. */
const failure = computed(() => {
  const error = overview.error;
  if (error === null || message.value !== null) return null;
  return failureOf(error, "The state of the local server could not be loaded.");
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
  <!-- It goes with the next state that the local server answers: no close button. -->
  <ActionFailureAlert
    v-else-if="failure"
    :failure="failure"
    :closable="false"
    rounded="0"
    class="status-banner"
  />
</template>

<style scoped>
.status-banner {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
