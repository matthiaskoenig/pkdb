<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VChip } from "vuetify/components";
import { useStudyViews } from "../context";
import type { Problem } from "../types";
import {
  acknowledgement,
  location,
  locationKey,
  SEVERITY_ICONS,
  SEVERITY_LABELS,
  suggestionView,
  tableQuery,
} from "../problems";

/**
 * One issue of the Problems and the Data sections: severity, code, message, location and
 * suggestions, with Show in table, Open in tables, Show notes and Acknowledge. A component of
 * its own, so that a long list renders only the issues whose props changed.
 */
const props = withDefaults(
  defineProps<{
    issue: Problem;
    /** The identity of the study, for the link to the Data section. */
    study: string;
    /** The start of the ids of the message and the location, unique in the page. */
    idBase: string;
    /** Whether the Data section can show the cell: only tables of the study. */
    showable: boolean;
    /** Acknowledged in the app, and the report of the study still lists it. */
    pending: boolean;
    /** Whether the local server validates the study after a write, or the curator does. */
    automatic: boolean;
    /** Why Acknowledge cannot be used now: review.json cannot be written, or a write runs. */
    disabled: boolean;
    /** Whether a validation is being queued. */
    validating: boolean;
    /** Whether a warning offers Acknowledge; the Data section lists the problems without it. */
    offersAcknowledge?: boolean;
    /** The query of the Data section that shows the notes of the issue above their table; null for another issue. */
    notesQuery?: Record<string, string> | null;
    /** Whether Open in tables opens the workbook at the place of the issue: only tables of the study. */
    opensTables?: boolean;
    /** Whether Open in tables of this issue runs. */
    opening?: boolean;
    /** Whether another action runs, so that Open in tables waits. */
    openDisabled?: boolean;
  }>(),
  { offersAcknowledge: true, notesQuery: null, opensTables: false, opening: false, openDisabled: false },
);
const emit = defineEmits<{ acknowledge: []; validate: []; "open-tables": [] }>();
const views = useStudyViews();
const capabilities = views.capabilities;

const where = computed(() => location(props.issue, { file: false }));
const suggestions = computed(() => (props.issue.suggestions ?? []).map(suggestionView));
const acknowledgeable = computed(() => props.offersAcknowledge && acknowledgement(props.issue) !== null);
const tableRoute = computed(() => views.routes.section(props.study, "data", tableQuery(props.issue) ?? {}));
const notesRoute = computed(() =>
  props.notesQuery ? views.routes.section(props.study, "data", props.notesQuery) : null,
);
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
        :prepend-icon="SEVERITY_ICONS[issue.severity]"
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
        automatic || !capabilities.edit
          ? "Acknowledged. It leaves this list after the next validation."
          : "Acknowledged. Validate the study to update this list."
      }}</span>
    </p>
    <div
      v-if="
        showable ||
        (capabilities.edit && opensTables) ||
        notesRoute ||
        (capabilities.edit && acknowledgeable && (!pending || !automatic))
      "
      class="problem-actions"
    >
      <VBtn
        v-if="showable"
        :to="tableRoute"
        variant="text"
        color="primary"
        prepend-icon="fas fa-table-cells"
        :aria-describedby="describedBy"
      >
        Show in table
      </VBtn>
      <VBtn
        v-if="capabilities.edit && opensTables"
        variant="text"
        color="primary"
        prepend-icon="fas fa-table"
        :disabled="openDisabled"
        :loading="opening"
        :aria-describedby="describedBy"
        class="problem-open-tables"
        @click="emit('open-tables')"
      >
        Open in tables
      </VBtn>
      <VBtn
        v-if="notesRoute"
        :to="notesRoute"
        variant="text"
        color="primary"
        prepend-icon="fas fa-note-sticky"
        :aria-describedby="describedBy"
      >
        Show notes
      </VBtn>
      <VBtn
        v-if="capabilities.edit && acknowledgeable && !pending"
        variant="text"
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
        v-else-if="capabilities.edit && acknowledgeable && !automatic"
        variant="text"
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
  font-size: calc(0.8125 * var(--study-rem, 1rem));
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
  width: var(--study-rem, 1rem);
  margin-inline: 0 8px;
}
</style>
