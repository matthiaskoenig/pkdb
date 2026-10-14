<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { VAlert } from "vuetify/components";
import { useStudyViews } from "../../study-views/context";
import { visibleSections, type ActionFailure } from "../../study-views/study";

/**
 * A failed action: what could not be done, in bold, and why below it; some of its issues with a
 * link to the section with all of them; and what the local server said about it in Details, with
 * Copy details and Show in Activity. The links need `study`, the study of the page. The slot
 * `append` puts an action, such as Retry, at the end of the alert. On a page the curator closes it;
 * in a dialog or a menu, and for a read that loads again, `closable` is false: the alert goes with
 * the next attempt or when the dialog opens again, and closing it would drop the focus to the page.
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
const views = useStudyViews();
/** The sections that the reader sees, the only ones a failure links to. */
const sections = computed(() => visibleSections(views.capabilities.value));
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
      class="action-failure-detail failure-detail"
      tabindex="0"
      >{{ failure.details.detail }}</pre>
    <ul v-if="failure.issues.length" class="action-failure-issues">
      <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
      <li v-if="failure.more">and {{ failure.more }} more</li>
    </ul>
    <RouterLink
      v-if="failure.link && study && sections.includes(failure.link.section)"
      :to="views.routes.section(study, failure.link.section)"
      class="action-failure-link"
    >
      {{ failure.link.label }}
    </RouterLink>
    <component
      :is="views.parts.failureDetails"
      v-if="failure.details && views.parts.failureDetails"
      :text="failure.text"
      :details="failure.details"
    >
      <RouterLink
        v-if="study && failure.details.activityId && views.capabilities.value.jobs"
        :to="views.routes.section(study, 'activity', { entry: failure.details.activityId })"
        class="action-failure-activity"
      >
        Show in Activity
      </RouterLink>
    </component>
    <template v-if="$slots.append" #append>
      <slot name="append" />
    </template>
  </VAlert>
</template>

<style scoped>
.action-failure-text {
  margin: 0;
  font-weight: 600;
}
/* The lines of the detail are capped by .failure-detail in styles.css. */
.action-failure-detail {
  margin: 2px 0 0;
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
