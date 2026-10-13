<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRoute } from "vue-router";
import { VApp, VMain } from "vuetify/components";
import AppHeader from "./components/AppHeader.vue";
import StatusBanner from "./components/StatusBanner.vue";
import { useColorTheme } from "./composables/useColorTheme";
import { useOverviewStore } from "./stores/overview";

const overview = useOverviewStore();
useColorTheme().restore();

const route = useRoute();
/** A page without the app bar, such as a PDF in a tab of its own. */
const bare = computed(() => route.meta.bare === true);

// The header of every page shows the state of the local server, so the app polls it on every page.
onMounted(() => void overview.start());
onBeforeUnmount(() => overview.stop());
</script>

<template>
  <VApp>
    <AppHeader v-if="!bare" />
    <VMain class="app-main">
      <StatusBanner />
      <RouterView />
    </VMain>
  </VApp>
</template>

<style scoped>
/* Vuetify slides the main area for 0.2 s when its padding changes. Its padding changes only when
   the app bar comes or goes with the route, between a PDF in a tab of its own and the other
   pages: the next page stands where it belongs from its first frame on. */
.app-main {
  transition: none;
}
</style>
