<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VBtn, VProgressLinear, VSwitch, VTab, VTabs } from "vuetify/components";
import type { TableResponse } from "../api/types";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import AddTableDialog from "../components/AddTableDialog.vue";
import ConflictPanel from "../components/ConflictPanel.vue";
import TableGrid from "../components/TableGrid.vue";
import UserHint from "../components/UserHint.vue";
import { useLoaded } from "../composables/useLoaded";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { sectionHeading } from "../composables/useReturnFocus";
import { columnCount, issueCells, itemsWithoutRows, keptColumns, targetLines, visibleColumns } from "../grid";
import { plural } from "../overview";
import { useStudyStore } from "../stores/study";
import { syncAlert, syncOutcome, syncSummary, tableOrder, withoutConflicts, type Side } from "../tables";
import {
  isRawTable,
  tableFiles,
  tablesOutcome,
} from "../study";

/**
 * The sync status of the workbook first, with the conflict panel while the workbook and the
 * tables conflict; then one tab per table and raw table with its rows, read only. Rows that open
 * review items target are amber and cells with problems are outlined. Tables are edited in the
 * workbook, which Open tables of the study header opens: Sync syncs it, and Add table adds a
 * sheet.
 *
 * The chosen table is the `file` of the route, and its `line` and `column` focus a cell, so that
 * the Problems, Review and Sources sections can link to a row.
 */
const study = useStudyStore();
const route = useRoute();
const router = useRouter();
const { notice, announce } = useNotice();
const id = useId();

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");

// Sync status and actions

const alert = computed(() => (detail.value ? syncAlert(detail.value.sync, detail.value.conflicts) : null));
/** The type of the alert, or the icon of a neutral one. */
const alertLook = computed(() => (alert.value?.tone ? { type: alert.value.tone } : { icon: "fas fa-circle-info" }));
/** What the last sync from the app did, while the workbook and the tables are in sync. */
const summary = computed(() =>
  detail.value?.sync.status === "in_sync" && study.lastSync?.ok ? syncSummary(study.lastSync) : null,
);
/** Whether the workbook and the tables conflict; the panel offers to keep a side even without the rows. */
const conflicted = computed(() => detail.value?.sync.status === "conflict");

type Action = "open" | "sync" | Side;

const { busy, working, failure, userText, run } = useAction<Action>(announce);
const addTable = ref(false);

/** Open workbook of the conflict panel, which explains the conflicts. */
function openWorkbook(): Promise<void> {
  return run("open", async () => {
    const result = await study.tablesAction("open");
    failure.value = tablesOutcome(withoutConflicts(result));
    return result.opened ? "The workbook opened." : "";
  });
}

function syncTables(): Promise<void> {
  return run("sync", async () => {
    const outcome = syncOutcome(await study.tablesAction("sync"), null);
    failure.value = outcome.failure;
    return outcome.notice;
  });
}

function keep(side: Side): Promise<void> {
  return run(side, async () => {
    const outcome = syncOutcome(await study.tablesAction("resolve", { keep: side }), side);
    failure.value = outcome.failure;
    return outcome.notice;
  });
}

function added(table: string): void {
  failure.value = null;
  announce(`Added the sheet ${table} to the workbook.`);
}

// Tables

const files = computed(() => (detail.value ? tableOrder(tableFiles(detail.value)) : []));
const raw = computed(() => new Set(files.value.filter(isRawTable)));

/** The problems and the open review items of each file, for its tab. */
const counts = computed(() => {
  const problems = new Map<string, number>();
  const items = new Map<string, number>();
  for (const issue of detail.value?.problems ?? []) {
    const file = issue.source?.file;
    if (file) problems.set(file, (problems.get(file) ?? 0) + 1);
  }
  for (const item of detail.value?.review.value?.items ?? []) {
    const file = item.target?.file;
    if (item.state === "open" && file) items.set(file, (items.get(file) ?? 0) + 1);
  }
  return { problems, items };
});

const linked = computed(() => (typeof route.query.file === "string" ? route.query.file : null));
/** The table of the route, else the first table. */
const selected = computed(() => files.value.find((file) => file === linked.value) ?? files.value[0] ?? null);
const tab = computed({
  get: () => selected.value ?? undefined,
  set: (value: unknown) => {
    if (typeof value !== "string" || value === linked.value) return;
    void router.replace({ query: { file: value } });
  },
});
const tabId = (file: string) => `${id}-tab-${file}`;
const panelId = `${id}-panel`;

/** The cell of the route: its line, and its column when it names one. */
const focus = computed(() => {
  if (selected.value === null || linked.value !== selected.value) return null;
  const line = Number(route.query.line);
  if (!Number.isInteger(line) || line < 1) return null;
  const column = typeof route.query.column === "string" ? route.query.column : "";
  return column ? { line, column } : { line };
});

const { data, error, loading, reload } = useLoaded<TableResponse>(
  () => selected.value,
  (file) => study.table(file),
  () => study.detail,
);
/** The rows of the chosen table; null while another one is shown or it loads. */
const table = computed(() => (data.value && data.value.key === selected.value ? data.value.content : null));

const hideEmpty = ref(false);
const highlight = computed(() =>
  table.value ? targetLines(table.value, detail.value?.review.value?.items ?? []) : new Set<number>(),
);
const issues = computed(() => issueCells(detail.value?.problems ?? [], selected.value ?? ""));

const without = computed(() =>
  table.value ? itemsWithoutRows(table.value, detail.value?.review.value?.items ?? []) : { whole: 0, unmatched: 0 },
);

/** The rows, the targets, the cells with problems and the hidden columns, in sentences. */
const caption = computed(() => {
  const shown = table.value;
  if (!shown) return "";
  const parts = [`${plural(shown.rows.length, "row")}.`];
  if (highlight.value.size) parts.push(`Open review items target ${plural(highlight.value.size, "row")}.`);
  const { whole, unmatched } = without.value;
  if (whole === 1) parts.push("1 open review item is about the whole table.");
  if (whole > 1) parts.push(`${whole} open review items are about the whole table.`);
  if (unmatched)
    parts.push(unmatched === 1 ? "1 open review item matches no row." : `${unmatched} open review items match no row.`);
  // A problem outlines its cell, the line of its row, or a header cell.
  const outlined = (detail.value?.problems ?? []).filter(
    (issue) => issue.source?.file === shown.file && issue.source.row != null,
  ).length;
  if (outlined === 1) parts.push("1 problem is outlined.");
  if (outlined > 1) parts.push(`${outlined.toLocaleString("en-US")} problems are outlined.`);
  if (hideEmpty.value) {
    const hidden =
      columnCount(shown) - visibleColumns(shown, true, keptColumns(issues.value, focus.value?.column)).length;
    if (hidden) parts.push(hidden === 1 ? "1 empty column is hidden." : `${hidden} empty columns are hidden.`);
  }
  return parts.join(" ");
});

/** The line of the route when it is no row of the table; line 1 of a table is its header. */
const missingLine = computed(() => {
  const shown = table.value;
  const line = focus.value?.line;
  if (!shown || line === undefined || (shown.kind === "table" && line === 1)) return null;
  return shown.rows.some((row) => row.line === line) ? null : line;
});
</script>

<template>
  <div class="tables">
    <VAlert
      v-if="alert"
      v-bind="alertLook"
      variant="tonal"
      density="compact"
      role="status"
      class="status-alert tables-sync"
    >
      <p class="tables-sync-text">{{ alert.text }}</p>
      <p v-if="summary" class="tables-sync-summary">{{ summary }}</p>
    </VAlert>

    <ConflictPanel
      v-if="conflicted && detail"
      :conflicts="detail.conflicts"
      :busy="busy === 'sync' ? null : busy"
      :disabled="working"
      @keep="keep"
      @open="openWorkbook"
    />

    <div class="tables-toolbar">
      <VBtn
        variant="tonal"
        color="primary"
        prepend-icon="fas fa-rotate"
        :disabled="working"
        :loading="busy === 'sync'"
        @click="syncTables"
      >
        Sync
      </VBtn>
      <VBtn variant="text" color="primary" prepend-icon="fas fa-plus" :disabled="working" @click="addTable = true">
        Add table
      </VBtn>
    </div>

    <ActionFailureAlert v-if="failure" :failure="failure" :study="identity" @close="failure = null" />
    <UserHint v-else-if="userText" :text="userText" />
    <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
    <span role="status" aria-live="polite" class="tables-notice">{{ notice }}</span>

    <p v-if="!files.length" class="tables-empty">
      The study has no tables yet. Add table adds a sheet to the workbook.
    </p>
    <template v-else>
      <VTabs
        v-model="tab"
        show-arrows
        center-active
        color="primary"
        density="compact"
        aria-label="Tables"
        class="tables-tabs scroll-tabs"
      >
        <VTab
          v-for="file in files"
          :id="tabId(file)"
          :key="file"
          :value="file"
          :prepend-icon="raw.has(file) ? 'fas fa-table-cells' : 'fas fa-table'"
          :aria-controls="file === selected ? panelId : undefined"
          class="tables-tab"
        >
          <span class="tab-name">{{ file }}</span>
          <span v-if="raw.has(file)" class="d-sr-only">, raw table</span>
          <span v-if="counts.problems.get(file)" class="tab-count tab-count--problems">
            <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
            <span aria-hidden="true">{{ counts.problems.get(file) }}</span>
            <span class="d-sr-only">, {{ plural(counts.problems.get(file) ?? 0, "problem") }}</span>
          </span>
          <span v-if="counts.items.get(file)" class="tab-count tab-count--items">
            <i class="fas fa-comment" aria-hidden="true"></i>
            <span aria-hidden="true">{{ counts.items.get(file) }}</span>
            <span class="d-sr-only">, {{ plural(counts.items.get(file) ?? 0, "open review item") }}</span>
          </span>
        </VTab>
      </VTabs>

      <div v-if="selected" :id="panelId" role="tabpanel" :aria-labelledby="tabId(selected)" class="tables-panel">
        <VProgressLinear v-if="loading" indeterminate color="primary" :aria-label="`Loading ${selected}`" />
        <VAlert v-else-if="error" type="error" variant="tonal" density="compact" class="status-alert">
          {{ selected }} could not be loaded. {{ error }}
          <template #append>
            <VBtn variant="text" size="small" @click="reload">Retry</VBtn>
          </template>
        </VAlert>
        <template v-else-if="table">
          <div class="tables-head">
            <p class="tables-caption">{{ caption }}</p>
            <VSwitch
              v-model="hideEmpty"
              label="Hide empty columns"
              color="primary"
              density="compact"
              hide-details
              inset
              class="tables-hide"
            />
          </div>
          <p v-if="missingLine !== null" class="field-note">
            Line {{ missingLine }} is not a row of {{ table.file }}. The table may have changed since the last
            validation.
          </p>
          <TableGrid
            :key="table.file"
            :table="table"
            :highlight-lines="highlight"
            :issue-cells="issues"
            :focus="focus"
            :hide-empty="hideEmpty"
            :label="table.kind === 'raw' ? `Raw table ${table.file}` : `Rows of ${table.file}`"
            class="tables-grid"
          />
        </template>
      </div>
    </template>

    <AddTableDialog v-model="addTable" :fallback-focus="sectionHeading" @added="added" />
  </div>
</template>

<style scoped>
.tables {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.tables-sync-text,
.tables-sync-summary {
  margin: 0;
}
.tables-sync-summary {
  font-size: 0.875rem;
}
.tables-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tables-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.tables-notice:empty {
  position: absolute;
}
.tables-empty {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.tables-tabs {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* The counts of a tab follow its name. */
.tab-count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-inline-start: 10px;
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.tab-count i {
  font-size: 0.75rem;
}
.tables-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
/* The caption and the switch share a line, or the switch goes below in a narrow window. */
.tables-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0 16px;
}
.tables-caption {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
}
.tables-hide {
  flex: 0 0 auto;
}
/* The label reads as a part of the caption beside it. */
.tables-hide :deep(.v-label) {
  font-size: 0.875rem;
}
/* The rows fill the window when the page scrolls to them, with the actions, the tabs and the
   caption above them in view below the app bar. */
.tables-grid {
  --rows-scroll-margin: 236px;
  --rows-max-height: max(420px, calc(100dvh - 252px));
}
/* The caption and the switch take more lines in a narrow window. */
@media (max-width: 599.98px) {
  .tables-grid {
    --rows-scroll-margin: 300px;
    --rows-max-height: max(320px, calc(100dvh - 316px));
  }
}
</style>
