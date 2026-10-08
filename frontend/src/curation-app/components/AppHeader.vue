<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useDisplay } from "vuetify";
import { VAppBar, VBtn, VCard, VDivider, VMenu, VSpacer } from "vuetify/components";
import logo from "../assets/pkdb_logo.png";
import { useColorTheme } from "../composables/useColorTheme";
import { useDialogStore } from "../stores/dialogs";
import { useOverviewStore } from "../stores/overview";
import AuthorStatus from "./AuthorStatus.vue";
import ConnectionMenu from "./ConnectionMenu.vue";
import SettingsDialog from "./SettingsDialog.vue";
import WatchingMenu from "./WatchingMenu.vue";
import WorkspaceDialog from "./WorkspaceDialog.vue";
import WorkspaceMenu from "./WorkspaceMenu.vue";

/** Below this width the controls of the header move into one menu. */
const COLLAPSE_BELOW = 960;

const overview = useOverviewStore();
const dialogs = useDialogStore();
const theme = useColorTheme();
const { width } = useDisplay();
const wide = computed(() => width.value >= COLLAPSE_BELOW);
const panel = ref(false);
// The collapsed menu closes when the header becomes wide, so that it does not open again by
// itself when the window becomes narrow.
watch(wide, () => {
  panel.value = false;
});
const snapshot = computed(() => overview.snapshot);

/**
 * The control of the header that takes the focus when a dialog closes and the control that
 * opened it is gone, such as an item of a menu: `selector` in the wide header, else the header
 * menu.
 */
function headerControl(selector: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(`.app-header ${wide.value ? selector : ".header-menu-button"}`);
}

/** Open a dialog from the collapsed menu, which closes first. */
function fromPanel(open: () => void): void {
  panel.value = false;
  open();
}
</script>

<template>
  <VAppBar elevation="0" class="app-header">
    <RouterLink to="/" class="brand">
      <img class="brand-logo" :src="logo" alt="PK-DB" width="40" height="40" />
      <span>Local curation</span>
    </RouterLink>
    <VSpacer />
    <div v-if="wide" class="header-controls">
      <template v-if="snapshot">
        <WorkspaceMenu :snapshot="snapshot" @choose="dialogs.openWorkspace" />
        <WatchingMenu :snapshot="snapshot" />
        <ConnectionMenu :snapshot="snapshot" @settings="dialogs.openSettings" />
        <AuthorStatus :author="snapshot.author" @settings="dialogs.openSettings" />
      </template>
      <VBtn
        icon="fas fa-gear"
        variant="text"
        aria-label="Settings"
        class="header-settings"
        @click="dialogs.openSettings"
      />
      <VBtn icon="fas fa-circle-half-stroke" variant="text" aria-label="Toggle color theme" @click="theme.toggle" />
    </div>
    <VMenu v-else v-model="panel" location="bottom end" :close-on-content-click="false">
      <template #activator="{ props: activator }">
        <VBtn v-bind="activator" icon="fas fa-bars" variant="text" aria-label="Header menu" class="header-menu-button" />
      </template>
      <VCard elevation="6" border class="header-menu header-panel">
        <template v-if="snapshot">
          <WorkspaceMenu :snapshot="snapshot" location="bottom" @choose="fromPanel(dialogs.openWorkspace)" />
          <WatchingMenu :snapshot="snapshot" location="bottom" />
          <ConnectionMenu :snapshot="snapshot" location="bottom" @settings="fromPanel(dialogs.openSettings)" />
          <AuthorStatus :author="snapshot.author" @settings="fromPanel(dialogs.openSettings)" />
          <VDivider />
        </template>
        <VBtn variant="text" prepend-icon="fas fa-gear" class="header-control" @click="fromPanel(dialogs.openSettings)">
          Settings
        </VBtn>
        <VBtn variant="text" prepend-icon="fas fa-circle-half-stroke" class="header-control" @click="theme.toggle">
          Toggle color theme
        </VBtn>
      </VCard>
    </VMenu>
  </VAppBar>
  <WorkspaceDialog v-model="dialogs.workspace" :fallback-focus="() => headerControl('.header-workspace')" />
  <SettingsDialog v-model="dialogs.settings" :fallback-focus="() => headerControl('.header-settings')" />
</template>
