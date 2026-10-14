<script setup lang="ts">
import { computed } from "vue";
import { VTooltip } from "vuetify/components";
import type { StudyRow } from "../../study-views/types";
import type { CellTip } from "../../study-views/composables/useCellTip";
import { otherSubstances } from "../../study-views/overview";

/**
 * The one tooltip of the study identities of the study table, at the identity of `tip`: the whole
 * identity, which a narrow cell cuts, and the other substance folders that the tables of the study
 * name. It renders apart from the rows, so that showing, moving and hiding it renders no row.
 */
const props = defineProps<{
  tip: CellTip;
  /** The study of a `data-tip` of an identity, which is the folder of the study. */
  studyOf: (path: string) => StudyRow | undefined;
}>();

const target = computed(() => props.tip.cell.value ?? undefined);

/** What the tooltip shows; a hiding tooltip keeps it while it fades out. */
const shown = computed<{ identity: string; others: string[] } | null>((previous = null) => {
  const key = props.tip.key.value;
  const row = key === null ? undefined : props.studyOf(key);
  return row ? { identity: `${row.substance}/${row.name}`, others: otherSubstances(row) } : previous;
});

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
    location="top"
    content-class="study-tooltip"
    @update:model-value="onToggle"
  >
    <template v-if="shown">
      <div>{{ shown.identity }}</div>
      <div v-if="shown.others.length" class="study-tooltip-more">+ {{ shown.others.join(", ") }}</div>
    </template>
  </VTooltip>
</template>

<style scoped>
/* The other substance folders, muted below the identity: at least 6:1 on the tooltip in both themes. */
.study-tooltip-more {
  opacity: 0.8;
}
</style>
