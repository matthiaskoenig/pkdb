<script setup lang="ts">
import { computed, reactive, ref, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VDialog,
  VSpacer,
  VSwitch,
  VTextField,
} from "vuetify/components";
import { useOverviewStore, type Settings } from "../stores/overview";

const open = defineModel<boolean>({ default: false });

const overview = useOverviewStore();
const titleId = useId();
/** The settings when the dialog opened, to send only what the curator changed. */
const initial = { endpoint: "", user: "", offline: false };
const form = reactive({ endpoint: "", user: "", offline: false });
// Write-only: the key never comes from the server and leaves this field on submit and on close.
const apiKey = ref("");
const busy = ref(false);
const error = ref<string | null>(null);

const keyHint = computed(() =>
  overview.snapshot?.authenticated ? "A key is set. Leave this empty to keep it." : "No key is set.",
);

function prefill(): void {
  const snapshot = overview.snapshot;
  initial.endpoint = form.endpoint = snapshot?.endpoint ?? "";
  initial.user = form.user = snapshot?.user ?? "";
  initial.offline = form.offline = snapshot?.offline ?? false;
  apiKey.value = "";
  error.value = null;
}

/** The changed settings, and the API key when one was typed. */
function changes(): Settings {
  const settings: Settings = {};
  const endpoint = form.endpoint.trim();
  const user = form.user.trim();
  if (endpoint !== initial.endpoint) settings.endpoint = endpoint;
  if (user !== initial.user) settings.user = user;
  if (form.offline !== initial.offline) settings.offline = form.offline;
  if (apiKey.value) settings.api_key = apiKey.value;
  return settings;
}

async function submit(): Promise<void> {
  const settings = changes();
  apiKey.value = "";
  if (Object.keys(settings).length === 0) {
    open.value = false;
    return;
  }
  busy.value = true;
  error.value = null;
  try {
    await overview.configure(settings);
    open.value = false;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : String(caught);
  } finally {
    busy.value = false;
  }
}

watch(
  open,
  (value) => {
    if (value) prefill();
    else apiKey.value = "";
  },
  { immediate: true },
);
</script>

<template>
  <VDialog v-model="open" max-width="560" :aria-labelledby="titleId">
    <form @submit.prevent="submit">
      <VCard>
        <VCardItem>
          <VCardTitle :id="titleId" tag="h2">Connection settings</VCardTitle>
        </VCardItem>
        <VCardText class="settings-fields">
          <VAlert
            v-if="overview.snapshot?.author.reason"
            type="warning"
            variant="tonal"
            density="compact"
            class="status-alert"
          >
            {{ overview.snapshot.author.reason }}
          </VAlert>
          <VTextField
            v-model="form.endpoint"
            label="PK-DB server"
            type="url"
            placeholder="https://beta.pk-db.com"
            autocomplete="url"
            spellcheck="false"
            hint="Checks and uploads go to this server."
            persistent-hint
          />
          <VTextField
            v-model="form.user"
            label="PK-DB user"
            autocomplete="username"
            spellcheck="false"
            hint="With an API key, the server checks this user."
            persistent-hint
          />
          <VTextField
            v-model="apiKey"
            label="Personal API key"
            type="password"
            autocomplete="new-password"
            spellcheck="false"
            :hint="keyHint"
            persistent-hint
          />
          <VSwitch v-model="form.offline" label="Work offline" color="primary" hide-details inset />
          <p class="settings-note">
            Offline, pkdb curate sends no network requests. It keeps the API key in memory only, and the browser
            never stores it.
          </p>
          <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
        </VCardText>
        <VCardActions class="dialog-actions">
          <VSpacer />
          <VBtn variant="text" @click="open = false">Cancel</VBtn>
          <VBtn type="submit" variant="flat" color="primary" :loading="busy">Save settings</VBtn>
        </VCardActions>
      </VCard>
    </form>
  </VDialog>
</template>

<style scoped>
.settings-fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.settings-fields :deep(.v-messages__message) {
  line-height: 1.35;
}
.settings-note {
  margin: 0;
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
