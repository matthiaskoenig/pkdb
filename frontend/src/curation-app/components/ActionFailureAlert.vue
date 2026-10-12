<script setup lang="ts">
import { RouterLink } from "vue-router";
import { VAlert } from "vuetify/components";
import { sectionRoute, type ActionFailure } from "../study";
import FailureDetails from "./FailureDetails.vue";

/**
 * A failed action: what could not be done, in bold, and why below it; some of its issues with a
 * link to the section with all of them; and what the local server said about it in Details, with
 * Copy details and Show in Activity. The links need `study`, the study of the page.
 */
withDefaults(
  defineProps<{
    failure: ActionFailure;
    study?: string | null;
    closable?: boolean;
  }>(),
  {
    study: null,
    closable: true,
  },
);
const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <VAlert
    type="error"
    variant="tonal"
    density="compact"
    :closable="closable"
    class="status-alert action-failure"
    @click:close="emit('close')"
  >
    <p class="action-failure-text">{{ failure.text }}</p>
    <pre
      v-if="failure.details?.detail"
      class="action-failure-detail"
      tabindex="0"
      >{{ failure.details.detail }}</pre>
    <ul v-if="failure.issues.length" class="action-failure-issues">
      <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
      <li v-if="failure.more">and {{ failure.more }} more</li>
    </ul>
    <RouterLink v-if="failure.link && study" :to="sectionRoute(study, failure.link.section)" class="action-failure-link">
      {{ failure.link.label }}
    </RouterLink>
    <FailureDetails
      v-if="failure.details"
      :text="failure.text"
      :details="failure.details"
    >
      <RouterLink
        v-if="study && failure.details.activityId"
        :to="
          sectionRoute(study, 'activity', { entry: failure.details.activityId })
        "
        class="action-failure-activity"
      >
        Show in Activity
      </RouterLink>
    </FailureDetails>
  </VAlert>
</template>

<style scoped>
.action-failure-text {
  margin: 0;
  font-weight: 600;
}
/* At most 6 lines of stderr; the rest scrolls, and Copy details has all of it. */
.action-failure-detail {
  max-height: calc(6 * 1.45em);
  margin: 2px 0 0;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8125rem;
  line-height: 1.45;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
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
