<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { accountApi } from "../../../api/account";
import { apiBase } from "../../../api/client";
import type { Provider } from "../../../api/session";
const providers = ref<Provider[]>([]);
const controller = new globalThis.AbortController();
onMounted(async () => {
  try {
    const result = await accountApi.providers(controller.signal);
    if (!controller.signal.aborted) providers.value = result;
  } catch {
    providers.value = [];
  }
});
onUnmounted(() => controller.abort());
</script>
<template>
  <div v-if="providers.length" class="mt-5">
    <v-divider class="mb-4" /><v-btn
      v-for="provider in providers"
      :key="provider"
      variant="outlined"
      block
      class="mt-2"
      :href="apiBase + '/api/v1/auth/' + provider + '/start'"
    >
      Continue with {{ provider === "github" ? "GitHub" : "ORCID" }}
    </v-btn>
  </div>
</template>
