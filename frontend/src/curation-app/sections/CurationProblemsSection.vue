<script setup lang="ts">
import { computed, ref, shallowRef, useTemplateRef, watch } from "vue";
import { VAlert, VBtn } from "vuetify/components";
import type { Problem, ValidationIssue } from "../../study-views/types";
import AcknowledgeDialog from "../components/AcknowledgeDialog.vue";
import ActionFailureAlert from "../../study-views/components/ActionFailureAlert.vue";
import UserHint from "../components/UserHint.vue";
import { useAction } from "../composables/useAction";
import { useNotice } from "../composables/useNotice";
import { sectionHeading } from "../../study-views/focus";
import { locationKey, openPlace, openTablesKey } from "../../study-views/problems";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import { tableFiles } from "../../study-views/study";
import { tablesOutcome } from "../local";
import ProblemsSection from "../../study-views/sections/ProblemsSection.vue";

/**
 * The Problems section of the curation app: the shared section (ProblemsSection.vue) with Open
 * tables, Open in tables, Acknowledge and Validate, Open of a file of the study, the failure and
 * notices of these actions, and the dialog that acknowledges a warning.
 */
const study = useStudyStore();
const overview = useOverviewStore();
const { notice, announce } = useNotice();
const section = useTemplateRef<InstanceType<typeof ProblemsSection>>("section");

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");
const problems = computed<Problem[]>(() => detail.value?.problems ?? []);
const tables = computed(() => new Set(detail.value ? tableFiles(detail.value) : []));

/** A file of the study that opens with the system; tables open in the workbook instead. */
function openable(file: string | null): file is string {
  return file !== null && !tables.value.has(file) && (detail.value?.files.includes(file) ?? false);
}

// Acknowledgements

const chosen = shallowRef<Problem | null>(null);
const dialog = ref(false);
/** Whether the dialog writes an acknowledgement; the other actions wait meanwhile. */
const acknowledging = ref(false);
/** The shown issues, in order, when the dialog opened: the place to move the focus to afterwards. */
let order: string[] = [];

/** Acknowledge `issue` in the dialog; `shown` are the shown issues in order, for the focus afterwards. */
function acknowledge(issue: Problem, shown: string[]): void {
  if (working.value) return;
  chosen.value = issue;
  order = shown;
  dialog.value = true;
}

function acknowledgedWarning(issue: Problem): void {
  // The acknowledgement covers exactly this warning. A validation that left it out already needs no mark.
  const key = locationKey(issue);
  if (problems.value.some((entry) => locationKey(entry) === key)) study.markAcknowledged(key);
  announce(`Warning ${issue.code} acknowledged.`);
}

/**
 * Where the focus goes when the dialog closed and the Acknowledge button of its warning went
 * away: the Acknowledge button of the next warning, else the heading of the file of the warning,
 * else the acknowledged warnings, else the heading of the section.
 */
function afterAcknowledge(): HTMLElement | null | undefined {
  const root = section.value?.$el instanceof HTMLElement ? section.value.$el : null;
  const issue = chosen.value;
  if (!root || !issue) return sectionHeading();
  const key = locationKey(issue);
  const items = [...root.querySelectorAll<HTMLElement>(".problem")];
  const button = (item: HTMLElement | undefined) =>
    item?.querySelector<HTMLButtonElement>(".problem-acknowledge:not([disabled])") ?? null;
  const next = order
    .slice(order.indexOf(key) + 1)
    .map((later) => button(items.find((item) => item.dataset.key === later)))
    .find((found) => found !== null);
  const heading = [...root.querySelectorAll<HTMLElement>(".problem-group")]
    .find((group) => group.dataset.file === (issue.source?.file ?? ""))
    ?.querySelector<HTMLElement>(".problem-file");
  return next ?? heading ?? root.querySelector<HTMLElement>(".problems-heading") ?? sectionHeading();
}

// Open tables and files

/**
 * The action that runs: `tables`, `validate` or the file that opens; one at a time, and none
 * while an acknowledgement is written.
 */
const { busy, working, failure, userText, run } = useAction<string>(announce, () => acknowledging.value);

/** What to do in the workbook after an open found it open already; it stays until it is closed or the next open. */
const openNotice = ref<string | null>(null);
watch(identity, () => (openNotice.value = null));

function openTables(): Promise<void> {
  return run("tables", async () => {
    openNotice.value = null;
    const result = await study.tablesAction("open");
    failure.value = tablesOutcome(result);
    return result.opened ? "The workbook opened." : "";
  });
}

/** Open the workbook at the sheet of the table of an issue, with its cell selected when it has one. */
function openAt(issue: ValidationIssue): Promise<void> {
  const place = openPlace(issue);
  if (!place) return Promise.resolve();
  return run(openTablesKey(issue), async () => {
    openNotice.value = null;
    const result = await study.tablesAction("open", place);
    failure.value = tablesOutcome(result);
    openNotice.value = result.notice ?? null;
    // The notice says what to do when the workbook could not be switched, so the status stays silent then.
    return result.opened && !result.notice ? "The workbook opened." : "";
  });
}

function validate(): Promise<void> {
  return run("validate", async () => {
    await overview.enqueue([identity.value], "validate");
    return "Validation queued.";
  });
}

function openFile(file: string): Promise<void> {
  return run(file, async () => {
    await overview.openFile(identity.value, file);
    return `Opened ${file}.`;
  });
}
</script>

<template>
  <ProblemsSection
    ref="section"
    :busy="busy"
    :working="working"
    @acknowledge="acknowledge"
    @validate="validate"
    @open-tables="openAt"
  >
    <template #toolbar>
      <VBtn
        variant="tonal"
        color="primary"
        prepend-icon="fas fa-table"
        :disabled="working"
        :loading="busy === 'tables'"
        class="problems-open-tables"
        @click="openTables"
      >
        Open tables
      </VBtn>
    </template>
    <template #status>
      <ActionFailureAlert
        v-if="failure"
        :failure="failure"
        :study="identity"
        class="problems-failure"
        @close="failure = null"
      />
      <UserHint v-else-if="userText" :text="userText" />
      <VAlert
        v-if="openNotice"
        type="info"
        variant="tonal"
        density="compact"
        closable
        role="status"
        class="status-alert problems-open-notice"
        @click:close="openNotice = null"
      >
        {{ openNotice }}
      </VAlert>
      <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
      <span role="status" aria-live="polite" class="problems-notice">{{ notice }}</span>
    </template>
    <template #group-actions="{ file }">
      <VBtn
        v-if="openable(file)"
        variant="text"
        size="small"
        color="primary"
        prepend-icon="fas fa-arrow-up-right-from-square"
        :disabled="working"
        :loading="busy === file"
        :aria-label="`Open ${file}`"
        class="problem-open"
        @click="openFile(file)"
      >
        Open
      </VBtn>
    </template>
    <template #dialogs>
      <AcknowledgeDialog
        v-model="dialog"
        v-model:busy="acknowledging"
        :issue="chosen"
        :fallback-focus="afterAcknowledge"
        @acknowledged="acknowledgedWarning"
      />
    </template>
  </ProblemsSection>
</template>

<style scoped>
.problems-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.problems-notice:empty {
  position: absolute;
}
/* The text of the button lines up with the end of the bar. */
.problem-open {
  flex: 0 0 auto;
  margin-inline-end: -8px;
}
</style>
