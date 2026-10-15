/**
 * Loading the views of the website (#963): the view of a study and the rows of the Studies page.
 * Both read again when the session changes (`epoch` of the session store: sign-in, sign-out, a
 * role change, the first profile load, a 401 that ended the session), keeping what they show until
 * the new answer comes, since the backend decides by the session what the reader sees.
 */
import { computed, onScopeDispose, shallowRef, toValue, watch, type MaybeRefOrGetter } from "vue";
import { useSessionStore } from "../../stores/session";
import { ApiError, isAbort } from "../../study-views/errors";
import type { Profile, StudyDetail, StudyRow } from "../../study-views/types";
import { studyViewsApi, type Audience } from "./api";

/** Whether the server has no view of the study for the reader: a study without stored views, or one that the reader may not read. */
export function isMissing(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

export function useWebsiteStudy(id: MaybeRefOrGetter<string>) {
  const session = useSessionStore();
  const detail = shallowRef<StudyDetail | null>(null);
  const audience = shallowRef<Audience | null>(null);
  const error = shallowRef<unknown>(null);
  let controller: AbortController | null = null;

  /** Read the view; `keep` shows the current one, or the current error, until the answer comes. */
  async function load(keep: boolean): Promise<void> {
    controller?.abort();
    const own = new AbortController();
    controller = own;
    if (!keep) {
      detail.value = null;
      audience.value = null;
      error.value = null;
    }
    try {
      const answer = await studyViewsApi.study(toValue(id), own.signal);
      if (own.signal.aborted) return;
      detail.value = answer.detail;
      audience.value = answer.audience;
      error.value = null;
    } catch (caught) {
      if (own.signal.aborted || isAbort(caught)) return;
      error.value = caught;
      // A study without a view, or one that the reader can no longer read, shows nothing of it.
      if (isMissing(caught)) {
        detail.value = null;
        audience.value = null;
      }
    }
  }

  watch(() => toValue(id), () => void load(false), { immediate: true });
  watch(() => session.epoch, () => void load(true));
  onScopeDispose(() => controller?.abort());

  return {
    detail,
    audience,
    error,
    missing: computed(() => isMissing(error.value)),
    reload: () => load(true),
  };
}

export type LoadStatus = "loading" | "ready" | "failed";

export function useWebsiteStudyRows() {
  const session = useSessionStore();
  const rows = shallowRef<StudyRow[]>([]);
  const profiles = shallowRef<readonly Profile[]>([]);
  const status = shallowRef<LoadStatus>("loading");
  const error = shallowRef<unknown>(null);
  let controller: AbortController | null = null;

  /** Read the rows; shown rows stay until the answer comes, a failed first read shows the loading again. */
  async function load(): Promise<void> {
    controller?.abort();
    const own = new AbortController();
    controller = own;
    if (status.value === "failed") status.value = "loading";
    try {
      const answer = await studyViewsApi.rows(own.signal);
      if (own.signal.aborted) return;
      rows.value = answer.rows;
      profiles.value = answer.profiles;
      error.value = null;
      status.value = "ready";
    } catch (caught) {
      if (own.signal.aborted || isAbort(caught)) return;
      error.value = caught;
      if (status.value !== "ready") status.value = "failed";
    }
  }

  void load();
  watch(() => session.epoch, () => void load());
  onScopeDispose(() => controller?.abort());

  return { rows, profiles, status, error, reload: load };
}
