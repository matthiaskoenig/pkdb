<script setup lang="ts">
import { searchExamples } from "../examples";
import type { Criteria } from "../model";
defineEmits<{ choose: [criteria: Criteria] }>();
</script>
<template>
  <details class="search-examples">
    <summary>Example searches</summary>
    <p>
      Choose an example to replace your draft. Results change only
      after you select Search.
    </p>
    <ul>
      <li v-for="example in searchExamples" :key="example.id">
        <button
          type="button"
          class="example-button"
          @click="$emit('choose', example.criteria())"
        >
          {{ example.title }}
        </button>
        <p>{{ example.description }}</p>
      </li>
    </ul>
  </details>
</template>
<style scoped>
.search-examples {
  margin-block: 1rem;
}
summary {
  cursor: pointer;
  font-weight: 600;
}
ul {
  padding-inline-start: 1.25rem;
}
li {
  margin-block: 1rem;
}
.example-button {
  color: rgb(var(--v-theme-primary));
  text-decoration: underline;
  text-align: left;
}
</style>
