<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import { VAlert, VBtn, VListItem, VSelect, VSwitch } from "vuetify/components";
import type { SourceSummary, SourceView, StudyDetail, TableKind, TableResponse } from "../../study-views/types";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import AddTableDialog from "../components/AddTableDialog.vue";
import ConflictPanel from "../components/ConflictPanel.vue";
import DataNavigator from "../components/DataNavigator.vue";
import PaperPane from "../components/PaperPane.vue";
import RowsPane from "../components/RowsPane.vue";
import SourcePane from "../components/SourcePane.vue";
import SplitPane from "../components/SplitPane.vue";
import TableNotes from "../components/TableNotes.vue";
import UserHint from "../components/UserHint.vue";
import { useAction } from "../composables/useAction";
import { useLoaded } from "../../study-views/composables/useLoaded";
import { useNotice } from "../composables/useNotice";
import { sectionHeading } from "../composables/useReturnFocus";
import {
  ALL_ROWS,
  fileForSource,
  isShared,
  ownerOf,
  PAPER,
  rowSource,
  selectedFile,
  selectedNotesKind,
  selectionOf,
  selectionQuery,
  sourceOfFile,
  tablesByInfo,
  type RowFilter,
  type Selection,
} from "../../study-views/data";
import { INFO_HEADINGS, infoOutlined, infoStyle } from "../../study-views/info";
import type { NameLink } from "../../study-views/links";
import { paperLine, type PaperPlace } from "../../study-views/paper";
import { useStudyStore } from "../stores/study";
import { beyondLimits, sectionRoute, tableFiles } from "../../study-views/study";
import { tablesOutcome } from "../local";
import { noteKinds } from "../../study-views/tableKinds";
import { syncAlert, syncOutcome, syncSummary, withoutConflicts, type Side } from "../tables";

/**
 * A source of the study beside the rows of a table, read only. The toolbar holds the switch of
 * the empty columns, Open sheet, Sync, Add table and what the sync status means; the head of a
 * shared table holds its Source filter. Below the toolbar are the navigator of the tables and
 * sources, the source pane and the rows pane, which a separator resizes. Tables are edited in the
 * workbook, which Open tables of the study header opens where it was left, and Open sheet at the
 * sheet of the shown table: Sync syncs it, and Add table adds a sheet. While the workbook and the
 * tables conflict, the conflict panel shows at the top of the rows pane.
 * Below it, the notes of the kind of the table in study.json open and close above the rows; they
 * edit the draft of the study store, whose banner under the section tabs shows its unsaved changes.
 * Below 1100 px the navigator becomes two selects, Table and Source, at the start of the
 * toolbar, and below 960 px the panes stack.
 * Beyond the upload limits a note says, in place of the navigator and the panes, that the app
 * cannot show the sources and tables; the sync actions and the conflicts stay.
 * The first source is the paper, the PDFs of the folder: a shared table opens beside it, and its
 * pane stays mounted, hidden, while other sources show. The route has `source=paper` while it
 * shows, and `pdf=<file>` once a PDF was chosen in the head of its pane: a PDF that the study
 * lacks shows the first. The pane keeps the PDF while other sources show, whose routes leave it out.
 *
 * The selection is the route query `source`, `file`, `line` and `column`, so that the Problems
 * and Review sections can link to a row (`data.ts` has its rules). A link may name `notes=<kind>`,
 * which opens those notes above the table and focuses them.
 * A link of a name in the rows opens its row in subjects.tsv or interventions.tsv as a step of its
 * own in the history, so that Back returns; every other change of the selection replaces the
 * address. A route without a source and a file gets the default selection once: the first table with problems or open review items,
 * else the first table, beside its source. After that only the actions of the curator change it.
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
const findSource = (name: string | null) => detail.value?.sources.find((entry) => entry.source === name) ?? null;
/**
 * The attributes of the list in the menu of a select of the toolbar. The list scrolls when its
 * entries do not fit, and the keyboard must reach a region that scrolls, which the tabindex of -1
 * that VSelect gives the list would prevent.
 */
const MENU_LIST: Record<string, unknown> = { tabindex: 0 };
/** The items of the Table select below 1100 px: the tables under the headings of their class of information, as in the navigator. */
const tableItems = computed(() =>
  (detail.value ? tablesByInfo(detail.value) : []).flatMap(({ info, tables }) => [
    { type: "subheader" as const, title: INFO_HEADINGS[info], info },
    ...tables.map((table) => ({ type: "item" as const, title: table.file, value: table.file, info })),
  ]),
);

// The selection

/** The file of the route when the study has it, else the first table of the source of the route, else the default table. */
const file = computed<string | null>(() => (detail.value ? selectedFile(detail.value, query.value) : null));

/** The PDF that the pane of the paper keeps while another source shows. */
const keptPaper = ref<string | null>(null);
/**
 * The PDF that the pane of the paper shows, chosen in its head; null for the first, `<name>.pdf`.
 * The route names it while the paper shows, and the pane keeps it while another source shows.
 */
const paperFile = computed(() => (query.value.source === PAPER ? query.value.pdf : keptPaper.value));
watch(paperFile, (value) => (keptPaper.value = value), { immediate: true });

/** The kind of the notes of the selected table in study.json; null for a raw table, which has none. */
const notesKind = computed<TableKind | null>(() => (detail.value ? selectedNotesKind(detail.value, query.value) : null));

/**
 * The notes that a link of the Problems section opened, whose toggle takes the focus once: not
 * again when the panes stack or stand side by side. The link names them as `notes=<kind>`; the
 * section opens them, which the draft keeps, and leaves only the selection in the address.
 */
const linkedNotes = ref<TableKind | null>(null);
watch(
  () => route.query.notes,
  (named) => {
    const value = detail.value;
    if (!value || typeof named !== "string") return;
    const { substance, name, section } = route.params;
    if (section !== "data" || value.id !== `${String(substance)}/${String(name)}`) return;
    const kind = noteKinds(value).find((candidate) => candidate === named) ?? null;
    if (kind) {
      study.draft.setNotesOpen(kind, true);
      linkedNotes.value = kind;
    }
    go(query.value);
  },
  { immediate: true },
);
watch(file, () => (linkedNotes.value = null));

const {
  data: rows,
  error: rowsError,
  loading: rowsLoading,
  reload: reloadRows,
} = useLoaded<TableResponse, StudyDetail | null>(
  () => file.value,
  (name) => study.table(name),
  () => study.detail,
  (name) => `${name} could not be loaded.`,
);
/** The rows of the selected file; null while another one is shown or it loads. */
const table = computed(() => (rows.value && rows.value.key === file.value ? rows.value.content : null));
/**
 * The study page that the rows were loaded for. Its review items and the lines that the local
 * server matched for them belong to these rows: after a table changed, a newer page can arrive
 * before the rows, and its lines would mark other rows.
 */
const rowsDetail = computed(() => (table.value ? (rows.value?.version ?? null) : null));

/** Whether the route links to a row of a shared table, whose row names the source to show. */
const linkedShared = computed(() => {
  const value = detail.value;
  const linked = query.value.file !== null && file.value === query.value.file && query.value.line !== null;
  return Boolean(value && linked && isShared(value, file.value!));
});
/** Whether the rows of a linked row of a shared table load: the source to show is not known yet. */
const rowPending = computed(() => linkedShared.value && !table.value && rowsLoading.value);

/**
 * The name of the selected source: the paper when the route names it and the study has a PDF,
 * else a source that the route names; else, for a linked row of a shared table, the source
 * that the row names once the rows load, and none while they load; else the source of the
 * table, else the paper, else the first source. Null for a study without sources and PDFs.
 */
const sourceName = computed<string | null>(() => {
  const value = detail.value;
  if (!value) return null;
  if (query.value.source === PAPER && value.papers.length) return PAPER;
  const named = findSource(query.value.source);
  if (named) return named.source;
  // The paper does not show while the rows load: the row may name another source.
  if (rowPending.value) return null;
  if (linkedShared.value && table.value) {
    const fromRow = findSource(rowSource(table.value, query.value.line!));
    if (fromRow) return fromRow.source;
  }
  return sourceOfFile(value, file.value);
});
/** Whether the source pane shows the paper. */
const paperShown = computed(() => sourceName.value === PAPER);
/** The selected source of the study; null while the paper shows. */
const source = computed<SourceSummary | null>(() => findSource(sourceName.value));

// The pane of the paper stays mounted once it showed, hidden while another source shows, so that
// the viewer keeps its page and zoom; another study starts without it.
const paperKept = ref(false);
/**
 * Where the viewer of the paper stands, kept here because the pane mounts again when the panes
 * stack or stand side by side again: the viewer opens its PDF there again.
 */
const paperPlace = ref<PaperPlace | null>(null);
watch(
  paperShown,
  (shown) => {
    if (shown) paperKept.value = true;
  },
  { immediate: true },
);
watch(identity, () => {
  paperKept.value = paperShown.value;
  keptPaper.value = null;
  paperPlace.value = null;
});

/** The items of the Source select below 1100 px: Paper first, disabled without a PDF, then the sources. */
const sourceItems = computed(() => {
  const value = detail.value;
  if (!value) return [];
  const paper = value.papers.length
    ? { title: "Paper", value: PAPER }
    : { title: paperLine(value), value: PAPER, props: { disabled: true } };
  return [paper, ...value.sources.map((entry) => ({ title: entry.source, value: entry.source }))];
});
/** Whether the Source select has a source to choose: the paper or a source of the study. */
const sourceChoices = computed(() => Boolean(detail.value && (detail.value.papers.length || detail.value.sources.length)));

const {
  data: view,
  error: viewError,
  loading: viewLoading,
  reload: reloadView,
} = useLoaded<SourceView>(
  () => source.value?.source ?? null,
  (name) => study.source(name),
  () => study.detail,
  (name) => `${name} could not be loaded.`,
);
/** The view of the selected source; null while another one is shown or it loads. */
const sourceView = computed(() =>
  view.value && view.value.key === source.value?.source ? view.value.content : null,
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

/** Show `selection`; while it shows the paper, the route names its PDF, the one of the pane by default. */
function go(selection: Omit<Selection, "pdf">, pdf = paperFile.value): void {
  void router.replace({ query: selectionQuery({ ...selection, pdf: selection.source === PAPER ? pdf : null }) });
}

/** Show the PDF chosen in the head of the pane of the paper, which shows. */
function selectPaper(name: string): void {
  go(query.value, name);
}

function selectSource(name: string): void {
  if (name === PAPER) {
    // The paper has no tables: the rows pane keeps its table and row.
    if (detail.value?.papers.length) go({ ...query.value, source: PAPER, file: file.value });
    return;
  }
  const summary = findSource(name);
  if (!summary || !detail.value) return;
  go({ source: name, file: fileForSource(detail.value, summary, file.value), line: null, column: null });
}

function selectFile(name: string): void {
  if (!detail.value) return;
  const owner = ownerOf(detail.value, name);
  go({ source: owner ?? sourceName.value, file: name, line: null, column: null });
}

/**
 * The selection of a row of the rows pane. A row of a shared table that names a source shows
 * that source, unless the paper shows: the curator reads the paper against the rows.
 */
function lineSelection(line: number): Omit<Selection, "pdf"> {
  const named = table.value && !paperShown.value ? findSource(rowSource(table.value, line)) : null;
  return { source: named?.source ?? sourceName.value, file: file.value, line, column: null };
}

/** Select a row of the rows pane. */
function selectLine(line: number): void {
  go(lineSelection(line));
}

/**
 * Follow the link of a name in the row at `line` to the row of the name. The row of the link is
 * selected first, as a click on it selects it, so that browser Back returns to it; the row of the
 * name is a step of its own in the history. The paper keeps showing with its PDF; else the source
 * that the row of the name names shows, as for a row that the Problems section links to.
 */
async function follow(link: NameLink, line: number): Promise<void> {
  const pdf = paperShown.value ? paperFile.value : null;
  const from = lineSelection(line);
  // A route that selects the row already keeps its column, which Back then returns to.
  const selected = query.value.line === line && query.value.file === from.file && query.value.source === from.source;
  if (!selected) await router.replace({ query: selectionQuery({ ...from, pdf: from.source === PAPER ? pdf : null }) });
  await router.push({
    query: selectionQuery({
      source: paperShown.value ? PAPER : null,
      pdf,
      file: link.file,
      line: link.line,
      column: null,
    }),
  });
}

function selectRow(row: { file: string; line: number }): void {
  go({ source: sourceName.value, file: row.file, line: row.line, column: null });
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
    const chosen = sourceName.value;
    if (chosen !== null || file.value !== null) go({ source: chosen, file: file.value, line: null, column: null });
  },
  { immediate: true },
);

// Most tables leave many of their fixed columns empty, so they are hidden until the curator shows them.
const hideEmpty = ref(true);
/** The filter of the rows of the selected shared table, which the study keeps per table while it is open. */
const filter = computed(() => (file.value ? study.rowFilter(file.value) : ALL_ROWS));

function setFilter(next: RowFilter): void {
  if (file.value) study.setRowFilter(file.value, next);
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
        filter: filter.value,
        hideEmpty: hideEmpty.value,
      }
    : null,
);
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
  <div class="data-section" :class="{ 'data-section--fill': !stacked && !limited }">
    <template v-if="detail">
      <!-- No toolbar role: its controls are reached with Tab, not with the arrow keys that a toolbar promises. -->
      <div class="data-toolbar">
        <template v-if="!wide">
          <VSelect
            v-if="files.length"
            :model-value="file"
            :items="tableItems"
            :list-props="MENU_LIST"
            label="Table"
            density="compact"
            hide-details
            class="data-select data-select--table"
            @update:model-value="selectFile"
          >
            <template #item="{ props: itemProps, item }">
              <VListItem v-bind="itemProps">
                <template #prepend>
                  <span
                    class="data-option-dot"
                    :class="{ 'data-option-dot--outlined': infoOutlined(item.info) }"
                    :style="infoStyle(item.info)"
                    aria-hidden="true"
                  ></span>
                </template>
              </VListItem>
            </template>
          </VSelect>
          <VSelect
            v-if="sourceChoices"
            :model-value="sourceName"
            :items="sourceItems"
            :list-props="MENU_LIST"
            label="Source"
            density="compact"
            hide-details
            class="data-select"
            @update:model-value="selectSource"
          />
        </template>
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
          v-if="file"
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
      </div>

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
      <ConflictPanel v-if="conflicted && !rowsPane" v-bind="conflictPanel" @keep="keep" @open="openWorkbook()" />

      <p v-if="limited" class="data-empty">
        This study is beyond the upload limits, so the app cannot show its sources and tables. See
        <RouterLink :to="sectionRoute(identity, 'problems')">Problems</RouterLink>.
      </p>
      <div v-else class="data-panes">
        <DataNavigator
          v-if="wide"
          :detail="detail"
          :source="sourceName"
          :file="file"
          :paper="paperFile"
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
            <PaperPane
              v-if="paperKept && detail.papers.length"
              v-show="paperShown"
              :file="paperFile"
              v-model:place="paperPlace"
              @update:file="selectPaper"
              :study="identity"
              :papers="detail.papers"
            />
            <SourcePane v-if="!paperShown && sourcePane" v-bind="sourcePane" @select-row="selectRow" @retry="reloadView" />
            <p v-else-if="!paperShown && !rowPending" class="data-empty data-pane-note">The study has no sources yet.</p>
          </template>
          <template #end>
            <RowsPane
              v-if="rowsPane"
              v-bind="rowsPane"
              @select-line="selectLine"
              @follow="follow"
              @retry="reloadRows"
              @update:filter="setFilter"
            >
              <ConflictPanel v-if="conflicted" v-bind="conflictPanel" @keep="keep" @open="openWorkbook()" />
              <TableNotes
                v-if="notesKind"
                :key="notesKind"
                :kind="notesKind"
                :focused="linkedNotes === notesKind"
                @took-focus="linkedNotes = null"
              />
            </RowsPane>
            <p v-else class="data-empty data-pane-note">
              The study has no tables yet. Add table adds a sheet to the workbook.
            </p>
          </template>
        </SplitPane>
        <div v-else class="data-stack">
          <PaperPane
            v-if="paperKept && detail.papers.length"
            v-show="paperShown"
            :file="paperFile"
            v-model:place="paperPlace"
            @update:file="selectPaper"
            :study="identity"
            :papers="detail.papers"
          />
          <SourcePane v-if="!paperShown && sourcePane" v-bind="sourcePane" @select-row="selectRow" @retry="reloadView" />
          <p v-else-if="!paperShown && !rowPending" class="data-empty data-pane-note">The study has no sources yet.</p>
          <RowsPane
            v-if="rowsPane"
            v-bind="rowsPane"
            @select-line="selectLine"
            @follow="follow"
            @retry="reloadRows"
            @update:filter="setFilter"
          >
            <ConflictPanel v-if="conflicted" v-bind="conflictPanel" @keep="keep" @open="openWorkbook()" />
            <TableNotes
              v-if="notesKind"
              :key="notesKind"
              :kind="notesKind"
              :focused="linkedNotes === notesKind"
              @took-focus="linkedNotes = null"
            />
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
/* In a window too short for the section, the page scrolls beyond the app, and keeps the color of
   the app there. */
:global(html:has(.data-section--fill)) {
  background: rgb(var(--v-theme-background));
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
/* A short window scrolls the page rather than squeezing the panes. The section and the banner of
   unsaved changes above it take at least 480 px together, so that the banner, which sticks while
   the page scrolls and it has something to say, covers no more of the panes than needed. */
.data-section--fill {
  flex: 1 1 0;
  min-height: calc(480px - var(--unsaved-banner-space, 0px));
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
/* The class of information of a table in the Table select: a dot in its color. */
.data-option-dot {
  width: 8px;
  height: 8px;
  margin-inline-end: 8px;
  border-radius: 50%;
  background: rgb(var(--info));
}
/* A raw extraction: an outline in its color, as its bar in the navigator. */
.data-option-dot--outlined {
  box-sizing: border-box;
  border: 1px solid rgb(var(--info));
  background: none;
}
/* The switch keeps its label apart from the button after it. */
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
/* As wide as its longest name beside its badges, whatever font the machine draws it in (DejaVu Sans
   is about 14 % wider than Noto Sans), from 232 px up to 320 px; a longer name ends with an
   ellipsis and its title gives it whole. A scrollbar widens it instead of cutting a name. */
.data-navigator-pane {
  flex: none;
  width: max-content;
  min-width: 232px;
  max-width: 320px;
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
/* Each stacked pane scrolls on its own. The source pane fits its content up to 70vh, so that a short
   image leaves no empty space; the paper and the rows pane have a fixed height. */
.data-stack > .source-pane {
  height: auto;
  max-height: 70vh;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.data-stack > .paper-pane {
  height: 70vh;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.data-stack > .rows-pane {
  height: 70vh;
}
</style>
