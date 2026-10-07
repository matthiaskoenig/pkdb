<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VChip,
  VChipGroup,
  VContainer,
  VProgressLinear,
  VSelect,
  VTextField,
  VTooltip,
} from "vuetify/components";
import type { Profile, SaveMode, StudyRow } from "../api/types";
import RetryDialog from "../components/RetryDialog.vue";
import StudyTable from "../components/StudyTable.vue";
import UploadDialog from "../components/UploadDialog.vue";
import {
  chipCounts,
  filterStudies,
  MODE_LABELS,
  plural,
  sortStudies,
  STATUS_CHIPS,
  substancesOf,
  uploadBlocker,
  type StatusChip,
  type StudySort,
} from "../overview";
import { useDialogStore } from "../stores/dialogs";
import { useOverviewStore } from "../stores/overview";
import { useStudyStore } from "../stores/study";

const overview = useOverviewStore();
const dialogs = useDialogStore();
const blockerId = useId();

const snapshot = computed(() => overview.snapshot);
const studies = computed(() => snapshot.value?.studies ?? []);
/** The local server does not answer: the table shows the last known state and offers no actions. */
const stale = computed(() => overview.error !== null);
const blocker = computed(() => (snapshot.value ? uploadBlocker(snapshot.value) : null));

// Filters
const search = ref("");
const substance = ref("");
const chip = ref<StatusChip>("all");
const sort = ref<StudySort>({ key: "study", descending: false });

const substanceItems = computed(() => [
  { title: "All substances", value: "" },
  ...substancesOf(studies.value).map((name) => ({ title: name, value: name })),
]);
/** The rows behind each chip, within the search and the substance. */
const counts = computed(() =>
  chipCounts(filterStudies(studies.value, { search: search.value, substance: substance.value, chip: "all" })),
);
const shown = computed(() =>
  sortStudies(
    filterStudies(studies.value, { search: search.value, substance: substance.value, chip: chip.value }),
    sort.value,
  ),
);
const countText = computed(() => {
  const total = plural(studies.value.length, "study", "studies");
  if (shown.value.length === studies.value.length) return total;
  return `${shown.value.length.toLocaleString("en-US")} of ${total}`;
});

function clearFilters(): void {
  search.value = "";
  substance.value = "";
  chip.value = "all";
}

// Selection and batch actions
const selected = ref<string[]>([]);
const mode = ref<SaveMode>("validate");
const busy = ref<"validate" | "mode" | null>(null);
const error = ref<string | null>(null);
const notice = ref("");

/** The selected studies in the order of the table. */
const chosen = computed(() => {
  const ids = new Set(selected.value);
  return shown.value.filter((row) => !row.duplicate && ids.has(row.id));
});
const chosenIds = computed(() => chosen.value.map((row) => row.id));
const selectionText = computed(() =>
  chosen.value.length ? `${plural(chosen.value.length, "study", "studies")} selected` : "No studies selected",
);
const canAct = computed(() => chosen.value.length > 0 && busy.value === null && !stale.value);
const modeItems = computed(() =>
  (Object.keys(MODE_LABELS) as SaveMode[]).map((value) => ({
    title: MODE_LABELS[value],
    value,
    props: { disabled: value === "upload" && blocker.value !== null },
  })),
);

// The notice of an action belongs to the selection that it acted on.
watch(selected, () => {
  notice.value = "";
});

// Upload on save needs an upload permission; without it the choice falls back to Validate.
watch(blocker, (value) => {
  if (value !== null && mode.value === "upload") mode.value = "validate";
});

// A study that the filters hide, or that left the workspace, leaves the selection.
watch(shown, (rows) => {
  const visible = new Set(rows.filter((row) => !row.duplicate).map((row) => row.id));
  if (selected.value.some((id) => !visible.has(id))) selected.value = selected.value.filter((id) => visible.has(id));
});

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : String(caught);
}

async function run(kind: "validate" | "mode", action: () => Promise<string>): Promise<void> {
  busy.value = kind;
  error.value = null;
  notice.value = "";
  try {
    notice.value = await action();
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = null;
  }
}

function validate(): Promise<void> {
  const ids = chosenIds.value;
  return run("validate", async () => {
    await overview.enqueue(ids, "validate");
    return `Validation queued for ${plural(ids.length, "study", "studies")}.`;
  });
}

function modeNotice(value: SaveMode, count: number): string {
  return `On save is ${MODE_LABELS[value]} for ${plural(count, "study", "studies")}.`;
}

// Upload and upload on save are reviewed in a dialog first.
const upload = ref<{ open: boolean; studies: StudyRow[]; action: "upload" | "enable" }>({
  open: false,
  studies: [],
  action: "upload",
});

function review(action: "upload" | "enable"): void {
  error.value = null;
  notice.value = "";
  upload.value = { open: true, studies: chosen.value, action };
}

function applyMode(): Promise<void> | void {
  const value = mode.value;
  if (value === "upload") return review("enable");
  const ids = chosenIds.value;
  return run("mode", async () => {
    await overview.setMode(ids, value);
    return modeNotice(value, ids.length);
  });
}

function uploaded(count: number): void {
  notice.value =
    upload.value.action === "upload"
      ? `Upload queued for ${plural(count, "study", "studies")}.`
      : modeNotice("upload", count);
}

// Uploads with an unknown outcome
const retryOpen = ref(false);
const retryStudy = shallowRef<StudyRow | null>(null);

function reviewRetry(row: StudyRow): void {
  retryStudy.value = row;
  retryOpen.value = true;
}

// Curator profiles for the avatars; without them the avatars show initials.
const profiles = shallowRef<ReadonlyMap<string, Profile>>(new Map());
onMounted(() => {
  useStudyStore()
    .curators()
    .then(
      (list) => {
        profiles.value = new Map(list.map((profile) => [profile.username.toLowerCase(), profile]));
      },
      () => undefined,
    );
});

const format1 = computed(() => snapshot.value?.format1_folders ?? 0);
</script>

<template>
  <VContainer fluid class="overview">
    <div class="overview-heading">
      <h1>Studies</h1>
      <span v-if="snapshot && studies.length" class="overview-count">{{ countText }}</span>
    </div>

    <template v-if="snapshot">
      <template v-if="studies.length">
        <div class="overview-filters">
          <VTextField
            v-model="search"
            label="Search studies"
            placeholder="Identity or title"
            prepend-inner-icon="fas fa-magnifying-glass"
            clearable
            hide-details
            class="overview-search"
            @click:clear="search = ''"
          />
          <VSelect
            v-model="substance"
            :items="substanceItems"
            label="Substance"
            hide-details
            class="overview-substance"
          />
          <VChipGroup
            v-model="chip"
            mandatory
            column
            color="primary"
            role="group"
            aria-label="Filter by status"
            class="overview-chips"
          >
            <VChip
              v-for="item in STATUS_CHIPS"
              :key="item.value"
              :value="item.value"
              tag="button"
              type="button"
              filter
              :aria-pressed="chip === item.value ? 'true' : 'false'"
            >
              {{ item.label }}<span class="chip-count">{{ counts[item.value] }}</span>
            </VChip>
          </VChipGroup>
        </div>

        <VAlert
          v-if="error"
          type="error"
          variant="tonal"
          density="compact"
          closable
          class="status-alert overview-error"
          @click:close="error = null"
        >
          {{ error }}
        </VAlert>

        <section class="study-panel" aria-label="Studies">
          <div class="batch-toolbar">
            <span class="batch-count">{{ selectionText }}</span>
            <div class="batch-actions">
              <VBtn
                variant="tonal"
                color="primary"
                prepend-icon="fas fa-circle-check"
                :disabled="!canAct"
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
                      :disabled="!canAct || blocker !== null"
                      :aria-describedby="blocker ? blockerId : undefined"
                      @click="review('upload')"
                    >
                      Upload
                    </VBtn>
                  </span>
                </template>
              </VTooltip>
              <span v-if="blocker" :id="blockerId" class="d-sr-only">{{ blocker }}</span>
            </div>
            <div class="batch-mode">
              <VSelect v-model="mode" :items="modeItems" label="On save" hide-details class="batch-mode-select" />
              <VBtn variant="text" color="primary" :disabled="!canAct" :loading="busy === 'mode'" @click="applyMode">
                Apply
              </VBtn>
            </div>
            <span role="status" class="batch-status">{{ notice }}</span>
          </div>

          <StudyTable
            v-if="shown.length"
            v-model:selected="selected"
            v-model:sort="sort"
            :rows="shown"
            :profiles="profiles"
            :repository="snapshot.github.repository"
            @retry="reviewRetry"
          />
          <div v-else class="overview-empty">
            <p>No studies match these filters.</p>
            <VBtn variant="tonal" color="primary" @click="clearFilters">Clear filters</VBtn>
          </div>
        </section>
      </template>

      <div v-else class="overview-empty">
        <p>This workspace has no study format 2 studies.</p>
        <VBtn variant="tonal" color="primary" prepend-icon="fas fa-folder-open" @click="dialogs.openWorkspace">
          Choose workspace
        </VBtn>
      </div>

      <p v-if="format1 > 0" class="overview-footer">
        {{ plural(format1, "study format 1 folder") }} {{ format1 === 1 ? "is" : "are" }} not listed. Convert
        {{ format1 === 1 ? "it" : "them" }} with <code>pkdb migrate</code>; until then
        {{ format1 === 1 ? "it stays" : "they stay" }} on the released app version.
      </p>
    </template>

    <div v-else-if="!stale" class="overview-loading">
      <VProgressLinear indeterminate color="primary" aria-label="Loading the studies" />
    </div>

    <UploadDialog v-model="upload.open" :studies="upload.studies" :action="upload.action" @done="uploaded" />
    <RetryDialog
      v-model="retryOpen"
      :study="retryStudy"
      @done="(row) => (notice = `Upload queued again for ${row.id}.`)"
    />
  </VContainer>
</template>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 16px;
}
.overview-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 12px;
}
.overview-heading h1 {
  margin: 0;
}
.overview-count {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.overview-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px;
}
.overview-search {
  flex: 1 1 18rem;
  max-width: 28rem;
}
.overview-substance {
  flex: 0 1 12rem;
  min-width: 10rem;
}
.overview-chips {
  flex: 1 1 auto;
}
/* On a phone the search and the substance take the whole width, one above the other. */
@media (max-width: 599.98px) {
  .overview-search,
  .overview-substance {
    flex: 1 1 100%;
    max-width: none;
  }
}
/* The group adds its own margins around the chips; the gap of the filters is enough. */
.overview-chips :deep(.v-slide-group__content) {
  margin: 0;
  padding: 0;
}
.chip-count {
  margin-inline-start: 8px;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.study-panel {
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
}
.batch-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  padding: 10px 12px 10px 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
/* Wide enough for "No studies selected", so that the actions keep their place. */
.batch-count {
  min-width: 10.5rem;
  font-weight: 600;
}
.batch-actions,
.batch-mode {
  display: flex;
  align-items: center;
  gap: 8px;
}
.upload-action {
  display: inline-flex;
}
.batch-mode-select {
  width: 9.5rem;
}
/* A live region stays in the page while it is empty, so that screen readers announce its text. */
.batch-status {
  flex: 1 1 auto;
  font-size: 0.875rem;
  text-align: end;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.overview-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 24px 16px;
}
.overview-empty p {
  margin: 0;
}
.overview-footer {
  margin: 0;
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.overview-loading {
  max-width: 24rem;
}
</style>
