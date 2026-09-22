<script setup lang="ts">
import { computed } from "vue";
import { useSearchStore } from "../../../stores/search";
import { fields } from "../fields";
import { scopeLabels, scopeHelp } from "../model";
const search = useSearchStore();
const applied = computed(() =>
  fields.flatMap((f) =>
    (search.applied.filters[f.key] ?? []).map((id) => ({
      key: f.key,
      id,
      label: f.label,
    })),
  ),
);
const drafts = computed(() =>
  fields.flatMap((f) =>
    (search.draft.filters[f.key] ?? []).map((id) => ({
      key: f.key,
      id,
      label: f.label,
    })),
  ),
);
function remove(key: string, id: string) {
  search.draft.filters[key] = (search.draft.filters[key] ?? []).filter(
    (value) => value !== id,
  );
}
</script>
<template>
  <section class="query-summary" aria-label="Applied query">
    <p class="eyebrow">Applied query</p>
    <h2>{{ scopeLabels[search.applied.scope] }}</h2>
    <p class="muted">{{ scopeHelp[search.applied.scope] }}</p>
    <div v-if="applied.length" class="chip-list">
      <v-chip
        v-for="item in applied"
        :key="`${item.key}:${item.id}`"
        size="small"
      >
        {{ item.label }}: {{ item.id }}
      </v-chip>
    </div>
    <p v-else>No field filters applied.</p>
    <p class="summary-toggles">
      Subjects:
      {{
        Object.entries(search.applied.subjects)
          .filter(([, yes]) => yes)
          .map(([name]) => name)
          .join(", ") || "none"
      }}
      · Licences:
      {{
        Object.entries(search.applied.licences)
          .filter(([, yes]) => yes)
          .map(([name]) => name)
          .join(", ") || "none"
      }}
      · Types:
      {{
        Object.entries(search.applied.types)
          .filter(([, yes]) => yes)
          .map(([name]) => (name === "array" ? "scatter" : name))
          .join(", ") || "none"
      }}
    </p>
    <div v-if="search.dirty" class="draft-summary">
      <strong>Changes not applied</strong>
      <p>Rows, counts and downloads still use the applied query above.</p>
      <div class="chip-list">
        <v-chip
          v-for="item in drafts"
          :key="`${item.key}:${item.id}`"
          closable
          :aria-label="`Remove draft ${item.id}`"
          @click:close="remove(item.key, item.id)"
        >
          {{ item.label }}: {{ item.id }}
        </v-chip>
      </div>
    </div>
  </section>
</template>
