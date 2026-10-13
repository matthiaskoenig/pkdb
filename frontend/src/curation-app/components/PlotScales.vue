<script setup lang="ts">
import { computed } from "vue";
import { plural } from "../overview";
import { AXES, logAxes, type Axis, type AxisScale, type AxisScales } from "../overlay";

/**
 * The scales of a plot of mapped rows, above it: `x: lin | log` and `y: lin | log`, and a note of
 * the points that a log axis leaves out, as it shows only values above 0. Each axis is a named
 * group of two native buttons, of which the scale of the axis is pressed, drawn as the zoom of the
 * image (`switch-group` of styles.css). The note is a polite live region that stays in the page,
 * so that a screen reader says it after a switch.
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

function pick(axis: Axis, scale: AxisScale): void {
  if (scale !== props.scales[axis]) emit("choose", axis, scale);
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
        <div class="switch-group" role="group" :aria-label="`Scale of the ${axis} axis`">
          <button
            v-for="choice in CHOICES"
            :key="choice.scale"
            type="button"
            :aria-pressed="scales[axis] === choice.scale"
            @click="pick(axis, choice.scale)"
          >
            {{ choice.text }}
          </button>
        </div>
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
/* Empty, the note takes no room. */
.plot-scales-note {
  margin: 0;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
