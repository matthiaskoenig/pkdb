<script setup lang="ts">
import { computed, onMounted, ref, useId, watch } from "vue";
import { VAlert, VBtn, VChip, VChipGroup } from "vuetify/components";
import { isNoUser } from "../api/client";
import type { AcknowledgedWarning, Profile, ValidationIssue } from "../api/types";
import AcknowledgeDialog from "../components/AcknowledgeDialog.vue";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";
import UserHint from "../components/UserHint.vue";
import { useNotice } from "../composables/useNotice";
import { formatTime, plural } from "../overview";
import {
  acknowledgement,
  filterIssues,
  groupByFile,
  groupCounts,
  isLimitIssue,
  location,
  locationKey,
  noIssuesText,
  SEVERITY_CHIPS,
  SEVERITY_LABELS,
  severityCounts,
  suggestionText,
  tableQuery,
  type SeverityFilter,
} from "../problems";
import { targetText } from "../review";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";
import {
  actionFailure,
  knownProfiles,
  messageOf,
  profileOf,
  sectionRoute,
  tableFiles,
  tablesOutcome,
  userHint,
  type ActionFailure,
} from "../study";

/**
 * The issues of the last validation by file, with a severity filter, links to the cells of the
 * tables, Open tables, and Acknowledge for warnings; below them the warnings that review items
 * acknowledge. A study beyond the upload limits names the limit first.
 */
const study = useStudyStore();
const overview = useOverviewStore();
const { notice, announce } = useNotice();
const id = useId();

const detail = computed(() => study.detail);
const identity = computed(() => detail.value?.id ?? "");
const problems = computed<ValidationIssue[]>(() => detail.value?.problems ?? []);
/** The issues of the upload limits, shown above the others. */
const limits = computed(() => problems.value.filter(isLimitIssue));
const listed = computed(() => problems.value.filter((issue) => !isLimitIssue(issue)));

const severity = ref<SeverityFilter>("all");
const counts = computed(() => severityCounts(listed.value));
const groups = computed(() => groupByFile(filterIssues(listed.value, severity.value)));

/** The issues that the last validation counted but did not list: it lists at most a thousand. */
const omitted = computed(() => {
  const total = (detail.value?.counts.errors ?? 0) + (detail.value?.counts.warnings ?? 0);
  const shown = problems.value.length;
  return total > shown
    ? `The last validation listed ${shown.toLocaleString("en-US")} of ${plural(total, "problem")}.`
    : null;
});

const emptyText = computed(() =>
  detail.value?.status === "discovered" ? "The study is not validated yet." : noIssuesText("all"),
);

const tables = computed(() => new Set(detail.value ? tableFiles(detail.value) : []));

/** Whether the Tables section can show the cell of the issue: only tables of the study. */
function showable(issue: ValidationIssue): boolean {
  return tables.value.has(issue.source?.file ?? "");
}

function tableRoute(issue: ValidationIssue) {
  return sectionRoute(identity.value, "tables", tableQuery(issue) ?? {});
}

/** A file of the study that opens with the system; tables open in the workbook instead. */
function openable(file: string | null): file is string {
  return file !== null && !tables.value.has(file) && (detail.value?.files.includes(file) ?? false);
}

// Profiles: the roster, and the people of the study who are not in it.
const roster = ref<Profile[]>([]);
onMounted(() => {
  study.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the roster the acknowledgements show user names.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));

const acknowledged = computed<AcknowledgedWarning[]>(() => detail.value?.acknowledged ?? []);

function acknowledgedBy(entry: AcknowledgedWarning): string {
  const name = profileOf(profiles.value, entry.author).display_name;
  return entry.resolved
    ? `Acknowledged by ${name} on ${formatTime(entry.resolved)}.`
    : `Acknowledged by ${name}. The review item is open.`;
}

// Acknowledgements

/** Why warnings cannot be acknowledged now: review.json cannot be written. */
const blocked = computed(() => {
  const review = detail.value?.review;
  if (!review) return null;
  if (review.revision === null)
    return "review.json cannot be written from the app, so warnings cannot be acknowledged.";
  if (review.value === null)
    return "review.json is not valid, so warnings cannot be acknowledged. Fix it in your editor.";
  return null;
});
const acknowledgeable = computed(() => listed.value.some((issue) => acknowledgement(issue) !== null));

/**
 * The locations of the warnings acknowledged here, until a validation leaves them out: the
 * watcher validates the study again after the write.
 */
const pending = ref<string[]>([]);
watch(problems, (issues) => {
  const keys = new Set(issues.map(locationKey));
  pending.value = pending.value.filter((key) => keys.has(key));
});

function isPending(issue: ValidationIssue): boolean {
  return pending.value.includes(locationKey(issue));
}

const chosen = ref<ValidationIssue | null>(null);
const dialog = ref(false);

function acknowledge(issue: ValidationIssue): void {
  chosen.value = issue;
  dialog.value = true;
}

function acknowledgedWarning(issue: ValidationIssue): void {
  const key = locationKey(issue);
  // A validation that left the warning out already needs no mark.
  if (problems.value.some((entry) => locationKey(entry) === key)) pending.value = [...pending.value, key];
  announce(`Warning ${issue.code} acknowledged.`);
}

// Open tables and files

/** The action that runs, `tables` or the file that opens; one at a time. */
const busy = ref<string | null>(null);
/** The failure of the last action; it stays until it is dismissed or the next action starts. */
const failure = ref<ActionFailure | null>(null);
/** What to do when the last action needed a user. */
const userText = ref<string | null>(null);

async function run(action: string, work: () => Promise<string>): Promise<void> {
  if (busy.value !== null) return;
  busy.value = action;
  failure.value = null;
  userText.value = null;
  announce("");
  try {
    announce(await work());
  } catch (caught) {
    if (isNoUser(caught)) userText.value = userHint(caught);
    else failure.value = actionFailure(messageOf(caught));
  } finally {
    busy.value = null;
  }
}

function openTables(): Promise<void> {
  return run("tables", async () => {
    const result = await study.tablesAction("open");
    failure.value = tablesOutcome(result);
    return result.opened ? "The workbook opened." : "";
  });
}

function openFile(file: string): Promise<void> {
  return run(file, async () => {
    await overview.openFile(identity.value, file);
    return `Opened ${file}.`;
  });
}

/** The ids of the message and the location of an issue, which describe its actions. */
function describedBy(groupIndex: number, index: number, issue: ValidationIssue): string {
  const base = `${id}-${groupIndex}-${index}`;
  return location(issue, { file: false }) ? `${base}-message ${base}-location` : `${base}-message`;
}
</script>

<template>
  <div class="problems">
    <VAlert v-if="limits.length" type="error" variant="tonal" density="compact" class="status-alert problems-limit">
      <p class="problems-alert-text">
        This study is beyond the upload limits. The app cannot show its tables and sources, and the study cannot be
        uploaded.
      </p>
      <ul class="problems-alert-issues">
        <li v-for="(issue, index) in limits" :key="index">
          {{ issue.message }} · <code class="problem-code">{{ issue.code }}</code>
        </li>
      </ul>
    </VAlert>

    <template v-if="listed.length">
      <div class="problems-toolbar">
        <VChipGroup
          v-model="severity"
          mandatory
          column
          color="primary"
          role="group"
          aria-label="Filter by severity"
          class="filter-chips problems-chips"
        >
          <VChip
            v-for="chip in SEVERITY_CHIPS"
            :key="chip.value"
            :value="chip.value"
            tag="button"
            type="button"
            filter
            :aria-pressed="severity === chip.value ? 'true' : 'false'"
          >
            {{ chip.label }}<span class="chip-count">{{ counts[chip.value] }}</span>
          </VChip>
        </VChipGroup>
        <VBtn
          variant="tonal"
          color="primary"
          prepend-icon="fas fa-table"
          :disabled="busy !== null"
          :loading="busy === 'tables'"
          class="problems-open-tables"
          @click="openTables"
        >
          Open tables
        </VBtn>
      </div>
      <p v-if="omitted" class="problems-note problems-omitted">{{ omitted }}</p>
      <p v-if="blocked && acknowledgeable" class="problems-note problems-blocked">{{ blocked }}</p>
    </template>

    <ActionFailureAlert
      v-if="failure"
      :failure="failure"
      :study="identity"
      class="problems-failure"
      @close="failure = null"
    />
    <UserHint v-else-if="userText" :text="userText" />
    <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
    <span role="status" aria-live="polite" class="problems-notice">{{ notice }}</span>

    <div v-if="groups.length" class="problems-groups">
      <section
        v-for="(group, groupIndex) in groups"
        :key="group.file ?? ''"
        class="problem-group"
        :aria-labelledby="`${id}-${groupIndex}`"
      >
        <div class="problem-group-head">
          <div class="problem-group-title">
            <h3 :id="`${id}-${groupIndex}`" class="problem-file">{{ group.file ?? "Whole study" }}</h3>
            <span class="problem-group-counts">{{ groupCounts(group.issues) }}</span>
          </div>
          <VBtn
            v-if="openable(group.file)"
            variant="text"
            size="small"
            color="primary"
            prepend-icon="fas fa-arrow-up-right-from-square"
            :disabled="busy !== null"
            :loading="busy === group.file"
            :aria-label="`Open ${group.file}`"
            class="problem-open"
            @click="openFile(group.file)"
          >
            Open
          </VBtn>
        </div>
        <ul class="problem-list">
          <li v-for="(issue, index) in group.issues" :key="index" class="problem">
            <div class="problem-head">
              <VChip
                size="small"
                variant="tonal"
                :color="issue.severity"
                :prepend-icon="issue.severity === 'error' ? 'fas fa-circle-xmark' : 'fas fa-triangle-exclamation'"
                class="status-chip problem-severity"
              >
                {{ SEVERITY_LABELS[issue.severity] }}
              </VChip>
              <code class="problem-code">{{ issue.code }}</code>
            </div>
            <p :id="`${id}-${groupIndex}-${index}-message`" class="problem-message">{{ issue.message }}</p>
            <p
              v-if="location(issue, { file: false })"
              :id="`${id}-${groupIndex}-${index}-location`"
              class="problem-fact problem-location"
            >
              <i class="fas fa-crosshairs problem-icon" aria-hidden="true"></i>
              <span>{{ location(issue, { file: false }) }}</span>
            </p>
            <div v-if="issue.suggestions?.length" class="problem-fact problem-suggestions">
              <i class="fas fa-lightbulb problem-icon" aria-hidden="true"></i>
              <div class="problem-suggestion-list">
                <div v-for="(suggestion, number) in issue.suggestions" :key="number">
                  <p class="problem-suggestion">{{ suggestionText(suggestion).text }}</p>
                  <ul v-if="suggestionText(suggestion).candidates.length" class="problem-candidates">
                    <li v-for="(candidate, place) in suggestionText(suggestion).candidates" :key="place">
                      <code>{{ candidate }}</code>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <p v-if="isPending(issue)" class="problem-fact problem-acknowledged">
              <i class="fas fa-check problem-icon" aria-hidden="true"></i>
              <span>Acknowledged. It leaves this list after the next validation.</span>
            </p>
            <div
              v-if="showable(issue) || (acknowledgement(issue) && !isPending(issue))"
              class="problem-actions"
            >
              <VBtn
                v-if="showable(issue)"
                :to="tableRoute(issue)"
                variant="text"
                density="compact"
                color="primary"
                prepend-icon="fas fa-table-cells"
                :aria-describedby="describedBy(groupIndex, index, issue)"
              >
                Show in table
              </VBtn>
              <VBtn
                v-if="acknowledgement(issue) && !isPending(issue)"
                variant="text"
                density="compact"
                color="primary"
                prepend-icon="fas fa-check"
                :disabled="blocked !== null"
                :aria-describedby="describedBy(groupIndex, index, issue)"
                @click="acknowledge(issue)"
              >
                Acknowledge
              </VBtn>
            </div>
          </li>
        </ul>
      </section>
    </div>
    <p v-else-if="listed.length" class="problems-empty">{{ noIssuesText(severity) }}</p>
    <p v-else-if="!limits.length" class="problems-empty">{{ emptyText }}</p>

    <section v-if="acknowledged.length" class="problems-acknowledged" :aria-labelledby="`${id}-acknowledged`">
      <h3 :id="`${id}-acknowledged`" class="problems-heading">Acknowledged warnings ({{ acknowledged.length }})</h3>
      <ul class="problem-group problem-list acknowledged-list">
        <li v-for="entry in acknowledged" :key="entry.id" class="acknowledged">
          <div class="problem-head">
            <code class="problem-code">{{ entry.code }}</code>
          </div>
          <p class="problem-fact">
            <i class="fas fa-crosshairs problem-icon" aria-hidden="true"></i>
            <span>{{ targetText(entry.target) }}</span>
          </p>
          <p class="problem-message">{{ entry.text }}</p>
          <p class="acknowledged-meta">
            <span>{{ acknowledgedBy(entry) }}</span>
            <RouterLink :to="sectionRoute(identity, 'review', { item: entry.id })">Show the review item</RouterLink>
          </p>
        </li>
      </ul>
    </section>

    <AcknowledgeDialog v-model="dialog" :issue="chosen" @acknowledged="acknowledgedWarning" />
  </div>
</template>

<style scoped>
.problems {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.problems-alert-text {
  margin: 0;
}
.problems-alert-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
  overflow-wrap: anywhere;
}
.problems-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.problems-chips {
  flex: 1 1 auto;
}
.problems-note,
.problems-empty {
  margin: 0;
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.problems-empty {
  font-size: 1rem;
}
.problems-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.problems-notice:empty {
  position: absolute;
}
.problems-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
/* A file is a card: its name in a bar, then its issues apart by a line. */
.problem-group {
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
}
.problem-group-head {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 6px 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}
/* The counts go below a long file name, and Open stays at the end of the bar. */
.problem-group-title {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px 12px;
  min-width: 0;
}
.problem-file {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.problem-group-counts {
  font-size: 0.8125rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The text of the button lines up with the end of the bar. */
.problem-open {
  flex: 0 0 auto;
  margin-inline-end: -8px;
}
.problem-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.problem,
.acknowledged {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}
.problem + .problem,
.acknowledged + .acknowledged {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.problem-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
}
.problem-code {
  font-size: 0.8125rem;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.problem-message {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.problem-fact {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.problem-icon {
  width: 1rem;
  flex: 0 0 auto;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.problem-location {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.problem-suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.problem-suggestion {
  margin: 0;
}
.problem-candidates {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
}
.problem-acknowledged .problem-icon {
  color: rgb(var(--v-theme-success));
}
/* The text of the first button lines up with the text above it. */
.problem-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-inline-start: -8px;
}
.problems-acknowledged {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.problems-heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.5;
}
.acknowledged-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 16px;
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
