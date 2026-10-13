<script setup lang="ts">
import { computed } from "vue";
import { VBtn, VBtnToggle } from "vuetify/components";
import { plural } from "../overview";
import { AXES, logAxes, type Axis, type AxisScale, type AxisScales } from "../overlay";

/**
 * The scales of a plot of mapped rows, above it: `x: lin | log` and `y: lin | log`, and a note of
 * the points that a log axis leaves out, as it shows only values above 0. The note is a polite
 * live region that stays in the page, so that a screen reader says it after a switch.
 */
const props = defineProps<{
  scales: AxisScales;
  /** How many points of the plot its log axes leave out. */
  hidden: number;
}>();
const emit = defineEmits<{ choose: [axis: Axis, scale: AxisScale] }>();

const CHOICES: readonly { scale: AxisScale; text: string }[] = [
  { scale: "linear", text: "lin" },
  { scale: "log", text: "log" },
];

function pick(axis: Axis, value: unknown): void {
  if ((value === "linear" || value === "log") && value !== props.scales[axis]) emit("choose", axis, value);
}

const note = computed(() => {
  if (!props.hidden) return "";
  const axes = logAxes(props.scales).length > 1 ? "axes" : "axis";
  return `${plural(props.hidden, "point")} at 0 or below ${props.hidden === 1 ? "is" : "are"} not shown on the log ${axes}`;
});
</script>

<template>
  <div class="plot-scales">
    <div class="plot-scales-axes">
      <div v-for="axis in AXES" :key="axis" class="plot-scale">
        <span class="plot-scale-axis" aria-hidden="true">{{ axis }}:</span>
        <VBtnToggle
          :model-value="scales[axis]"
          mandatory
          divided
          variant="outlined"
          color="primary"
          density="compact"
          role="group"
          :aria-label="`Scale of the ${axis} axis`"
          class="plot-scale-toggle"
          @update:model-value="pick(axis, $event)"
        >
          <VBtn
            v-for="choice in CHOICES"
            :key="choice.scale"
            :value="choice.scale"
            :aria-pressed="scales[axis] === choice.scale"
            >{{ choice.text }}</VBtn
          >
        </VBtnToggle>
      </div>
    </div>
    <p class="plot-scales-note" aria-live="polite">{{ note }}</p>
  </div>
</template>

<style scoped>
.plot-scales {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.plot-scales-axes {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 16px;
}
.plot-scale {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.plot-scale-axis {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* As high as the zoom of the image and the smallest target of the app, 24 px. */
.plot-scale-toggle.v-btn-group {
  height: 24px;
}
.plot-scale-toggle :deep(.v-btn) {
  min-width: 0;
  height: 100%;
  padding-inline: 8px;
  font-size: 12px;
  letter-spacing: normal;
  text-transform: none;
}
/* Empty, the note takes no room. */
.plot-scales-note {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
