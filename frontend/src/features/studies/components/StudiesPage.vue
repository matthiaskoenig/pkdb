<script setup lang="ts">
import "../../../study-views/styles.css";
import { computed, useTemplateRef, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { VBtn, VDefaultsProvider, VProgressLinear } from "vuetify/components";
import ActionFailureAlert from "../../../study-views/components/ActionFailureAlert.vue";
import StudyFilters from "../../../study-views/components/StudyFilters.vue";
import StudyTable from "../../../study-views/components/StudyTable.vue";
import { provideStudyViews } from "../../../study-views/context";
import { COMPACT_DEFAULTS } from "../../../study-views/density";
import { filterStudies, sortStudies, type StatusChip, type StudySort } from "../../../study-views/overview";
import { failureOf } from "../../../study-views/study";
import { useSessionStore } from "../../../stores/session";
import { useStudyListStore } from "../../../stores/studyList";
import { listCapabilities, STORAGE_PREFIX, studyListData, websiteRoutes } from "../context";
import { listQuery, readListQuery, sameQuery, type ListState } from "../listQuery";
import { useWebsiteStudyRows } from "../useWebsiteStudy";

/**
 * The Studies page of the website (#963): the study format 2 studies with a stored view that the
 * reader may read, in the study list of the curation app with its search, Substance and Curator
 * filters. A reader who may write any of them also sees the columns and status chips of the
 * curation. The filters and the order live in the address (listQuery.ts).
 */
const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const remembered = useStudyListStore();
const list = useWebsiteStudyRows();
const { rows, status } = list;
const capabilities = computed(() => listCapabilities(rows.value));
provideStudyViews({
  capabilities,
  routes: websiteRoutes(route),
  data: studyListData({ rows, profiles: list.profiles }),
  parts: { failureDetails: null },
  storagePrefix: STORAGE_PREFIX,
});

const state = computed(() => readListQuery(route.query, capabilities.value));

function update(change: Partial<ListState>): void {
  void router.replace({ query: listQuery({ ...state.value, ...change }) });
}

// Once the rows tell what the reader sees, an address that names more becomes the one it shows.
watch(
  [status, state],
  ([current, value]) => {
    if (current !== "ready") return;
    const query = listQuery(value);
    remembered.query = query;
    if (!sameQuery(route.query, query)) void router.replace({ query });
  },
  { immediate: true },
);

const search = computed({ get: () => state.value.search, set: (value: string) => update({ search: value }) });
const substance = computed({ get: () => state.value.substance, set: (value: string) => update({ substance: value }) });
const curator = computed({ get: () => state.value.curator, set: (value: string) => update({ curator: value }) });
const chip = computed({ get: () => state.value.chip, set: (value: StatusChip) => update({ chip: value }) });
const sort = computed({ get: () => state.value.sort, set: (value: StudySort) => update({ sort: value }) });

const filtered = computed(() =>
  filterStudies(
    rows.value,
    { search: search.value, substance: substance.value, curator: curator.value, chip: chip.value },
    capabilities.value,
  ),
);
const shown = computed(() => sortStudies(filtered.value.shown, sort.value));

const filterLine = useTemplateRef<InstanceType<typeof StudyFilters>>("filterLine");
function clearFilters(): void {
  filterLine.value?.flushSearch("");
  update({ search: "", substance: "", curator: "", chip: "all" });
}

const failure = computed(() => (list.error.value ? failureOf(list.error.value, "The studies could not be loaded.") : null));
</script>

<template>
  <div class="website-studies">
    <VDefaultsProvider :defaults="COMPACT_DEFAULTS">
      <StudyFilters
        ref="filterLine"
        v-model:search="search"
        v-model:substance="substance"
        v-model:curator="curator"
        v-model:chip="chip"
        :counts="filtered.counts"
        :shown="shown.length"
        :me="session.profile?.username ?? null"
      />
      <ActionFailureAlert v-if="failure" :failure="failure" :closable="false">
        <template #append>
          <VBtn variant="tonal" color="primary" @click="list.reload()">Retry</VBtn>
        </template>
      </ActionFailureAlert>
      <template v-if="status === 'ready'">
        <section v-if="rows.length" class="studies-panel" aria-label="Studies">
          <StudyTable v-if="shown.length" v-model:sort="sort" :rows="shown" caption="Studies of PK-DB" />
          <div v-else class="studies-empty">
            <p>No studies match these filters.</p>
            <VBtn variant="tonal" color="primary" @click="clearFilters">Clear filters</VBtn>
          </div>
        </section>
        <p v-else class="studies-none">
          No studies are listed yet. <RouterLink to="/data">Explore data</RouterLink> searches all studies.
        </p>
      </template>
      <div v-else-if="status === 'loading'" class="studies-loading">
        <VProgressLinear indeterminate color="primary" aria-label="Loading the studies" />
      </div>
    </VDefaultsProvider>
  </div>
</template>

<style scoped>
.website-studies {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.studies-panel {
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
}
.studies-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 24px 16px;
}
.studies-empty p,
.studies-none {
  margin: 0;
}
.studies-loading {
  max-width: 24rem;
}
</style>
