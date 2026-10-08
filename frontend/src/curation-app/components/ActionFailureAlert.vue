<script setup lang="ts">
import { VAlert } from "vuetify/components";
import { sectionRoute, type ActionFailure } from "../study";

/** A failed action of the study `study`: the text, some of its issues and a link to the section with all of them. */
defineProps<{ failure: ActionFailure; study: string }>();
const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <VAlert
    type="error"
    variant="tonal"
    density="compact"
    closable
    class="status-alert action-failure"
    @click:close="emit('close')"
  >
    <p class="action-failure-text">{{ failure.text }}</p>
    <ul v-if="failure.issues.length" class="action-failure-issues">
      <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
      <li v-if="failure.more">and {{ failure.more }} more</li>
    </ul>
    <RouterLink v-if="failure.link" :to="sectionRoute(study, failure.link.section)" class="action-failure-link">
      {{ failure.link.label }}
    </RouterLink>
  </VAlert>
</template>

<style scoped>
.action-failure-text {
  margin: 0;
}
.action-failure-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
  overflow-wrap: anywhere;
}
.action-failure-link {
  display: inline-block;
  margin-top: 4px;
}
</style>
