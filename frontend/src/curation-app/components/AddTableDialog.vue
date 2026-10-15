<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import {
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
import type { TableFileKind } from "../../study-views/types";
import { usePreview } from "../composables/usePreview";
import { useReturnFocus } from "../composables/useReturnFocus";
import type { FocusTarget } from "../../study-views/focus";
import { useStudyStore } from "../stores/study";
import { failureOf, issuesFailure, type ActionFailure } from "../../study-views/study";
import { userHint } from "../local";
import { addableKinds } from "../../study-views/tableKinds";
import ActionFailureAlert from "../../study-views/components/ActionFailureAlert.vue";
import UserHint from "./UserHint.vue";

const open = defineModel<boolean>({ default: false });
const props = defineProps<{
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
const emit = defineEmits<{ added: [table: string] }>();

const study = useStudyStore();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
/** The kinds that Add table adds, as the study page describes them. */
const kinds = computed(() => (study.detail ? addableKinds(study.detail) : []));
const kind = ref<TableFileKind>("outputs");
const source = ref("");
const busy = ref(false);
/** Why the table was not added, with the issues of the API. */
const failure = ref<ActionFailure | null>(null);
/** What to do when the write was refused without a user. */
const userText = ref<string | null>(null);

const preview = usePreview(
  () => {
    const detail = study.detail;
    const name = source.value.trim();
    // A closed dialog asks nothing.
    if (!open.value || !detail || !name) return null;
    // The files of the study stand for the folder, so an added image or table file asks again; a
    // preview that failed while the local server did not answer is asked again once it answers.
    return { study: detail.id, files: detail.files, answering: study.error === null, kind: kind.value, source: name };
  },
  (value) => study.previewTable(value.kind, value.source),
  "The table could not be previewed.",
);
/** The new table as the server previews it: for the current kind and source, or the last one while that loads. */
const table = computed(() => preview.shown.value);
/** Why the table cannot be added: the refusal of the server; a failed preview has its alert. */
const problem = computed(() => table.value?.issues[0]?.message ?? null);
/** Only the answer for the current kind and source can add a table. */
const canAdd = computed(() => {
  const current = preview.data.value;
  return current !== null && current.issues.length === 0 && !busy.value;
});
/** What the preview says, for screen readers; a refusal is announced as the message of the field. */
const ready = computed(() => {
  const value = table.value;
  if (!value || value.issues.length) return "";
  if (value.image === null) return `${value.table} can be added.`;
  return `${value.table} can be added. ${value.image_found ? "The image is in the folder." : "The image is missing."}`;
});
const hint = computed(() =>
  kind.value === "raw"
    ? "A paper table such as Tab3."
    : "A paper table such as Tab3, a figure such as Fig2A, or Text.",
);

// At once, so that the preview never asks for the source of the last time the dialog was open.
watch(
  open,
  (value) => {
    if (!value) return;
    kind.value = kinds.value[0]?.value ?? "outputs";
    source.value = "";
    failure.value = null;
    userText.value = null;
  },
  { flush: "sync" },
);

// A failure belongs to the table that it was about.
watch([kind, source], () => {
  failure.value = null;
  userText.value = null;
});

async function add(): Promise<void> {
  const chosen = preview.data.value;
  if (!chosen || !canAdd.value) return;
  busy.value = true;
  failure.value = null;
  userText.value = null;
  try {
    const result = await study.tablesAction("add", { kind: kind.value, source: source.value.trim() });
    if (result.ok) {
      open.value = false;
      emit("added", result.table ?? chosen.table);
    } else {
      failure.value = issuesFailure(
        `${chosen.table} was not added.`,
        result.issues.map((issue) => issue.message),
      );
    }
  } catch (caught) {
    if (isNoUser(caught)) userText.value = userHint(caught);
    else failure.value = failureOf(caught);
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
        <VRadioGroup v-model="kind" label="Kind" inline hide-details>
          <VRadio v-for="item in kinds" :key="item.value" :value="item.value" :label="item.label" />
        </VRadioGroup>
        <!-- While the answer for the current kind and source loads, the last one stays, marked as
             updating: the messages of the field, the facts and the status line, not the field. -->
        <VTextField
          v-model="source"
          label="Source"
          placeholder="Tab3"
          :hint="hint"
          persistent-hint
          :error-messages="problem"
          :class="{ 'is-updating': preview.loading.value }"
          autocomplete="off"
          spellcheck="false"
        />
        <dl
          v-if="table && !table.issues.length"
          class="panel-facts table-preview"
          :class="{ 'is-updating': preview.loading.value }"
          :aria-busy="preview.loading.value"
        >
          <dt>Sheet</dt>
          <dd>{{ table.table }}</dd>
          <dt>File</dt>
          <dd>{{ table.file }}</dd>
          <dt>Image</dt>
          <dd v-if="table.image" class="table-image">
            <span class="table-image-name">
              {{ table.image }}
              <VChip
                size="small"
                variant="tonal"
                :color="table.image_found ? 'success' : 'warning'"
                class="status-chip image-state"
              >
                {{ table.image_found ? "In the folder" : "Missing" }}
              </VChip>
            </span>
            <span v-if="!table.image_found" class="table-image-note">
              Add {{ table.image }} to the folder. Validation needs the image of every paper table and figure.
            </span>
          </dd>
          <dd v-else>None for the text of the paper</dd>
        </dl>
        <span role="status" aria-live="polite" class="d-sr-only" :aria-busy="preview.loading.value">{{ ready }}</span>
        <!-- It goes with the next preview that the local server answers: no close button. -->
        <ActionFailureAlert
          v-if="preview.shownError.value"
          :failure="preview.shownError.value"
          :study="study.detail?.id ?? null"
          :closable="false"
          :class="{ 'is-updating': preview.loading.value }"
        />
        <ActionFailureAlert v-if="failure" :failure="failure" :study="study.detail?.id ?? null" :closable="false" />
        <UserHint v-else-if="userText" :text="userText" />
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn type="submit" variant="flat" color="primary" :disabled="!canAdd" :loading="busy">
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
</style>
