/**
 * Mount the shared study views as a page of the website or of the curation app shows them: below
 * a component that provides their context, with the capabilities, routes and reads of the test.
 * A context provided this way wins over the curation app's, which tests/setup.ts installs.
 */
import { mount, type VueWrapper } from "@vue/test-utils";
import { computed, defineComponent, h, shallowRef, type Component, type Plugin } from "vue";
import { createMemoryHistory, createRouter, type Router } from "vue-router";
import {
  provideStudyViews,
  type StudyCapabilities,
  type StudyViewData,
  type StudyViewParts,
  type StudyViewRoutes,
  type StudyViewsContext,
} from "../../src/study-views/context";
import { ALL_ROWS, type RowFilter } from "../../src/study-views/data";
import { usePlotScaleChoice } from "../../src/study-views/plotScales";
import { isSection, profileMap, studyName } from "../../src/study-views/study";
import type { Profile, SourceView, StudyDetail, StudyRow, TableKind, TableResponse } from "../../src/study-views/types";

export const EVERYTHING: StudyCapabilities = { edit: true, curation: true, files: true, jobs: true };
/** What a reader of the website sees of a study that they may not write. */
export const PUBLIC: StudyCapabilities = { edit: false, curation: false, files: false, jobs: false };
/** What a reader of the website who may write the study sees. */
export const CURATOR: StudyCapabilities = { edit: false, curation: true, files: true, jobs: false };

/** The keys of the search of the website, which its study page keeps in its query (features/search/codec.ts). */
export const SEARCH_KEYS = ["v", "q", "scope", "tab", "page", "pageSize", "order", "tableSearch"];

/** Routes as the website has them: a study at `/data/<substance>/<name>/<section>` and no page of its own for a PDF. */
export function websiteRoutes(): StudyViewRoutes {
  const params = (id: string) => ({ substance: id.slice(0, id.indexOf("/")), name: studyName({ id }) });
  return {
    overview: () => ({ name: "WebStudies" }),
    study: (id) => ({ name: "WebStudy", params: params(id) }),
    section: (id, section, query = {}) => ({ name: "WebStudy", params: { ...params(id), section }, query }),
    paper: () => null,
    current(route) {
      if (route.name !== "WebStudy") return null;
      const { substance, name, section } = route.params;
      return { id: `${String(substance)}/${String(name)}`, section: isSection(section) ? section : null };
    },
    query: (current, own) => ({
      ...Object.fromEntries(Object.entries(current).filter(([key]) => SEARCH_KEYS.includes(key))),
      ...own,
    }),
  };
}

/** The page of a route of `websiteRouter`, which renders nothing. */
const Blank: Component = { render: () => null };

/** A router in memory with the routes of `websiteRoutes`. */
export function websiteRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/studies", name: "WebStudies", component: Blank },
      { path: "/data/:substance/:name/:section?", name: "WebStudy", component: Blank },
    ],
  });
}

export interface MemoryOptions {
  detail?: StudyDetail | null;
  tables?: Record<string, TableResponse>;
  sources?: Record<string, SourceView>;
  rows?: StudyRow[];
  profiles?: Profile[];
  repository?: string;
}

/** The reads of a page that holds everything in memory; a table or source that it lacks fails to load. */
export function memoryData(options: MemoryOptions = {}): StudyViewData {
  const filters = shallowRef<ReadonlyMap<string, RowFilter>>(new Map());
  const notesOpen = shallowRef<ReadonlySet<TableKind>>(new Set());
  const missing = (name: string) => Promise.reject(new Error(`${name} could not be loaded.`));
  // Loaded once, as every page answers the views that call it when they mount.
  const curators = Promise.resolve(options.profiles ?? []);
  return {
    detail: shallowRef(options.detail ?? null),
    error: shallowRef<unknown>(null),
    table(file) {
      const table = options.tables?.[file];
      return table ? Promise.resolve(table) : missing(file);
    },
    source(name) {
      const source = options.sources?.[name];
      return source ? Promise.resolve(source) : missing(name);
    },
    curators: () => curators,
    acknowledgedKeys: shallowRef<readonly string[]>([]),
    rowFilter: (file) => filters.value.get(file) ?? ALL_ROWS,
    setRowFilter(file, filter) {
      filters.value = new Map(filters.value).set(file, filter);
    },
    notesOpen,
    setNotesOpen(kind, open) {
      const next = new Set(notesOpen.value);
      if (open) next.add(kind);
      else next.delete(kind);
      notesOpen.value = next;
    },
    validatesAfterWrite: shallowRef(true),
    plotScales: (study, view) => usePlotScaleChoice(study, view),
    rows: shallowRef(options.rows ?? []),
    profiles: shallowRef(profileMap(options.profiles ?? [])),
    repository: shallowRef(options.repository ?? ""),
    pdfjsAssets: () => "https://pk-db.example/pdfjs/",
    checkFile: () => Promise.resolve(),
  };
}

/** A context with everything allowed, the routes of the website and empty reads, with `changes`. */
export function viewsContext(
  changes: {
    capabilities?: StudyCapabilities;
    routes?: StudyViewRoutes;
    data?: StudyViewData;
    parts?: StudyViewParts;
    storagePrefix?: string;
  } = {},
): StudyViewsContext {
  const capabilities = changes.capabilities ?? EVERYTHING;
  return {
    capabilities: computed(() => capabilities),
    routes: changes.routes ?? websiteRoutes(),
    data: changes.data ?? memoryData(),
    parts: changes.parts ?? { failureDetails: null },
    storagePrefix: changes.storagePrefix ?? "pkdb-test",
  };
}

export interface MountOptions {
  context: StudyViewsContext;
  props?: Record<string, unknown>;
  slots?: Record<string, (props: Record<string, unknown>) => unknown>;
  plugins?: Plugin[];
  stubs?: Record<string, Component | boolean>;
  attachTo?: Element;
}

/** Mount `component` with `props` and `slots` below a page that provides `context`. */
export function mountViews(component: Component, options: MountOptions): VueWrapper {
  const { context, props = {}, slots = {}, plugins = [], stubs = {}, attachTo } = options;
  const Page = defineComponent({
    name: "StudyViewsPage",
    setup() {
      provideStudyViews(context);
      return () => h(component, props, slots);
    },
  });
  return mount(Page, { ...(attachTo ? { attachTo } : {}), global: { plugins, stubs } });
}
