<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import { VSelect } from "vuetify/components";
import { plural } from "../overview";
import { SECTION_LABELS, SECTIONS, type Section } from "../study";

const props = defineProps<{
  substance: string;
  name: string;
  /** The section on the screen; null before the study loaded. */
  active: Section | null;
  counts: Partial<Record<Section, number>>;
  /** The sections with unsaved changes. */
  unsaved: readonly Section[];
  /** The facts of the study at the end of the line, such as "On save: Validate"; a fact with `href` is a link. */
  facts?: { text: string; href?: string }[];
}>();

const router = useRouter();
// Below 600 px the tabs would not fit on one line: they become a select.
const { xs } = useDisplay();

/** What a count means, for screen readers. */
const COUNT_NOUNS: Partial<Record<Section, [string, string]>> = {
  review: ["open item", "open items"],
  problems: ["problem", "problems"],
};

const items = computed(() =>
  SECTIONS.map((section) => {
    const count = props.counts[section];
    const nouns = COUNT_NOUNS[section];
    return {
      section,
      label: SECTION_LABELS[section],
      count,
      meaning: count === undefined || !nouns ? null : plural(count, nouns[0], nouns[1]),
      unsaved: props.unsaved.includes(section),
      to: { name: "Study", params: { substance: props.substance, name: props.name, section } },
    };
  }),
);

const selectItems = computed(() =>
  items.value.map(({ section, label, count, unsaved }) => ({
    title: `${count === undefined ? label : `${label} (${count})`}${unsaved ? ", unsaved changes" : ""}`,
    value: section,
  })),
);

function show(section: Section | null): void {
  if (section) void router.push({ name: "Study", params: { substance: props.substance, name: props.name, section } });
}
</script>

<template>
  <VSelect
    v-if="xs"
    :model-value="active"
    :items="selectItems"
    label="Section"
    hide-details
    density="compact"
    class="section-tabs-select"
    @update:model-value="show"
  />
  <nav v-else aria-label="Study sections" class="section-tabs">
    <ul class="section-tabs-list">
      <li v-for="item in items" :key="item.section">
        <RouterLink
          :to="item.to"
          class="section-tab"
          :class="{ 'section-tab--active': item.section === active }"
          :aria-current="item.section === active ? 'page' : undefined"
        >
          <!-- Screen readers hear what the count means, such as "Review, 1 open item". -->
          <span class="section-tab-label"
            >{{ item.label }}<span v-if="item.meaning" class="d-sr-only">, {{ item.meaning }}</span
            ><span v-if="item.unsaved" class="d-sr-only">, unsaved changes</span></span
          >
          <span v-if="item.unsaved" class="section-tab-unsaved" title="Unsaved changes" aria-hidden="true"></span>
          <span v-if="item.count !== undefined" class="section-tab-count" aria-hidden="true">{{ item.count }}</span>
        </RouterLink>
      </li>
    </ul>
    <p v-if="facts?.length" class="section-tabs-facts">
      <template v-for="(fact, index) in facts" :key="fact.text">
        <span v-if="index > 0" aria-hidden="true"> · </span>
        <a v-if="fact.href" :href="fact.href" target="_blank" rel="noopener noreferrer">{{ fact.text }}</a>
        <span v-else>{{ fact.text }}</span>
      </template>
    </p>
  </nav>
</template>

<style scoped>
.section-tabs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.section-tabs-list {
  display: flex;
  margin: 0;
  padding: 0;
  list-style: none;
}
.section-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  border-bottom: 2px solid transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 12.5px;
  text-decoration: none;
}
.section-tab:hover {
  background: rgba(var(--v-theme-on-surface), 0.06);
}
.section-tab--active,
.section-tab--active:hover {
  border-bottom-color: rgb(var(--v-theme-primary));
  font-weight: 600;
}
.section-tab:focus-visible {
  outline-offset: -3px;
}
/* A dot after the label marks unsaved changes, as an editor marks a changed file. */
.section-tab-unsaved {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
}
.section-tab-count {
  min-width: 16px;
  padding: 0 5px;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  font-size: 10.5px;
  font-weight: 600;
  line-height: 16px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.section-tabs-facts {
  margin: 0;
  margin-inline-start: auto;
  font-size: 11.5px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
