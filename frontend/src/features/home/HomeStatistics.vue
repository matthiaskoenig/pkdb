<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue";
import { useSessionStore } from "../../stores/session";
import { errorMessage } from "../../api/client";
import { fetchStatistics, type StatisticsOverview } from "./statistics";
import StatisticsDashboard from "./StatisticsDashboard.vue";
import { defaultCriteria, defaultView } from "../search/defaults";
import { encodeLocation } from "../search/codec";
import type { ResultTab } from "../search/model";
type StatisticsState =
  | { status: "idle" | "loading" }
  | { status: "ready"; overview: StatisticsOverview }
  | { status: "error"; message: string };
const session = useSessionStore(),
  state = ref<StatisticsState>({ status: "idle" });
let generation = 0,
  controller: AbortController | undefined;
async function load() {
  const own = ++generation;
  controller?.abort();
  if (!session.ready) {
    state.value = { status: "idle" };
    return;
  }
  const request = new globalThis.AbortController();
  controller = request;
  state.value = { status: "loading" };
  try {
    const overview = await fetchStatistics(request.signal);
    if (own === generation && !request.signal.aborted)
      state.value = { status: "ready", overview };
  } catch (error) {
    if (own === generation && !request.signal.aborted)
      state.value = { status: "error", message: errorMessage(error) };
  }
}
watch(() => [session.ready, session.epoch], load, {
  immediate: true,
  flush: "sync",
});
onUnmounted(() => {
  generation++;
  controller?.abort();
});
function destination(tab: ResultTab) {
  // Statistics count every visible study's records, not a filtered measurement subset.
  return {
    path: "/data",
    query: encodeLocation({
      criteria: { ...defaultCriteria(), scope: "studies" },
      view: { ...defaultView(), tab },
    }),
  };
}
</script>
<template>
  <section
    class="database-statistics"
    aria-labelledby="database-statistics-title"
    :aria-busy="state.status === 'loading'"
  >
    <h2 id="database-statistics-title">Database at a glance</h2>
    <p>
      Live counts from the studies you can access. Select a category to explore.
    </p>
    <p
      v-if="state.status === 'idle' || state.status === 'loading'"
      role="status"
    >
      Loading database counts…
    </p>
    <v-alert v-else-if="state.status === 'error'" type="error" role="alert">
      {{ state.message }}
      <v-btn variant="text" @click="load">Retry database counts</v-btn>
    </v-alert>
    <template v-else-if="state.status === 'ready'">
      <ul class="statistic-grid">
        <li v-for="row in state.overview.rows" :key="row.tab">
          <RouterLink :to="destination(row.tab)">
            <strong>{{ row.count.toLocaleString() }}</strong
            ><span>{{ row.label }}</span>
          </RouterLink>
        </li>
      </ul>
      <StatisticsDashboard :overview="state.overview" />
    </template>
  </section>
</template>
<style scoped>
.database-statistics {
  padding: 1.5rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
}
.database-statistics p {
  margin: 0.75rem 0 1.5rem;
}
.statistic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
  gap: 1rem;
  padding: 0;
  list-style: none;
}
.statistic-grid a {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 12px;
  text-decoration: none;
  color: rgb(var(--v-theme-on-surface));
}
.statistic-grid a:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
.statistic-grid strong {
  font-size: 1.75rem;
  font-variant-numeric: tabular-nums;
}
</style>
