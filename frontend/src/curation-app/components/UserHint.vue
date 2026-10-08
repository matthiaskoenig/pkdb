<script setup lang="ts">
import { VAlert, VBtn } from "vuetify/components";
import { useDialogStore } from "../stores/dialogs";

/** A write was refused without a user: what to do, and a button that opens the settings. */
defineProps<{ text: string }>();

const dialogs = useDialogStore();
</script>

<template>
  <VAlert type="error" variant="tonal" density="compact" class="status-alert user-hint">
    <div class="user-hint-row">
      <p class="user-hint-text">{{ text }}</p>
      <VBtn variant="flat" color="primary" size="small" @click="dialogs.openSettings">Open settings</VBtn>
    </div>
  </VAlert>
</template>

<style scoped>
/* The button follows the text, and goes below it in a narrow column. */
.user-hint-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.user-hint-text {
  flex: 1 1 18rem;
  margin: 0;
}
</style>
