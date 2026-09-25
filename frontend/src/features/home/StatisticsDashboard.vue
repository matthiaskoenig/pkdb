<script setup lang="ts">
import { computed, ref } from "vue";
import StatisticsChart from "./StatisticsChart.vue";
import type { StatisticsOverview } from "./statistics";
import type { OverviewTrace } from "./chart";
const props = defineProps<{ overview: StatisticsOverview }>();
const cumulative = ref(true);
const from = ref(0), to = ref(9999);
const parameter = ref("");
const substanceLimit = ref(15);
const years = computed(() => props.overview.years.filter(row => row.year! >= from.value && row.year! <= to.value));
const parameterOptions = computed(() => [...new Map(props.overview.parameters.map(p => [p.sid, p.name])).entries()].sort((a, b) => a[1].localeCompare(b[1])));
function trace(name: string, x: (number | string)[], y: number[], color: string, line = false): OverviewTrace {
  return { name, x, y, type: line ? "scatter" : "bar", ...(line ? { mode: "lines+markers" as const } : {}), marker: { color } };
}
const studies = computed(() => [trace("Studies", years.value.map(r => r.year!), years.value.map(r => cumulative.value ? r.cumulative_study_count : r.study_count), "#278a99", cumulative.value)]);
const substances = computed(() => [trace("Substances", years.value.map(r => r.year!), years.value.map(r => cumulative.value ? r.cumulative_substance_count : r.substance_count), "#8364b5", cumulative.value)]);
const parameters = computed(() => {
  const rows = props.overview.parameters.filter(p => !parameter.value || p.sid === parameter.value);
  const totals = new Map<number | null, { reported: number; calculated: number }>();
  for (const row of rows) {
    const total = totals.get(row.year) ?? { reported: 0, calculated: 0 };
    total.reported += row.reported; total.calculated += row.calculated; totals.set(row.year, total);
  }
  const x = years.value.map(r => r.year!);
  return [trace("Reported", x, x.map(y => totals.get(y)?.reported ?? 0), "#278a99"), trace("Calculated", x, x.map(y => totals.get(y)?.calculated ?? 0), "#e7a33e")];
});
const current = computed(() => {
  const rows = props.overview.substances.slice(0, substanceLimit.value || undefined);
  return [trace("Timecourses", rows.map(r => r.name), rows.map(r => r.timecourse_count), "#8364b5")];
});
</script>
<template>
  <div class="overview-dashboard">
    <dl class="coverage-totals">
      <div><dt>Substances with timecourses</dt><dd>{{ overview.counts.substance_count.toLocaleString() }}</dd></div>
      <div><dt>PK parameter values</dt><dd>{{ overview.counts.pk_count.toLocaleString() }}</dd></div>
      <div><dt>Calculated PK values</dt><dd>{{ overview.counts.pk_calculated_count.toLocaleString() }}</dd></div>
    </dl>
    <div class="coverage-heading"><h2>Explore database coverage</h2><p>By study date. These charts describe the studies currently available to you, not historical database snapshots.</p></div>
    <div v-if="overview.years.length" class="controls">
      <label>From year <select v-model.number="from" aria-label="From year"><option :value="0">First year</option><option v-for="row in overview.years" :key="row.year!" :value="row.year">{{ row.year }}</option></select></label>
      <label>To year <select v-model.number="to" aria-label="To year"><option :value="9999">Latest year</option><option v-for="row in overview.years" :key="row.year!" :value="row.year">{{ row.year }}</option></select></label>
      <label><input v-model="cumulative" type="checkbox" /> Cumulative studies and substances</label>
    </div>
    <p v-if="!years.length" role="status">No dated studies in this range.</p>
    <template v-else>
      <p class="chart-help">Hover for values. Drag to zoom; double-click to reset. Use the toolbar to pan or download a chart.<span v-if="cumulative"> Cumulative totals include years before the selected range.</span></p>
      <div class="chart-grid">
        <StatisticsChart :title="cumulative ? 'Cumulative studies' : 'Studies per year'" :traces="studies" />
        <StatisticsChart :title="cumulative ? 'Cumulative substances with timecourses' : 'Substances with timecourses per year'" :traces="substances" />
      </div>
      <div class="controls"><label>PK parameter <select v-model="parameter" aria-label="PK parameter"><option value="">All PK parameters</option><option v-for="[sid, name] in parameterOptions" :key="sid" :value="sid">{{ name }}</option></select></label></div>
      <StatisticsChart title="PK parameter values per year" :traces="parameters" />
    </template>
    <p v-if="overview.undated.study_count" class="undated">{{ overview.undated.study_count.toLocaleString() }} undated {{ overview.undated.study_count === 1 ? "study is" : "studies are" }} included in current totals, but excluded from yearly charts ({{ overview.undated.substance_count.toLocaleString() }} {{ overview.undated.substance_count === 1 ? "substance" : "substances" }} with timecourses; {{ overview.undated.pk_count.toLocaleString() }} PK values).</p>
    <div class="coverage-heading"><h2>Current timecourse coverage</h2><p>Distinct timecourses per substance across all study dates.</p></div>
    <template v-if="overview.substances.length">
      <div class="controls"><label>Show substances <select v-model.number="substanceLimit" aria-label="Show substances"><option :value="15">Top 15</option><option :value="30">Top 30</option><option :value="0">All substances</option></select></label></div>
      <StatisticsChart title="Timecourses by substance" x-label="Substance" :traces="current" category />
    </template>
    <p v-else>No substances with timecourses are available yet.</p>
  </div>
</template>
<style scoped>
.overview-dashboard { margin-top: 1.5rem; }
.coverage-totals { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.coverage-totals > div { padding: 1.2rem; border-radius: 12px; background: rgba(var(--v-theme-primary), .07); display: flex; flex-direction: column-reverse; gap: .3rem; }
dd { font-size: 2rem; font-weight: 650; font-variant-numeric: tabular-nums; }
dt { font-size: .9rem; }
.coverage-heading { margin: 2rem 0 1rem; }
.coverage-heading p, .chart-help { color: rgba(var(--v-theme-on-surface), .75); line-height: 1.6; margin-top: .5rem; }
.controls { display: flex; flex-wrap: wrap; align-items: center; gap: 1rem; margin: 1rem 0; }
label { display: flex; align-items: center; gap: .5rem; }
select { padding: .5rem 2rem .5rem .6rem; border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)); border-radius: 6px; background: rgb(var(--v-theme-surface)); color: rgb(var(--v-theme-on-surface)); appearance: auto; max-width: 100%; }
.chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-top: 1rem; }
.undated { margin-top: 1rem; padding: 1rem; background: rgba(var(--v-theme-primary), .07); border-radius: 8px; }
@media (max-width: 800px) { .chart-grid { grid-template-columns: 1fr; } }
@media (max-width: 550px) { .coverage-totals { grid-template-columns: 1fr; } }
</style>
