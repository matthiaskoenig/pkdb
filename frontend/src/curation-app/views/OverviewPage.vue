<script setup lang="ts">
import { computed, ref, shallowRef, useId, useTemplateRef, watch } from "vue";
import { VBtn, VContainer, VProgressLinear, VTooltip } from "vuetify/components";
import type { StudyRow } from "../../study-views/types";
import StudyFilters from "../../study-views/components/StudyFilters.vue";
import RetryDialog from "../components/RetryDialog.vue";
import StudyTable from "../../study-views/components/StudyTable.vue";
import UploadDialog from "../components/UploadDialog.vue";
import { storeToRefs } from "pinia";
import { useStudyViews } from "../../study-views/context";
import { filterStudies, plural, sortStudies } from "../../study-views/overview";
import { uploadBlocker } from "../uploads";
import { useNotice } from "../composables/useNotice";
import { useDialogStore } from "../stores/dialogs";
import { useOverviewStore } from "../stores/overview";
import { useOverviewFilters } from "../stores/overviewFilters";
import { useStudyStore } from "../stores/study";
import { failureOf, type ActionFailure } from "../../study-views/study";
import ActionFailureAlert from "../../study-views/components/ActionFailureAlert.vue";

const overview = useOverviewStore();
const dialogs = useDialogStore();
const views = useStudyViews();
const blockerId = useId();

const snapshot = computed(() => overview.snapshot);
const studies = computed(() => snapshot.value?.studies ?? []);
/** The local server does not answer: the table shows the last known state and offers no actions. */
const stale = computed(() => overview.error !== null);
const blocker = computed(() => (snapshot.value ? uploadBlocker(snapshot.value) : null));

// The profiles of the curators for the avatars and the Curator filter, which the study store
// keeps; without them the avatars show initials and the filter shows user names. They load with
// the state of the local server until they loaded: a launch URL pasted into the open overview
// creates the session without mounting the page again.
let profilesLoaded = false;
watch(
  snapshot,
  (state) => {
    if (!state || profilesLoaded) return;
    useStudyStore()
      .curators()
      .then(
        () => (profilesLoaded = true),
        () => undefined,
      );
  },
  { immediate: true },
);

// Filters
const filters = useOverviewFilters();
const { search, substance, curator, chip, sort } = storeToRefs(filters);
/** The filter line, whose search field writes the search 150 ms after the last keystroke. */
const filterLine = useTemplateRef<InstanceType<typeof StudyFilters>>("filterLine");
watch(
  () => snapshot.value?.workspace,
  (path) => {
    if (path !== undefined) filters.forWorkspace(path);
  },
  { immediate: true },
);

/** The rows of the filters and the counts of the chips, from one pass over the studies. */
const filtered = computed(() =>
  filterStudies(
    studies.value,
    {
      search: search.value,
      substance: substance.value,
      curator: curator.value,
      chip: chip.value,
    },
    views.capabilities.value,
  ),
);
/** The rows behind each chip, within the search, the substance and the curator. */
const counts = computed(() => filtered.value.counts);
const shown = computed(() => sortStudies(filtered.value.shown, sort.value));

function clearFilters(): void {
  filterLine.value?.flushSearch("");
  filters.clear();
}

// Selection and batch actions
const selected = ref<string[]>([]);
/** Whether the validation of the selected studies is being queued. */
const busy = ref(false);
const failure = ref<ActionFailure | null>(null);
/** The notice of the last action that succeeded; it disappears after a few seconds. */
const { notice, announce } = useNotice();

/** The selected studies in the order of the table. */
const chosen = computed(() => {
  const ids = new Set(selected.value);
  return shown.value.filter((row) => !row.duplicate && ids.has(row.id));
});
const chosenIds = computed(() => chosen.value.map((row) => row.id));
const selectionText = computed(() =>
  chosen.value.length ? `${plural(chosen.value.length, "study", "studies")} selected` : "No studies selected",
);
const canAct = computed(() => chosen.value.length > 0 && !busy.value && !stale.value);

// The notice of an action belongs to the selection that it acted on.
watch(selected, () => announce(""));

// A study that the filters hide, or that left the workspace, leaves the selection.
watch(shown, (rows) => {
  const visible = new Set(rows.filter((row) => !row.duplicate).map((row) => row.id));
  if (selected.value.some((id) => !visible.has(id))) selected.value = selected.value.filter((id) => visible.has(id));
});

async function run(action: () => Promise<string>): Promise<void> {
  busy.value = true;
  failure.value = null;
  announce("");
  // Every change of the selection makes a new list.
  const selection = selected.value;
  try {
    const text = await action();
    // A notice about studies that are no longer the selection would mislead.
    if (selected.value === selection) announce(text);
  } catch (caught) {
    failure.value = failureOf(caught);
  } finally {
    busy.value = false;
  }
}

function validate(): Promise<void> {
  const ids = chosenIds.value;
  return run(async () => {
    await overview.enqueue(ids, "validate");
    return `Validation queued for ${plural(ids.length, "study", "studies")}.`;
  });
}

// An upload is reviewed in a dialog first. On save, which the top bar sets, applies to every study.
const upload = ref<{ open: boolean; studies: StudyRow[] }>({ open: false, studies: [] });

function review(): void {
  failure.value = null;
  announce("");
  upload.value = { open: true, studies: chosen.value };
}

function uploaded(count: number): void {
  announce(`Upload queued for ${plural(count, "study", "studies")}.`);
}

// Uploads with an unknown outcome
const retryOpen = ref(false);
const retryStudy = shallowRef<StudyRow | null>(null);

function reviewRetry(row: StudyRow): void {
  retryStudy.value = row;
  retryOpen.value = true;
}

// The focus after a dialog when the control that opened it is gone.
const panel = ref<HTMLElement | null>(null);
/** The checkbox that selects all studies, when Upload went with the selection. */
const selectAll = () => panel.value?.querySelector<HTMLElement>("thead .cell-select input");
/** The link of the study of the retry, when its Review went with the unknown outcome. */
function retriedStudy(): HTMLElement | null | undefined {
  const id = retryStudy.value?.id;
  return [...(panel.value?.querySelectorAll<HTMLElement>("tr[data-study]") ?? [])]
    .find((row) => row.dataset.study === id)
    ?.querySelector<HTMLElement>("a.study-identity");
}

const format1 = computed(() => snapshot.value?.format1_folders ?? 0);
const format1Notice = computed(() =>
  format1.value === 1
    ? "1 study format 1 folder is not listed. It stays on the released app version until it is converted."
    : `${plural(format1.value, "study format 1 folder")} are not listed. ` +
      "They stay on the released app version until they are converted.",
);
</script>

<template>
  <VContainer fluid class="overview">
    <StudyFilters
      ref="filterLine"
      v-model:search="search"
      v-model:substance="substance"
      v-model:curator="curator"
      v-model:chip="chip"
      :counts="counts"
      :shown="shown.length"
      :me="snapshot?.author.user ?? null"
    />

    <template v-if="snapshot">
      <template v-if="studies.length">

        <ActionFailureAlert v-if="failure" :failure="failure" class="overview-error" @close="failure = null" />

        <section ref="panel" class="study-panel" aria-label="Studies">
          <div class="batch-toolbar">
            <span class="batch-count">{{ selectionText }}</span>
            <div class="batch-actions">
              <VBtn
                variant="tonal"
                color="primary"
                prepend-icon="fas fa-circle-check"
                :disabled="!canAct"
                :loading="busy"
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
                      @click="review"
                    >
                      Upload
                    </VBtn>
                  </span>
                </template>
              </VTooltip>
              <span v-if="blocker" :id="blockerId" class="d-sr-only">{{ blocker }}</span>
            </div>
            <span role="status" class="batch-status">{{ notice }}</span>
          </div>

          <StudyTable
            v-if="shown.length"
            v-model:selected="selected"
            v-model:sort="sort"
            :rows="shown"
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

      <p v-if="format1 > 0" class="overview-footer">{{ format1Notice }}</p>
    </template>

    <div v-else-if="!stale" class="overview-loading">
      <VProgressLinear indeterminate color="primary" aria-label="Loading the studies" />
    </div>

    <UploadDialog
      v-model="upload.open"
      :studies="upload.studies"
      action="upload"
      :fallback-focus="selectAll"
      @done="uploaded"
    />
    <RetryDialog
      v-model="retryOpen"
      :study="retryStudy"
      :fallback-focus="retriedStudy"
      @done="(row) => announce(`Upload queued again for ${row.id}.`)"
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
.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.upload-action {
  display: inline-flex;
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
