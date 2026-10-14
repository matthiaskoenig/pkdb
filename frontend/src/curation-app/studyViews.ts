/**
 * The study views in the curation app (#963): every capability, the routes of its hash router
 * (routes.ts), the reads of its stores and the details of a failure of the local server. The
 * stores are looked up when a view reads, so that the plugin can be installed before Pinia is
 * active: `tests/setup.ts` installs it for every component test.
 */
import { computed, type Plugin } from "vue";
import {
  provideStudyViews,
  type StudyCapabilities,
  type StudyViewData,
  type StudyViewsContext,
} from "../study-views/context";
import { validatesAfterWrite } from "./acknowledging";
import { checkFile } from "./api/client";
import FailureDetails from "./components/FailureDetails.vue";
import { usePlotScales } from "./composables/usePlotScales";
import { curationRoutes } from "./routes";
import { useOverviewStore } from "./stores/overview";
import { useStudyStore } from "./stores/study";

/** The curation app shows and does everything: it works on the curator's own copy of a study. */
const EVERYTHING: StudyCapabilities = { edit: true, curation: true, files: true, jobs: true };

/** The reads of the study views from the store of the open study and the state of the local server. */
export function curationStudyData(): StudyViewData {
  return {
    detail: computed(() => useStudyStore().detail),
    error: computed(() => useStudyStore().error),
    table: (file) => useStudyStore().table(file),
    source: (name) => useStudyStore().source(name),
    curators: () => useStudyStore().curators(),
    acknowledgedKeys: computed(() => useStudyStore().acknowledgedKeys),
    rowFilter: (file) => useStudyStore().rowFilter(file),
    setRowFilter: (file, filter) => useStudyStore().setRowFilter(file, filter),
    validatesAfterWrite: computed(() => validatesAfterWrite(useOverviewStore().snapshot ?? null)),
    plotScales: (study, view) => usePlotScales(study, view),
    rows: computed(() => useOverviewStore().snapshot?.studies ?? []),
    profiles: computed(() => useStudyStore().profiles),
    repository: computed(() => useOverviewStore().snapshot?.github.repository ?? ""),
    pdfjsAssets: () => new URL("pdfjs/", document.baseURI).href,
    checkFile,
  };
}

export function curationStudyViews(): StudyViewsContext {
  return {
    capabilities: computed(() => EVERYTHING),
    routes: curationRoutes,
    data: curationStudyData(),
    parts: { failureDetails: FailureDetails },
  };
}

/** Provides the study views of the curation app to every component of the app. */
export const studyViewsPlugin: Plugin = {
  install(app) {
    provideStudyViews(curationStudyViews(), app);
  },
};
