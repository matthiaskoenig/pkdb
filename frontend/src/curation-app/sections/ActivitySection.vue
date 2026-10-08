<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import {
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
import {
  ACTION_ICONS,
  ACTION_LABELS,
  datetime,
  JOB_STATUS_LABELS,
  JOB_STATUS_TONES,
  messageParts,
  persistenceLabel,
  reportFileName,
  saveFile,
  uploadUrl,
} from "../activity";
import { ApiError } from "../api/client";
import type { Job } from "../api/types";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import RetryDialog from "../components/RetryDialog.vue";
import UserHint from "../components/UserHint.vue";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { useReturnFocus } from "../composables/useReturnFocus";
import { formatTime, plural } from "../overview";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { actionFailure, messageOf, sectionRoute } from "../study";

/**
 * The jobs of the study in the current workspace, newest first: validations and uploads of the
 * local server and the writes of the app. A finished job offers its report, a queued one Cancel,
 * and an upload with an unknown outcome the review of the overview. Clear finished history
 * clears the finished jobs of the whole workspace.
 */
const study = useStudyStore();
const overview = useOverviewStore();
const { notice, announce } = useNotice();
const id = useId();

const root = ref<HTMLElement | null>(null);

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");

const entries = computed(() =>
  (detail.value?.jobs ?? []).map((job) => ({
    job,
    textId: `${id}-${job.id}-text`,
    metaId: `${id}-${job.id}-meta`,
    // Writes name review items by id; the parts name them by kind and text.
    parts: messageParts(job, detail.value?.review.value?.items ?? []),
    persistence: persistenceLabel(job),
    url: uploadUrl(job),
    cancelable: job.status === "queued",
    reviewable: job.action === "upload" && job.status === "unknown",
  })),
);

/** The overview row of the study, which the review of an uncertain upload needs. */
const row = computed(
  () =>
    overview.snapshot?.studies.find((candidate) => candidate.id === identity.value && !candidate.duplicate) ??
    null,
);
/** The finished jobs of the workspace that clearing removes, as the server counts them. */
const clearableJobs = computed(() => overview.snapshot?.clearable_jobs ?? 0);
const clearText = computed(
  () =>
    `This removes ${plural(clearableJobs.value, "finished job")} of this workspace from the activity and deletes ` +
    `${clearableJobs.value === 1 ? "its report" : "their reports"}. Queued and running jobs, uploads with an ` +
    "unknown outcome, and the last upload and the current report of each study stay.",
);

/** The running action: one at a time, so that feedback never mixes. */
const { busy, working, failure, userText, run } = useAction<string>(announce);
const confirming = ref(false);
const retrying = ref(false);
/** Takes the focus after a dialog when the control that opened it is gone. */
const activityList = () => root.value?.querySelector<HTMLElement>(".activity-list, .activity-empty");
useReturnFocus(confirming, activityList);

/**
 * Keep the keyboard focus in the section when the control that had it goes away: on the element
 * of `selector`, after the next render.
 */
async function focusOn(selector: string): Promise<void> {
  await nextTick();
  root.value?.querySelector<HTMLElement>(selector)?.focus();
}

/** The name of an action in a sentence, such as "server validation". */
function named(job: Job): string {
  return ACTION_LABELS[job.action].toLowerCase();
}

function download(job: Job): Promise<void> | void {
  const report = job.report_id;
  if (report === null) return;
  return run(
    `report:${job.id}`,
    async () => {
      const name = reportFileName(report);
      saveFile(name, `${JSON.stringify(await overview.report(report), null, 2)}\n`, "application/json");
      return `Downloaded ${name}.`;
    },
    (caught) =>
      actionFailure(
        caught instanceof ApiError && caught.status === 404
          ? "The report of this job is no longer available."
          : `The report could not be downloaded. ${messageOf(caught)}`,
      ),
  );
}

function cancel(job: Job): Promise<void> {
  return run(`cancel:${job.id}`, async () => {
    const state = await overview.cancelJobs([job.id]);
    await study.refresh();
    // The server cancels only a job that has not started yet; its answer has the jobs after the cancel.
    const current = state.jobs.find((entry) => entry.id === job.id);
    // Cancel is gone with the queued job: the focus goes to the job.
    await focusOn(`[data-job="${job.id}"]`);
    if (current && current.status !== "canceled") {
      failure.value = actionFailure(`The ${named(job)} started before it could be canceled.`);
      return "";
    }
    return `Canceled the queued ${named(job)}.`;
  });
}

function clear(): Promise<void> {
  confirming.value = false;
  return run("clear", async () => {
    await overview.clearHistory();
    await study.refresh();
    // Clear is disabled now that nothing is left to clear: the focus goes to the activity.
    await focusOn(".activity-list, .activity-empty");
    return "Cleared the finished history.";
  });
}

/** The upload whose Review opened the dialog. */
let reviewed: string | null = null;

function review(job: Job): void {
  reviewed = job.id;
  retrying.value = true;
}

async function retried(): Promise<void> {
  announce("Upload queued again.");
  const job = reviewed;
  await study.refresh();
  // The dialog returned the focus to Review, which went with the unknown outcome: the focus goes to the job.
  if (document.activeElement === document.body) await focusOn(`[data-job="${job}"]`);
}
</script>

<template>
  <div ref="root" class="activity">
    <div class="activity-toolbar">
      <p class="activity-caption">Newest first. The app keeps the last 100 finished jobs.</p>
      <VDialog v-model="confirming" max-width="480" :aria-labelledby="`${id}-clear`">
        <template #activator="{ props: activator }">
          <VBtn
            v-bind="activator"
            variant="text"
            color="primary"
            prepend-icon="fas fa-broom"
            :disabled="clearableJobs === 0 || (working && busy !== 'clear')"
            :loading="busy === 'clear'"
            class="activity-clear"
          >
            Clear finished history
          </VBtn>
        </template>
        <VCard>
          <VCardItem>
            <VCardTitle :id="`${id}-clear`" tag="h2">Clear finished history?</VCardTitle>
          </VCardItem>
          <VCardText class="clear-text">{{ clearText }}</VCardText>
          <VCardActions class="dialog-actions">
            <VSpacer />
            <VBtn variant="text" @click="confirming = false">Keep history</VBtn>
            <VBtn variant="flat" color="primary" @click="clear">Clear history</VBtn>
          </VCardActions>
        </VCard>
      </VDialog>
    </div>

    <ActionFailureAlert v-if="failure" :failure="failure" :study="identity" @close="failure = null" />
    <UserHint v-else-if="userText" :text="userText" />
    <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
    <span role="status" aria-live="polite" class="activity-notice">{{ notice }}</span>

    <!-- The list and the empty text take the focus after a clear, and an entry after Cancel. -->
    <p v-if="!entries.length" tabindex="-1" class="activity-empty">
      No activity yet. Validations, uploads and changes in the app appear here.
    </p>
    <ol v-else tabindex="-1" class="activity-list">
      <li v-for="entry in entries" :key="entry.job.id" :data-job="entry.job.id" tabindex="-1" class="activity-entry">
        <i :class="[ACTION_ICONS[entry.job.action], 'activity-icon']" aria-hidden="true"></i>
        <div class="activity-body">
          <div class="activity-head">
            <p :id="entry.textId" class="activity-text">
              <template v-for="(part, index) in entry.parts" :key="index">
                <RouterLink
                  v-if="part.item"
                  :to="sectionRoute(identity, 'review', { item: part.item })"
                  class="activity-item"
                >
                  {{ part.text }}
                </RouterLink>
                <template v-else>{{ part.text }}</template>
              </template>
            </p>
            <VChip
              size="small"
              variant="tonal"
              :color="JOB_STATUS_TONES[entry.job.status]"
              class="status-chip activity-status"
            >
              {{ JOB_STATUS_LABELS[entry.job.status] }}
            </VChip>
          </div>
          <p :id="entry.metaId" class="activity-meta">
            <span class="activity-action">{{ ACTION_LABELS[entry.job.action] }}</span>
            <template v-if="entry.persistence">
              · <span class="activity-persistence">{{ entry.persistence }}</span>
            </template>
            <!-- Started by the local server: after a save, or by the first scan. -->
            <template v-if="entry.job.automatic"> · automatic</template>
            · <time :datetime="datetime(entry.job.created_at)" class="activity-time">{{ formatTime(entry.job.created_at) }}</time>
          </p>
          <div
            v-if="entry.reviewable || entry.cancelable || entry.url || entry.job.report_id"
            class="activity-actions"
          >
            <VBtn
              v-if="entry.reviewable"
              variant="text"
              density="compact"
              color="primary"
              prepend-icon="fas fa-triangle-exclamation"
              :disabled="working || row === null"
              aria-label="Review uncertain upload"
              @click="review(entry.job)"
            >
              Review
            </VBtn>
            <VBtn
              v-if="entry.cancelable"
              variant="text"
              density="compact"
              color="primary"
              prepend-icon="fas fa-xmark"
              :disabled="working && busy !== `cancel:${entry.job.id}`"
              :loading="busy === `cancel:${entry.job.id}`"
              :aria-label="`Cancel queued ${named(entry.job)}`"
              @click="cancel(entry.job)"
            >
              Cancel
            </VBtn>
            <VBtn
              v-if="entry.url"
              :href="entry.url"
              target="_blank"
              rel="noopener noreferrer"
              variant="text"
              density="compact"
              color="primary"
              prepend-icon="fas fa-arrow-up-right-from-square"
              :aria-describedby="`${entry.textId} ${entry.metaId}`"
              class="activity-link"
            >
              Open on PK-DB
            </VBtn>
            <VBtn
              v-if="entry.job.report_id"
              variant="text"
              density="compact"
              color="primary"
              prepend-icon="fas fa-download"
              :disabled="working && busy !== `report:${entry.job.id}`"
              :loading="busy === `report:${entry.job.id}`"
              :aria-describedby="`${entry.textId} ${entry.metaId}`"
              @click="download(entry.job)"
            >
              Download report
            </VBtn>
          </div>
        </div>
      </li>
    </ol>

    <RetryDialog v-model="retrying" :study="row" :fallback-focus="activityList" @done="retried" />
  </div>
</template>

<style scoped>
.activity {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* The caption and Clear share a line, or Clear goes below in a narrow window. */
.activity-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 4px 16px;
}
.activity-caption {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The label of Clear ends with the list, and its icon starts with the caption when it goes
   below it. */
.activity-clear {
  margin-inline: -8px;
}
.activity-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.activity-notice:empty {
  position: absolute;
}
.activity-empty {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The jobs are a card, apart by a line, as the issues of a file in Problems. */
.activity-list {
  margin: 0;
  padding: 0;
  overflow: hidden;
  list-style: none;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
}
/* The icon of the action in a column of its own, on the line of the text. */
.activity-entry {
  display: grid;
  grid-template-columns: 1rem minmax(0, 1fr);
  align-items: baseline;
  column-gap: 12px;
  padding: 12px;
}
.activity-entry + .activity-entry {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* The list clips what overflows it, so a focused entry has its ring inside. */
.activity-entry:focus-visible {
  outline-offset: -3px;
}
.activity-icon {
  font-size: 0.875rem;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.activity-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
/* The status follows the text on its first line, at the end, or goes below a text that would
   get too narrow beside it. */
.activity-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 12px;
}
.activity-text {
  flex: 1 1 12rem;
  min-width: 0;
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.activity-status {
  flex: 0 0 auto;
}
.activity-meta {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The time stays with its date. */
.activity-time {
  white-space: nowrap;
}
/* The icons of the buttons start where the text above does: 8 px of padding sit outside the
   content edge, then the 1rem wide icon and its 8 px gap, as the actions of an issue. */
.activity-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-inline-start: -8px;
}
.activity-actions :deep(.v-btn),
.activity-clear {
  padding-inline: 8px;
}
.activity-actions :deep(.v-btn__prepend),
.activity-clear :deep(.v-btn__prepend) {
  justify-content: center;
  width: 1rem;
  margin-inline: 0 8px;
}
</style>
