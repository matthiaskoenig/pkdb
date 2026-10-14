/**
 * What a page that shows a study with the shared study views gives them (#963): what the reader
 * may see and do (`capabilities`), where their links and the changes of their query go
 * (`routes`), where they read the study and the study list (`data`), and the parts that only one
 * app has (`parts`). The curation app provides it once for the app (its `studyViews.ts`); a page
 * of the website provides it for the study it shows. A component of the views reads it
 * with `useStudyViews()`: it never reads a store or names a route of either app.
 */
import {
  inject,
  provide,
  type App,
  type Component,
  type ComputedRef,
  type InjectionKey,
  type MaybeRefOrGetter,
  type Ref,
} from "vue";
import type { LocationQuery, LocationQueryRaw, RouteLocationNormalizedLoaded, RouteLocationRaw } from "vue-router";
import type { RowFilter } from "./data";
import type { PlotScales } from "./plotScales";
import type { Section } from "./study";
import type { Profile, SourceView, StudyDetail, StudyRow, TableResponse } from "./types";

/**
 * What the reader may see and do. A component hides what its reader may not, and renders no
 * disabled control for it. On the website they follow the audience of the loaded study, so they
 * are reactive.
 */
export interface StudyCapabilities {
  /** Writes and local actions: forms, save, sync, Open in the workbook, the folder or the PDF program, Validate, Upload, the actions of review items, Add table, the notes editor, kept plot scales. */
  edit: boolean;
  /** The curation of the study: Review, Problems, issue links, the review status and open items, the sync state, problem outlines and counts. */
  curation: boolean;
  /** The files of the study: its PDFs, the images of its sources and its raw tables. */
  files: boolean;
  /** The jobs of a local server: Activity, what a study is doing, the last upload. */
  jobs: boolean;
}

/** The study and the section that a route shows. */
export interface CurrentStudy {
  /** `<substance>/<name>`. */
  id: string;
  /** Null when the route names no section, as before the page chose one. */
  section: Section | null;
}

/** Where the links of the views go. */
export interface StudyViewRoutes {
  /** The list of studies. */
  overview(): RouteLocationRaw;
  /** A study, in the section that its page chooses. */
  study(id: string): RouteLocationRaw;
  /** A section of a study with the query of the section, such as `{ file, line }` of the Data section. */
  section(id: string, section: Section, query?: Record<string, string>): RouteLocationRaw;
  /** A PDF of a study in a page of its own; null when the app has no such page, which drops New tab. */
  paper(id: string, file: string): RouteLocationRaw | null;
  /** The study and the section of `route`; null for a route that shows no study. */
  current(route: RouteLocationNormalizedLoaded): CurrentStudy | null;
  /**
   * The query that a section replaces or pushes when it wants `own` in the address while the
   * route has `current`: the curation app returns `own`, the website keeps the keys of its
   * search too.
   */
  query(current: LocationQuery, own: LocationQueryRaw): LocationQueryRaw;
}

/** What the views read. Writes are no part of it: the components of the curation app write through its stores. */
export interface StudyViewData {
  /** The study that the page shows; null while it loads. */
  detail: Readonly<Ref<StudyDetail | null>>;
  /** Why the last load of the study failed; null while it loads well. */
  error: Readonly<Ref<unknown>>;
  /** The rows of a table, or the grid of a raw table, of the study. */
  table(file: string, signal?: AbortSignal): Promise<TableResponse>;
  /** The view of a source of the study: its image, raw extraction, mapped rows and plot. */
  source(name: string, signal?: AbortSignal): Promise<SourceView>;
  /**
   * The profiles of the curators that the page knows, such as the roster of the curation app.
   * Every view that names people calls it when it mounts, so the page loads them once and
   * answers every call with that answer.
   */
  curators(): Promise<Profile[]>;
  /** The location keys of the warnings acknowledged on this page that no later validation checked yet. */
  acknowledgedKeys: Readonly<Ref<readonly string[]>>;
  /** The filter of the rows of a shared table, which the page keeps while the study is open. */
  rowFilter(file: string): RowFilter;
  setRowFilter(file: string, filter: RowFilter): void;
  /** Whether the server validates the study by itself after a write. */
  validatesAfterWrite: Readonly<Ref<boolean>>;
  /** The scales of the plot of a source and the choice of the reader; call it in `setup`. */
  plotScales(study: MaybeRefOrGetter<string>, view: MaybeRefOrGetter<SourceView | null>): PlotScales;
  /** The rows of the study list. */
  rows: Readonly<Ref<StudyRow[]>>;
  /** The profiles of the study list by user name, matched without case (`profileMap`). */
  profiles: Readonly<Ref<ReadonlyMap<string, Profile>>>;
  /** The GitHub repository of the issues, `<owner>/<name>`; empty without one. */
  repository: Readonly<Ref<string>>;
  /** The URL of the folder of the files of PDF.js, ending with `/`. */
  pdfjsAssets(): string;
  /** Resolves when the server serves the file at `url`; rejects with its `ApiError` or `SessionMissing` otherwise. */
  checkFile(url: string): Promise<void>;
}

/** The components that only one app has, which the views render where they are given. */
export interface StudyViewParts {
  /** The details of a failure below its alert, with the props `text` and `details` and a default slot for links; null shows none. */
  failureDetails: Component | null;
}

export interface StudyViewsContext {
  capabilities: ComputedRef<StudyCapabilities>;
  routes: StudyViewRoutes;
  data: StudyViewData;
  parts: StudyViewParts;
}

export const STUDY_VIEWS: InjectionKey<StudyViewsContext> = Symbol("study-views");

/** Give the views below the calling component, or below every component of `app`, their context. */
export function provideStudyViews(context: StudyViewsContext, app?: App): void {
  if (app) app.provide(STUDY_VIEWS, context);
  else provide(STUDY_VIEWS, context);
}

/** The context of the nearest page, or of the app, that provides it. */
export function useStudyViews(): StudyViewsContext {
  const context = inject(STUDY_VIEWS, null);
  if (context === null)
    throw new Error("The study views need a context: call provideStudyViews() in their page or app.");
  return context;
}
