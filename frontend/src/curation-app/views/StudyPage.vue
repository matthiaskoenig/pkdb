<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { VContainer } from "vuetify/components";

const route = useRoute();
const identity = computed(
  () => `${String(route.params.substance)}/${String(route.params.name)}`,
);
</script>

<template>
  <VContainer fluid>
    <h1>{{ identity }}</h1>
  </VContainer>
</template>
