<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { loadPlotly } from "../plotly";
import { plotModel, type PlotLayout } from "../types";

const props = defineProps<{
  points: unknown;
  kind: "timecourse" | "scatter";
}>();
const host = ref<HTMLElement>();
const logX = ref(false);
const logY = ref(false);
const failure = ref("");
const loading = ref(false);
let generation = 0;
let engine: Awaited<ReturnType<typeof loadPlotly>> | undefined;
let observer: ResizeObserver | undefined;
let disposed = false;
let rendering = Promise.resolve();
const model = computed(() => {
  try {
    return { value: plotModel(props.points, props.kind), error: "" };
  } catch (error) {
    return {
      value: undefined,
      error:
        error instanceof Error ? error.message : "Unable to plot this data.",
    };
  }
});
watch(
  [host, model, logX, logY],
  () => {
    const current = ++generation;
    const element = host.value;
    observer?.disconnect();
    if (!element || !model.value.value) return;
    const data = model.value.value;
    loading.value = true;
    failure.value = "";
    const render = async () => {
      if (disposed || generation !== current) return;
      try {
        const loaded = await loadPlotly();
        if (disposed || generation !== current) return;
        engine = loaded;
        const layout: PlotLayout = {
          autosize: true,
          height: 380,
          xaxis: {
            title: { text: data.xLabel },
            type: logX.value ? "log" : "linear",
          },
          yaxis: {
            title: { text: data.yLabel },
            type: logY.value ? "log" : "linear",
          },
          margin: { l: 75, r: 25, t: 30, b: 65 },
          uirevision: JSON.stringify(data.points),
        };
        await loaded.react(element, data.traces, layout, {
          responsive: true,
          displaylogo: false,
          displayModeBar: true,
          modeBarButtonsToRemove: ["toImage"],
        });
        if (disposed) {
          loaded.purge(element);
          return;
        }
        if (generation !== current) return;
        observer = new ResizeObserver(() => {
          void loaded.Plots.resize(element).catch(() => undefined);
        });
        observer.observe(element);
      } catch (error) {
        if (generation === current)
          failure.value =
            error instanceof Error
              ? error.message
              : "The chart could not be displayed.";
      } finally {
        if (generation === current) loading.value = false;
      }
    };
    // Serialize Plotly mutations so an older asynchronous render cannot finish
    // after its replacement and restore stale scientific data.
    rendering = rendering.catch(() => undefined).then(render);
  },
  { flush: "post" },
);
onBeforeUnmount(() => {
  disposed = true;
  generation++;
  observer?.disconnect();
  if (host.value) engine?.purge(host.value);
});
</script>

<template>
  <section aria-label="Scientific plot">
    <p v-if="model.error || failure" role="alert">
      {{ model.error || failure }}
    </p>
    <template v-if="model.value">
      <div class="plot-controls">
        <label
          ><input v-model="logX" type="checkbox" /> Logarithmic X axis</label
        ><label
          ><input v-model="logY" type="checkbox" /> Logarithmic Y axis</label
        >
      </div>
      <p v-if="logX || logY">
        Zero and negative values cannot appear on logarithmic axes; all values
        remain in the data table.
      </p>
      <p v-if="loading" role="status">Loading chart…</p>
      <div
        ref="host"
        class="plot"
        role="img"
        :aria-label="`${model.value.yLabel} versus ${model.value.xLabel}`"
      />
      <p v-for="note in model.value.notes" :key="note">{{ note }}</p>
      <details>
        <summary>Accessible plot data and uncertainty</summary>
        <div class="plot-data">
          <table>
            <caption>
              Reported point values; missing values are shown as -
            </caption>
            <thead>
              <tr>
                <th>Point</th>
                <th>Axis</th>
                <th>Time</th>
                <th>Time unit</th>
                <th>Value</th>
                <th>Mean</th>
                <th>Median</th>
                <th>SD</th>
                <th>SE</th>
                <th>CV</th>
                <th>Unit</th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="(pair, index) in model.value.points"
                :key="index"
              >
                <tr v-for="(point, axis) in pair" :key="point.pk">
                  <th>{{ point.pk }}</th>
                  <td>
                    {{ kind === "timecourse" ? "Y" : axis === 0 ? "X" : "Y" }}
                  </td>
                  <td>{{ point.time ?? "-" }}</td>
                  <td>{{ point.time_unit ?? "-" }}</td>
                  <td>{{ point.value ?? "-" }}</td>
                  <td>{{ point.mean ?? "-" }}</td>
                  <td>{{ point.median ?? "-" }}</td>
                  <td>{{ point.sd ?? "-" }}</td>
                  <td>{{ point.se ?? "-" }}</td>
                  <td>{{ point.cv ?? "-" }}</td>
                  <td>{{ point.unit ?? "-" }}</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </details>
    </template>
  </section>
</template>
<style scoped>
.plot {
  min-height: 380px;
  width: 100%;
}
.plot-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}
.plot-data {
  overflow-x: auto;
}
th,
td {
  padding: 0.4rem;
  text-align: left;
  white-space: nowrap;
}
</style>
