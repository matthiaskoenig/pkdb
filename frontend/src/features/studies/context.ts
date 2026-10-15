/**
 * The study views on the website (#963): what the reader may see, from the audience that the
 * backend answers with; the routes of the study page, which keep the keys of the data search;
 * and the reads of a study page and of the Studies page. Each page provides them with
 * provideStudyViews in its setup.
 */
import { computed, shallowRef, toValue, watch, type MaybeRefOrGetter, type Ref } from "vue";
import type { LocationQuery, RouteLocationNormalizedLoaded } from "vue-router";
import type { StudyCapabilities, StudyViewData, StudyViewRoutes } from "../../study-views/context";
import { ALL_ROWS, type RowFilter } from "../../study-views/data";
import { COMPACT_DEFAULTS } from "../../study-views/density";
import { usePlotScaleChoice } from "../../study-views/plotScales";
import { isSection, profileMap, studyName } from "../../study-views/study";
import type { Profile, StudyDetail, StudyRow, TableKind } from "../../study-views/types";
import { SEARCH_QUERY_KEYS } from "../search/codec";
import { studyViewsApi, type Audience } from "./api";

/** The route of a study format 2 study, `/data/:substance/:name/:section?` (router/index.ts). */
export const STUDY_ROUTE = "StudyByName";
/** The route of the Studies page, `/studies`. */
export const STUDIES_ROUTE = "Studies";
/** The prefix of what the views keep in the storage of the browser on the website. */
export const STORAGE_PREFIX = "pkdb-website";
/** The class that gives the study pages of the website the sizes of the curation app (src/study-views/styles.css). */
export const STUDY_VIEWS_SCOPE = "website-study-views";
/**
 * The compact defaults of the curation app, and the scope on the menus and tooltips that the
 * views open: Vuetify teleports them out of the page, to the end of the document.
 */
export const WEBSITE_VIEW_DEFAULTS = {
  ...COMPACT_DEFAULTS,
  VMenu: { class: STUDY_VIEWS_SCOPE },
  VTooltip: { class: STUDY_VIEWS_SCOPE },
} as const;

/** What a reader sees of a study: the curation and its files who may write it, nothing of them everyone else. The website writes nothing and runs no jobs. */
export const AUDIENCE_CAPABILITIES: Record<Audience, StudyCapabilities> = {
  public: { edit: false, curation: false, files: false, jobs: false },
  curator: { edit: false, curation: true, files: true, jobs: false },
};

/**
 * What the Studies page shows: the columns and chips of the curation when the reader may write
 * any listed study (its other rows show "-" there), and no file.
 */
export function listCapabilities(rows: readonly StudyRow[]): StudyCapabilities {
  return { ...AUDIENCE_CAPABILITIES.public, curation: rows.some((row) => row.curator === true) };
}

const SEARCH_KEYS: ReadonlySet<string> = new Set(SEARCH_QUERY_KEYS);

/** The keys of the data search in `query`, which a study page opened from the search keeps. */
export function searchQuery(query: LocationQuery): LocationQuery {
  return Object.fromEntries(Object.entries(query).filter(([key]) => SEARCH_KEYS.has(key)));
}

/** Whether `query` holds a search, which the study page then offers to go back to. */
export function hasSearch(query: LocationQuery): boolean {
  return typeof query.v === "string";
}

function params(id: string): { substance: string; name: string } {
  return { substance: id.slice(0, id.indexOf("/")), name: studyName({ id }) };
}

/**
 * The routes of the views on the website: a study at `/data/<substance>/<name>/<section>`, with
 * the keys of the data search of `route` on every link and query, so that the search survives the
 * study page; no page of its own for a PDF.
 */
export function websiteRoutes(route: RouteLocationNormalizedLoaded): StudyViewRoutes {
  return {
    overview: () => ({ name: STUDIES_ROUTE }),
    study: (id) => ({ name: STUDY_ROUTE, params: params(id), query: searchQuery(route.query) }),
    section: (id, section, query = {}) => ({
      name: STUDY_ROUTE,
      params: { ...params(id), section },
      query: { ...searchQuery(route.query), ...query },
    }),
    paper: () => null,
    current(location) {
      if (location.name !== STUDY_ROUTE) return null;
      const { substance, name, section } = location.params;
      return { id: `${String(substance)}/${String(name)}`, section: isSection(section) ? section : null };
    },
    query: (current, own) => ({ ...searchQuery(current), ...own }),
  };
}

/** The folder of the files of PDF.js in the build of the website, at its root: not next to the study URL. */
export function pdfjsAssets(): string {
  return new URL(`${import.meta.env.BASE_URL}pdfjs/`, window.location.origin).href;
}

/** What the reads of a study page need of it: the study it shows and its loaded view. */
export interface StudyPage {
  id: MaybeRefOrGetter<string>;
  detail: Readonly<Ref<StudyDetail | null>>;
  error: Readonly<Ref<unknown>>;
}

/**
 * The roster of a study page, one answer for every view: none, as the views name the people of
 * the study by the profiles of its view (`knownProfiles(roster, detail.people)`).
 */
const NO_ROSTER: Promise<Profile[]> = Promise.resolve([]);

/**
 * The reads of a study page of the website. The row filters and the open notes belong to the shown
 * study and go with it, as when the curation app closes a study. Call it in `setup`.
 */
export function studyPageData(page: StudyPage): StudyViewData {
  const filters = shallowRef<ReadonlyMap<string, RowFilter>>(new Map());
  const notesOpen = shallowRef<ReadonlySet<TableKind>>(new Set());
  watch(
    () => toValue(page.id),
    () => {
      filters.value = new Map();
      notesOpen.value = new Set();
    },
  );
  return {
    detail: page.detail,
    error: page.error,
    table: (file, signal) => studyViewsApi.table(toValue(page.id), file, signal),
    source: (name, signal) => studyViewsApi.source(toValue(page.id), name, signal),
    curators: () => NO_ROSTER,
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
    validatesAfterWrite: shallowRef(false),
    plotScales: (study, view) => usePlotScaleChoice(study, view),
    rows: shallowRef<StudyRow[]>([]),
    profiles: shallowRef<ReadonlyMap<string, Profile>>(new Map()),
    repository: shallowRef(""),
    pdfjsAssets,
    checkFile: (url) => studyViewsApi.checkFile(url),
  };
}

/** What the reads of the Studies page need of it: the rows and the profiles of their people. */
export interface StudyList {
  rows: Readonly<Ref<StudyRow[]>>;
  profiles: Readonly<Ref<readonly Profile[]>>;
}

/** The reads of the Studies page: its rows and profiles; it shows no study. */
export function studyListData(list: StudyList): StudyViewData {
  const none = () => Promise.reject(new Error("The Studies page shows no study."));
  let roster: { from: readonly Profile[]; answer: Promise<Profile[]> } | null = null;
  return {
    detail: shallowRef<StudyDetail | null>(null),
    error: shallowRef<unknown>(null),
    table: none,
    source: none,
    curators() {
      const from = list.profiles.value;
      if (roster?.from !== from) roster = { from, answer: Promise.resolve([...from]) };
      return roster.answer;
    },
    acknowledgedKeys: shallowRef<readonly string[]>([]),
    rowFilter: () => ALL_ROWS,
    setRowFilter: () => undefined,
    notesOpen: shallowRef<ReadonlySet<TableKind>>(new Set()),
    setNotesOpen: () => undefined,
    validatesAfterWrite: shallowRef(false),
    plotScales: (study, view) => usePlotScaleChoice(study, view),
    rows: list.rows,
    profiles: computed(() => profileMap(list.profiles.value)),
    repository: shallowRef(""),
    pdfjsAssets,
    checkFile: (url) => studyViewsApi.checkFile(url),
  };
}
