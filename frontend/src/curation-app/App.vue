<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import { VApp, VMain } from "vuetify/components";
import AppHeader from "./components/AppHeader.vue";
import StatusBanner from "./components/StatusBanner.vue";
import { useColorTheme } from "./composables/useColorTheme";
import { useOverviewStore } from "./stores/overview";

const overview = useOverviewStore();
useColorTheme().restore();

// The header of every page shows the state of the local server, so the app polls it on every page.
onMounted(() => void overview.start());
onBeforeUnmount(() => overview.stop());
</script>

<template>
  <VApp>
    <AppHeader />
    <VMain>
      <StatusBanner />
      <RouterView />
    </VMain>
  </VApp>
</template>
