<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { VAlert, VChip, VChipGroup } from "vuetify/components";
import { useStudyViews } from "../../study-views/context";
import type { AcknowledgedWarning, Problem, Profile, ValidationIssue } from "../../study-views/types";
import ProblemItem from "../components/ProblemItem.vue";
import { formatTime, plural } from "../../study-views/overview";
import {
  acknowledgement,
  filterIssues,
  groupByFile,
  groupCounts,
  locationKey,
  noIssuesText,
  notesQuery,
  openTablesKey,
  scopeText,
  SEVERITY_CHIPS,
  severityCounts,
  type SeverityFilter,
} from "../../study-views/problems";
import { targetParts } from "../../study-views/review";
import { isLimitIssue, knownProfiles, profileOf, tableFiles } from "../../study-views/study";

/**
 * The issues of the last validation by file, with a severity filter, links to the cells of the
 * tables, Open in tables, Open tables, and Acknowledge for warnings; below them the warnings that review items
 * acknowledge. A study beyond the upload limits names the limit first. The actions on the issues
 * come from the page through the events and slots.
 */
const props = withDefaults(defineProps<{ busy?: string | null; working?: boolean }>(), { busy: null, working: false });
const emit = defineEmits<{
  acknowledge: [issue: Problem, order: string[]];
  validate: [];
  "open-tables": [issue: Problem];
}>();
defineSlots<{
  toolbar?: () => unknown;
  status?: () => unknown;
  "group-actions"?: (props: { file: string | null }) => unknown;
  dialogs?: () => unknown;
}>();

const views = useStudyViews();
const id = useId();

const detail = views.data.detail;
const identity = computed(() => detail.value?.id ?? "");
const problems = computed<Problem[]>(() => detail.value?.problems ?? []);
/** The issues of the upload limits, shown above the others. */
const limits = computed(() => problems.value.filter(isLimitIssue));
const listed = computed(() => problems.value.filter((issue) => !isLimitIssue(issue)));

const severity = ref<SeverityFilter>("all");
const counts = computed(() => severityCounts(listed.value));
const groups = computed(() => groupByFile(filterIssues(listed.value, severity.value)));

/**
 * The issues that render at once. A long list renders in steps of this many issues, one step
 * per frame, so that the first issues show at once and the page never freezes: a report lists
 * up to 1,000 issues.
 */
const STEP = 100;
const limit = ref(STEP);
let frame = 0;

/** Render the next step of issues in the next frame, until all of them show. */
function grow(): void {
  cancelAnimationFrame(frame);
  const total = groups.value.reduce((sum, group) => sum + group.issues.length, 0);
  if (limit.value < total)
    frame = requestAnimationFrame(() => {
      limit.value += STEP;
      grow();
    });
}

// Another severity starts with the first step again; new data of the study keeps the issues that
// show, so that the page keeps its scroll position.
watch(severity, () => (limit.value = STEP));
watch(groups, grow, { immediate: true });
onBeforeUnmount(() => cancelAnimationFrame(frame));

/** The groups with the issues that render so far; `all` holds every issue of the file. */
const rendered = computed(() => {
  let budget = limit.value;
  return groups.value.flatMap((group) => {
    if (budget <= 0) return [];
    const issues = group.issues.slice(0, budget);
    budget -= issues.length;
    return [{ file: group.file, issues, all: group.issues }];
  });
});

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

/** Whether the Data section can show the cell of the issue: only tables of the study. */
function showable(issue: ValidationIssue): boolean {
  return tables.value.has(issue.source?.file ?? "");
}

/** The query of the Data section that opens the notes of an issue in the notes of a table; null for another issue. */
function notesOf(issue: ValidationIssue): Record<string, string> | null {
  return detail.value ? notesQuery(detail.value, issue) : null;
}

// Profiles: the roster, and the people of the study who are not in it.
const roster = ref<Profile[]>([]);
onMounted(() => {
  views.data.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the roster the acknowledgements show user names.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));

const acknowledged = computed<AcknowledgedWarning[]>(() => detail.value?.acknowledged ?? []);
/** The review items, which the targets of acknowledgements of warnings about review.json name. */
const items = computed(() => detail.value?.review.value?.items ?? []);

function authorName(entry: AcknowledgedWarning): string {
  return profileOf(profiles.value, entry.author).display_name;
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
 * Whether a warning was acknowledged in the app and the report of the study still lists it: the
 * page keeps it until the next report, which leaves it out.
 */
function isPending(issue: ValidationIssue): boolean {
  return views.data.acknowledgedKeys.value.includes(locationKey(issue));
}

/** Whether the server validates the study after the acknowledgement, or the curator does. */
const automatic = views.data.validatesAfterWrite;

/** Ask the page to acknowledge `issue`, with the shown issues in order for the focus afterwards. */
function acknowledge(issue: Problem): void {
  if (props.working) return;
  emit("acknowledge", issue, groups.value.flatMap((group) => group.issues.map(locationKey)));
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
        <slot name="toolbar" />
      </div>
      <p v-if="omitted" class="problems-note problems-omitted">{{ omitted }}</p>
      <p v-if="blocked && acknowledgeable" class="problems-note problems-blocked">{{ blocked }}</p>
    </template>

    <slot name="status" />

    <div v-if="groups.length" class="problems-groups">
      <section
        v-for="(group, groupIndex) in rendered"
        :key="group.file ?? ''"
        class="problem-group"
        :data-file="group.file ?? ''"
        :aria-labelledby="`${id}-${groupIndex}`"
      >
        <div class="problem-group-head">
          <div class="problem-group-title">
            <h3 :id="`${id}-${groupIndex}`" tabindex="-1" class="problem-file">{{ group.file ?? "Whole study" }}</h3>
            <span class="problem-group-counts">{{ groupCounts(group.all) }}</span>
          </div>
          <slot name="group-actions" :file="group.file" />
        </div>
        <ul class="problem-list">
          <ProblemItem
            v-for="(issue, index) in group.issues"
            :key="index"
            :issue="issue"
            :study="identity"
            :id-base="`${id}-${groupIndex}-${index}`"
            :showable="showable(issue)"
            :notes-query="notesOf(issue)"
            :pending="isPending(issue)"
            :automatic="automatic"
            :disabled="blocked !== null || working"
            :validating="busy === 'validate'"
            :opens-tables="showable(issue)"
            :opening="busy === openTablesKey(issue)"
            :open-disabled="working"
            @open-tables="emit('open-tables', issue)"
            @acknowledge="acknowledge(issue)"
            @validate="emit('validate')"
          />
        </ul>
      </section>
    </div>
    <p v-else-if="listed.length" class="problems-empty">{{ noIssuesText(severity) }}</p>
    <p v-else-if="!limits.length" class="problems-empty">{{ emptyText }}</p>

    <section v-if="acknowledged.length" class="problems-acknowledged" :aria-labelledby="`${id}-acknowledged`">
      <h3 :id="`${id}-acknowledged`" tabindex="-1" class="problems-heading">
        Acknowledged warnings ({{ acknowledged.length }})
      </h3>
      <ul class="problem-group problem-list acknowledged-list">
        <li v-for="entry in acknowledged" :key="entry.id" class="acknowledged">
          <div class="problem-head">
            <code class="problem-code">{{ entry.code }}</code>
          </div>
          <p class="problem-fact">
            <i class="fas fa-crosshairs problem-icon" aria-hidden="true"></i>
            <span>
              <template v-for="(part, index) in targetParts(entry.target, items)" :key="index">
                <RouterLink v-if="part.item" :to="views.routes.section(identity, 'review', { item: part.item })">{{
                  part.text
                }}</RouterLink>
                <template v-else>{{ part.text }}</template>
              </template>
            </span>
          </p>
          <!-- A target of a whole file, a column or the study covers more than one warning, also later ones. -->
          <p v-if="scopeText(entry)" class="problem-fact acknowledged-scope">
            <i class="fas fa-layer-group problem-icon" aria-hidden="true"></i>
            <span>{{ scopeText(entry) }}</span>
          </p>
          <p class="problem-message">{{ entry.text }}</p>
          <p class="acknowledged-meta">
            <span v-if="entry.resolved">
              Acknowledged by {{ authorName(entry) }} on
              <span class="acknowledged-time">{{ formatTime(entry.resolved) }}</span>.
            </span>
            <span v-else>Acknowledged by {{ authorName(entry) }}. The review item is open.</span>
            <RouterLink :to="views.routes.section(identity, 'review', { item: entry.id })"
              >Show the review item</RouterLink
            >
          </p>
        </li>
      </ul>
    </section>

    <slot name="dialogs" />
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
.problems-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.acknowledged {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}
.acknowledged + .acknowledged {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
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
/* The time stays with its date. */
.acknowledged-time {
  white-space: nowrap;
}
</style>
