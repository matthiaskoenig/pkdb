<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VChip,
  VDialog,
  VSpacer,
} from "vuetify/components";
import type { StudyRow } from "../api/types";
import { useReturnFocus, type FocusTarget } from "../composables/useReturnFocus";
import { plural } from "../overview";
import { useOverviewStore } from "../stores/overview";
import { messageOf } from "../study";

const open = defineModel<boolean>({ default: false });
const props = defineProps<{
  studies: StudyRow[];
  /** `upload` uploads the studies now; `enable` makes Upload their On save action. */
  action: "upload" | "enable";
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
const emit = defineEmits<{ done: [count: number] }>();

const overview = useOverviewStore();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
const busy = ref(false);
const error = ref<string | null>(null);

const title = computed(() => (props.action === "upload" ? "Review upload" : "Turn on upload on save"));
const confirmLabel = computed(() => (props.action === "upload" ? "Validate and upload" : "Turn on upload on save"));
const withErrors = computed(() => props.studies.some((study) => study.counts.errors > 0));

watch(open, (value) => {
  if (value) error.value = null;
});

async function confirm(): Promise<void> {
  const ids = props.studies.map((study) => study.id);
  busy.value = true;
  error.value = null;
  try {
    if (props.action === "upload") await overview.enqueue(ids, "upload");
    else await overview.setMode(ids, "upload");
    open.value = false;
    emit("done", ids.length);
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <VDialog v-model="open" max-width="560" scrollable :aria-labelledby="titleId">
    <VCard>
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">{{ title }}</VCardTitle>
      </VCardItem>
      <VCardText class="upload-body">
        <dl class="panel-facts">
          <dt>Server</dt>
          <dd>{{ overview.snapshot?.endpoint || "Not configured" }}</dd>
          <dt>PK-DB account</dt>
          <dd>{{ overview.snapshot?.account ?? "Not verified" }}</dd>
        </dl>
        <section>
          <h3 class="upload-heading">{{ plural(studies.length, "study", "studies") }}</h3>
          <ul class="upload-studies">
            <li v-for="study in studies" :key="study.path" class="upload-study">
              <span class="upload-study-text">
                <span class="upload-study-identity">{{ study.id }}</span>
                <span v-if="study.summary.title" class="upload-study-title">{{ study.summary.title }}</span>
              </span>
              <VChip v-if="study.counts.errors" size="small" color="error" variant="tonal" class="status-chip">
                {{ plural(study.counts.errors, "error") }}
              </VChip>
            </li>
          </ul>
        </section>
        <p v-if="action === 'upload'" class="upload-note">
          Every upload validates the study first. An upload can replace the study on the server.
        </p>
        <p v-else class="upload-note">
          From now on, saving a file of these studies validates the study and uploads it to this server. An upload can
          replace the study on the server.
        </p>
        <p v-if="withErrors" class="upload-note">Studies with errors fail the validation and are not uploaded.</p>
        <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn variant="flat" color="primary" :loading="busy" @click="confirm">{{ confirmLabel }}</VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.upload-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.upload-heading {
  margin: 0 0 6px;
  font-size: 0.875rem;
  font-weight: 600;
}
.upload-studies {
  max-height: 240px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.upload-study {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
}
.upload-study + .upload-study {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.upload-study-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.upload-study-identity {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.upload-study-title {
  overflow: hidden;
  font-size: 0.8125rem;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.upload-note {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
</style>
