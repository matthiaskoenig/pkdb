import { onScopeDispose, ref, shallowRef, watch, type Ref, type ShallowRef } from "vue";
import { isAbort } from "../errors";
import { failureOf, type ActionFailure } from "../study";

export interface Loaded<T, V> {
  /**
   * The last answer with its key and the value of `changed` that it was loaded for, such as the
   * study page whose targets match its rows; it stays while the same key loads again.
   */
  data: ShallowRef<{ key: string; content: T; version: V } | null>;
  /** Why the last load failed, with what the local server said about it. */
  error: Ref<ActionFailure | null>;
  /** Whether the key loads without an answer to show meanwhile. */
  loading: Ref<boolean>;
  /** Load the current key again, such as after a failure. */
  reload: () => Promise<void>;
}

/**
 * Loads `read(key, signal)` when `key` changes and when `changed` does, such as the detail of the
 * open study, whose ETag-revalidated resources may have changed with it. `signal` aborts when a
 * newer load starts and when the component unmounts: the answers of such a load are dropped, and
 * so are loads aborted because the study closed, without a failure. A failure starts with
 * `lead(key)`, such as `outputs_Tab2.tsv could not be loaded.`, unless the message of the server
 * says what could not be read.
 */
export function useLoaded<T, V = unknown>(
  key: () => string | null,
  read: (key: string, signal: AbortSignal) => Promise<T>,
  changed: () => V,
  lead: (key: string) => string,
): Loaded<T, V> {
  // Shallow: a table of thousands of rows needs no deep reactivity.
  const data = shallowRef<{ key: string; content: T; version: V } | null>(null);
  const error = ref<ActionFailure | null>(null);
  const loading = ref(false);
  let request = 0;
  /** Aborts the read of the last load. */
  let controller: AbortController | null = null;

  async function load(name: string | null, version: V): Promise<void> {
    const current = ++request;
    controller?.abort();
    controller = null;
    error.value = null;
    if (data.value?.key !== name) data.value = null;
    if (name === null) {
      loading.value = false;
      return;
    }
    loading.value = data.value === null;
    const { signal } = (controller = new AbortController());
    try {
      const content = await read(name, signal);
      if (current === request && !signal.aborted) data.value = { key: name, content, version };
    } catch (caught) {
      if (current === request && !signal.aborted && !isAbort(caught)) error.value = failureOf(caught, lead(name));
    } finally {
      if (current === request) loading.value = false;
    }
  }

  watch([key, changed], ([name, version]) => void load(name, version), { immediate: true });
  onScopeDispose(() => controller?.abort());
  return { data, error, loading, reload: () => load(key(), changed()) };
}
