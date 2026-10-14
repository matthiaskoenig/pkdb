<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import { VSelect } from "vuetify/components";
import { useStudyViews } from "../../study-views/context";
import { plural } from "../../study-views/overview";
import { SECTION_LABELS, visibleSections, type Section } from "../../study-views/study";

const props = defineProps<{
  substance: string;
  name: string;
  /** The section on the screen; null before the study loaded. */
  active: Section | null;
  counts: Partial<Record<Section, number>>;
  /** The sections with unsaved changes. */
  unsaved: readonly Section[];
  /** The facts of the study at the end of the line, such as the last upload; a fact with `href` is a link. */
  facts?: { text: string; href?: string }[];
}>();

const router = useRouter();
// Below 600 px the tabs would not fit on one line: they become a select.
const { xs } = useDisplay();
const views = useStudyViews();
const study = computed(() => `${props.substance}/${props.name}`);

/** What a count means, for screen readers. */
const COUNT_NOUNS: Partial<Record<Section, [string, string]>> = {
  review: ["open item", "open items"],
  problems: ["problem", "problems"],
};

const items = computed(() =>
  visibleSections(views.capabilities.value).map((section) => {
    const count = props.counts[section];
    const nouns = COUNT_NOUNS[section];
    return {
      section,
      label: SECTION_LABELS[section],
      count,
      meaning: count === undefined || !nouns ? null : plural(count, nouns[0], nouns[1]),
      unsaved: props.unsaved.includes(section),
      to: views.routes.section(study.value, section),
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
  if (section) void router.push(views.routes.section(study.value, section));
}
</script>

<template>
  <div class="section-tabs-line" :class="{ 'section-tabs-line--select': xs }">
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
            <span class="section-tab-label" :data-label="item.label"
              >{{ item.label }}<span v-if="item.meaning" class="d-sr-only">, {{ item.meaning }}</span
              ><span v-if="item.unsaved" class="d-sr-only">, unsaved changes</span></span
            >
            <span v-if="item.unsaved" class="section-tab-unsaved" title="Unsaved changes" aria-hidden="true"></span>
            <span v-if="item.count !== undefined" class="section-tab-count" aria-hidden="true">{{ item.count }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
    <p v-if="facts?.length" class="section-tabs-facts">
      <template v-for="(fact, index) in facts" :key="fact.text">
        <span v-if="index > 0" aria-hidden="true"> · </span>
        <a v-if="fact.href" :href="fact.href" target="_blank" rel="noopener noreferrer">{{ fact.text }}</a>
        <span v-else>{{ fact.text }}</span>
      </template>
    </p>
  </div>
</template>

<style scoped>
/* The tabs and the facts of the study share the last line of the study band (StudyPage.vue),
   whose rule is below it; the facts wrap below the tabs in a narrow window, and stand below the
   select of the sections on a phone, 8 px above the rule. */
.section-tabs-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0 16px;
}
.section-tabs-line--select {
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
  padding-bottom: 8px;
}
/* The label of the select stands above its field, clear of the header. */
.section-tabs-select {
  margin-top: 8px;
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
/* Each label is as wide as its bold form, so that the tabs keep their places when the active one
   changes: a hidden bold copy of the label, without height, sets the width. */
.section-tab-label {
  display: inline-flex;
  flex-direction: column;
}
.section-tab-label::after {
  content: attr(data-label);
  height: 0;
  overflow: hidden;
  font-weight: 600;
  visibility: hidden;
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
.section-tabs-line--select .section-tabs-facts {
  margin-inline-start: 0;
}
</style>
