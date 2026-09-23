import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { isAxiosError } from "axios";
import { createSelection } from "../api/search";
import type { Selection } from "../api/search";
import { fetchRows } from "../api/results";
import type { ResultPage } from "../api/contracts";
import { errorMessage } from "../api/client";
import { isRecord } from "../api/errors";
import {
  defaultCriteria,
  defaultView,
  cloneCriteria,
} from "../features/search/defaults";
import { canonicalCriteria, criteriaKey } from "../features/search/codec";
import type { SearchLocation } from "../features/search/model";
type State<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string; code: number | undefined };
export const useSearchStore = defineStore("search", () => {
  const draft = ref(defaultCriteria()),
    applied = ref(defaultCriteria()),
    view = ref(defaultView());
  const selection = ref<State<Selection>>({ status: "idle" }),
    rows = ref<State<ResultPage>>({ status: "idle" });
  const notice = ref(""),
    urlError = ref("");
  const dirty = computed(() => {
    // Draft controls can contain invalid, unfinished input. Validate on Search,
    // while keeping rendering and reset usable during editing.
    try {
      return criteriaKey(draft.value) !== criteriaKey(applied.value);
    } catch {
      return true;
    }
  });
  let generation = 0,
    controller: AbortController | undefined,
    selectionIdentity = "",
    activeKey = "",
    inFlight = false;
  function invalidate() {
    generation++;
    controller?.abort();
    selection.value = { status: "idle" };
    rows.value = { status: "idle" };
    selectionIdentity = "";
    activeKey = "";
    inFlight = false;
  }
  function resetDraft() {
    draft.value = defaultCriteria();
    urlError.value = "";
  }
  function rejectUrl(message: string) {
    invalidate();
    urlError.value = message;
  }
  // Only an explicitly initiated result-view transition/retry preserves the draft.
  // Route restoration (including Back/Forward) always replaces it.
  async function load(
    location: SearchLocation,
    epoch: number,
    force = false,
    preserveDraft = false,
  ): Promise<number | undefined> {
    const criteria = canonicalCriteria(location.criteria),
      key = criteriaKey(criteria);
    const identity = `${epoch}:${key}`,
      requestKey = JSON.stringify([identity, location.view]);
    if (!preserveDraft || criteriaKey(applied.value) !== key)
      draft.value = cloneCriteria(criteria);
    if (!force && inFlight && activeKey === requestKey) return;
    const reuse =
      !force &&
      selectionIdentity === identity &&
      selection.value.status === "ready"
        ? selection.value.data
        : undefined;
    const own = ++generation;
    controller?.abort();
    const abort = new AbortController();
    controller = abort;
    activeKey = requestKey;
    inFlight = true;
    applied.value = cloneCriteria(criteria);
    view.value = { ...location.view };
    urlError.value = "";
    notice.value = "";
    rows.value = { status: "loading" };
    if (!reuse) selection.value = { status: "loading" };
    const current = () => generation === own && !abort.signal.aborted;
    try {
      let selected = reuse ?? (await createSelection(criteria, abort.signal));
      if (!current()) return;
      selection.value = { status: "ready", data: selected };
      selectionIdentity = identity;
      let recreated = false;
      while (current()) {
        try {
          const page = await fetchRows(
            selected.uuid,
            location.view,
            abort.signal,
          );
          if (current()) rows.value = { status: "ready", data: page };
          return;
        } catch (error) {
          if (!current()) return;
          const data: unknown = isAxiosError(error)
            ? error.response?.data
            : undefined;
          const detail = isRecord(data) ? data.detail : undefined;
          const missing = isAxiosError(error) && error.response?.status === 404;
          if (missing && detail === "Saved filter unavailable" && !recreated) {
            recreated = true;
            selection.value = { status: "loading" };
            selectionIdentity = "";
            selected = await createSelection(criteria, abort.signal);
            if (!current()) return;
            selection.value = { status: "ready", data: selected };
            selectionIdentity = identity;
            notice.value =
              "The search selection expired. Results were refreshed using your applied criteria.";
          } else if (
            missing &&
            detail === "Invalid page" &&
            location.view.page > 1
          ) {
            notice.value =
              "The data changed and this page is no longer available. Returned to page 1.";
            return 1;
          } else throw error;
        }
      }
    } catch (error) {
      if (current()) {
        const code = isAxiosError(error) ? error.response?.status : undefined;
        const state = {
          status: "error" as const,
          message: errorMessage(error),
          code,
        };
        const data: unknown = isAxiosError(error)
          ? error.response?.data
          : undefined;
        const expired =
          code === 404 &&
          isRecord(data) &&
          data.detail === "Saved filter unavailable";
        if (
          selection.value.status === "loading" ||
          code === 401 ||
          code === 403 ||
          expired
        ) {
          selection.value = state;
          selectionIdentity = "";
        }
        rows.value = state;
      }
    } finally {
      if (current()) inFlight = false;
    }
  }
  return {
    draft,
    applied,
    view,
    selection,
    rows,
    notice,
    urlError,
    dirty,
    resetDraft,
    invalidate,
    rejectUrl,
    load,
  };
});
