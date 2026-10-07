<script setup lang="ts">
import { computed, useTemplateRef, watchPostEffect } from "vue";
import { useRouter } from "vue-router";
import { VAvatar, VBtn, VCheckboxBtn, VChip, VIcon, VTable } from "vuetify/components";
import type { Profile, StudyRow } from "../api/types";
import {
  activityLabel,
  formatTime,
  issueUrl,
  MODE_LABELS,
  problemLabels,
  REVIEW_LABELS,
  REVIEW_TONES,
  SYNC_LABELS,
  SYNC_TONES,
  type SortKey,
  type StudySort,
} from "../overview";

/** Avatars that a row shows before it counts the other curators. */
const SHOWN_CURATORS = 3;

const props = defineProps<{
  rows: StudyRow[];
  /** The profiles of the curator roster by lowercase username. */
  profiles: ReadonlyMap<string, Profile>;
  /** The GitHub repository of the issues, `<owner>/<name>`. */
  repository: string;
}>();
const selected = defineModel<string[]>("selected", { required: true });
const sort = defineModel<StudySort>("sort", { required: true });
const emit = defineEmits<{ retry: [row: StudyRow] }>();

const router = useRouter();

const columns: { key: SortKey | null; label: string; cell: string }[] = [
  { key: "study", label: "Study", cell: "cell-study" },
  { key: "review", label: "Review", cell: "cell-review" },
  { key: "open_items", label: "Open items", cell: "cell-open" },
  { key: "problems", label: "Problems", cell: "cell-problems" },
  { key: "sync", label: "Sync", cell: "cell-sync" },
  { key: "release", label: "Release", cell: "cell-release" },
  { key: "issue", label: "Issue", cell: "cell-issue" },
  { key: null, label: "Curators", cell: "cell-curators" },
  { key: "mode", label: "On save", cell: "cell-mode" },
  { key: "upload", label: "Last upload", cell: "cell-upload" },
];

/** Rows with a duplicate identity cannot be selected: every action of the server refuses them. */
const selectable = computed(() => props.rows.filter((row) => !row.duplicate));
const chosen = computed(() => new Set(selected.value));
const allSelected = computed(
  () => selectable.value.length > 0 && selectable.value.every((row) => chosen.value.has(row.id)),
);
const someSelected = computed(() => !allSelected.value && selectable.value.some((row) => chosen.value.has(row.id)));

// Vuetify marks a partial selection with aria-checked="mixed" only; the native state of the
// checkbox has to match it.
const selectAll = useTemplateRef<HTMLElement>("select-all");
watchPostEffect(() => {
  const input = selectAll.value?.querySelector("input");
  if (input) input.indeterminate = someSelected.value;
});

function isSelected(row: StudyRow): boolean {
  return !row.duplicate && chosen.value.has(row.id);
}

function toggle(row: StudyRow): void {
  selected.value = isSelected(row) ? selected.value.filter((id) => id !== row.id) : [...selected.value, row.id];
}

function toggleAll(): void {
  selected.value = allSelected.value ? [] : selectable.value.map((row) => row.id);
}

function sortBy(key: SortKey): void {
  sort.value = { key, descending: sort.value.key === key ? !sort.value.descending : false };
}

function ariaSort(key: SortKey | null): "ascending" | "descending" | undefined {
  if (key === null || sort.value.key !== key) return undefined;
  return sort.value.descending ? "descending" : "ascending";
}

function sortIcon(key: SortKey): string {
  if (sort.value.key !== key) return "fas fa-sort";
  return sort.value.descending ? "fas fa-sort-down" : "fas fa-sort-up";
}

function studyRoute(row: StudyRow) {
  return { name: "Study", params: { substance: row.substance, name: row.name } };
}

/** A click on a row opens its study, unless it hits a control of the row. */
function openRow(row: StudyRow, event: MouseEvent): void {
  if (row.duplicate) return;
  if (event.target instanceof Element && event.target.closest("a, button, input, label, .v-selection-control")) return;
  void router.push(studyRoute(row));
}

interface Curator {
  name: string;
  avatar: string | null;
  initials: string;
}

function curator(user: string): Curator {
  const profile = props.profiles.get(user.toLowerCase());
  const name = profile?.display_name ?? user;
  const words = name.split(/\s+/).filter(Boolean);
  const initials = (words.length > 1 ? `${words[0]![0]}${words.at(-1)![0]}` : name.slice(0, 1)).toUpperCase();
  return { name, avatar: profile?.avatar_url ?? null, initials };
}

function aiTitle(row: StudyRow): string {
  const method = row.summary.provenance?.method;
  return method ? `AI curated with ${method}` : "AI curated";
}

/** What a row shows besides the fields of the study row. */
const items = computed(() =>
  props.rows.map((row) => {
    const people = (row.summary.curators ?? []).map(curator);
    // A hidden remainder of one would take the room of its own avatar.
    const cut = people.length > SHOWN_CURATORS + 1 ? SHOWN_CURATORS : people.length;
    const number = row.issue?.number ?? row.summary.issue ?? null;
    const url = issueUrl(row, props.repository);
    return {
      row,
      curators: people.slice(0, cut),
      others: people
        .slice(cut)
        .map((person) => person.name)
        .join(", "),
      hidden: people.length - cut,
      problems: problemLabels(row),
      activity: activityLabel(row),
      issue: number !== null && url !== null ? { number, url } : null,
    };
  }),
);
</script>

<template>
  <VTable class="study-table" density="compact">
    <caption class="d-sr-only">
      Studies of the workspace
    </caption>
    <thead>
      <tr>
        <th ref="select-all" scope="col" class="cell-select">
          <VCheckboxBtn
            :model-value="allSelected"
            :indeterminate="someSelected"
            :disabled="selectable.length === 0"
            density="compact"
            aria-label="Select all shown studies"
            @update:model-value="toggleAll"
          />
        </th>
        <th
          v-for="column in columns"
          :key="column.cell"
          scope="col"
          :class="column.cell"
          :aria-sort="ariaSort(column.key)"
        >
          <button v-if="column.key" type="button" class="sort-button" @click="sortBy(column.key)">
            {{ column.label }}<VIcon :icon="sortIcon(column.key)" size="12" class="sort-icon" />
          </button>
          <template v-else>{{ column.label }}</template>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="{ row, curators, others, hidden, problems, activity, issue } in items"
        :key="row.path"
        :class="{ 'study-row--link': !row.duplicate, 'study-row--selected': isSelected(row) }"
        @click="openRow(row, $event)"
      >
        <td class="cell-select">
          <VCheckboxBtn
            :model-value="isSelected(row)"
            :disabled="row.duplicate"
            density="compact"
            :aria-label="`Select ${row.id}`"
            @update:model-value="toggle(row)"
          />
        </td>
        <td class="cell-study">
          <div class="study-heading">
            <span v-if="row.duplicate" class="study-identity">{{ row.id }}</span>
            <RouterLink v-else :to="studyRoute(row)" class="study-identity">{{ row.id }}</RouterLink>
            <VChip
              v-if="row.duplicate"
              size="x-small"
              color="error"
              variant="tonal"
              class="status-chip"
              title="Two folders have this identity. Rename one of them."
            >
              Duplicate identity
            </VChip>
          </div>
          <div v-if="row.duplicate" class="study-path">{{ row.path }}</div>
          <div v-if="row.summary.title" class="study-title" :title="row.summary.title">{{ row.summary.title }}</div>
          <div v-else class="study-title study-title--missing">No reference title yet</div>
        </td>
        <td class="cell-review">
          <div class="cell-chips">
            <VChip
              v-if="row.summary.review_status"
              size="small"
              variant="tonal"
              :color="REVIEW_TONES[row.summary.review_status]"
              class="status-chip"
            >
              {{ REVIEW_LABELS[row.summary.review_status] }}
            </VChip>
            <span v-else class="cell-empty">-</span>
            <VChip
              v-if="row.summary.ai"
              size="small"
              variant="outlined"
              prepend-icon="fas fa-robot"
              class="ai-marker"
              :title="aiTitle(row)"
            >
              AI
            </VChip>
          </div>
        </td>
        <td class="cell-open">{{ row.summary.open_items ?? 0 }}</td>
        <td class="cell-problems">
          <div v-if="problems.length" class="cell-chips">
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
          </div>
          <div v-if="activity" class="cell-note">{{ activity }}</div>
          <div v-if="row.message" class="cell-message" :title="row.message">{{ row.message }}</div>
          <VBtn
            v-if="row.status === 'unknown'"
            size="small"
            variant="tonal"
            color="primary"
            class="retry-button"
            :aria-label="`Review uncertain upload of ${row.id}`"
            @click="emit('retry', row)"
          >
            Review uncertain upload
          </VBtn>
        </td>
        <td class="cell-sync">
          <VChip size="small" variant="tonal" :color="SYNC_TONES[row.sync.status]" class="status-chip">
            {{ SYNC_LABELS[row.sync.status] }}
          </VChip>
        </td>
        <td class="cell-release">
          <span v-if="row.summary.release" :title="`Released on ${row.summary.release.date}`">
            {{ row.summary.release.pkdb_id }}
          </span>
          <span v-else class="cell-empty">-</span>
        </td>
        <td class="cell-issue">
          <a
            v-if="issue"
            :href="issue.url"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="`GitHub issue #${issue.number}`"
          >
            #{{ issue.number }}
          </a>
          <span v-else class="cell-empty">-</span>
        </td>
        <td class="cell-curators">
          <div v-if="curators.length" class="curators">
            <VAvatar
              v-for="(person, index) in curators"
              :key="index"
              size="28"
              color="primary"
              variant="tonal"
              class="curator"
              :title="person.name"
            >
              <img v-if="person.avatar" :src="person.avatar" :alt="person.name" class="curator-photo" />
              <span v-else role="img" :aria-label="person.name" class="curator-initials">{{ person.initials }}</span>
            </VAvatar>
            <span v-if="hidden" role="img" class="curator-more" :aria-label="`And ${others}`" :title="others">
              +{{ hidden }}
            </span>
          </div>
          <span v-else class="cell-empty">-</span>
        </td>
        <td class="cell-mode">{{ MODE_LABELS[row.mode] }}</td>
        <td class="cell-upload">
          <a
            v-if="row.last_upload?.url"
            :href="row.last_upload.url"
            target="_blank"
            rel="noopener noreferrer"
            :title="`Open ${row.id} in PK-DB`"
          >
            {{ formatTime(row.last_upload.at) }}
          </a>
          <span v-else-if="row.last_upload">{{ formatTime(row.last_upload.at) }}</span>
          <span v-else class="cell-empty">-</span>
        </td>
      </tr>
    </tbody>
  </VTable>
</template>

<style scoped>
.study-table {
  background: transparent;
}
.study-table :deep(table) {
  min-width: 100%;
}
.study-table th,
.study-table td {
  padding: 8px 10px;
  white-space: nowrap;
  vertical-align: top;
}
.study-table th {
  vertical-align: middle;
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-table .cell-select {
  width: 48px;
  min-width: 48px;
  padding-inline: 8px 0;
  vertical-align: middle;
}
.study-table td.cell-select {
  vertical-align: top;
}
.cell-select :deep(.v-selection-control) {
  justify-content: center;
}
.sort-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  cursor: pointer;
}
.sort-icon {
  opacity: 0.6;
}
th[aria-sort] .sort-button {
  color: rgb(var(--v-theme-on-surface));
}
th[aria-sort] .sort-icon {
  opacity: 1;
}
.study-row--link {
  cursor: pointer;
}
.study-table tbody tr:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}
.study-table tbody tr.study-row--selected {
  background: rgba(var(--v-theme-primary), 0.08);
}
/* The study column takes the room that the table has left, and its title wraps within a
   readable measure; every other cell stays on one line at the width of its content. */
.study-table th,
.study-table td {
  width: 1px;
}
.study-table .cell-study {
  width: auto;
  min-width: 15rem;
}
.study-table td.cell-study {
  white-space: normal;
}
.study-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  min-height: 24px;
}
.study-identity {
  font-weight: 600;
  overflow-wrap: anywhere;
}
a.study-identity {
  text-decoration: none;
}
a.study-identity:hover {
  text-decoration: underline;
}
.study-path {
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-title {
  display: -webkit-box;
  max-width: 30rem;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  font-size: 0.8125rem;
  line-height: 1.35;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-title--missing {
  font-style: italic;
}
.ai-marker {
  border-color: rgba(var(--v-theme-on-surface), 0.3);
}
.cell-chips {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 24px;
}
.study-table td.cell-open {
  text-align: end;
  line-height: 24px;
  font-variant-numeric: tabular-nums;
}
.study-table th.cell-open .sort-button {
  flex-direction: row-reverse;
}
.study-table th.cell-open {
  text-align: end;
}
.cell-note,
.cell-message {
  margin-top: 2px;
  font-size: 0.8125rem;
  line-height: 1.35;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* A note without chips above it sits on the line of the other cells. */
.cell-note:first-child {
  margin-top: 0;
  line-height: 24px;
}
.cell-message {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  max-width: 12rem;
  overflow: hidden;
  white-space: normal;
}
.retry-button {
  margin-top: 6px;
}
.cell-release,
.cell-issue,
.cell-mode,
.cell-upload {
  line-height: 24px;
}
.cell-release,
.cell-upload {
  font-variant-numeric: tabular-nums;
}
.cell-empty {
  line-height: 24px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The avatars are taller than a line of the row; they center on the first line. */
.curators {
  display: flex;
  align-items: center;
  margin-block: -2px;
}
/* Avatars overlap a little, each with a ring of the surface color. */
.curator {
  border: 2px solid rgb(var(--v-theme-surface));
  font-size: 0.75rem;
  font-weight: 700;
}
.curator + .curator,
.curators .curator-more {
  margin-inline-start: -6px;
}
.curator-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.curator-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 4px;
  border: 2px solid rgb(var(--v-theme-surface));
  border-radius: 14px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  font-size: 0.6875rem;
  font-weight: 700;
}
</style>
