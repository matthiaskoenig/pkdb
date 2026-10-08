import { getCurrentScope, onScopeDispose, ref, shallowRef, watch, type Ref, type ShallowRef } from "vue";
import { messageOf } from "../study";

/** The preview of the local server for the current input of a dialog. */
export interface Preview<O> {
  /** The answer for the current input; null without input, while it loads, or after a failure. */
  data: ShallowRef<O | null>;
  /** Whether the answer for the current input is still to come. */
  loading: Ref<boolean>;
  /** Why the preview of the current input failed, or null. */
  error: Ref<string | null>;
}

/**
 * A preview of the local server for the input of a dialog, such as a new table or the rows that
 * a draft review target matches. It asks again whenever the input changes, with one request at a
 * time: an input that changes during a request is asked for when that request ends, and only the
 * answer for the current input is kept. A null input clears the preview.
 */
export function usePreview<I, O>(input: () => I | null, load: (value: I) => Promise<O>): Preview<O> {
  const data = shallowRef<O | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  let wanted: I | null = null;
  let version = 0;
  let running = false;

  async function drain(): Promise<void> {
    running = true;
    while (wanted !== null) {
      const asked = version;
      const value: I = wanted;
      let answer: O | null = null;
      let failure: string | null = null;
      try {
        answer = await load(value);
      } catch (caught) {
        failure = messageOf(caught);
      }
      // The input changed meanwhile: ask for the newest one, if any.
      if (asked !== version) continue;
      data.value = answer;
      error.value = failure;
      wanted = null;
    }
    running = false;
    loading.value = false;
  }

  watch(
    () => {
      const value = input();
      return value === null ? null : JSON.stringify(value);
    },
    () => {
      version += 1;
      wanted = input();
      data.value = null;
      error.value = null;
      loading.value = wanted !== null;
      if (!running && wanted !== null) void drain();
    },
    { immediate: true },
  );
  return { data, loading, error };
}

/** How long a dialog keeps showing the last answer of a preview while the next one loads. */
export const PREVIEW_HOLD_MS = 100;

/** A preview as a dialog shows it; see `useShownPreview`. */
export interface ShownPreview<O> {
  data: Readonly<Ref<O | null>>;
  error: Readonly<Ref<string | null>>;
}

/**
 * What a dialog shows of a preview: the answer for the current input and its failure, or, while
 * that answer loads, the last ones for at most `holdMs`. The local server usually answers within
 * milliseconds, so its answer replaces the last one without an empty state in between, and the
 * messages of a field neither animate nor are announced again at every key. Whether an action
 * can run is decided on `preview.data`, which is null while the answer for the current input loads.
 */
export function useShownPreview<O>(preview: Preview<O>, holdMs = PREVIEW_HOLD_MS): ShownPreview<O> {
  const data = shallowRef<O | null>(preview.data.value);
  const error = ref<string | null>(preview.error.value);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function show(answer: O | null, failure: string | null): void {
    data.value = answer;
    error.value = failure;
  }

  watch([preview.data, preview.error, preview.loading], ([answer, failure, loading]) => {
    clearTimeout(timer);
    timer = loading ? setTimeout(() => show(null, null), holdMs) : undefined;
    if (!loading) show(answer, failure);
  });
  if (getCurrentScope()) onScopeDispose(() => clearTimeout(timer));
  return { data, error };
}
