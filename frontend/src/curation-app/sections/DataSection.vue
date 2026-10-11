<script setup lang="ts">
import { computed, ref, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import { VBtn, VSelect, VSwitch } from "vuetify/components";
import type { SourceSummary, SourceView, StudyDetail, TableResponse } from "../api/types";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import AddTableDialog from "../components/AddTableDialog.vue";
import ConflictPanel from "../components/ConflictPanel.vue";
import DataNavigator from "../components/DataNavigator.vue";
import RowsPane from "../components/RowsPane.vue";
import SourcePane from "../components/SourcePane.vue";
import SplitPane from "../components/SplitPane.vue";
import UserHint from "../components/UserHint.vue";
import { useAction } from "../composables/useAction";
import { useLoaded } from "../composables/useLoaded";
import { useNotice } from "../composables/useNotice";
import { sectionHeading } from "../composables/useReturnFocus";
import {
  defaultSource,
  fileForSource,
  isShared,
  ownerOf,
  rowSource,
  selectionOf,
  selectionQuery,
  type Selection,
  type SourceRows,
} from "../data";
import { useStudyStore } from "../stores/study";
import { beyondLimits, sectionRoute, tableFiles, tablesOutcome } from "../study";
import { syncAlert, syncOutcome, syncSummary, withoutConflicts, type Side } from "../tables";

/**
 * A source of the study beside the rows of a table, read only. The toolbar holds the source
 * filter of a shared table, the switch of the empty columns, Sync, Add table and what the sync
 * status means; below it the navigator of the sources and table files, the source pane and the
 * rows pane, which a separator resizes. Tables are edited in the workbook, which Open tables of
 * the study header opens: Sync syncs it, and Add table adds a sheet. While the workbook and the
 * tables conflict, the conflict panel shows at the top of the rows pane. Below 1100 px the
 * navigator becomes two selects, and below 960 px the panes stack. Beyond the upload limits a
 * note says, in place of the navigator and the panes, that the app cannot show the sources and
 * tables; the sync actions and the conflicts stay.
 *
 * The selection is the route query `source`, `file`, `line` and `column`, so that the Problems
 * and Review sections can link to a row (`data.ts` has its rules). A route without a source and
 * a file gets the default selection once; after that only the actions of the curator change it.
 */
const study = useStudyStore();
const route = useRoute();
const router = useRouter();
const { notice, announce } = useNotice();

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");
/** Beyond the upload limits the local server lists no sources and tables, which the study may well have. */
const limited = computed(() => (detail.value ? beyondLimits(detail.value) : false));
const query = computed(() => selectionOf(route.query));
const files = computed(() => (detail.value ? tableFiles(detail.value) : []));
const sourceNames = computed(() => detail.value?.sources.map((entry) => entry.source) ?? []);
const findSource = (name: string | null) => detail.value?.sources.find((entry) => entry.source === name) ?? null;

// The selection

/** The file of the route when the study has it, else the file of the source. */
const file = computed<string | null>(() => {
  const value = detail.value;
  if (!value) return null;
  if (query.value.file !== null && files.value.includes(query.value.file)) return query.value.file;
  const source = findSource(query.value.source) ?? defaultSource(value);
  return source ? fileForSource(value, source, null) : (files.value[0] ?? null);
});

const {
  data: rows,
  error: rowsError,
  loading: rowsLoading,
  reload: reloadRows,
} = useLoaded<TableResponse, StudyDetail | null>(
  () => file.value,
  (name) => study.table(name),
  () => study.detail,
);
/** The rows of the selected file; null while another one is shown or it loads. */
const table = computed(() => (rows.value && rows.value.key === file.value ? rows.value.content : null));
/**
 * The study page that the rows were loaded for. Its review items and the lines that the local
 * server matched for them belong to these rows: after a table changed, a newer page can arrive
 * before the rows, and its lines would mark other rows.
 */
const rowsDetail = computed(() => (table.value ? (rows.value?.version ?? null) : null));

/**
 * The source of the route; else, for a linked file, its owner or the source named in the linked
 * row of a shared table; else the default source.
 */
const source = computed<SourceSummary | null>(() => {
  const value = detail.value;
  if (!value) return null;
  const named = findSource(query.value.source);
  if (named) return named;
  if (query.value.file !== null && file.value === query.value.file) {
    const owner = findSource(ownerOf(value, file.value));
    if (owner) return owner;
    if (table.value && query.value.line !== null) {
      const fromRow = findSource(rowSource(table.value, query.value.line));
      if (fromRow) return fromRow;
    }
  }
  return defaultSource(value);
});

const {
  data: view,
  error: viewError,
  loading: viewLoading,
  reload: reloadView,
} = useLoaded<SourceView>(
  () => source.value?.source ?? null,
  (name) => study.source(name),
  () => study.detail,
);
/** The view of the selected source; null while another one is shown or it loads. */
const sourceView = computed(() =>
  view.value && view.value.key === source.value?.source ? view.value.content : null,
);
/**
 * The rows of the selected source per file, for the navigator. While the next source loads, those
 * of the last one stay with its name, so that the counts and the dimmed files do not flicker on
 * every click; a source that failed to load, a study without sources and another study have none.
 */
const sourceRows = shallowRef<SourceRows | null>(null);
watch(
  [sourceView, viewError, () => source.value === null, identity],
  ([shown, error, none, study], previous) => {
    if (shown)
      sourceRows.value = {
        source: shown.source,
        files: new Map(shown.mapped.map((entry) => [entry.file, entry.rows.length])),
      };
    else if (error !== null || none || study !== previous?.[3]) sourceRows.value = null;
  },
  { immediate: true },
);
/** The cell of the route in the selected file: its line, and its column when it names one. */
const focus = computed(() =>
  query.value.line !== null && file.value === query.value.file
    ? query.value.column !== null
      ? { line: query.value.line, column: query.value.column }
      : { line: query.value.line }
    : null,
);
/** The selected row, whose point the plot or overlay of the source rings. */
const selectedRow = computed(() => (focus.value && file.value ? { file: file.value, line: focus.value.line } : null));

function go(selection: Selection): void {
  void router.replace({ query: selectionQuery(selection) });
}

function selectSource(name: string): void {
  const summary = findSource(name);
  if (!summary || !detail.value) return;
  go({ source: name, file: fileForSource(detail.value, summary, file.value), line: null, column: null });
}

function selectFile(name: string): void {
  if (!detail.value) return;
  const owner = ownerOf(detail.value, name);
  go({ source: owner ?? source.value?.source ?? null, file: name, line: null, column: null });
}

function selectLine(line: number): void {
  const named = table.value ? findSource(rowSource(table.value, line)) : null;
  go({ source: named?.source ?? source.value?.source ?? null, file: file.value, line, column: null });
}

function selectRow(row: { file: string; line: number }): void {
  go({ source: source.value?.source ?? null, file: row.file, line: row.line, column: null });
}

// The default selection goes into the route as soon as the study is loaded, so that it stays when
// the problems that chose it change, such as when the curator fixes them. Only the route of this
// section of this study takes it: a route that leaves the section changes before it unmounts.
watch(
  [detail, query],
  ([value, selection]) => {
    if (!value || selection.source !== null || selection.file !== null) return;
    const { substance, name, section } = route.params;
    if (section !== "data" || value.id !== `${String(substance)}/${String(name)}`) return;
    const chosen = source.value?.source ?? null;
    if (chosen !== null || file.value !== null) go({ source: chosen, file: file.value, line: null, column: null });
  },
  { immediate: true },
);

// Most tables leave many of their fixed columns empty, so they are hidden until the curator shows them.
const hideEmpty = ref(true);
// A shared table shows the rows of the selected source until the curator shows all.
const onlySource = ref(true);
watch(file, () => (onlySource.value = true));
/** Whether the rows are of a shared table, which names the source of each row. */
const shared = computed(() => detail.value !== null && file.value !== null && isShared(detail.value, file.value));

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

// The panes, side by side or stacked

const display = useDisplay();
/** Whether the navigator has room beside the panes; else it becomes two selects in the toolbar. */
const wide = computed(() => display.width.value >= 1100);
/** Whether the panes are too narrow side by side; they then stack, the source above its rows. */
const stacked = computed(() => display.width.value < 960);

/** The props of the source pane, which both layouts share; null without a source. */
const sourcePane = computed(() =>
  source.value
    ? {
        summary: source.value,
        view: sourceView.value,
        loading: viewLoading.value,
        error: viewError.value,
        selected: selectedRow.value,
      }
    : null,
);
/** The props of the rows pane, which both layouts share; null without a table. */
const rowsPane = computed(() =>
  detail.value && file.value
    ? {
        detail: detail.value,
        file: file.value,
        table: table.value,
        rowsDetail: rowsDetail.value,
        loading: rowsLoading.value,
        error: rowsError.value,
        focus: focus.value,
        source: source.value?.source ?? null,
        onlySource: onlySource.value,
        hideEmpty: hideEmpty.value,
      }
    : null,
);
/** The props of the conflict panel; the progress of Sync shows on its own button. */
const conflictPanel = computed(() => {
  const running = busy.value;
  return { conflicts: detail.value?.conflicts ?? [], busy: running === "sync" ? null : running, disabled: working.value };
});
</script>

<template>
  <div class="data-section" :class="{ 'data-section--fill': !stacked && !limited }">
    <template v-if="detail">
      <!-- No toolbar role: its controls are reached with Tab, not with the arrow keys that a toolbar promises. -->
      <div class="data-toolbar">
        <template v-if="!wide">
          <VSelect
            v-if="sourceNames.length"
            :model-value="source?.source ?? null"
            :items="sourceNames"
            label="Source"
            density="compact"
            hide-details
            class="data-select"
            @update:model-value="selectSource"
          />
          <VSelect
            v-if="files.length"
            :model-value="file"
            :items="files"
            label="Table"
            density="compact"
            hide-details
            class="data-select data-select--table"
            @update:model-value="selectFile"
          />
        </template>
        <VSwitch
          v-if="shared && source"
          v-model="onlySource"
          :label="`Rows of ${source.source} only`"
          color="primary"
          density="compact"
          hide-details
          inset
          class="data-switch"
        />
        <VSwitch
          v-if="file"
          v-model="hideEmpty"
          label="Hide empty columns"
          color="primary"
          density="compact"
          hide-details
          inset
          class="data-switch"
        />
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
      </div>

      <ActionFailureAlert v-if="failure" :failure="failure" :study="identity" @close="failure = null" />
      <UserHint v-else-if="userText" :text="userText" />
      <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
      <span role="status" aria-live="polite" class="data-notice">{{ notice }}</span>
      <!-- Without a table, also beyond the upload limits, the conflicts have no rows pane to show in. -->
      <ConflictPanel v-if="conflicted && !rowsPane" v-bind="conflictPanel" @keep="keep" @open="openWorkbook" />

      <p v-if="limited" class="data-empty">
        This study is beyond the upload limits, so the app cannot show its sources and tables. See
        <RouterLink :to="sectionRoute(identity, 'problems')">Problems</RouterLink>.
      </p>
      <div v-else class="data-panes">
        <DataNavigator
          v-if="wide"
          :detail="detail"
          :source="source?.source ?? null"
          :file="file"
          :rows="sourceRows"
          class="data-navigator-pane"
          @select-source="selectSource"
          @select-file="selectFile"
        />
        <SplitPane
          v-if="!stacked"
          storage-key="pkdb-curation:data-split"
          label="Resize the source and the rows"
          class="data-split"
        >
          <template #start>
            <SourcePane v-if="sourcePane" v-bind="sourcePane" @select-row="selectRow" @retry="reloadView" />
            <p v-else class="data-empty data-pane-note">The study has no sources yet.</p>
          </template>
          <template #end>
            <RowsPane
              v-if="rowsPane"
              v-bind="rowsPane"
              @select-line="selectLine"
              @retry="reloadRows"
              @show-all="onlySource = false"
            >
              <ConflictPanel v-if="conflicted" v-bind="conflictPanel" @keep="keep" @open="openWorkbook" />
            </RowsPane>
            <p v-else class="data-empty data-pane-note">
              The study has no tables yet. Add table adds a sheet to the workbook.
            </p>
          </template>
        </SplitPane>
        <div v-else class="data-stack">
          <SourcePane v-if="sourcePane" v-bind="sourcePane" @select-row="selectRow" @retry="reloadView" />
          <p v-else class="data-empty data-pane-note">The study has no sources yet.</p>
          <RowsPane
            v-if="rowsPane"
            v-bind="rowsPane"
            @select-line="selectLine"
            @retry="reloadRows"
            @show-all="onlySource = false"
          >
            <ConflictPanel v-if="conflicted" v-bind="conflictPanel" @keep="keep" @open="openWorkbook" />
          </RowsPane>
          <p v-else class="data-empty data-pane-note">
            The study has no tables yet. Add table adds a sheet to the workbook.
          </p>
        </div>
      </div>

      <AddTableDialog v-model="addTable" :fallback-focus="sectionHeading" @added="added" />
    </template>
  </div>
</template>

<style scoped>
.data-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
/* While the panes stand side by side, the page fills the window and does not scroll: a flex column
   from the app down to the section, which takes what the app bar, a status banner, the study
   header and the section tabs leave of the window, and its panes scroll on their own. Other
   sections scroll with the page, as do stacked panes, each at most 70 % of the window, and the
   note beyond the upload limits. */
:global(.v-application__wrap:has(.data-section--fill)) {
  height: 100dvh;
}
:global(.v-main:has(.data-section--fill)) {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-height: 0;
}
:global(.study-page:has(.data-section--fill)) {
  flex: 1 1 0;
  min-height: 0;
}
:global(.study-section:has(.data-section--fill)) {
  flex: 1 1 0;
  min-height: 0;
}
/* A short window scrolls the page rather than squeezing the panes. */
.data-section--fill {
  flex: 1 1 0;
  min-height: 480px;
}
/* A wrapped line leaves room for the labels of the selects, which stand above their fields. */
.data-toolbar {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 6px;
  min-height: 30px;
}
.data-select {
  flex: 0 1 140px;
  min-width: 110px;
}
.data-select--table {
  flex-basis: 240px;
}
/* A switch keeps apart from the label of the switch before it. */
.data-switch {
  flex: 0 0 auto;
  margin-inline-end: 6px;
}
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
.data-empty {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.data-pane-note {
  padding: 8px;
  font-size: 13px;
}
.data-panes {
  display: flex;
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  background: rgb(var(--v-theme-surface));
}
.data-navigator-pane {
  flex: 0 0 184px;
  border-inline-end: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.data-split {
  flex: 1 1 0;
}
.data-stack {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  min-width: 0;
}
/* Each stacked pane scrolls on its own. The rows pane has a fixed height, which its grid fills. */
.data-stack > .source-pane {
  max-height: 70vh;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.data-stack > .rows-pane {
  height: 70vh;
}
</style>
