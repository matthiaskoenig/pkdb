<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VChip } from "vuetify/components";
import type { ValidationIssue } from "../api/types";
import { acknowledgement, location, locationKey, SEVERITY_LABELS, suggestionView, tableQuery } from "../problems";
import { sectionRoute } from "../study";

/**
 * One issue of the Problems and the Sources sections: severity, code, message, location and
 * suggestions, with Show in table and Acknowledge. A component of its own, so that a long list
 * renders only the issues whose props changed.
 */
const props = withDefaults(
  defineProps<{
    issue: ValidationIssue;
    /** The identity of the study, for the link to the Tables section. */
    study: string;
    /** The start of the ids of the message and the location, unique in the page. */
    idBase: string;
    /** Whether the Tables section can show the cell: only tables of the study. */
    showable: boolean;
    /** Acknowledged in the app, and the report of the study still lists it. */
    pending: boolean;
    /** Whether the local server validates the study after a write, or the curator does. */
    automatic: boolean;
    /** Why Acknowledge cannot be used now: review.json cannot be written, or a write runs. */
    disabled: boolean;
    /** Whether a validation is being queued. */
    validating: boolean;
    /** Whether a warning offers Acknowledge; the Sources section lists the problems without it. */
    offersAcknowledge?: boolean;
  }>(),
  { offersAcknowledge: true },
);
const emit = defineEmits<{ acknowledge: []; validate: [] }>();

const where = computed(() => location(props.issue, { file: false }));
const suggestions = computed(() => (props.issue.suggestions ?? []).map(suggestionView));
const acknowledgeable = computed(() => props.offersAcknowledge && acknowledgement(props.issue) !== null);
const tableRoute = computed(() => sectionRoute(props.study, "tables", tableQuery(props.issue) ?? {}));
/** The message and the location describe the actions. */
const describedBy = computed(() =>
  where.value ? `${props.idBase}-message ${props.idBase}-location` : `${props.idBase}-message`,
);
</script>

<template>
  <li :data-key="locationKey(issue)" class="problem">
    <div class="problem-head">
      <VChip
        size="small"
        variant="tonal"
        :color="issue.severity"
        :prepend-icon="issue.severity === 'error' ? 'fas fa-circle-xmark' : 'fas fa-triangle-exclamation'"
        class="status-chip problem-severity"
      >
        {{ SEVERITY_LABELS[issue.severity] }}
      </VChip>
      <code class="problem-code">{{ issue.code }}</code>
    </div>
    <p :id="`${idBase}-message`" class="problem-message">{{ issue.message }}</p>
    <p v-if="where" :id="`${idBase}-location`" class="problem-fact problem-location">
      <i class="fas fa-crosshairs problem-icon" aria-hidden="true"></i>
      <span>{{ where }}</span>
    </p>
    <div v-if="suggestions.length" class="problem-fact problem-suggestions">
      <i class="fas fa-lightbulb problem-icon" aria-hidden="true"></i>
      <div class="problem-suggestion-list">
        <div v-for="(suggestion, number) in suggestions" :key="number" class="problem-suggestion">
          <div class="problem-suggestion-row">
            <span class="problem-suggestion-lead">{{ suggestion.lead }}</span>
            <ul v-if="suggestion.candidates.length" class="problem-candidates">
              <li v-for="(candidate, place) in suggestion.candidates" :key="place">
                <code class="problem-candidate">{{ candidate }}</code>
              </li>
            </ul>
          </div>
          <p v-if="suggestion.note" class="problem-suggestion-note">{{ suggestion.note }}</p>
        </div>
      </div>
    </div>
    <p v-if="pending" class="problem-fact problem-acknowledged">
      <i class="fas fa-check problem-icon" aria-hidden="true"></i>
      <span>{{
        automatic
          ? "Acknowledged. It leaves this list after the next validation."
          : "Acknowledged. Validate the study to update this list."
      }}</span>
    </p>
    <div v-if="showable || (acknowledgeable && (!pending || !automatic))" class="problem-actions">
      <VBtn
        v-if="showable"
        :to="tableRoute"
        variant="text"
        density="compact"
        color="primary"
        prepend-icon="fas fa-table-cells"
        :aria-describedby="describedBy"
      >
        Show in table
      </VBtn>
      <VBtn
        v-if="acknowledgeable && !pending"
        variant="text"
        density="compact"
        color="primary"
        prepend-icon="fas fa-check"
        :disabled="disabled"
        :aria-describedby="describedBy"
        class="problem-acknowledge"
        @click="emit('acknowledge')"
      >
        Acknowledge
      </VBtn>
      <VBtn
        v-else-if="acknowledgeable && !automatic"
        variant="text"
        density="compact"
        color="primary"
        prepend-icon="fas fa-circle-check"
        :disabled="disabled"
        :loading="validating"
        class="problem-validate"
        @click="emit('validate')"
      >
        Validate
      </VBtn>
    </div>
  </li>
</template>

<style scoped>
.problem {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}
.problem + .problem {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.problem-location {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.problem-suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
/* The candidates follow their lead text, or go below it when it is long. */
.problem-suggestion-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 8px;
}
.problem-suggestion-note {
  margin: 2px 0 0;
}
.problem-candidates {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
/* Each candidate is a tinted chip, so that one with a space never reads as two. */
.problem-candidate {
  display: inline-block;
  padding: 0 6px;
  border-radius: 4px;
  background-color: rgba(var(--v-theme-on-surface), 0.08);
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.problem-acknowledged .problem-icon {
  color: rgb(var(--v-theme-success));
}
/* The icons of the buttons stand in the column of the icons of the facts above, and their
   labels start where the text of the facts does: 8 px of padding sit outside the content edge,
   then the 1rem wide icon and its 8 px gap. */
.problem-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-inline-start: -8px;
}
.problem-actions :deep(.v-btn) {
  padding-inline: 8px;
}
.problem-actions :deep(.v-btn__prepend) {
  justify-content: center;
  width: 1rem;
  margin-inline: 0 8px;
}
</style>
