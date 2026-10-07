<script setup lang="ts">
import { VApp, VAppBar, VMain } from "vuetify/components";
import logo from "./assets/pkdb_logo.png";
</script>

<template>
  <VApp>
    <VAppBar elevation="0" class="app-header">
      <RouterLink to="/" class="brand">
        <img class="brand-logo" :src="logo" alt="PK-DB" width="40" height="40" />
        <span>Local curation</span>
      </RouterLink>
    </VAppBar>
    <VMain>
      <RouterView />
    </VMain>
  </VApp>
</template>
