<script setup lang="ts">
import { computed } from "vue";
import { VTooltip } from "vuetify/components";
import type { ValidationIssue } from "../../study-views/types";
import type { CellTip } from "../../study-views/composables/useCellTip";
import { isLineTipKey } from "../../study-views/grid";
import ProblemTip from "./ProblemTip.vue";

/**
 * The one tooltip of the problems of a table grid, at the cell of `tip`. It renders apart from
 * the grid, so that showing, moving and hiding it renders no row. The tooltip of a line starts at
 * its line cell, so that it extends over its row; the tooltip of a cell is below its middle. It
 * touches its cell, so that the pointer moves onto it without crossing the cells below.
 */
const props = defineProps<{
  tip: CellTip;
  /** The problems that the tooltip can list, by the `data-tip` of their cell. */
  tips: ReadonlyMap<string, readonly ValidationIssue[]>;
}>();

const target = computed(() => props.tip.cell.value ?? undefined);

// A hiding tooltip keeps its problems and its place while it fades out.

const issues = computed<readonly ValidationIssue[]>((shown = []) => {
  const key = props.tip.key.value;
  return (key === null ? undefined : props.tips.get(key)) ?? shown;
});
const location = computed<"bottom" | "bottom start">((shown = "bottom") => {
  const key = props.tip.key.value;
  if (key === null) return shown;
  return isLineTipKey(key) ? "bottom start" : "bottom";
});

/** The pointer can rest on the tooltip. */
const contentProps = { onMouseenter: () => props.tip.enterTip(), onMouseleave: () => props.tip.leaveTip() };

/** Vuetify closes the tooltip, such as on a click outside it. */
function onToggle(open: boolean): void {
  if (!open) props.tip.hide();
}
</script>

<template>
  <VTooltip
    :model-value="target !== undefined"
    :target="target"
    :open-on-hover="false"
    :open-on-focus="false"
    :eager="false"
    interactive
    :location="location"
    :offset="0"
    max-width="380"
    content-class="problem-tooltip"
    :content-props="contentProps"
    @update:model-value="onToggle"
  >
    <ProblemTip :issues="issues" />
  </VTooltip>
</template>
