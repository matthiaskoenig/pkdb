<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { VAlert, VBtn, VCard, VChip, VMenu, VSelect, VTooltip } from "vuetify/components";
import { isNoUser, isRevisionConflict, isValidationError } from "../api/client";
import type { ReviewStatus, StudyDetail, TablesResult } from "../api/types";
import {
  activityLabel,
  formatTime,
  issueUrl,
  MODE_LABELS,
  problemLabels,
  REVIEW_LABELS,
  SYNC_LABELS,
  SYNC_TONES,
  uploadBlocker,
} from "../overview";
import { useDialogStore } from "../stores/dialogs";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import {
  approvalRefusal,
  folderPath,
  issueLabel,
  provenanceLabel,
  releaseLabel,
  studyName,
} from "../study";
import AddTableDialog from "./AddTableDialog.vue";
import UploadDialog from "./UploadDialog.vue";

const props = defineProps<{
  detail: StudyDetail;
  /** The last load of the study failed: the header shows the last known state and offers no actions. */
  stale: boolean;
}>();

const study = useStudyStore();
const overview = useOverviewStore();
const dialogs = useDialogStore();
const blockerId = useId();

type Action = "status" | "tables" | "validate" | "folder" | "pdf" | "copy";

const busy = ref<Action | null>(null);
/** The failure of the last action, with the issues that the API listed. */
const failure = ref<{ text: string; issues: string[] } | null>(null);
const notice = ref("");
const menu = ref(false);
const addTable = ref(false);
const upload = ref(false);

const substance = computed(() => props.detail.id.slice(0, props.detail.id.indexOf("/")));
const name = computed(() => studyName(props.detail));
const summary = computed(() => props.detail.summary);
const release = computed(() => (summary.value.release ? releaseLabel(summary.value.release) : null));
const issue = computed(() => {
  const label = issueLabel(props.detail.issue, summary.value.issue);
  if (label === null) return null;
  return { label, url: issueUrl(props.detail, overview.snapshot?.github.repository ?? "") };
});
const provenance = computed(() => provenanceLabel(summary.value));
const pmid = computed(() => {
  const reference = props.detail.reference;
  const fromReference = reference && "pmid" in reference ? reference.pmid : null;
  return props.detail.metadata.value?.reference?.pmid ?? fromReference ?? null;
});
const problems = computed(() => problemLabels(props.detail));
const activity = computed(() => activityLabel(props.detail));
const pdf = computed(() => `${name.value}.pdf`);
const hasPdf = computed(() => props.detail.files.includes(pdf.value));

// Review status
const STATUS_ITEMS = (Object.keys(REVIEW_LABELS) as ReviewStatus[]).map((value) => ({
  title: REVIEW_LABELS[value],
  value,
}));
/** The status that a write is setting; the select shows it until the write ends. */
const pendingStatus = ref<ReviewStatus | null>(null);
const savedStatus = computed(() => props.detail.review.value?.status ?? summary.value.review_status ?? null);
const reviewStatus = computed(() => pendingStatus.value ?? savedStatus.value);
/** An invalid review.json has no status to change; the Problems section names its issues. */
const canSetStatus = computed(
  () => props.detail.review.revision !== null && props.detail.review.value !== null && !props.stale,
);

// Upload
/** The overview row of the study, which the upload review lists. */
const row = computed(
  () =>
    overview.snapshot?.studies.find((candidate) => candidate.id === props.detail.id && !candidate.duplicate) ??
    null,
);
const blocker = computed(() => (overview.snapshot ? uploadBlocker(overview.snapshot) : null));
const canUpload = computed(() => row.value !== null && blocker.value === null && !props.stale);

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught);
}

/** Run an action; a write that needs a user opens the settings. */
async function run(action: Action, work: () => Promise<string | void>, explain = messageOf): Promise<void> {
  busy.value = action;
  failure.value = null;
  notice.value = "";
  try {
    notice.value = (await work()) ?? "";
  } catch (caught) {
    if (isNoUser(caught)) dialogs.openSettings();
    failure.value = { text: explain(caught), issues: [] };
  } finally {
    busy.value = null;
  }
}

function setStatus(value: ReviewStatus | null): Promise<void> | void {
  const revision = props.detail.review.revision;
  if (value === null || value === savedStatus.value || revision === null) return;
  pendingStatus.value = value;
  return run(
    "status",
    async () => {
      await study.reviewAction(revision, "status", { status: value });
      return `Review status set to ${REVIEW_LABELS[value]}.`;
    },
    (caught) => {
      if (isValidationError(caught) && caught.body.code === "approval_refused")
        return approvalRefusal(caught.message);
      if (isRevisionConflict(caught))
        return "review.json changed on disk, so the status was not set. Check the review and set it again.";
      return messageOf(caught);
    },
  ).finally(() => {
    pendingStatus.value = null;
  });
}

/** What the curator should know after Open tables: nothing for a clean sync. */
function tablesOutcome(result: TablesResult): { text: string; issues: string[] } | null {
  const issues = result.issues.map((item) => item.message);
  const unresolved = result.conflicts.filter((conflict) => conflict.kept === null).length;
  if (unresolved === 1) issues.push("A sheet conflicts with its table. Resolve the conflict in Tables.");
  if (unresolved > 1) issues.push(`${unresolved} sheets conflict with their tables. Resolve the conflicts in Tables.`);
  if (!result.opened) return { text: "The workbook could not be opened.", issues };
  return issues.length ? { text: "The workbook opened, but the sync found problems.", issues } : null;
}

function openTables(): Promise<void> {
  return run("tables", async () => {
    const result = await study.tablesAction("open");
    failure.value = tablesOutcome(result);
    return result.opened ? "The workbook opened." : "";
  });
}

function validate(): Promise<void> {
  return run("validate", async () => {
    await overview.enqueue([props.detail.id], "validate");
    return "Validation queued.";
  });
}

function fromMenu(action: () => unknown): void {
  menu.value = false;
  void action();
}

function openFolder(): Promise<void> {
  return run("folder", () => overview.openFile(props.detail.id));
}

function openPdf(): Promise<void> {
  return run("pdf", () => overview.openFile(props.detail.id, pdf.value));
}

function copyPath(): Promise<void> {
  const workspace = overview.snapshot?.workspace;
  const path = workspace ? folderPath(workspace, props.detail.path) : props.detail.path;
  return run(
    "copy",
    async () => {
      await navigator.clipboard.writeText(path);
      return "Path copied.";
    },
    () => `The path could not be copied: ${path}`,
  );
}

function added(table: string): void {
  failure.value = null;
  notice.value = `Added the sheet ${table} to the workbook.`;
}
</script>

<template>
  <header class="study-header">
    <div class="study-header-row">
      <div class="study-heading">
        <!-- A long identity wraps after the slash rather than inside a name. -->
        <h1 class="study-identity">{{ substance }}/<wbr />{{ name }}</h1>
        <div v-if="release || issue || provenance" class="study-chips">
          <VChip
            v-if="release"
            size="small"
            variant="tonal"
            color="success"
            prepend-icon="fas fa-tag"
            class="status-chip release-chip"
          >
            {{ release }}
          </VChip>
          <template v-if="issue">
            <VChip
              v-if="issue.url"
              :href="issue.url"
              target="_blank"
              rel="noopener noreferrer"
              size="small"
              variant="outlined"
              prepend-icon="fas fa-circle-dot"
              class="header-chip issue-chip"
              :aria-label="`GitHub issue ${issue.label}`"
            >
              {{ issue.label }}
            </VChip>
            <VChip
              v-else
              size="small"
              variant="outlined"
              prepend-icon="fas fa-circle-dot"
              class="header-chip issue-chip"
            >
              {{ issue.label }}
            </VChip>
          </template>
          <VChip
            v-if="provenance"
            size="small"
            variant="outlined"
            prepend-icon="fas fa-robot"
            class="header-chip provenance-chip"
          >
            {{ provenance }}
          </VChip>
        </div>
      </div>

      <div class="study-actions">
        <VSelect
          :model-value="reviewStatus"
          :items="STATUS_ITEMS"
          label="Review status"
          density="compact"
          hide-details
          :disabled="!canSetStatus"
          :loading="busy === 'status'"
          class="review-select"
          @update:model-value="setStatus"
        />
        <div class="study-buttons">
          <VBtn
            variant="tonal"
            color="primary"
            prepend-icon="fas fa-table"
            :disabled="stale"
            :loading="busy === 'tables'"
            @click="openTables"
          >
            Open tables
          </VBtn>
          <VBtn
            variant="tonal"
            color="primary"
            prepend-icon="fas fa-circle-check"
            :disabled="stale"
            :loading="busy === 'validate'"
            @click="validate"
          >
            Validate
          </VBtn>
          <!-- Not eager: a closed tooltip in the page would be a tooltip without a visible name. -->
          <VTooltip :disabled="!blocker" :text="blocker ?? ''" :eager="false" location="top">
            <template #activator="{ props: tooltip }">
              <span v-bind="tooltip" class="upload-action">
                <VBtn
                  variant="tonal"
                  color="primary"
                  prepend-icon="fas fa-cloud-arrow-up"
                  :disabled="!canUpload"
                  :aria-describedby="blocker ? blockerId : undefined"
                  @click="upload = true"
                >
                  Upload
                </VBtn>
              </span>
            </template>
          </VTooltip>
          <span v-if="blocker" :id="blockerId" class="d-sr-only">{{ blocker }}</span>
          <VMenu v-model="menu" location="bottom end">
            <template #activator="{ props: activator }">
              <VBtn
                v-bind="activator"
                icon="fas fa-ellipsis-vertical"
                variant="text"
                density="comfortable"
                class="more-actions"
                aria-label="More actions"
              />
            </template>
            <VCard elevation="6" border class="header-menu header-panel study-menu">
              <VBtn
                variant="text"
                prepend-icon="fas fa-folder-open"
                class="header-control"
                :disabled="stale"
                @click="fromMenu(openFolder)"
              >
                Open folder
              </VBtn>
              <VBtn
                variant="text"
                prepend-icon="fas fa-file-pdf"
                class="header-control"
                :disabled="stale || !hasPdf"
                @click="fromMenu(openPdf)"
              >
                Open PDF
              </VBtn>
              <p v-if="!hasPdf" class="study-menu-note">No {{ pdf }} in the folder</p>
              <VBtn
                variant="text"
                prepend-icon="fas fa-plus"
                class="header-control"
                :disabled="stale"
                @click="fromMenu(() => (addTable = true))"
              >
                Add table
              </VBtn>
              <VBtn variant="text" prepend-icon="fas fa-copy" class="header-control" @click="fromMenu(copyPath)">
                Copy path
              </VBtn>
            </VCard>
          </VMenu>
        </div>
      </div>
    </div>

    <p class="study-title" :class="{ 'study-title--missing': !summary.title }">
      {{ summary.title || "No reference title yet" }}
    </p>
    <ul class="study-facts">
      <li v-if="pmid" class="fact fact-pmid">
        <span class="fact-name">PMID</span>
        <a :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}/`" target="_blank" rel="noopener noreferrer">{{ pmid }}</a>
      </li>
      <li class="fact fact-mode"><span class="fact-name">On save</span> {{ MODE_LABELS[detail.mode] }}</li>
      <li class="fact fact-sync">
        <VChip size="small" variant="tonal" :color="SYNC_TONES[detail.sync.status]" class="status-chip">
          {{ SYNC_LABELS[detail.sync.status] }}
        </VChip>
      </li>
      <li v-if="problems.length || activity" class="fact fact-problems">
        <VChip
          v-for="problem in problems"
          :key="problem.label"
          size="small"
          variant="tonal"
          :color="problem.tone"
          class="status-chip"
        >
          {{ problem.label }}
        </VChip>
        <span v-if="activity" class="fact-activity">{{ activity }}</span>
      </li>
      <li v-if="detail.last_upload" class="fact fact-upload">
        <span class="fact-name">Last upload</span>
        <a v-if="detail.last_upload.url" :href="detail.last_upload.url" target="_blank" rel="noopener noreferrer">
          {{ formatTime(detail.last_upload.at) }}
        </a>
        <span v-else>{{ formatTime(detail.last_upload.at) }}</span>
      </li>
    </ul>

    <VAlert
      v-if="failure"
      type="error"
      variant="tonal"
      density="compact"
      closable
      class="status-alert study-alert"
      @click:close="failure = null"
    >
      {{ failure.text }}
      <ul v-if="failure.issues.length" class="study-alert-issues">
        <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
      </ul>
    </VAlert>
    <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
    <span role="status" class="study-notice">{{ notice }}</span>

    <AddTableDialog v-model="addTable" @added="added" />
    <UploadDialog
      v-if="row"
      v-model="upload"
      :studies="[row]"
      action="upload"
      @done="notice = 'Upload queued.'"
    />
  </header>
</template>

<style scoped>
.study-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.study-header-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 24px;
}
.study-heading {
  display: flex;
  flex: 1 1 20rem;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  min-width: 0;
  /* As tall as the select beside it, so that both center on one line. */
  min-height: 40px;
}
.study-identity {
  margin: 0;
  overflow-wrap: anywhere;
}
.study-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.header-chip {
  border-color: rgba(var(--v-theme-on-surface), 0.3);
}
.study-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.review-select {
  width: 10.5rem;
  flex: 0 0 auto;
}
.study-buttons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.upload-action {
  display: inline-flex;
}
.study-title {
  max-width: 60rem;
  margin: 0;
  font-size: 1rem;
  line-height: 1.4;
}
.study-title--missing {
  font-style: italic;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The facts are apart by a wide gap rather than a separator, which would start a wrapped line. */
.study-facts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 20px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.875rem;
}
.fact {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  min-height: 24px;
}
.fact-name,
.fact-activity {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-alert-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
}
.study-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap of the header. */
.study-notice:empty {
  position: absolute;
}
/* On a phone the review status and the menu share the first line and the three actions the
   second one, without icons. */
@media (max-width: 599.98px) {
  .study-actions {
    width: 100%;
    gap: 8px;
  }
  .review-select {
    flex: 1 1 calc(100% - 56px);
  }
  .study-buttons {
    display: contents;
  }
  .study-buttons > .v-btn,
  .upload-action {
    flex: 1 1 auto;
    order: 1;
  }
  .upload-action > .v-btn {
    flex: 1 1 auto;
  }
  .study-buttons > .more-actions {
    flex: 0 0 auto;
    order: 0;
  }
  .study-buttons :deep(.v-btn__prepend) {
    display: none;
  }
}
.study-menu {
  width: auto;
  min-width: 12rem;
}
.study-menu-note {
  margin: -4px 0 4px 44px;
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
