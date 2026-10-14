<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import { VBtn, VCard, VChip, VMenu } from "vuetify/components";
import type { SaveMode, Snapshot } from "../api/types";
import { uploadBlocker } from "../uploads";
import { useOverviewStore } from "../stores/overview";
import { stateChip } from "../stateChip";
import { failureOf, type ActionFailure } from "../../study-views/study";
import ActionFailureAlert from "./ActionFailureAlert.vue";

type Anchor = "bottom end" | "bottom";

/** The actions of On save in the order of the menu: how the header shows each, and what a save then does. */
const OPTIONS: readonly {
  value: SaveMode;
  label: string;
  icon: string;
  tone: "success" | "info" | "warning";
  text: string;
}[] = [
  {
    value: "validate",
    label: "Validate",
    icon: "fas fa-circle-check",
    tone: "success",
    text: "A save syncs, formats and validates the study.",
  },
  {
    value: "upload",
    label: "Upload",
    icon: "fas fa-cloud-arrow-up",
    tone: "info",
    text: "A save also uploads the study to the server when it has no errors.",
  },
  {
    value: "off",
    label: "Off",
    icon: "fas fa-pause",
    tone: "warning",
    text: "A save marks the study as changed. Validate or upload it yourself.",
  },
];

const props = withDefaults(
  defineProps<{
    snapshot: Snapshot;
    location?: Anchor;
    /** On the teal app bar: the chip of the button takes the colors of the bar. */
    bar?: boolean;
  }>(),
  { location: "bottom end", bar: false },
);
/** The curator chose Upload, which the header confirms in a dialog first. */
const emit = defineEmits<{ upload: [] }>();

const overview = useOverviewStore();
const id = useId();
const open = ref(false);
/** The action being set. */
const busy = ref<SaveMode | null>(null);
const failure = ref<ActionFailure | null>(null);

// A failure belongs to the action that caused it, not to the next visit of the menu.
watch(open, (value) => {
  if (value) failure.value = null;
});

const current = computed(() => OPTIONS.find((option) => option.value === props.snapshot.mode) ?? OPTIONS[0]!);
/** The local server does not answer: the menu shows the last known state and offers no change. */
const stale = computed(() => overview.error !== null);
const buttonChip = computed(() => stateChip(stale.value ? undefined : current.value.tone, props.bar));
/** Why Upload cannot be chosen, or null. */
const blocker = computed(() => uploadBlocker(props.snapshot));

function disabled(value: SaveMode): boolean {
  return stale.value || (value === "upload" && blocker.value !== null);
}

/** Set Validate or Off for every study; Upload goes through the confirmation of the header. */
async function choose(value: SaveMode): Promise<void> {
  if (busy.value !== null || value === props.snapshot.mode) return;
  if (value === "upload") {
    open.value = false;
    emit("upload");
    return;
  }
  busy.value = value;
  failure.value = null;
  try {
    await overview.setMode(value);
  } catch (caught) {
    failure.value = failureOf(caught);
  } finally {
    busy.value = null;
  }
}
</script>

<template>
  <VMenu v-model="open" :location="location" :close-on-content-click="false">
    <template #activator="{ props: activator }">
      <VBtn
        v-bind="activator"
        variant="text"
        :prepend-icon="current.icon"
        class="header-control header-on-save"
        :aria-label="`On save: ${current.label}`"
      >
        <span class="header-control-label">On save</span>
        <VChip :color="buttonChip.color" :variant="buttonChip.variant" size="small" :class="buttonChip.class">
          {{ current.label }}
        </VChip>
      </VBtn>
    </template>
    <VCard elevation="6" border class="header-menu on-save-panel">
      <div class="panel-heading">
        <h2>On save</h2>
        <VChip :color="stale ? undefined : current.tone" variant="tonal" size="small" class="status-chip">
          {{ current.label }}
        </VChip>
      </div>
      <p v-if="stale" class="panel-note">The local server does not answer. This is the last known state.</p>
      <p>What a save of a file starts. It applies to every study of this workspace, with this server and PK-DB account.</p>
      <div role="group" aria-label="On save action" class="on-save-options">
        <template v-for="option in OPTIONS" :key="option.value">
          <VBtn
            :variant="option.value === current.value ? 'tonal' : 'text'"
            :color="option.value === current.value ? 'primary' : undefined"
            :prepend-icon="option.icon"
            :aria-pressed="option.value === current.value ? 'true' : 'false'"
            :aria-describedby="`${id}-${option.value}`"
            :disabled="disabled(option.value)"
            :loading="busy === option.value"
            class="on-save-choice"
            @click="choose(option.value)"
          >
            {{ option.label }}
          </VBtn>
          <p :id="`${id}-${option.value}`" class="on-save-line">
            {{ option.text }}
            <span v-if="option.value === 'upload' && blocker" class="on-save-blocker">{{ blocker }}</span>
          </p>
        </template>
      </div>
      <ActionFailureAlert v-if="failure" :failure="failure" :closable="false" />
    </VCard>
  </VMenu>
</template>

<style scoped>
/* Each action beside its line; the buttons share the width of the widest. */
.on-save-options {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
  gap: 8px 12px;
}
.on-save-choice {
  justify-content: flex-start;
}
.on-save-blocker {
  display: block;
  margin-top: 2px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
