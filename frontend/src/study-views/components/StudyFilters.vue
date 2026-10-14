<script setup lang="ts">
import { computed } from "vue";
import { VChip, VChipGroup, VSelect, VTextField } from "vuetify/components";
import { useDebounced } from "../composables/useDebounced";
import { useStudyViews } from "../context";
import {
  COLLATOR,
  curatorsOf,
  plural,
  SEARCH_DELAY_MS,
  STATUS_CHIPS,
  substancesOf,
  type StatusChip,
} from "../overview";
import { findProfile } from "../study";

/**
 * The line above the study list: the heading Studies with the number of shown studies, the
 * search, the Substance and Curator filters and the status chips with their counts. The studies
 * are the rows of the page (`data.rows`); the page filters them with the models of this line
 * (`filterStudies`) and passes back the counts of the chips and the number of shown rows. The
 * search follows the field 150 ms after the last keystroke; `flushSearch` sets both at once.
 */
const props = defineProps<{
  /** The rows behind each status chip, within the search, the substance and the curator. */
  counts: Record<StatusChip, number>;
  /** The number of rows that the filters show. */
  shown: number;
  /** The user name of the reader, offered first as Me in the Curator filter; null without one. */
  me: string | null;
}>();
const search = defineModel<string>("search", { required: true });
const substance = defineModel<string>("substance", { required: true });
const curator = defineModel<string>("curator", { required: true });
const chip = defineModel<StatusChip>("chip", { required: true });

const views = useStudyViews();
const rows = views.data.rows;
const profiles = views.data.profiles;

/** The text of the search field; the filter follows it 150 ms after the last keystroke. */
const { text: searchText, flush: flushSearch } = useDebounced(search, SEARCH_DELAY_MS);

const substanceItems = computed(() => [
  { title: "All substances", value: "" },
  ...substancesOf(rows.value).map((name) => ({ title: name, value: name })),
]);
/** Every curator with the number of their studies; the reader comes first, as Me. */
const curatorItems = computed(() => {
  const name = (user: string) => findProfile(profiles.value, user)?.display_name ?? user;
  const me = props.me;
  const curators = curatorsOf(rows.value);
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
/** The digits of the number of studies: no chip count has more, and each keeps room for them. */
const countDigits = computed(() => String(rows.value.length).length);
const countText = computed(() => {
  const total = plural(rows.value.length, "study", "studies");
  if (props.shown === rows.value.length) return total;
  return `${props.shown.toLocaleString("en-US")} of ${total}`;
});
/** The longest text of the count, "N of N studies": its hidden copy keeps the width of the count. */
const countSizer = computed(
  () => `${rows.value.length.toLocaleString("en-US")} of ${plural(rows.value.length, "study", "studies")}`,
);

defineExpose({ flushSearch });
</script>

<template>
  <!-- The heading, the count and, with studies, the search, the selects and the status chips
       share one line where they fit; the chips come last, so they move to the next line first. -->
  <div class="overview-header">
    <div class="overview-heading">
      <h1>Studies</h1>
      <span v-if="rows.length" class="overview-count-box">
        <span class="overview-count">{{ countText }}</span>
        <span class="overview-count-sizer" aria-hidden="true">{{ countSizer }}</span>
      </span>
    </div>
    <template v-if="rows.length">
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
      <VSelect v-model="substance" :items="substanceItems" label="Substance" hide-details class="overview-substance" />
      <VSelect v-model="curator" :items="curatorItems" label="Curator" hide-details class="overview-curator" />
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
</template>

<style scoped>
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
</style>
