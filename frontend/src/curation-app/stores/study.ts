import { computed, ref, shallowRef, watch } from "vue";
import { defineStore } from "pinia";
import { getJson, postJson, studyPath } from "../api/client";
import {
  isCurators,
  isMetadataWrite,
  isReferenceCandidates,
  isReferencePreview,
  isReferenceRead,
  isReferenceSaved,
  isReviewWrite,
  isTablePreview,
  isTablesResult,
  type MetadataWrite,
  type ReferenceAuthor,
  type ReferencePreview,
  type ReferenceRecord,
  type ReviewWrite,
  type TablePreview,
  type TablesResult,
} from "../api/types";
import {
  isSourceView,
  isStudyDetail,
  isTableResponse,
  isTargetMatch,
  type Guard,
  type Profile,
  type ReviewTarget,
  type SourceView,
  type StudyDetail,
  type StudyMetadata,
  type TableFileKind,
  type TableResponse,
  type TargetMatch,
} from "../../study-views/types";
import { POLL_INTERVAL_MS, usePolling } from "../composables/usePolling";
import { useStudyDraft } from "../composables/useStudyDraft";
import { ALL_ROWS, type RowFilter } from "../../study-views/data";
import { profileMap } from "../../study-views/study";
import { lastWrite, reportAfter, type AcknowledgedMark } from "../acknowledging";

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
  // Aborts the table and source requests of the open study when it closes.
  let requests = new AbortController();
  let roster: Promise<Profile[]> | undefined;
  /** The profiles of the roster by user name once `curators` loaded it (`profileMap`); empty before. */
  const rosterProfiles = shallowRef<ReadonlyMap<string, Profile>>(new Map());
  /**
   * The warnings acknowledged in the app by study, until a report of a job queued after the
   * write arrives. They outlive the study page, so that the Problems section does not offer
   * them again while the validation that leaves them out has not run.
   */
  const acknowledging = ref<Record<string, AcknowledgedMark[]>>({});
  /** The result of the last sync of the open study from the app: Open tables, Sync or a resolved conflict. */
  const lastSync = shallowRef<TablesResult | null>(null);
  /** The filter of the rows of each shared table of the open study, by file, which the Data section keeps while the study is open. */
  const rowFilters = shallowRef<ReadonlyMap<string, RowFilter>>(new Map());
  /**
   * The draft of study.json of the open study, which the Metadata and Data sections edit and
   * save; `close` forgets it. Components read its values, such as `draft.dirty`, unwrapped.
   */
  const draft = useStudyDraft({ detail: () => polling.data.value, save: saveMetadata });

  // A report of a job queued after an acknowledgement ends its mark.
  watch(
    () => polling.data.value,
    (detail) => {
      const marks = detail ? acknowledging.value[detail.id] : undefined;
      if (!detail || !marks) return;
      const kept = marks.filter((mark) => !reportAfter(detail, mark));
      if (kept.length !== marks.length) acknowledging.value = { ...acknowledging.value, [detail.id]: kept };
    },
  );

  /**
   * Mark the warnings of the location `key` as acknowledged in the open study. Called after the
   * write, when the detail lists the write in the activity of the study.
   */
  function markAcknowledged(key: string): void {
    const detail = polling.data.value;
    if (!detail || detail.id !== identity.value) return;
    const mark: AcknowledgedMark = { key, since: lastWrite(detail.jobs), report: detail.report_id };
    acknowledging.value = { ...acknowledging.value, [detail.id]: [...(acknowledging.value[detail.id] ?? []), mark] };
  }

  /** The location keys of the warnings acknowledged in the app that no later report has checked yet. */
  const acknowledgedKeys = computed<string[]>(() => {
    const detail = polling.data.value;
    const marks = detail ? (acknowledging.value[detail.id] ?? []) : [];
    return detail ? marks.filter((mark) => !reportAfter(detail, mark)).map((mark) => mark.key) : [];
  });

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
    requests.abort();
    requests = new AbortController();
    identity.value = null;
    lastSync.value = null;
    draft.reset();
    rowFilters.value = new Map();
    tables.clear();
    sources.clear();
  }

  function refresh(): Promise<void> {
    return identity.value === null ? Promise.resolve() : polling.refresh();
  }

  /**
   * GET a route of the open study; it rejects with an AbortError (`isAbort`) when the study closes
   * first or `caller` aborts.
   */
  async function revalidated<T>(
    cache: Map<string, Cached<T>>,
    path: string,
    accept: Guard<T>,
    caller?: AbortSignal,
  ): Promise<T> {
    const signal = caller ? AbortSignal.any([requests.signal, caller]) : requests.signal;
    const cached = cache.get(path);
    const result = await getJson(path, accept, { etag: cached?.etag ?? null, signal });
    // An answer that arrives after the study closed or its caller left is neither cached nor returned.
    if (signal.aborted) throw new DOMException("The read was aborted", "AbortError");
    if (result.status === 200) {
      cache.set(path, { etag: result.etag, data: result.data });
      return result.data;
    }
    if (!cached) throw new Error(`Unexpected 304 for ${path}`);
    return cached.data;
  }

  /** The header and rows of a table, or the grid of a raw table, of the open study (see `revalidated`). */
  function table(file: string, signal?: AbortSignal): Promise<TableResponse> {
    return revalidated(tables, studyPath(opened(), "tables", file), isTableResponse, signal);
  }

  /** The source view of the open study: image, raw extraction, mapped rows and overlay (see `revalidated`). */
  function source(name: string, signal?: AbortSignal): Promise<SourceView> {
    return revalidated(sources, studyPath(opened(), "sources", name), isSourceView, signal);
  }

  /** The profiles of the bundled curator roster, loaded once. */
  function curators(): Promise<Profile[]> {
    roster ??= getJson("/local/curators", isCurators).then(
      (result) => {
        const list = result.status === 200 ? result.data.curators : [];
        rosterProfiles.value = profileMap(list);
        return list;
      },
      (error: unknown) => {
        roster = undefined;
        throw error;
      },
    );
    return roster;
  }

  /**
   * POST a write of the open study, then load the detail that it changed.
   *
   * The detail is loaded after a failure too, such as a stale revision or an unexpected answer
   * to a write that took effect. The caller receives the failure.
   */
  async function write<T>(path: string, body: Record<string, unknown>, accept: Guard<T>): Promise<T> {
    try {
      return await postJson(path, { ...body, study: opened() }, accept);
    } finally {
      await refresh();
    }
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

  /** Open the workbook, sync it, resolve its conflicts or add a sheet; all but `add` sync. */
  async function tablesAction(action: TablesAction, payload: Record<string, unknown> = {}): Promise<TablesResult> {
    const study = opened();
    const result = await write("/local/studies/tables", { ...payload, action }, isTablesResult);
    // Not for another study that opened meanwhile.
    if (action !== "add" && identity.value === study) lastSync.value = result;
    return result;
  }

  /** What Add table would add for `kind` and `source`, and why the server would refuse it; writes nothing. */
  function previewTable(kind: TableFileKind, source: string): Promise<TablePreview> {
    return postJson("/local/studies/tables/preview", { study: opened(), kind, source }, isTablePreview);
  }

  /** The rows and the digitized series that a draft review target selects; writes nothing. */
  function previewTarget(target: ReviewTarget): Promise<TargetMatch> {
    return postJson("/local/studies/review/preview", { study: opened(), target }, isTargetMatch);
  }

  /** `reference.json` of the open study; empty when there is none. */
  async function readReference(): Promise<ReferenceRecord> {
    return (await postJson("/local/reference/read", { id: opened() }, isReferenceRead)).reference;
  }

  /** Publications that match a citation, from Crossref. */
  async function searchReference(citation: string): Promise<ReferenceRecord[]> {
    return (await postJson("/local/reference/search", { id: opened(), citation }, isReferenceCandidates)).candidates;
  }

  /**
   * The reference that saving `input` would write; `input` holds the fields to correct.
   * `refetch` asks the providers again; `resetOverrides` drops the saved corrections.
   */
  function previewReference(
    input: Partial<Record<"title" | "journal" | "publication_date", string | null>> & { authors?: ReferenceAuthor[] },
    { refetch = false, resetOverrides = false }: { refetch?: boolean; resetOverrides?: boolean } = {},
  ): Promise<ReferencePreview> {
    return postJson(
      "/local/reference/preview",
      { id: opened(), input, refresh: refetch, reset_overrides: resetOverrides },
      isReferencePreview,
    );
  }

  /** Write the reference of the preview `token` to `reference.json`, then load the detail that it changed. */
  async function saveReference(token: string): Promise<void> {
    try {
      await postJson("/local/reference/save", { id: opened(), token }, isReferenceSaved);
    } finally {
      await refresh();
    }
  }

  /** The filter of the rows of the shared table `file`: All until the curator chooses another. */
  function rowFilter(file: string): RowFilter {
    return rowFilters.value.get(file) ?? ALL_ROWS;
  }

  function setRowFilter(file: string, filter: RowFilter): void {
    rowFilters.value = new Map(rowFilters.value).set(file, filter);
  }

  return {
    identity: computed(() => identity.value),
    detail: computed(() => polling.data.value),
    error: computed(() => polling.error.value),
    lastSync: computed(() => lastSync.value),
    draft,
    open,
    close,
    refresh,
    table,
    source,
    curators,
    profiles: computed(() => rosterProfiles.value),
    saveMetadata,
    reviewAction,
    tablesAction,
    previewTable,
    previewTarget,
    readReference,
    searchReference,
    previewReference,
    saveReference,
    markAcknowledged,
    acknowledgedKeys,
    rowFilter,
    setRowFilter,
  };
});
