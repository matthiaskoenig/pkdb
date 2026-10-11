import { ref } from "vue";
import { defineStore } from "pinia";
import type { StatusChip, StudySort } from "../overview";

const DEFAULT_SORT: StudySort = { key: "study", descending: false };

/**
 * The filters and the sort order of the overview. They last as long as the app, so that they stay
 * when the curator opens a study and returns, and start again in another workspace.
 */
export const useOverviewFilters = defineStore("curation-overview-filters", () => {
  const search = ref("");
  const substance = ref("");
  /** The user name of one curator, or "" for all. */
  const curator = ref("");
  const chip = ref<StatusChip>("all");
  const sort = ref<StudySort>({ ...DEFAULT_SORT });
  /** The workspace of the filters, or null before the first state arrived. */
  let workspace: string | null = null;

  /** Show every study again; the sort order stays. */
  function clear(): void {
    search.value = "";
    substance.value = "";
    curator.value = "";
    chip.value = "all";
  }

  /** Apply the filters to `path`: another workspace starts with the default filters and sort order. */
  function forWorkspace(path: string): void {
    if (workspace !== null && workspace !== path) {
      clear();
      sort.value = { ...DEFAULT_SORT };
    }
    workspace = path;
  }

  return { search, substance, curator, chip, sort, clear, forWorkspace };
});
