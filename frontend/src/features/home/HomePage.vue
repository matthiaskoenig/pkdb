<script setup lang="ts">
import HomeStatistics from "./HomeStatistics.vue";
defineOptions({ name: "HomePage" });
</script>
<template>
  <div class="home-page">
    <section class="home-hero" aria-labelledby="home-title">
      <p class="eyebrow">The pharmacokinetics database</p>
      <h1 id="home-title">Evidence for better models.</h1>
      <div class="home-purpose">
        <div>
          <h2>Our mission</h2>
          <p>
            Make curated pharmacokinetic data accessible and reusable, with the
            study context needed to interpret it.
          </p>
        </div>
        <div>
          <h2>Our vision</h2>
          <p>
            Enable reproducible, individualized and stratified computational
            modeling through connected pharmacokinetic evidence.
          </p>
        </div>
      </div>
      <v-btn to="/data" color="primary" size="large">Explore data</v-btn>
    </section>
    <HomeStatistics />
  </div>
</template>
<style scoped>
.home-page {
  max-width: 1200px;
  margin: auto;
}
.home-hero {
  max-width: none;
  padding: 2rem 0 2.5rem;
}
.home-hero h1 {
  font-size: clamp(2.2rem, 4vw, 3.5rem);
  margin-bottom: 1.75rem;
}
.home-hero .v-btn {
  color: #fff;
}
.home-purpose {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.5rem 3rem;
  margin-bottom: 1.75rem;
}
.home-purpose h2 {
  font-size: 1rem;
  margin: 0 0 0.5rem;
}
.home-purpose p {
  max-width: 48ch;
  font-size: 1.05rem;
  line-height: 1.65;
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.8);
}
@media (max-width: 600px) {
  .home-hero { padding: 1.25rem 0 2rem; }
  .home-purpose { grid-template-columns: 1fr; }
}
</style>
