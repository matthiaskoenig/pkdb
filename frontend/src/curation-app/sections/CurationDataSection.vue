<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from "vue";
import { VAlert, VBtn } from "vuetify/components";
import type { TableKind } from "../../study-views/types";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import AddTableDialog from "../components/AddTableDialog.vue";
import ConflictPanel from "../components/ConflictPanel.vue";
import CurationPaperPane from "../components/CurationPaperPane.vue";
import TableNotes from "../components/TableNotes.vue";
import UserHint from "../components/UserHint.vue";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { sectionHeading } from "../composables/useReturnFocus";
import { useStudyStore } from "../stores/study";
import { tablesOutcome } from "../local";
import { syncAlert, syncOutcome, syncSummary, withoutConflicts, type Side } from "../tables";
import DataSection from "./DataSection.vue";

/**
 * The Data section of the curation app: the shared section (DataSection.vue) with Open sheet,
 * Sync, Add table and the sync status in its toolbar, the failure and notices of those actions
 * and the conflict panel below it, the conflict panel and the notes editor (TableNotes) above the
 * rows, the paper pane with Open in PDF program, and the Add table dialog. The page fills the
 * window while the panes stand side by side (fill).
 */
const study = useStudyStore();
const { notice, announce } = useNotice();

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");
const section = useTemplateRef<InstanceType<typeof DataSection>>("section");
/** The table file that the section shows. */
const file = computed(() => section.value?.file ?? null);

/** A link opened the notes of `kind`: the draft keeps them open. */
function openNotes(kind: TableKind): void {
  study.draft.setNotesOpen(kind, true);
}

// Sync status and actions

const alert = computed(() => (detail.value ? syncAlert(detail.value.sync, detail.value.conflicts) : null));
/** What the last sync from the app did, while the workbook and the tables are in sync. */
const summary = computed(() =>
  detail.value?.sync.status === "in_sync" && study.lastSync?.ok ? syncSummary(study.lastSync) : null,
);
/** What the sync status means while it is not in sync, else what the last sync from the app did; the header shows the status. */
const syncText = computed(() =>
  detail.value?.sync.status !== "in_sync" ? (alert.value?.text ?? "") : (summary.value ?? ""),
);
/** Whether the workbook and the tables conflict; the panel offers to keep a side even without the rows. */
const conflicted = computed(() => detail.value?.sync.status === "conflict");

type Action = "open" | "sheet" | "sync" | Side;

const { busy, working, failure, userText, run } = useAction<Action>(announce);
const addTable = ref(false);
/** What to do in the workbook after an open found it open already; it stays until it is closed or the next action. */
const openNotice = ref<string | null>(null);
// The notice names a sheet of the table that was shown, so it ends with the table and with the study.
watch([file, identity], () => (openNotice.value = null));

/**
 * Open the workbook at the sheet of the shown table: Open sheet of the toolbar (`sheet`), and Open
 * workbook of the conflict panel (`open`), which explains the conflicts.
 */
function openWorkbook(action: "open" | "sheet" = "open"): Promise<void> {
  return run(action, async () => {
    openNotice.value = null;
    const shown = file.value;
    const result = await study.tablesAction("open", shown ? { file: shown } : {});
    failure.value = tablesOutcome(withoutConflicts(result));
    openNotice.value = result.notice ?? null;
    // The notice says what to do when the workbook was open already, so the status stays silent then.
    return result.opened && !result.notice ? "The workbook opened." : "";
  });
}

function syncTables(): Promise<void> {
  return run("sync", async () => {
    openNotice.value = null;
    const outcome = syncOutcome(await study.tablesAction("sync"), null);
    failure.value = outcome.failure;
    return outcome.notice;
  });
}

function keep(side: Side): Promise<void> {
  return run(side, async () => {
    openNotice.value = null;
    const outcome = syncOutcome(await study.tablesAction("resolve", { keep: side }), side);
    failure.value = outcome.failure;
    return outcome.notice;
  });
}

function added(table: string): void {
  failure.value = null;
  announce(`Added the sheet ${table} to the workbook.`);
}

/** The props of the conflict panel; the progress of Sync shows on its own button. */
const conflictPanel = computed(() => {
  const running = busy.value;
  return {
    conflicts: detail.value?.conflicts ?? [],
    busy: running === "sync" || running === "sheet" ? null : running,
    disabled: working.value,
  };
});
</script>

<template>
  <DataSection ref="section" @open-notes="openNotes">
    <template #toolbar="{ file: shown }">
      <VBtn
        v-if="shown"
        variant="tonal"
        color="primary"
        size="small"
        prepend-icon="fas fa-table"
        :disabled="working"
        :loading="busy === 'sheet'"
        class="data-open-sheet"
        @click="openWorkbook('sheet')"
      >
        Open sheet
      </VBtn>
      <VBtn
        variant="tonal"
        color="primary"
        size="small"
        prepend-icon="fas fa-rotate"
        :disabled="working"
        :loading="busy === 'sync'"
        @click="syncTables"
      >
        Sync
      </VBtn>
      <VBtn
        variant="text"
        color="primary"
        size="small"
        prepend-icon="fas fa-plus"
        :disabled="working"
        @click="addTable = true"
      >
        Add table
      </VBtn>
      <!-- A live region stays in the page while it is empty, so that screen readers announce a
           status that changes outside the app, such as a saved workbook or a conflict. -->
      <span role="status" aria-live="polite" class="data-sync-text">{{ syncText }}</span>
    </template>
    <template #status="{ rows }">
      <ActionFailureAlert v-if="failure" :failure="failure" :study="identity" @close="failure = null" />
      <UserHint v-else-if="userText" :text="userText" />
      <VAlert
        v-if="openNotice"
        type="info"
        variant="tonal"
        density="compact"
        closable
        role="status"
        class="status-alert data-open-notice"
        @click:close="openNotice = null"
      >
        {{ openNotice }}
      </VAlert>
      <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
      <span role="status" aria-live="polite" class="data-notice">{{ notice }}</span>
      <!-- Without a table, also beyond the upload limits, the conflicts have no rows pane to show in. -->
      <ConflictPanel v-if="conflicted && !rows" v-bind="conflictPanel" @keep="keep" @open="openWorkbook()" />
    </template>
    <template #rows="{ kind, linked, unlink }">
      <ConflictPanel v-if="conflicted" v-bind="conflictPanel" @keep="keep" @open="openWorkbook()" />
      <TableNotes v-if="kind" :key="kind" :kind="kind" :focused="linked" @took-focus="unlink" />
    </template>
    <template #paper="paper">
      <CurationPaperPane
        v-show="paper.shown"
        :file="paper.file"
        :place="paper.place"
        :study="paper.study"
        :papers="paper.papers"
        @update:place="paper.keep"
        @update:file="paper.choose"
      />
    </template>
    <template #dialogs>
      <AddTableDialog v-model="addTable" :fallback-focus="sectionHeading" @added="added" />
    </template>
  </DataSection>
</template>

<style scoped>
.data-sync-text {
  flex: 1 1 12rem;
  min-width: 0;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.data-notice {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.data-notice:empty {
  position: absolute;
}
</style>
