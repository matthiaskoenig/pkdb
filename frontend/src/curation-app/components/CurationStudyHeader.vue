<script setup lang="ts">
/**
 * The study header of the curation app: the shared header (StudyHeader.vue) with the review
 * status, Open tables, Validate, Upload and the menu of the study in its line, and below it why
 * Upload waits, the failure or notice of the last action and the dialogs.
 */
import { computed, ref, useId, useTemplateRef } from "vue";
import { VBtn, VCard, VMenu, VProgressLinear, VSelect, VTooltip } from "vuetify/components";
import { isRevisionConflict, isValidationError } from "../api/client";
import type { ReviewStatus, StudyDetail } from "../../study-views/types";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { REVIEW_LABELS } from "../../study-views/overview";
import { uploadBlocker } from "../uploads";
import { mainPaper, paperName } from "../../study-views/paper";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { actionFailure, failureOf, openItems, type ActionFailure } from "../../study-views/study";
import { approvalRefusal, folderPath, tablesOutcome } from "../local";
import ActionFailureAlert from "../../study-views/components/ActionFailureAlert.vue";
import AddTableDialog from "./AddTableDialog.vue";
import StudyHeader from "../../study-views/components/StudyHeader.vue";
import UploadDialog from "./UploadDialog.vue";
import UserHint from "./UserHint.vue";

const props = defineProps<{
  detail: StudyDetail;
  /** The last load of the study failed: the header shows the last known state and offers no actions. */
  stale: boolean;
}>();

const study = useStudyStore();
const overview = useOverviewStore();
const reasonId = useId();
const statusId = useId();

type Action = "status" | "tables" | "validate" | "folder" | "pdf" | "copy";

/** The notice of the last action that succeeded; it disappears after a few seconds. */
const { notice, announce } = useNotice();
/** The running action: one at a time, so that feedback and revisions never mix. */
const { busy, working, failure, userText, run } = useAction<Action>(announce);
const menu = ref(false);
const addTable = ref(false);
const upload = ref(false);
const actions = useTemplateRef<HTMLElement>("actions");
/** Takes the focus after a dialog when the control that opened it is gone, such as an item of the menu. */
const moreActions = () => actions.value?.querySelector<HTMLElement>(".more-actions");

const summary = computed(() => props.detail.summary);
const pdf = computed(() => paperName(props.detail));
/** The PDF named after the study among its PDFs, which the study page lists also beyond the upload limits. */
const mainPdf = computed(() => mainPaper(props.detail));

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
/** Why Upload is disabled; null while the state of the local server loads or when it can upload. */
const uploadReason = computed(() => {
  const snapshot = overview.snapshot;
  if (!snapshot) return null;
  if (row.value === null) return "The workspace scan has not listed this study yet. Upload waits for the next scan.";
  return uploadBlocker(snapshot);
});
const canUpload = computed(() => row.value !== null && uploadReason.value === null && !props.stale);

/** Why the status was not set: approval explains its rule and lists the errors that block it. */
function statusFailure(caught: unknown): ActionFailure {
  if (isValidationError(caught) && caught.body.code === "approval_refused") {
    const errors = caught.body.issues.map((item) => item.message);
    const link: ActionFailure["link"] = errors.length
      ? { section: "problems", label: "Show the problems" }
      : openItems(props.detail) > 0
        ? { section: "review", label: "Show the open items" }
        : null;
    return actionFailure(approvalRefusal(caught.message), errors, link);
  }
  if (isRevisionConflict(caught))
    return actionFailure("review.json changed on disk, so the status was not set. Check the review and set it again.");
  return failureOf(caught);
}

function setStatus(value: ReviewStatus | null): Promise<void> | void {
  const revision = props.detail.review.revision;
  // While a status is written, the select ignores another choice: it would go over the old revision.
  if (value === null || value === savedStatus.value || revision === null || working.value) return;
  pendingStatus.value = value;
  return run(
    "status",
    async () => {
      await study.reviewAction(revision, "status", { status: value });
      return `Review status set to ${REVIEW_LABELS[value]}.`;
    },
    statusFailure,
  ).finally(() => {
    pendingStatus.value = null;
  });
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
  const file = mainPdf.value?.file;
  return file ? run("pdf", () => overview.openFile(props.detail.id, file)) : Promise.resolve();
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
    () => actionFailure(`The path could not be copied: ${path}`),
  );
}

function added(table: string): void {
  failure.value = null;
  announce(`Added the sheet ${table} to the workbook.`);
}
</script>

<template>
  <StudyHeader :detail="detail">
    <template #actions>
      <div ref="actions" class="study-actions">
        <!-- The field keeps "Review status" as its name; its label stands beside it, as PMID does,
             since a label above the field would not fit into the line. -->
        <span class="fact-status">
          <label :for="statusId" class="fact-name">Review</label>
          <VSelect
            :id="statusId"
            :model-value="reviewStatus"
            :items="STATUS_ITEMS"
            label="Review status"
            single-line
            density="compact"
            hide-details
            :disabled="!canSetStatus || working"
            :loading="busy === 'status'"
            class="review-select"
            @update:model-value="setStatus"
          >
            <!-- Vuetify's loader has no accessible name. -->
            <template #loader="{ isActive, color }">
              <VProgressLinear
                :active="isActive"
                :color="color"
                height="2"
                indeterminate
                aria-label="Setting the review status"
              />
            </template>
          </VSelect>
        </span>
        <div class="study-buttons">
          <VBtn
            variant="tonal"
            color="primary"
            size="small"
            prepend-icon="fas fa-table"
            :disabled="stale || working"
            :loading="busy === 'tables'"
            @click="openTables"
          >
            Open tables
          </VBtn>
          <VBtn
            variant="tonal"
            color="primary"
            size="small"
            prepend-icon="fas fa-circle-check"
            :disabled="stale || working"
            :loading="busy === 'validate'"
            @click="validate"
          >
            Validate
          </VBtn>
          <!-- Not eager: a closed tooltip in the page would be a tooltip without a visible name. -->
          <VTooltip :disabled="!uploadReason" :text="uploadReason ?? ''" :eager="false" location="top">
            <template #activator="{ props: tooltip }">
              <span v-bind="tooltip" class="upload-action">
                <VBtn
                  variant="tonal"
                  color="primary"
                  size="small"
                  prepend-icon="fas fa-cloud-arrow-up"
                  :disabled="!canUpload || working"
                  :aria-describedby="uploadReason ? reasonId : undefined"
                  @click="upload = true"
                >
                  Upload
                </VBtn>
              </span>
            </template>
          </VTooltip>
          <VMenu v-model="menu" location="bottom end">
            <template #activator="{ props: activator }">
              <VBtn
                v-bind="activator"
                icon="fas fa-ellipsis-vertical"
                variant="text"
                size="small"
                :disabled="working"
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
                :disabled="stale || !mainPdf"
                @click="fromMenu(openPdf)"
              >
                Open PDF
              </VBtn>
              <p v-if="!mainPdf" class="study-menu-note">No {{ pdf }} in the folder</p>
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
    </template>
    <template #after>
      <!-- The reason describes Upload for screen readers, and shows where no pointer can hover. -->
      <p v-if="uploadReason" :id="reasonId" class="upload-reason">{{ uploadReason }}</p>
      <ActionFailureAlert
        v-if="failure"
        :failure="failure"
        :study="detail.id"
        class="study-alert"
        @close="failure = null"
      />
      <UserHint v-else-if="userText" :text="userText" />
      <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
      <span role="status" aria-live="polite" class="study-notice">{{ notice }}</span>

      <AddTableDialog v-model="addTable" :fallback-focus="moreActions" @added="added" />
      <UploadDialog
        v-if="row"
        v-model="upload"
        :studies="[row]"
        action="upload"
        :fallback-focus="moreActions"
        @done="announce('Upload queued.')"
      />
    </template>
  </StudyHeader>
</template>

<style scoped>
.fact-name {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-actions {
  display: flex;
  flex: 0 0 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
}
.fact-status {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
}
.review-select {
  width: 150px;
  flex: 0 0 auto;
}
.more-actions {
  width: 28px;
  height: 28px;
}
.study-buttons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.upload-action {
  display: inline-flex;
}
/* Hidden like d-sr-only where the tooltip of Upload says it, on a wide window with a pointer. */
.upload-reason {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
@media (max-width: 599.98px), (hover: none) {
  .upload-reason {
    position: static;
    flex: 1 1 100%;
    width: auto;
    height: auto;
    overflow: visible;
    clip: auto;
    font-size: 13px;
    line-height: 1.4;
    white-space: normal;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  }
}
.study-notice {
  font-size: 13px;
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
  .fact-status {
    flex: 1 1 calc(100% - 56px);
  }
  .review-select {
    flex: 1 1 auto;
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
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
