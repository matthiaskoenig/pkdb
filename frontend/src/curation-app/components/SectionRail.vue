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
}>();

const router = useRouter();
// Below 600 px the rail would take the room of the section: it becomes a select.
const { xs } = useDisplay();

/** What a count means, for screen readers. */
const COUNT_NOUNS: Partial<Record<Section, [string, string]>> = {
  review: ["open item", "open items"],
  problems: ["problem", "problems"],
  sources: ["source", "sources"],
  tables: ["table", "tables"],
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
      to: { name: "Study", params: { substance: props.substance, name: props.name, section } },
    };
  }),
);

const selectItems = computed(() =>
  items.value.map(({ section, label, count }) => ({
    title: count === undefined ? label : `${label} (${count})`,
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
    class="rail-select"
    @update:model-value="show"
  />
  <nav v-else aria-label="Study sections" class="rail">
    <ul class="rail-list">
      <li v-for="item in items" :key="item.section">
        <RouterLink
          :to="item.to"
          class="rail-link"
          :class="{ 'rail-link--active': item.section === active }"
          :aria-current="item.section === active ? 'page' : undefined"
        >
          <!-- Screen readers hear what the count means, such as "Review, 1 open item". -->
          <span class="rail-label"
            >{{ item.label }}<span v-if="item.meaning" class="d-sr-only">, {{ item.meaning }}</span></span
          >
          <span v-if="item.count !== undefined" class="rail-count" aria-hidden="true">{{ item.count }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.rail-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.rail-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 8px;
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.9375rem;
  text-decoration: none;
}
.rail-link:hover {
  background: rgba(var(--v-theme-on-surface), 0.06);
}
.rail-link--active,
.rail-link--active:hover {
  background: rgba(var(--v-theme-primary), 0.12);
  font-weight: 600;
}
/* The focus ring stays inside the column of the rail. */
.rail-link:focus-visible {
  outline-offset: -3px;
}
.rail-count {
  min-width: 24px;
  padding: 0 6px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 20px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
</style>
