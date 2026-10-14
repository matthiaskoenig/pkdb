<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { VAlert, VChip, VChipGroup, VSelect } from "vuetify/components";
import { useStudyViews } from "../context";
import type { Profile, ReviewItem } from "../types";
import ReviewItemCard from "../components/ReviewItemCard.vue";
import ReviewItemDetail from "../components/ReviewItemDetail.vue";
import TargetView from "../components/TargetView.vue";
import {
  emptyText,
  filterItems,
  KIND_FILTERS,
  STATE_CHIPS,
  stateCounts,
  type ItemAction,
  type KindFilter,
  type StateFilter,
} from "../review";
import { knownProfiles, profileOf } from "../study";

/**
 * The review items of review.json: state and kind filters, the cards of the items, and the
 * selected item with its thread, its actions and its target. The selected item is the `item` of
 * the route, so that other sections can link to it; without one, the first shown item.
 *
 * The page runs the actions on the selected item (`act`), with `busy` and `blocked` while it
 * writes, and fills the slots: its tools after the Kind filter, what it says about the selected
 * item, and its dialogs.
 */
const props = withDefaults(defineProps<{ busy?: ItemAction | null; blocked?: boolean }>(), {
  busy: null,
  blocked: false,
});
const emit = defineEmits<{ act: [action: ItemAction, item: ReviewItem, text: string] }>();
defineSlots<{
  tools?: () => unknown;
  detail?: (props: { item: ReviewItem | null }) => unknown;
  dialogs?: () => unknown;
}>();

const route = useRoute();
const router = useRouter();
const views = useStudyViews();
const capabilities = views.capabilities;
const detail = views.data.detail;

const review = computed(() => detail.value?.review ?? null);
/**
 * Why the items do not show: review.json cannot be written from the app, which only a reader who
 * may edit hears of, or it is not valid.
 */
const invalidText = computed(() => {
  if (review.value?.revision !== null) return "review.json is not valid, so the items cannot be shown.";
  return capabilities.value.edit ? "review.json cannot be written from the app." : "The review items cannot be shown.";
});
const items = computed<ReviewItem[]>(() => review.value?.value?.items ?? []);
const approved = computed(() => review.value?.value?.status === "approved");
const writable = computed(() => review.value?.revision != null && review.value.value !== null);

// Profiles: the roster, and the people of the study who are not in it.
const roster = ref<Profile[]>([]);
onMounted(() => {
  views.data.curators().then(
    (profiles) => (roster.value = profiles),
    // Without the roster the items show user names.
    () => undefined,
  );
});
const profiles = computed(() => knownProfiles(roster.value, detail.value?.people));

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
  // The section keeps every key of the address and sets its own `item`.
  const own = { ...route.query };
  if (id === null) delete own.item;
  else own.item = id;
  void router.replace({ query: views.routes.query(route.query, own) });
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

const listColumn = ref<HTMLElement | null>(null);
const detailColumn = ref<HTMLElement | null>(null);

/**
 * Select an item from its card. Beside the cards, the item stays in view in its sticky column,
 * which starts at the top again. Below the cards, the page scrolls to the item when it is out of
 * view.
 */
async function choose(id: string): Promise<void> {
  select(id);
  await nextTick();
  const list = listColumn.value;
  const column = detailColumn.value;
  if (!list || !column) return;
  const below = column.getBoundingClientRect().left === list.getBoundingClientRect().left;
  if (!below) {
    column.scrollTop = 0;
    return;
  }
  // Below the app bar, and with the start of the item in view.
  const top = column.getBoundingClientRect().top;
  if (top < 64 || top > window.innerHeight - 160) {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    column.scrollIntoView?.({ block: "start", behavior: reduced ? "auto" : "smooth" });
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

/** Ask the page to run `action` on the selected item, with its reply; the item stays selected after the write. */
function act(action: ItemAction): void {
  const item = selected.value;
  if (!item || review.value?.revision == null || props.busy !== null || props.blocked) return;
  // A dismissed item has no reply box, so a draft left from before is not posted.
  const text = item.state === "dismissed" ? "" : (drafts.value[item.id] ?? "").trim();
  if (action === "reply" && !text) return;
  // The item stays selected after the write, also when the filters hide it then.
  select(item.id);
  emit("act", action, item, text);
}

/** Forget the reply draft of the item `id`, after its page posted it. */
function clearDraft(id: string): void {
  drafts.value = { ...drafts.value, [id]: "" };
}

defineExpose({ selected, select, clearDraft });
</script>

<template>
  <div class="review">
    <section v-if="!review?.value" class="review-invalid">
      <VAlert type="error" variant="tonal" density="compact" class="status-alert">
        <p class="review-alert-text">{{ invalidText }}</p>
        <ul v-if="review?.issues.length" class="review-alert-issues">
          <li v-for="(problem, index) in review.issues" :key="index">{{ problem.message }}</li>
        </ul>
      </VAlert>
      <p v-if="capabilities.edit" class="review-text">
        Fix review.json in your editor. The items show again when it is valid.
      </p>
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
          <slot v-if="capabilities.edit" name="tools" />
        </div>
      </div>
      <p v-if="capabilities.edit && approved" class="review-approved">
        The study is approved. Set the review status to In review to add or reopen items.
      </p>

      <div class="review-body">
        <div ref="listColumn" class="review-list-column">
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
            :blocked="blocked"
            :can-reopen="!approved"
            @act="act"
          />
          <slot v-if="capabilities.edit" name="detail" :item="selected" />
          <TargetView v-if="selected" :item="selected" />
        </div>
      </div>
    </template>

    <slot v-if="capabilities.edit" name="dialogs" />
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
/* The cards beside the selected item where the section is wide enough for both. The item stays
   in view below the app bar while the cards scroll, and scrolls on its own when it is taller
   than the window. */
@container (min-width: 760px) {
  .review-body {
    grid-template-columns: minmax(17rem, 2fr) minmax(0, 3fr);
  }
  /* Below the app bar, and below the banner of unsaved changes of study.json while it sticks. */
  .review-selected {
    position: sticky;
    top: calc(80px + var(--unsaved-banner-height, 0px));
    max-height: calc(100vh - 96px - var(--unsaved-banner-height, 0px));
    overflow-y: auto;
  }
  /* The cards keep their height in the limited column, which scrolls instead. */
  .review-selected > *,
  .review-selected > :slotted(*) {
    flex-shrink: 0;
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
/* The page keeps the room of the app bar and of the banner of unsaved changes while the banner
   sticks (UnsavedBanner): the item scrolls to just below the banner. */
:global(html:has(.unsaved-banner--sticky) .review-selected) {
  scroll-margin-top: 0;
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
