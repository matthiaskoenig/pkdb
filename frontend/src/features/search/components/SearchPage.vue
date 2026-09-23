<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDisplay } from "vuetify";
import { useSearchController } from "../useSearchController";
import { tabs, tabLabels } from "../model";
import { encodeLocation } from "../codec";
import { endpoints } from "../../../api/results";
import SearchPanel from "./SearchPanel.vue";
import QuerySummary from "./QuerySummary.vue";
import ResultsTable from "../../results/components/ResultsTable.vue";
import DetailPanel from "../../details/components/DetailPanel.vue";
import SearchExamples from "./SearchExamples.vue";
import { useSessionStore } from "../../../stores/session";
import type { Criteria, ResultTab } from "../model";
import {
  rememberResultPosition,
  restoreResultPosition,
  studyOriginKey,
  takeResultPosition,
} from "../../details/resultPosition";
const { search, submit, changeView, retry } = useSearchController(),
  router = useRouter(),
  route = useRoute(),
  session = useSessionStore(),
  { mdAndUp } = useDisplay();
const showFilters = ref(false),
  detail = ref<{ entity: string; identifier: string | number } | null>(null),
  tableDraft = ref(""),
  shareMessage = ref("");
let returnFocus: HTMLElement | null = null;
let restorationFrame: number | undefined,
  disposed = false;
const result = computed(() =>
  search.rows.status === "ready" ? search.rows.data : undefined,
);
const pending = computed(
  () =>
    search.rows.status === "loading" || search.selection.status === "loading",
);
watch(
  () => search.view.tableSearch,
  (value) => {
    tableDraft.value = value;
  },
  {immediate: true},
);
watch(
  () => search.selection.status,
  () => {
    if (search.selection.status !== "ready") detail.value = null;
  },
);
async function doSearch() {
  await submit();
  showFilters.value = false;
}
async function openDetail(identifier: string | number) {
  returnFocus =
    document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
  if (search.view.tab === "studies") {
    const origin = rememberResultPosition(route.fullPath, session.epoch);
    await router.push({
      path: `/data/${encodeURIComponent(String(identifier))}`,
      query: encodeLocation({ criteria: search.applied, view: search.view }),
      state: { [studyOriginKey]: { ...origin } },
    });
    return;
  }
  detail.value = { entity: endpoints[search.view.tab], identifier };
}
async function closeDetail() {
  detail.value = null;
  await nextTick();
  returnFocus?.focus();
}
function chooseExample(criteria: Criteria) {
  search.draft = criteria;
  showFilters.value = true;
  shareMessage.value =
    "Example loaded into the draft. Choose Search to apply it.";
}
async function moveTab(event: KeyboardEvent, tab: ResultTab) {
  if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const index = tabs.indexOf(tab),
    destination =
      event.key === "Home"
        ? tabs[0]
        : event.key === "End"
          ? tabs.at(-1)
          : tabs[
              (index + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) %
                tabs.length
            ];
  if (!destination) return;
  document.getElementById(`tab-${destination}`)?.focus();
  await changeView({ tab: destination });
}
watch(
  () => search.rows.status,
  async (status) => {
    if (status !== "ready") return;
    const position = takeResultPosition(route.fullPath, session.epoch);
    if (!position) return;
    await nextTick();
    if (disposed) return;
    restorationFrame = requestAnimationFrame(() => {
      if (
        !disposed &&
        position.epoch === session.epoch &&
        position.path === route.fullPath
      )
        restoreResultPosition(position);
    });
  },
);
onBeforeUnmount(() => {
  disposed = true;
  if (restorationFrame !== undefined) cancelAnimationFrame(restorationFrame);
});
async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href);
    shareMessage.value =
      "Search link copied. It shares criteria, not a frozen dataset or access permissions.";
  } catch {
    shareMessage.value =
      "Copy the address from your browser to share the applied search.";
  }
}
</script>
<template>
  <div class="research-page">
    <header class="page-heading">
      <div>
        <p class="eyebrow">Explore the evidence</p>
        <h1>Search pharmacokinetic data</h1>
        <p>
          Connect measurements with their subjects, interventions and source
          studies.
        </p>
      </div>
      <v-btn variant="outlined" @click="copyLink">Share applied search</v-btn>
    </header>
    <p v-if="shareMessage" role="status">{{ shareMessage }}</p>
    <SearchExamples @choose="chooseExample" />
    <v-alert v-if="search.urlError" type="error" role="alert" class="mb-4">
      {{ search.urlError
      }}<v-btn
        class="ml-2"
        @click="
          search.resetDraft();
          doSearch();
        "
      >
        Reset and search
      </v-btn>
    </v-alert>
    <div class="research-layout">
      <aside v-if="mdAndUp" class="filters">
        <SearchPanel @search="doSearch" />
      </aside>
      <v-dialog v-else v-model="showFilters" fullscreen scrollable>
        <template #activator="{ props }">
          <v-btn v-bind="props" color="primary" class="mobile-filters">
            Filters and Search
          </v-btn> </template
        ><v-card class="mobile-filter-card">
          <v-card-title class="filter-dialog-heading">
            <span>Research filters</span
            ><v-btn variant="text" @click="showFilters = false">
              Close filters
            </v-btn> </v-card-title
          ><v-card-text><SearchPanel @search="doSearch" /></v-card-text
          ><v-card-actions>
            <v-btn color="primary" @click="doSearch"> Apply search </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <section
        class="results-area"
        aria-label="Search results"
        :aria-busy="pending"
      >
        <QuerySummary />
        <v-alert v-if="search.notice" type="info" class="my-3" role="status">
          {{ search.notice }}
        </v-alert>
        <div class="result-tabs" role="tablist" aria-label="Result categories">
          <button
            v-for="tab in tabs"
            :id="`tab-${tab}`"
            :key="tab"
            type="button"
            role="tab"
            :tabindex="search.view.tab === tab ? 0 : -1"
            :aria-selected="search.view.tab === tab"
            aria-controls="result-panel"
            :class="{ active: search.view.tab === tab }"
            @keydown="moveTab($event, tab)"
            @click="changeView({ tab })"
          >
            {{ tabLabels[tab] }}
            <span class="count">{{
              search.selection.status === "ready"
                ? search.selection.data.counts[tab].toLocaleString()
                : "…"
            }}</span>
          </button>
        </div>
        <div
          id="result-panel"
          role="tabpanel"
          :aria-labelledby="`tab-${search.view.tab}`"
        >
          <div class="results-toolbar">
            <form
              class="table-search"
              @submit.prevent="changeView({ tableSearch: tableDraft })"
            >
              <v-text-field
                v-model="tableDraft"
                label="Search table"
                hide-details
                clearable
                @click:clear="tableDraft = ''"
              /><v-btn type="submit" variant="outlined">
                Apply table search
              </v-btn>
            </form>
          </div>
          <p class="muted">
            Table search refines this table only.
          </p>
          <p v-if="pending" role="status" class="result-state">
            Loading {{ tabLabels[search.view.tab].toLowerCase() }} for the
            applied query…
          </p>
          <div
            v-else-if="search.rows.status === 'error'"
            role="alert"
            class="result-state"
          >
            <h3>
              {{
                search.rows.code === 403
                  ? "Access is not permitted"
                  : search.rows.code === 401
                    ? "Sign in required"
                    : "Results could not be loaded"
              }}
            </h3>
            <p>{{ search.rows.message }}</p>
            <v-btn @click="retry">Retry</v-btn>
          </div>
          <template v-else-if="result">
            <p class="row-count" role="status">
              {{ result.count.toLocaleString() }}
              {{ tabLabels[search.view.tab].toLowerCase()
              }}{{
                search.view.tableSearch
                  ? " in this table refinement"
                  : " in the applied selection"
              }}
            </p>
            <div v-if="result.items.length === 0" class="result-state">
              <h3>No results for this selection</h3>
              <p>Adjust your draft filters, then choose Search.</p>
            </div>
            <ResultsTable
              v-else
              :tab="search.view.tab"
              :items="result.items"
              :order="search.view.order"
              :query="search.view.tableSearch"
              @order="changeView({ order: $event })"
              @detail="openDetail"
            />
            <nav class="pagination" aria-label="Result pagination">
              <v-btn
                variant="outlined"
                :disabled="result.page <= 1"
                @click="changeView({ page: result.page - 1 })"
              >
                Previous </v-btn
              ><span>Page {{ result.page }} of {{ result.lastPage }}</span
              ><v-btn
                variant="outlined"
                :disabled="result.page >= result.lastPage"
                @click="changeView({ page: result.page + 1 })"
              >
                Next </v-btn
              ><v-select
                :model-value="search.view.pageSize"
                :items="[20, 50, 100]"
                label="Rows per page"
                hide-details
                @update:model-value="changeView({ pageSize: $event })"
              />
            </nav>
          </template>
        </div>
      </section>
    </div>
    <v-dialog
      :model-value="detail !== null"
      max-width="1100"
      scrollable
      @update:model-value="
        (value) => {
          if (!value) closeDetail();
        }
      "
    >
      <v-card v-if="detail">
        <v-card-text>
          <DetailPanel
            :entity="detail.entity"
            :identifier="detail.identifier"
            @close="closeDetail"
          /> </v-card-text
        ><v-card-actions>
          <v-btn @click="closeDetail">Close details</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.filter-dialog-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}
</style>
