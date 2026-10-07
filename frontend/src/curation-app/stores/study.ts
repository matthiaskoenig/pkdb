import { ref } from "vue";
import { defineStore } from "pinia";
import { getJson, postJson, studyPath } from "../api/client";
import {
  isCurators,
  isMetadataWrite,
  isReviewWrite,
  isSourceView,
  isStudyDetail,
  isTableResponse,
  isTablesResult,
  type Guard,
  type MetadataWrite,
  type Profile,
  type ReviewWrite,
  type SourceView,
  type StudyDetail,
  type StudyMetadata,
  type TableResponse,
  type TablesResult,
} from "../api/types";
import { POLL_INTERVAL_MS, usePolling } from "../composables/usePolling";

export type ReviewAction = "add" | "reply" | "resolve" | "dismiss" | "reopen" | "status" | "acknowledge";

export type TablesAction = "open" | "sync" | "resolve" | "add";

/** The last response of a route, revalidated with its ETag. */
interface Cached<T> {
  etag: string | null;
  data: T;
}

/** The study that the study page shows, polled while it is open. */
export const useStudyStore = defineStore("curation-study", () => {
  const identity = ref<string | null>(null);
  const polling = usePolling<StudyDetail>(
    (etag, signal) => getJson(studyPath(opened()), isStudyDetail, { etag, signal }),
    POLL_INTERVAL_MS,
    { immediate: false },
  );
  const tables = new Map<string, Cached<TableResponse>>();
  const sources = new Map<string, Cached<SourceView>>();
  let roster: Promise<Profile[]> | undefined;

  function opened(): string {
    if (identity.value === null) throw new Error("No study is open");
    return identity.value;
  }

  /** Show the study `<substance>/<name>` and poll its detail; resolves after the first load. */
  function open(substance: string, name: string): Promise<void> {
    const next = `${substance}/${name}`;
    if (identity.value !== next) {
      close();
      identity.value = next;
    }
    return polling.start();
  }

  function close(): void {
    polling.reset();
    identity.value = null;
    tables.clear();
    sources.clear();
  }

  function refresh(): Promise<void> {
    return identity.value === null ? Promise.resolve() : polling.refresh();
  }

  async function revalidated<T>(cache: Map<string, Cached<T>>, path: string, accept: Guard<T>): Promise<T> {
    const cached = cache.get(path);
    const result = await getJson(path, accept, { etag: cached?.etag ?? null });
    if (result.status === 200) {
      cache.set(path, { etag: result.etag, data: result.data });
      return result.data;
    }
    if (!cached) throw new Error(`Unexpected 304 for ${path}`);
    return cached.data;
  }

  /** The header and rows of a table, or the grid of a raw table, of the open study. */
  function table(file: string): Promise<TableResponse> {
    return revalidated(tables, studyPath(opened(), "tables", file), isTableResponse);
  }

  /** The source view of the open study: image, raw extraction, mapped rows and overlay. */
  function source(name: string): Promise<SourceView> {
    return revalidated(sources, studyPath(opened(), "sources", name), isSourceView);
  }

  /** The profiles of the bundled curator roster, loaded once. */
  function curators(): Promise<Profile[]> {
    roster ??= getJson("/local/curators", isCurators).then(
      (result) => (result.status === 200 ? result.data.curators : []),
      (error: unknown) => {
        roster = undefined;
        throw error;
      },
    );
    return roster;
  }

  /** POST a write of the open study, then load the detail that it changed. */
  async function write<T>(path: string, body: Record<string, unknown>, accept: Guard<T>): Promise<T> {
    const result = await postJson(path, { ...body, study: opened() }, accept);
    await polling.refresh();
    return result;
  }

  /** Write `study.json` over the revision that was read; a stale revision is a revision conflict. */
  function saveMetadata(revision: string, metadata: StudyMetadata): Promise<MetadataWrite> {
    return write("/local/studies/metadata", { revision, metadata }, isMetadataWrite);
  }

  /** Change `review.json` over the revision that was read. */
  function reviewAction(
    revision: string,
    action: ReviewAction,
    payload: Record<string, unknown> = {},
  ): Promise<ReviewWrite> {
    return write("/local/studies/review", { ...payload, revision, action }, isReviewWrite);
  }

  /** Open the workbook, sync it, resolve its conflicts or add a sheet. */
  function tablesAction(action: TablesAction, payload: Record<string, unknown> = {}): Promise<TablesResult> {
    return write("/local/studies/tables", { ...payload, action }, isTablesResult);
  }

  return {
    identity,
    detail: polling.data,
    error: polling.error,
    open,
    close,
    refresh,
    table,
    source,
    curators,
    saveMetadata,
    reviewAction,
    tablesAction,
  };
});
