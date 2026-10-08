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
  VRadio,
  VRadioGroup,
  VSpacer,
  VTextField,
} from "vuetify/components";
import { isNoUser } from "../api/client";
import { useReturnFocus, type FocusTarget } from "../composables/useReturnFocus";
import { useDialogStore } from "../stores/dialogs";
import { useStudyStore } from "../stores/study";
import { NEW_TABLE_KINDS, newTable, type NewTableKind } from "../study";

const open = defineModel<boolean>({ default: false });
const props = defineProps<{
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
const emit = defineEmits<{ added: [table: string] }>();

const study = useStudyStore();
const dialogs = useDialogStore();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
const kind = ref<NewTableKind>("outputs");
const source = ref("");
const busy = ref(false);
/** Why the table was not added, with the issues of the API. */
const failure = ref<{ text: string; issues: string[] } | null>(null);

const table = computed(() => (study.detail ? newTable(study.detail, kind.value, source.value) : null));
const hint = computed(() =>
  kind.value === "raw"
    ? "A paper table such as Tab3."
    : "A paper table such as Tab3, a figure such as Fig2A, or Text.",
);

watch(open, (value) => {
  if (!value) return;
  kind.value = "outputs";
  source.value = "";
  failure.value = null;
});

// A failure belongs to the table that it was about.
watch([kind, source], () => {
  failure.value = null;
});

async function add(): Promise<void> {
  const chosen = table.value;
  if (!chosen || chosen.problem || busy.value) return;
  busy.value = true;
  failure.value = null;
  try {
    const result = await study.tablesAction("add", chosen.payload);
    if (result.ok) {
      open.value = false;
      emit("added", result.table ?? chosen.sheet);
    } else {
      failure.value = {
        text: `${chosen.sheet} was not added.`,
        issues: result.issues.map((issue) => issue.message),
      };
    }
  } catch (caught) {
    if (isNoUser(caught)) dialogs.openSettings();
    failure.value = { text: caught instanceof Error ? caught.message : String(caught), issues: [] };
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <VDialog v-model="open" max-width="560" scrollable :aria-labelledby="titleId">
    <VCard tag="form" @submit.prevent="add">
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">Add table</VCardTitle>
      </VCardItem>
      <VCardText class="add-table-body">
        <p class="add-table-note">
          Adds an empty sheet to the workbook. The table file appears when the sheet has content and you save the
          workbook.
        </p>
        <VRadioGroup v-model="kind" label="Kind" inline hide-details class="add-table-kind">
          <VRadio v-for="item in NEW_TABLE_KINDS" :key="item.value" :value="item.value" :label="item.label" />
        </VRadioGroup>
        <VTextField
          v-model="source"
          label="Source"
          placeholder="Tab3"
          :hint="hint"
          persistent-hint
          :error-messages="table?.problem ?? null"
          autocomplete="off"
          spellcheck="false"
        />
        <dl v-if="table && !table.problem" class="panel-facts table-preview">
          <dt>Sheet</dt>
          <dd>{{ table.sheet }}</dd>
          <dt>File</dt>
          <dd>{{ table.file }}</dd>
          <dt>Image</dt>
          <dd v-if="table.image" class="table-image">
            <span class="table-image-name">
              {{ table.image }}
              <VChip
                size="small"
                variant="tonal"
                :color="table.imageFound ? 'success' : 'warning'"
                class="status-chip image-state"
              >
                {{ table.imageFound ? "In the folder" : "Missing" }}
              </VChip>
            </span>
            <span v-if="!table.imageFound" class="table-image-note">
              Add {{ table.image }} to the folder. Validation needs the image of every paper table and figure.
            </span>
          </dd>
          <dd v-else>None for the text of the paper</dd>
        </dl>
        <VAlert v-if="failure" type="error" variant="tonal" density="compact" class="status-alert">
          {{ failure.text }}
          <ul v-if="failure.issues.length" class="add-table-issues">
            <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
          </ul>
        </VAlert>
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn type="submit" variant="flat" color="primary" :disabled="!table || table.problem !== null" :loading="busy">
          Add
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.add-table-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.add-table-note {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
/* The label and the circles of the radio buttons start at the edge of the text above them. */
.add-table-kind :deep(.v-input__control > .v-label) {
  margin-inline-start: 0;
}
.add-table-kind :deep(.v-selection-control-group) {
  margin-inline-start: -8px;
}
.table-preview dd {
  overflow-wrap: anywhere;
}
.table-image {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.table-image-name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}
.table-image-note {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.add-table-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
}
</style>
