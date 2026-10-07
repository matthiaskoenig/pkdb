<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VBtn, VChip, VChipGroup, VSelect } from "vuetify/components";
import type { Profile, ReviewItem } from "../api/types";
import NewItemDialog from "../components/NewItemDialog.vue";
import ReviewItemCard from "../components/ReviewItemCard.vue";
import ReviewItemDetail from "../components/ReviewItemDetail.vue";
import TargetView from "../components/TargetView.vue";
import UserHint from "../components/UserHint.vue";
import { useNotice } from "../composables/useNotice";
import {
  emptyText,
  filterItems,
  KIND_FILTERS,
  reviewFailure,
  STATE_CHIPS,
  stateCounts,
  type ItemAction,
  type KindFilter,
  type ReviewFailure,
  type StateFilter,
} from "../review";
import { useStudyStore } from "../stores/study";
import { knownProfiles, profileOf } from "../study";

/**
 * The review items of review.json: state and kind filters, the cards of the items, and the
 * selected item with its thread, its actions and its target. The selected item is the `item` of
 * the route, so that other sections can link to it; without one, the first shown item.
 *
 * Every write goes over the revision that the page read. One action runs at a time; a stale
 * revision reloads the items and asks to repeat the action.
 */
const study = useStudyStore();
const route = useRoute();
const router = useRouter();
const { notice, announce } = useNotice();

const review = computed(() => study.detail?.review ?? null);
const items = computed<ReviewItem[]>(() => review.value?.value?.items ?? []);
const approved = computed(() => review.value?.value?.status === "approved");
const writable = computed(() => review.value?.revision != null && review.value.value !== null);

// Profiles: the roster, and the people of the study who are not in it.
const roster = ref<Profile[]>([]);
onMounted(() => {
  study.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the roster the items show user names.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, study.detail?.people));

// Filters and selection

const kind = ref<KindFilter>("all");
/** The open items first; a study without open items shows all of them. */
const state = ref<StateFilter>(items.value.some((item) => item.state === "open") ? "open" : "all");
const shown = computed(() => filterItems(items.value, state.value, kind.value));
const counts = computed(() => stateCounts(items.value, kind.value));

const linked = computed(() => (typeof route.query.item === "string" ? route.query.item : null));
/** The item that was selected or linked; the route follows it. */
const chosen = ref<string | null>(null);
/** The chosen item, also when the filters hide it after an action; else the first shown item. */
const selected = computed(
  () => items.value.find((item) => item.id === chosen.value) ?? shown.value[0] ?? null,
);

function isShown(id: string | null): boolean {
  return shown.value.some((item) => item.id === id);
}

/** Switch the filters to the item `id` when they hide it. */
function reveal(id: string): void {
  const item = items.value.find((candidate) => candidate.id === id);
  if (item && !isShown(id)) {
    state.value = item.state;
    kind.value = "all";
  }
}

/**
 * Select the item `id`, or none, and put it in the route. The selection does not wait for the
 * navigation, which Vuetify's overlays delay by a timer.
 */
function select(id: string | null, { show = false }: { show?: boolean } = {}): void {
  chosen.value = id;
  if (id !== null && show) reveal(id);
  if (id === linked.value) return;
  const query = { ...route.query };
  if (id === null) delete query.item;
  else query.item = id;
  void router.replace({ query });
}

// A link to an item, such as from the Problems section, selects it and shows it among the cards.
watch(
  linked,
  (id) => {
    if (id === chosen.value) return;
    chosen.value = id;
    if (id !== null) reveal(id);
  },
  { immediate: true },
);

// A filter that hides the selected item lets the first shown item be selected.
watch([state, kind], () => {
  if (chosen.value !== null && !isShown(chosen.value)) select(null);
});

const detailColumn = ref<HTMLElement | null>(null);

/** Select an item from its card; the item comes into view where it is beside or below the cards. */
async function choose(id: string): Promise<void> {
  select(id);
  await nextTick();
  const element = detailColumn.value;
  if (!element) return;
  // Below the app bar, and with the start of the item in view.
  const top = element.getBoundingClientRect().top;
  if (top < 64 || top > window.innerHeight - 160) {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView?.({ block: "start", behavior: reduced ? "auto" : "smooth" });
  }
}

// Actions

/** The reply drafts by item, so that selecting another item keeps them. */
const drafts = ref<Record<string, string>>({});
const draft = computed({
  get: () => (selected.value ? (drafts.value[selected.value.id] ?? "") : ""),
  set: (value: string) => {
    if (selected.value) drafts.value = { ...drafts.value, [selected.value.id]: value };
  },
});

/** The action that runs; one at a time, so that feedback and revisions never mix. */
const busy = ref<ItemAction | null>(null);
/** The failure of the last action; it stays until it is dismissed or the next action starts. */
const failure = ref<ReviewFailure | null>(null);
const adding = ref(false);

const REFUSED: Record<ItemAction, string> = {
  reply: "The reply was not posted.",
  resolve: "The item was not resolved.",
  dismiss: "The item was not dismissed.",
  reopen: "The item was not reopened.",
};

/** What an action did; for an acknowledgement, also what became of its warning. */
function doneText(action: ItemAction, item: ReviewItem): string {
  const code = item.acknowledges;
  switch (action) {
    case "reply":
      return "Reply posted.";
    case "resolve":
      return "Item resolved.";
    case "dismiss":
      return code ? `Item dismissed. Its warning ${code} is no longer acknowledged.` : "Item dismissed.";
    case "reopen":
      return code && item.state === "dismissed"
        ? `Item reopened. It acknowledges ${code} again.`
        : "Item reopened.";
  }
}

async function act(action: ItemAction): Promise<void> {
  const item = selected.value;
  const revision = review.value?.revision;
  if (!item || revision == null || busy.value !== null) return;
  const text = drafts.value[item.id] ?? "";
  if (action === "reply" && !text.trim()) return;
  busy.value = action;
  failure.value = null;
  announce("");
  try {
    // The item stays selected after the write, also when the filters hide it then.
    select(item.id);
    const payload =
      action === "reopen" ? { item: item.id } : { item: item.id, ...(text.trim() ? { text } : {}) };
    await study.reviewAction(revision, action, payload);
    if (action !== "reopen") drafts.value = { ...drafts.value, [item.id]: "" };
    announce(doneText(action, item));
  } catch (caught) {
    failure.value = reviewFailure(caught, REFUSED[action]);
  } finally {
    busy.value = null;
  }
}

function added(item: ReviewItem | null): void {
  failure.value = null;
  if (item) select(item.id, { show: true });
  announce("Item added.");
}
</script>

<template>
  <div class="review">
    <section v-if="!review?.value" class="review-invalid">
      <VAlert type="error" variant="tonal" density="compact" class="status-alert">
        <p class="review-alert-text">
          {{
            review?.revision === null
              ? "review.json cannot be written from the app."
              : "review.json is not valid, so the items cannot be shown."
          }}
        </p>
        <ul v-if="review?.issues.length" class="review-alert-issues">
          <li v-for="(problem, index) in review.issues" :key="index">{{ problem.message }}</li>
        </ul>
      </VAlert>
      <p class="review-text">Fix review.json in your editor. The items show again when it is valid.</p>
    </section>

    <template v-else>
      <div class="review-toolbar">
        <VChipGroup
          v-model="state"
          mandatory
          column
          color="primary"
          role="group"
          aria-label="Filter by state"
          class="filter-chips review-chips"
        >
          <VChip
            v-for="chip in STATE_CHIPS"
            :key="chip.value"
            :value="chip.value"
            tag="button"
            type="button"
            filter
            :aria-pressed="state === chip.value ? 'true' : 'false'"
          >
            {{ chip.label }}<span class="chip-count">{{ counts[chip.value] }}</span>
          </VChip>
        </VChipGroup>
        <div class="review-tools">
          <VSelect v-model="kind" :items="KIND_FILTERS" label="Kind" hide-details class="review-kind" />
          <VBtn
            color="primary"
            prepend-icon="fas fa-plus"
            :disabled="!writable || approved"
            class="review-new"
            @click="adding = true"
          >
            New item
          </VBtn>
        </div>
      </div>
      <p v-if="approved" class="review-approved">
        The study is approved. Set the review status to In review to add or reopen items.
      </p>

      <div class="review-body">
        <div class="review-list-column">
          <ul v-if="shown.length" class="review-list" aria-label="Review items">
            <li v-for="item in shown" :key="item.id">
              <ReviewItemCard
                :item="item"
                :selected="item.id === selected?.id"
                :author="profileOf(profiles, item.author).display_name"
                @select="choose(item.id)"
              />
            </li>
          </ul>
          <p v-else class="review-empty">{{ emptyText(state, kind) }}</p>
        </div>

        <div ref="detailColumn" class="review-selected">
          <ReviewItemDetail
            v-if="selected"
            v-model:draft="draft"
            :item="selected"
            :profiles="profiles"
            :busy="busy"
            :writable="writable"
            :can-reopen="!approved"
            @act="act"
          />
          <VAlert
            v-if="failure?.kind === 'conflict'"
            type="warning"
            variant="tonal"
            density="compact"
            closable
            class="status-alert review-conflict"
            @click:close="failure = null"
          >
            {{ failure.text }}
          </VAlert>
          <UserHint v-else-if="failure?.kind === 'user'" :text="failure.text" />
          <VAlert
            v-else-if="failure"
            type="error"
            variant="tonal"
            density="compact"
            closable
            class="status-alert review-failure"
            @click:close="failure = null"
          >
            <p class="review-alert-text">{{ failure.text }}</p>
            <ul v-if="failure.issues.length" class="review-alert-issues">
              <li v-for="(message, index) in failure.issues" :key="index">{{ message }}</li>
            </ul>
          </VAlert>
          <!-- A live region stays in the page while it is empty, so that screen readers announce its text. -->
          <span role="status" aria-live="polite" class="review-notice">{{ notice }}</span>
          <TargetView v-if="selected" :target="selected.target" />
        </div>
      </div>
    </template>

    <NewItemDialog v-model="adding" @added="added" />
  </div>
</template>

<style scoped>
.review {
  container-type: inline-size;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.review-alert-text,
.review-text {
  margin: 0;
}
.review-alert-issues {
  margin: 4px 0 0;
  padding-inline-start: 20px;
  overflow-wrap: anywhere;
}
.review-invalid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 56rem;
}
.review-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
}
.review-chips {
  flex: 1 1 auto;
}
.review-tools {
  display: flex;
  align-items: center;
  gap: 12px;
}
.review-kind {
  width: 11rem;
  flex: 0 0 auto;
}
.review-approved {
  margin: 0;
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.review-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: start;
  gap: 16px;
}
/* The cards beside the selected item where the section is wide enough for both. */
@container (min-width: 760px) {
  .review-body {
    grid-template-columns: minmax(17rem, 2fr) minmax(0, 3fr);
  }
}
.review-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.review-empty {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
.review-selected {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  /* Below the app bar when it scrolls into view. */
  scroll-margin-top: 80px;
}
.review-notice {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* Empty, it stays in the page for screen readers but takes no gap. */
.review-notice:empty {
  position: absolute;
}
/* On a phone the kind and New item share the line below the chips. */
@media (max-width: 599.98px) {
  .review-tools {
    width: 100%;
  }
  .review-kind {
    flex: 1 1 auto;
    width: auto;
  }
}
</style>
