import { ref, shallowRef, watch, type Ref, type ShallowRef } from "vue";
import { failureOf, type ActionFailure } from "../../study-views/study";

/** The preview of the local server for the current input of a dialog. */
export interface Preview<O> {
  /** The answer for the current input; null without input, while it loads, or after a failure. Actions use it. */
  data: ShallowRef<O | null>;
  /** Whether the answer for the current input is still to come. */
  loading: Ref<boolean>;
  /** Why the preview of the current input failed, with what the local server said about it, or null. */
  error: Ref<ActionFailure | null>;
  /**
   * What the dialog shows: the answer of the last input that settled, kept while the answer for a
   * newer input loads, when the dialog marks it as updating; null without input. Never the answer
   * of an input that changed before its answer arrived.
   */
  shown: ShallowRef<O | null>;
  /** The failure of the last input that settled, kept like `shown`. */
  shownError: Ref<ActionFailure | null>;
}

/**
 * A preview of the local server for the input of a dialog, such as a new table or the rows that
 * a draft review target matches. It asks again whenever the input changes, with one request at a
 * time: an input that changes during a request is asked for when that request ends, and only the
 * answer for the current input is kept. A null input clears the preview.
 *
 * While an answer loads, the dialog shows the last settled answer marked as updating, so that it
 * neither empties and fills again nor announces the same message again at every key. A failure
 * starts with `lead`, such as `The rows could not be matched.`, unless the message of the local
 * server says what could not be previewed.
 */
export function usePreview<I, O>(
  input: () => I | null,
  load: (value: I) => Promise<O>,
  lead = "",
): Preview<O> {
  const data = shallowRef<O | null>(null);
  const loading = ref(false);
  const error = ref<ActionFailure | null>(null);
  const shown = shallowRef<O | null>(null);
  const shownError = ref<ActionFailure | null>(null);
  let wanted: I | null = null;
  let version = 0;
  let running = false;

  async function drain(): Promise<void> {
    running = true;
    while (wanted !== null) {
      const asked = version;
      const value: I = wanted;
      let answer: O | null = null;
      let failure: ActionFailure | null = null;
      try {
        answer = await load(value);
      } catch (caught) {
        failure = failureOf(caught, lead);
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
