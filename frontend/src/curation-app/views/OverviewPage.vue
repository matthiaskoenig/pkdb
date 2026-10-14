<script setup lang="ts">
import { computed, ref, shallowRef, useId, watch } from "vue";
import {
  VBtn,
  VChip,
  VChipGroup,
  VContainer,
  VProgressLinear,
  VSelect,
  VTextField,
  VTooltip,
} from "vuetify/components";
import type { Profile, StudyRow } from "../../study-views/types";
import RetryDialog from "../components/RetryDialog.vue";
import StudyTable from "../components/StudyTable.vue";
import UploadDialog from "../components/UploadDialog.vue";
import { storeToRefs } from "pinia";
import {
  COLLATOR,
  curatorsOf,
  filterStudies,
  plural,
  SEARCH_DELAY_MS,
  sortStudies,
  STATUS_CHIPS,
  substancesOf,
} from "../../study-views/overview";
import { uploadBlocker } from "../uploads";
import { useDebounced } from "../../study-views/composables/useDebounced";
import { useNotice } from "../composables/useNotice";
import { useDialogStore } from "../stores/dialogs";
import { useOverviewStore } from "../stores/overview";
import { useOverviewFilters } from "../stores/overviewFilters";
import { useStudyStore } from "../stores/study";
import { failureOf, findProfile, profileMap, type ActionFailure } from "../../study-views/study";
import ActionFailureAlert from "../components/ActionFailureAlert.vue";

const overview = useOverviewStore();
const dialogs = useDialogStore();
const blockerId = useId();

const snapshot = computed(() => overview.snapshot);
const studies = computed(() => snapshot.value?.studies ?? []);
/** The local server does not answer: the table shows the last known state and offers no actions. */
const stale = computed(() => overview.error !== null);
const blocker = computed(() => (snapshot.value ? uploadBlocker(snapshot.value) : null));

// Curator profiles for the avatars and the Curator filter; without them the avatars show initials
// and the filter shows user names. They load with the state of the local server until they loaded:
// a launch URL pasted into the open overview creates the session without mounting the page again.
const profiles = shallowRef<ReadonlyMap<string, Profile>>(new Map());
let profilesLoaded = false;
watch(
  snapshot,
  (state) => {
    if (!state || profilesLoaded) return;
    useStudyStore()
      .curators()
      .then(
        (list) => {
          profiles.value = profileMap(list);
          profilesLoaded = true;
        },
        () => undefined,
      );
  },
  { immediate: true },
);

// Filters
const filters = useOverviewFilters();
const { search, substance, curator, chip, sort } = storeToRefs(filters);
/** The text of the search field; the filter follows it 150 ms after the last keystroke. */
const { text: searchText, flush: flushSearch } = useDebounced(search, SEARCH_DELAY_MS);
watch(
  () => snapshot.value?.workspace,
  (path) => {
    if (path !== undefined) filters.forWorkspace(path);
  },
  { immediate: true },
);

const substanceItems = computed(() => [
  { title: "All substances", value: "" },
  ...substancesOf(studies.value).map((name) => ({ title: name, value: name })),
]);
/** Every curator with the number of their studies; the user of the app comes first, as Me. */
const curatorItems = computed(() => {
  const name = (user: string) => findProfile(profiles.value, user)?.display_name ?? user;
  const me = snapshot.value?.author.user ?? null;
  const curators = curatorsOf(studies.value);
  const mine = me ? curators.find(({ user }) => user.toLowerCase() === me.toLowerCase()) : undefined;
  const others = curators
    .filter((entry) => entry !== mine)
    .map(({ user, studies: count }) => ({ title: `${name(user)} (${count.toLocaleString("en-US")})`, value: user }))
    .sort((a, b) => COLLATOR.compare(a.title, b.title));
  return [
    { title: "All curators", value: "" },
    ...(me ? [{ title: `Me: ${name(me)} (${(mine?.studies ?? 0).toLocaleString("en-US")})`, value: me }] : []),
    ...others,
  ];
});
/** The rows of the filters and the counts of the chips, from one pass over the studies. */
const filtered = computed(() =>
  filterStudies(studies.value, {
    search: search.value,
    substance: substance.value,
    curator: curator.value,
    chip: chip.value,
  }),
);
/** The rows behind each chip, within the search, the substance and the curator. */
const counts = computed(() => filtered.value.counts);
const shown = computed(() => sortStudies(filtered.value.shown, sort.value));
/** The digits of the number of studies: no chip count has more, and each keeps room for them. */
const countDigits = computed(() => String(studies.value.length).length);
const countText = computed(() => {
  const total = plural(studies.value.length, "study", "studies");
  if (shown.value.length === studies.value.length) return total;
  return `${shown.value.length.toLocaleString("en-US")} of ${total}`;
});

/** The longest text of the count, "N of N studies": its hidden copy keeps the width of the count. */
const countSizer = computed(
  () => `${studies.value.length.toLocaleString("en-US")} of ${plural(studies.value.length, "study", "studies")}`,
);

function clearFilters(): void {
  flushSearch("");
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
    <!-- The heading, the count and, with studies, the search, the selects and the status chips
         share one line where they fit; the chips come last, so they move to the next line first. -->
    <div class="overview-header">
      <div class="overview-heading">
        <h1>Studies</h1>
        <span v-if="studies.length" class="overview-count-box">
          <span class="overview-count">{{ countText }}</span>
          <span class="overview-count-sizer" aria-hidden="true">{{ countSizer }}</span>
        </span>
      </div>
      <template v-if="studies.length">
        <VTextField
          v-model="searchText"
          label="Search studies"
          placeholder="Identity or title"
          prepend-inner-icon="fas fa-magnifying-glass"
          clearable
          hide-details
          class="overview-search"
          @click:clear="flushSearch('')"
        />
        <VSelect
          v-model="substance"
          :items="substanceItems"
          label="Substance"
          hide-details
          class="overview-substance"
        />
        <VSelect
          v-model="curator"
          :items="curatorItems"
          label="Curator"
          hide-details
          class="overview-curator"
        />
        <VChipGroup
          v-model="chip"
          mandatory
          column
          color="primary"
          role="group"
          aria-label="Filter by status"
          class="filter-chips overview-chips"
          :style="{ '--count-digits': countDigits }"
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
      </template>
    </div>

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
/*
 * The heading, the count, the search, the two selects and the status chips share one line where
 * they fit. The chips come last, so a narrower window moves them to the next line first, then the
 * selects. The counts of the chips change with the filters, and the chips may wrap. So that they
 * never move the fields, the fields do not grow and keep to the top of the line. Their 6px margin
 * puts them on the center line of the first row of chips: a field is 30px high, and a chip of
 * 26px stands 8px below the top of its group. The line of the heading is 28px high (1.6rem at a
 * line height of 1.25): 7px above it put it on the same center line.
 */
.overview-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 4px 12px;
}
.overview-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 12px;
  margin-block: 7px;
}
.overview-heading h1 {
  margin: 0;
}
/* The count keeps the width of its longest text, "N of N studies": a hidden copy of it in the same
   grid cell sets the width, so that the fields after it stay in place while a search changes the
   number of shown studies. Tabular digits make no shown count wider than that copy. */
.overview-count-box {
  display: inline-grid;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.overview-count,
.overview-count-sizer {
  grid-area: 1 / 1;
}
.overview-count-sizer {
  visibility: hidden;
}
.overview-search,
.overview-substance,
.overview-curator {
  margin-block: 6px;
}
/* 14rem (196px) and the 12px gap of the header let the header of pkdb_data's 1,503 studies, with
   its four-digit counts, fit one line in a 1440px window with a scrollbar. */
.overview-search {
  flex: 0 1 14rem;
}
.overview-substance {
  flex: 0 1 12rem;
  min-width: 10rem;
}
.overview-curator {
  flex: 0 1 16rem;
  min-width: 12rem;
}
.overview-chips {
  flex: 1 1 auto;
}
/* Each chip count keeps the room of the digits of the total, so that the chips keep their width
   (and do not jump between lines) while a search or a filter lowers the counts. */
.overview-chips .chip-count {
  display: inline-block;
  min-width: calc(var(--count-digits) * 1ch);
  text-align: end;
  font-variant-numeric: tabular-nums;
}
/* On a phone the search, the substance and the curator take the whole width, one above the other. */
@media (max-width: 599.98px) {
  .overview-search,
  .overview-substance,
  .overview-curator {
    flex: 1 1 100%;
    max-width: none;
  }
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
