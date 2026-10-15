<script setup lang="ts">
import { computed } from "vue";
import { VChip } from "vuetify/components";
import type { ValidationIssue } from "../types";
import { hintOf, SEVERITY_ICONS, SEVERITY_LABELS, tipProblems } from "../problems";

/**
 * The problems of one place of a table, as its tooltip lists them: the severity chip, the code,
 * the message and the hint of each, errors first, at most five, then how many more there are.
 */
const props = defineProps<{ issues: readonly ValidationIssue[] }>();

const tip = computed(() => {
  const { shown, more } = tipProblems(props.issues);
  return { more, items: shown.map((issue) => ({ issue, hint: hintOf(issue) })) };
});
</script>

<template>
  <div class="problem-tip">
    <ul class="problem-tip-list">
      <li v-for="({ issue, hint }, index) in tip.items" :key="index" class="problem-tip-item">
        <div class="problem-head">
          <VChip
            size="small"
            variant="tonal"
            :color="issue.severity"
            :prepend-icon="SEVERITY_ICONS[issue.severity]"
            class="status-chip"
          >
            {{ SEVERITY_LABELS[issue.severity] }}
          </VChip>
          <code class="problem-code problem-tip-code">{{ issue.code }}</code>
        </div>
        <p class="problem-tip-message">{{ issue.message }}</p>
        <p v-if="hint" class="problem-tip-hint">{{ hint }}</p>
      </li>
    </ul>
    <p v-if="tip.more" class="problem-tip-more">and {{ tip.more }} more</p>
  </div>
</template>

<style scoped>
.problem-tip-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.problem-tip-message,
.problem-tip-hint,
.problem-tip-more {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
}
.problem-tip-hint,
.problem-tip-more {
  font-size: calc(0.8125 * var(--study-rem, 1rem));
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
