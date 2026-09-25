<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { useTheme } from "vuetify";
import { loadPlotly } from "../plots/plotly";
import type { OverviewTrace, OverviewLayout } from "./chart";
const props = defineProps<{ title: string; traces: OverviewTrace[]; category?: boolean; xLabel?: string }>();
const theme = useTheme();
const host = ref<HTMLElement>();
const failure = ref("");
let engine: Awaited<ReturnType<typeof loadPlotly>> | undefined;
let observer: ResizeObserver | undefined;
let generation = 0;
let disposed = false;
let rendering = Promise.resolve();
watch([host, () => props.traces, () => theme.current.value.dark], () => {
  const current = ++generation, element = host.value;
  observer?.disconnect();
  if (!element) return;
  rendering = rendering.catch(() => undefined).then(async () => {
    if (disposed || current !== generation) return;
    failure.value = "";
    try {
      const loaded = await loadPlotly();
      if (disposed || current !== generation) return;
      engine = loaded;
      const layout: OverviewLayout = {
        autosize: true, height: 380,
        xaxis: { title: { text: props.xLabel ?? "Study year" }, type: props.category ? "category" : "linear", automargin: true, ...(props.category ? {} : { tickformat: "d", ...((props.traces[0]?.x.length ?? 0) < 20 ? { dtick: 1 } : {}) }) },
        yaxis: { title: { text: "Count" }, rangemode: "tozero", automargin: true, ...(props.traces.every(trace => trace.y.every(value => value <= 10)) ? { dtick: 1 } : {}) },
        margin: { l: 55, r: 20, t: 20, b: 110 },
        paper_bgcolor: "transparent", plot_bgcolor: "transparent",
        font: { color: String(theme.current.value.colors["on-surface"] ?? "#222") },
        barmode: "stack", legend: { orientation: "h", x: 0, y: -0.35, yanchor: "top" }, uirevision: JSON.stringify([props.title, props.traces.map(trace => trace.x)]),
      };
      await loaded.react(element, props.traces, layout, { responsive: true, displaylogo: false, displayModeBar: true, modeBarButtonsToRemove: ["sendChartToCloud", "select2d", "lasso2d"] });
      if (disposed) { loaded.purge(element); return; }
      if (current !== generation) return;
      observer = new ResizeObserver(() => { void loaded.Plots.resize(element).catch(() => undefined); });
      observer.observe(element);
    } catch { if (current === generation) failure.value = "Chart unavailable. The values are available in the data table below."; }
  });
}, { flush: "post" });
onBeforeUnmount(() => { disposed = true; generation++; observer?.disconnect(); if (host.value) engine?.purge(host.value); });
</script>
<template>
  <section class="statistics-chart">
    <h3>{{ title }}</h3>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <div ref="host" class="chart" role="img" :aria-label="title" />
    <details>
      <summary>View data for {{ title.toLowerCase() }}</summary>
      <div class="table-scroll"><table>
        <caption>{{ title }}</caption>
        <thead><tr><th>{{ xLabel ?? "Study year" }}</th><th v-for="trace in traces" :key="trace.name">{{ trace.name }}</th></tr></thead>
        <tbody><tr v-for="(x, index) in traces[0]?.x ?? []" :key="x"><th>{{ x }}</th><td v-for="trace in traces" :key="trace.name">{{ trace.y[index]?.toLocaleString() }}</td></tr></tbody>
      </table></div>
    </details>
  </section>
</template>
<style scoped>
.statistics-chart { min-width: 0; padding: 1rem; border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)); border-radius: 12px; }
.chart { width: 100%; min-height: 380px; }
h3 { font-size: 1.1rem; }
summary { cursor: pointer; color: rgb(var(--v-theme-primary)); }
.table-scroll { overflow: auto; max-height: 360px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: .5rem; border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)); }
</style>
