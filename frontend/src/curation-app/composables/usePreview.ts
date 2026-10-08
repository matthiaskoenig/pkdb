import { ref, shallowRef, watch, type Ref, type ShallowRef } from "vue";
import { messageOf } from "../study";

/** The preview of the local server for the current input of a dialog. */
export interface Preview<O> {
  /** The answer for the current input; null without input, while it loads, or after a failure. Actions use it. */
  data: ShallowRef<O | null>;
  /** Whether the answer for the current input is still to come. */
  loading: Ref<boolean>;
  /** Why the preview of the current input failed, or null. */
  error: Ref<string | null>;
  /**
   * What the dialog shows: the answer of the last input that settled, kept while the answer for a
   * newer input loads, when the dialog marks it as updating; null without input. Never the answer
   * of an input that changed before its answer arrived.
   */
  shown: ShallowRef<O | null>;
  /** The failure of the last input that settled, kept like `shown`. */
  shownError: Ref<string | null>;
}

/**
 * A preview of the local server for the input of a dialog, such as a new table or the rows that
 * a draft review target matches. It asks again whenever the input changes, with one request at a
 * time: an input that changes during a request is asked for when that request ends, and only the
 * answer for the current input is kept. A null input clears the preview.
 *
 * While an answer loads, the dialog shows the last settled answer marked as updating, so that it
 * neither empties and fills again nor announces the same message again at every key.
 */
export function usePreview<I, O>(input: () => I | null, load: (value: I) => Promise<O>): Preview<O> {
  const data = shallowRef<O | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const shown = shallowRef<O | null>(null);
  const shownError = ref<string | null>(null);
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
      data.value = shown.value = answer;
      error.value = shownError.value = failure;
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
      if (wanted === null) {
        shown.value = null;
        shownError.value = null;
      } else if (!running) void drain();
    },
    { immediate: true },
  );
  return { data, loading, error, shown, shownError };
}
