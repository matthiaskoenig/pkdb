<script setup lang="ts">
import { computed } from "vue";
import { useSearchStore } from "../../../stores/search";
import { fields } from "../fields";
import { scopeLabels, scopeHelp } from "../model";
import FilterSelect from "./FilterSelect.vue";
const search = useSearchStore(),
  emit = defineEmits<{ search: [] }>();
const groups = [
  "Studies",
  "Subjects",
  "Interventions",
  "Measurements",
] as const;
const appliedLoading = computed(() => search.selection.status === "loading");
function update(key: string, values: string[]) {
  search.draft.filters[key] = values;
}
</script>
<template>
  <form aria-label="Research filters" @submit.prevent="emit('search')">
    <div class="filter-heading">
      <h2>Build your search</h2>
      <v-btn variant="text" size="small" @click="search.resetDraft()">
        Reset
      </v-btn>
    </div>
    <p class="muted">Choose filters, then apply them with Search.</p>
    <v-expansion-panels
      multiple
      :model-value="[0, 1, 2, 3]"
      variant="accordion"
    >
      <v-expansion-panel v-for="group in groups" :key="group" :title="group">
        <v-expansion-panel-text>
          <FilterSelect
            v-for="field in fields.filter((f) => f.group === group)"
            :key="field.key"
            :field="field"
            :model-value="search.draft.filters[field.key] ?? []"
            @update:model-value="update(field.key, $event)"
          />
          <fieldset v-if="group === 'Studies'" class="toggle-group">
            <legend>Study licence</legend>
            <v-checkbox
              v-model="search.draft.licences.open"
              label="Open licence"
              hide-details
            /><v-checkbox
              v-model="search.draft.licences.closed"
              label="Closed licence"
              hide-details
            />
          </fieldset>
          <fieldset v-if="group === 'Subjects'" class="toggle-group">
            <legend>Subject categories</legend>
            <v-checkbox
              v-model="search.draft.subjects.groups"
              label="Groups"
              hide-details
            /><v-checkbox
              v-model="search.draft.subjects.individuals"
              label="Individuals"
              hide-details
            />
          </fieldset>
          <fieldset v-if="group === 'Measurements'" class="toggle-group">
            <legend>Measurement data</legend>
            <v-checkbox
              v-model="search.draft.types.output"
              label="Scalar measurements"
              hide-details
            /><v-checkbox
              v-model="search.draft.types.timecourse"
              label="Timecourses"
              hide-details
            /><v-checkbox
              v-model="search.draft.types.array"
              label="Scatter data"
              hide-details
            />
          </fieldset>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
    <fieldset class="scope-control">
      <legend>Selection scope</legend>
      <v-radio-group v-model="search.draft.scope" hide-details>
        <v-radio value="matching" :label="scopeLabels.matching" /><v-radio
          value="studies"
          :label="scopeLabels.studies"
        />
      </v-radio-group>
      <p class="muted">{{ scopeHelp[search.draft.scope] }}</p>
    </fieldset>
    <div class="filter-submit">
      <p v-if="search.dirty" role="status" class="pending">
        Changes not applied
      </p>
      <v-btn type="submit" color="primary" block :aria-busy="appliedLoading">
        Search
      </v-btn>
    </div>
  </form>
</template>
