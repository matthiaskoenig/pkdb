<script setup lang="ts">
defineOptions({ name: "NotFoundPage" });
</script>
<template>
  <section class="content-page">
    <h1>Page not found</h1>
    <p>This address does not match a PK-DB page.</p>
    <v-btn to="/data" color="primary">Explore data</v-btn>
  </section>
</template>
